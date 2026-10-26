"""Extracción de texto de adjuntos (bases, anexos, formularios) entregados por el usuario.

ADR 0008: los adjuntos no se descargan de Mercado Público; llegan por subida manual. Este
módulo los convierte en texto por página para que la ficha de análisis cite documento y página.

Formatos: PDF (con texto o escaneado), Word (.docx), Excel (.xlsx), texto (.txt/.csv) y ZIP
con cualquiera de ellos. Los PDF escaneados se pasan por OCR si se entrega un motor (Textract).
Los archivos son datos no confiables: límites de tamaño, sin rutas peligrosas, nada se ejecuta.
"""

import io
import zipfile
from pathlib import PurePosixPath
from typing import Literal, Protocol

from pydantic import BaseModel, Field

MAX_BYTES_ARCHIVO = 50 * 1024 * 1024
MAX_BYTES_ZIP_TOTAL = 200 * 1024 * 1024
MAX_ARCHIVOS_ZIP = 50
MIN_CARACTERES_PAGINA = 40  # menos que esto en una página de PDF = probablemente escaneada
MAX_PAGINAS_OCR = 60
DPI_OCR = 200


class OCR(Protocol):
    def texto(self, imagen_png: bytes) -> str: ...


class Pagina(BaseModel):
    numero: int
    texto: str
    origen: Literal["texto", "ocr", "sin_texto"] = "texto"


class DocumentoTexto(BaseModel):
    nombre: str
    formato: str
    paginas: list[Pagina] = Field(default_factory=list)
    calidad: Literal["ok", "baja", "sin_texto"] = "ok"
    necesita_ocr: bool = False
    advertencias: list[str] = Field(default_factory=list)

    @property
    def texto_completo(self) -> str:
        """Texto con marcas de página, listo para que la IA cite '[documento, página N]'."""
        return "\n\n".join(f"[{self.nombre} · página {p.numero}]\n{p.texto}" for p in self.paginas)

    @property
    def caracteres(self) -> int:
        return sum(len(p.texto) for p in self.paginas)


def _calidad(doc: DocumentoTexto) -> DocumentoTexto:
    vacias = sum(1 for p in doc.paginas if p.origen == "sin_texto")
    if not doc.paginas or vacias == len(doc.paginas):
        doc.calidad = "sin_texto"
    elif vacias:
        doc.calidad = "baja"
        doc.advertencias.append(f"{vacias} de {len(doc.paginas)} páginas sin texto legible")
    return doc


def _pdf(nombre: str, data: bytes, ocr: OCR | None) -> DocumentoTexto:
    import pymupdf

    doc = DocumentoTexto(nombre=nombre, formato="pdf")
    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
    except Exception:  # noqa: BLE001 - PDF corrupto o protegido
        doc.advertencias.append("No se pudo abrir el PDF (dañado o protegido)")
        doc.calidad = "sin_texto"
        return doc
    ocr_usadas = 0
    for i, page in enumerate(pdf, start=1):
        texto = page.get_text("text").strip()
        if len(texto) >= MIN_CARACTERES_PAGINA:
            doc.paginas.append(Pagina(numero=i, texto=texto))
            continue
        doc.necesita_ocr = True
        if ocr and ocr_usadas < MAX_PAGINAS_OCR:
            png = page.get_pixmap(dpi=DPI_OCR).tobytes("png")
            texto_ocr = ocr.texto(png).strip()
            ocr_usadas += 1
            origen = "ocr" if texto_ocr else "sin_texto"
            doc.paginas.append(Pagina(numero=i, texto=texto_ocr, origen=origen))
        else:
            doc.paginas.append(Pagina(numero=i, texto=texto, origen="sin_texto"))
    if doc.necesita_ocr and not ocr:
        doc.advertencias.append("PDF escaneado: requiere OCR para leer las páginas sin texto")
    if ocr_usadas >= MAX_PAGINAS_OCR:
        doc.advertencias.append(f"OCR limitado a {MAX_PAGINAS_OCR} páginas")
    return _calidad(doc)


def _docx(nombre: str, data: bytes) -> DocumentoTexto:
    import docx

    d = docx.Document(io.BytesIO(data))
    partes = [p.text for p in d.paragraphs if p.text.strip()]
    for tabla in d.tables:
        for fila in tabla.rows:
            celdas = [c.text.strip() for c in fila.cells]
            if any(celdas):
                partes.append(" | ".join(celdas))
    doc = DocumentoTexto(nombre=nombre, formato="docx")
    doc.paginas.append(Pagina(numero=1, texto="\n".join(partes), origen="texto"))
    doc.advertencias.append("Word no tiene páginas fijas: se cita como página 1")
    return _calidad(doc)


