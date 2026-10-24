"""Exploración de la página de adjuntos de una licitación (ViewAttachment.aspx).

Uso:
    uv run python scripts/probe_adjuntos.py [codigo_licitacion]

2 peticiones a páginas públicas, con pausa. No descarga archivos todavía: lista qué adjuntos
hay y cómo se piden (controles del formulario). Guarda el HTML en exploracion/.
"""

import html as htmllib
import re
import sys
import time
from pathlib import Path

import httpx

OUT = Path("exploracion")
UA = "Mercadoboy-POC/0.1 (exploracion; contacto pcisterna@aptivia.net)"
FICHA = "https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx"
ATTACH = "https://www.mercadopublico.cl/Procurement/Modules/Attachment/"


def texto(fragmento: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragmento))).strip()


def main():
    OUT.mkdir(exist_ok=True)
    lic = sys.argv[1] if len(sys.argv) > 1 else "1705-26-L126"
    with httpx.Client(headers={"User-Agent": UA}, timeout=60, follow_redirects=True) as c:
        ficha = c.get(FICHA, params={"idlicitacion": lic}).text
        time.sleep(3)
        m = re.search(r"ViewAttachment\.aspx\?enc=([^'\"&]+)", htmllib.unescape(ficha))
        if not m:
            sys.exit("No se encontró el enlace a adjuntos en la ficha")
        r = c.get(f"{ATTACH}ViewAttachment.aspx?enc={m.group(1)}")
        print(f"ViewAttachment -> HTTP {r.status_code}, {len(r.text):,} caracteres")
        (OUT / f"adjuntos_{lic}.html").write_text(r.text)

    h = r.text
    filas = re.findall(r"<tr[^>]*>(.*?)</tr>", h, flags=re.S | re.I)
    print(f"\nFilas de tabla: {len(filas)}")
    for f in filas[:20]:
        celdas = [texto(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", f, flags=re.S | re.I)]
        controles = re.findall(
            r'<input[^>]+name="([^"]+)"[^>]*type="image"|type="image"[^>]+name="([^"]+)"', f
        )
        if any(celdas):
            print(f" · {' | '.join(c for c in celdas if c)[:150]}")
            nombres = [a or b for a, b in controles]
            if nombres:
                print(f"     controles: {nombres[:3]}")
    print("\nCampos ocultos del formulario:")
    for n in re.findall(r'<input type="hidden" name="([^"]+)"', h)[:10]:
        print(f" · {n}")


if __name__ == "__main__":
    main()
