import io
import zipfile

import docx
import openpyxl
import pymupdf

from mp_core.documentos import TextractOCR, extraer


def pdf_bytes(paginas_texto: list[str | None]) -> bytes:
    """None = página 'escaneada' (solo un rectángulo, sin texto)."""
    d = pymupdf.open()
    for t in paginas_texto:
        p = d.new_page()
        if t:
            p.insert_text((72, 72), t, fontsize=11)
        else:
            p.draw_rect(pymupdf.Rect(50, 50, 300, 300), fill=(0.5, 0.5, 0.5))
    return d.tobytes()


TEXTO = "BASES ADMINISTRATIVAS. Garantia de seriedad de la oferta: 5% del monto. " * 2


class FakeOCR:
    def __init__(self):
        self.llamadas = 0

    def texto(self, imagen_png):
        assert imagen_png[:4] == b"\x89PNG"
        self.llamadas += 1
        return "200 Unidad galleta dulce Costa obsesion bolsa 85 grs o similar"


def test_pdf_con_texto():
    [doc] = extraer("bases.pdf", pdf_bytes([TEXTO, TEXTO]))
    assert doc.formato == "pdf" and doc.calidad == "ok" and not doc.necesita_ocr
    assert len(doc.paginas) == 2 and "seriedad" in doc.paginas[0].texto
    assert "[bases.pdf · página 2]" in doc.texto_completo


def test_pdf_escaneado_sin_ocr():
    [doc] = extraer("crp.pdf", pdf_bytes([None, None]))
    assert doc.necesita_ocr and doc.calidad == "sin_texto"
    assert any("OCR" in a for a in doc.advertencias)


def test_pdf_mixto_con_ocr():
    ocr = FakeOCR()
    [doc] = extraer("crp.pdf", pdf_bytes([TEXTO, None]), ocr=ocr)
    assert ocr.llamadas == 1
    assert doc.paginas[1].origen == "ocr" and "Costa" in doc.paginas[1].texto
    assert doc.calidad == "ok"


def test_pdf_danado():
    [doc] = extraer("x.pdf", b"%PDF-1.4 basura")
    assert doc.calidad == "sin_texto"


def test_docx():
    d = docx.Document()
    d.add_paragraph("Formulario N°1 Identificación del oferente")
    t = d.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Producto", "Cantidad"
    buf = io.BytesIO()
    d.save(buf)
    [doc] = extraer("anexo.docx", buf.getvalue())
    assert "Formulario" in doc.paginas[0].texto and "Producto | Cantidad" in doc.paginas[0].texto


def test_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Productos"
    ws.append(["Cantidad", "Producto"])
    ws.append([200, "galleta dulce gretel"])
    buf = io.BytesIO()
    wb.save(buf)
    [doc] = extraer("detalle.xlsx", buf.getvalue())
    assert "Hoja: Productos" in doc.paginas[0].texto and "200 | galleta" in doc.paginas[0].texto


def test_zip_con_ruta_peligrosa():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("bases.pdf", pdf_bytes([TEXTO]))
        z.writestr("../../etc/passwd", "x")
        z.writestr("__MACOSX/._bases.pdf", "x")
        z.writestr("notas.txt", "Muestras: entregar en bodega central")
    docs = extraer("adjuntos.zip", buf.getvalue())
    nombres = [d.nombre for d in docs]
    assert "adjuntos.zip/bases.pdf" in nombres and "adjuntos.zip/notas.txt" in nombres
    assert any("ruta no permitida" in a for d in docs for a in d.advertencias)


def test_formato_no_soportado_y_tamano():
    [doc] = extraer("viejo.doc", b"\xd0\xcf\x11\xe0")
    assert doc.calidad == "sin_texto" and "no soportado" in doc.advertencias[0]
    [doc] = extraer("enorme.pdf", b"0" * (50 * 1024 * 1024 + 1))
    assert "tamaño máximo" in doc.advertencias[0]


def test_textract_ocr_con_cliente_falso():
    class Cliente:
        def detect_document_text(self, Document):  # noqa: N803
            return {
                "Blocks": [
                    {"BlockType": "LINE", "Text": "linea 1"},
                    {"BlockType": "WORD", "Text": "x"},
                    {"BlockType": "LINE", "Text": "linea 2"},
                ]
            }

    assert TextractOCR(cliente=Cliente()).texto(b"\x89PNG") == "linea 1\nlinea 2"