def _xlsx(nombre: str, data: bytes) -> DocumentoTexto:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    doc = DocumentoTexto(nombre=nombre, formato="xlsx")
    for i, hoja in enumerate(wb.worksheets, start=1):
        filas = []
        for fila in hoja.iter_rows(values_only=True):
            valores = ["" if v is None else str(v) for v in fila]
            if any(v.strip() for v in valores):
                filas.append(" | ".join(valores).rstrip(" |"))
        doc.paginas.append(Pagina(numero=i, texto=f"Hoja: {hoja.title}\n" + "\n".join(filas)))
    wb.close()
    return _calidad(doc)


def _texto_plano(nombre: str, data: bytes, formato: str) -> DocumentoTexto:
    texto = data.decode("utf-8", errors="replace")
    doc = DocumentoTexto(nombre=nombre, formato=formato)
    doc.paginas.append(Pagina(numero=1, texto=texto))
    return _calidad(doc)


def _ruta_segura(nombre: str) -> bool:
    p = PurePosixPath(nombre.replace("\\", "/"))
    return not p.is_absolute() and ".." not in p.parts and not nombre.startswith("__MACOSX")


def _zip(nombre: str, data: bytes, ocr: OCR | None) -> list[DocumentoTexto]:
    docs: list[DocumentoTexto] = []
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return [
            DocumentoTexto(
                nombre=nombre, formato="zip", calidad="sin_texto", advertencias=["ZIP dañado"]
            )
        ]
    entradas = [i for i in z.infolist() if not i.is_dir()]
    total = 0
    omitidos = []
    for info in entradas[:MAX_ARCHIVOS_ZIP]:
        if not _ruta_segura(info.filename):
            omitidos.append(f"{info.filename} (ruta no permitida)")
            continue
        total += info.file_size
        if total > MAX_BYTES_ZIP_TOTAL:
            omitidos.append("resto del ZIP (supera el tamaño máximo)")
            break
        interno = f"{nombre}/{info.filename}"
        if info.filename.lower().endswith(".zip"):
            omitidos.append(f"{info.filename} (ZIP dentro de ZIP)")
            continue
        docs += extraer(interno, z.read(info), ocr=ocr, permitir_zip=False)
    if len(entradas) > MAX_ARCHIVOS_ZIP:
        omitidos.append(f"{len(entradas) - MAX_ARCHIVOS_ZIP} archivos sobre el máximo")
    if omitidos and docs:
        docs[0].advertencias.append("Omitidos del ZIP: " + "; ".join(omitidos))
    elif omitidos:
        docs.append(
            DocumentoTexto(
                nombre=nombre,
                formato="zip",
                calidad="sin_texto",
                advertencias=["Omitidos del ZIP: " + "; ".join(omitidos)],
            )
        )
    return docs


def extraer(
    nombre: str, data: bytes, ocr: OCR | None = None, permitir_zip: bool = True
) -> list[DocumentoTexto]:
    """Extrae el texto de un archivo. Devuelve una lista (un ZIP puede traer varios)."""
    if len(data) > MAX_BYTES_ARCHIVO:
        return [
            DocumentoTexto(
                nombre=nombre,
                formato="?",
                calidad="sin_texto",
                advertencias=["Archivo sobre el tamaño máximo (50 MB)"],
            )
        ]
    ext = PurePosixPath(nombre.lower()).suffix
    if ext == ".pdf" or data[:5] == b"%PDF-":
        return [_pdf(nombre, data, ocr)]
    if ext == ".zip" or (data[:2] == b"PK" and ext not in {".docx", ".xlsx", ".xlsm"}):
        if not permitir_zip:
            return []
        return _zip(nombre, data, ocr)
    if ext == ".docx":
        return [_docx(nombre, data)]
    if ext in {".xlsx", ".xlsm"}:
        return [_xlsx(nombre, data)]
    if ext in {".txt", ".csv"}:
        return [_texto_plano(nombre, data, ext[1:])]
    return [
        DocumentoTexto(
            nombre=nombre,
            formato=ext.lstrip(".") or "?",
            calidad="sin_texto",
            advertencias=[f"Formato no soportado ({ext or 'sin extensión'})"],
        )
    ]


class TextractOCR:
    """OCR con Amazon Textract (DetectDocumentText, síncrono, una imagen por página).

    ~USD 0,0015 por página. Requiere el extra `aws` (boto3) y permisos textract:DetectDocumentText.
    """

    def __init__(self, cliente=None, region: str = "us-east-1"):
        if cliente is None:
            import boto3

            cliente = boto3.client("textract", region_name=region)
        self.cliente = cliente

    def texto(self, imagen_png: bytes) -> str:
        r = self.cliente.detect_document_text(Document={"Bytes": imagen_png})
        return "\n".join(b["Text"] for b in r.get("Blocks", []) if b.get("BlockType") == "LINE")
