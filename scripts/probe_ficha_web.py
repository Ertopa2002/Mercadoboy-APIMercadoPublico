"""Exploración de la ficha web pública (adjuntos) de una licitación y una Compra Ágil.

Uso:
    uv run python scripts/probe_ficha_web.py [codigo_licitacion]

Solo lectura de páginas públicas, pocas peticiones y con pausa. Guarda el HTML en
exploracion/ficha_*.html y lista los enlaces que parecen adjuntos. También guarda robots.txt.
No usa el ticket.
"""

import json
import re
import sys
import time
from pathlib import Path

import httpx

OUT = Path("exploracion")
UA = "Mercadoboy-POC/0.1 (exploracion; contacto pcisterna@aptivia.net)"
PATRONES = re.compile(
    r"(Attachment|ViewAttachment|adjunto|Adjunto|enc=|\.pdf|\.docx?|\.xlsx?|\.zip|descarga|documento)",
)


def bajar(c: httpx.Client, url: str, nombre: str) -> str:
    r = c.get(url)
    print(f"   GET {url[:110]} -> HTTP {r.status_code}, {len(r.text):,} car. -> {str(r.url)[:80]}")
    (OUT / nombre).write_text(r.text)
    time.sleep(3)
    return r.text


def enlaces(html: str, max_n: int = 25) -> None:
    vistos = set()
    for m in re.finditer(r"""(?:href|src|onclick|action)\s*=\s*["']([^"']+)["']""", html):
        v = m.group(1)
        if PATRONES.search(v) and v not in vistos:
            vistos.add(v)
            print(f"     · {v[:160]}")
            if len(vistos) >= max_n:
                break
    if not vistos:
        print("     (sin enlaces de adjuntos; la página puede cargar datos por JavaScript)")
    apis = set(re.findall(r"https?://[a-zA-Z0-9.-]*mercadopublico\.cl/[^\s\"'<>]{0,80}", html))
    if apis:
        print("   URLs de mercadopublico.cl dentro del HTML:")
        for a in sorted(apis)[:15]:
            print(f"     · {a}")


def main():
    OUT.mkdir(exist_ok=True)
    lic = sys.argv[1] if len(sys.argv) > 1 else "1705-26-L126"
    ca = None
    ca_listado = OUT / "ca_listado.json"
    if ca_listado.exists():
        for it in json.loads(ca_listado.read_text())["payload"]["items"]:
            if it.get("documentos"):
                ca = it
                break

    with httpx.Client(headers={"User-Agent": UA}, timeout=60, follow_redirects=True) as c:
        print("0) robots.txt")
        txt = bajar(c, "https://www.mercadopublico.cl/robots.txt", "robots_mercadopublico.txt")
        for linea in txt.splitlines()[:30]:
            print(f"     {linea}")

        print(f"\n1) Ficha de licitación {lic}")
        url = f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={lic}"
        enlaces(bajar(c, url, f"ficha_lic_{lic}.html"))

        if ca:
            print(f"\n2) Compra Ágil {ca['codigo']} · documentos según la API:")
            for d in ca["documentos"][:5]:
                print(f"     · {d}")
            print(f"   links.detalle: {ca.get('links', {}).get('detalle')}")
            url = f"https://buscador.mercadopublico.cl/ficha?code={ca['codigo']}"
            enlaces(bajar(c, url, f"ficha_ca_{ca['codigo']}.html"))
        else:
            print("\n2) Sin Compra Ágil con documentos en exploracion/ca_listado.json")


if __name__ == "__main__":
    main()
