"""Extrae el texto de un adjunto local y muestra el resultado.

Uso:
    uv run python scripts/probar_documento.py ruta/al/archivo.pdf
    uv run --extra aws python scripts/probar_documento.py archivo.pdf --ocr   # con Textract

Con --ocr usa Amazon Textract (~USD 0,0015 por página escaneada). Necesita sesión AWS activa:
    aws sso login --profile <perfil> && export AWS_PROFILE=<perfil>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mp_core.documentos import TextractOCR, extraer  # noqa: E402


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ruta = Path(sys.argv[1])
    ocr = TextractOCR() if "--ocr" in sys.argv else None
    for doc in extraer(ruta.name, ruta.read_bytes(), ocr=ocr):
        print(
            f"\n== {doc.nombre} · {doc.formato} · calidad {doc.calidad} · "
            f"{len(doc.paginas)} página(s) · {doc.caracteres:,} caracteres"
        )
        for a in doc.advertencias:
            print(f"   ! {a}")
        for p in doc.paginas[:3]:
            print(f"\n   [página {p.numero} · {p.origen}]")
            print("   " + p.texto[:600].replace("\n", "\n   "))


if __name__ == "__main__":
    main()
