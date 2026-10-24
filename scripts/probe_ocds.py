"""Exploración de la API de datos abiertos OCDS de ChileCompra: ¿trae enlaces a documentos?

Uso:
    uv run python scripts/probe_ocds.py [codigo_licitacion]

Prueba rutas candidatas (la documentación del portal requiere JavaScript), pocas peticiones
y con pausa. Guarda la primera respuesta JSON en exploracion/ocds_<codigo>.json.
"""

import json
import sys
import time
from pathlib import Path

import httpx

OUT = Path("exploracion")
UA = "Mercadoboy-POC/0.1 (exploracion; contacto pcisterna@aptivia.net)"
CANDIDATAS = [
    "https://apis.mercadopublico.cl/OCDS/data/record/{c}",
    "https://apis.mercadopublico.cl/OCDS/data/tender/{c}",
]


def documentos(obj, ruta=""):
    """Recorre el JSON y devuelve (ruta, documento) de cada lista 'documents'."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "documents" and isinstance(v, list):
                for d in v:
                    yield f"{ruta}.{k}", d
            else:
                yield from documentos(v, f"{ruta}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from documentos(v, f"{ruta}[{i}]")


def main():
    OUT.mkdir(exist_ok=True)
    # Por defecto: una licitación activa antigua (OCDS puede tardar en publicar las nuevas)
    codigo = sys.argv[1] if len(sys.argv) > 1 else "1116005-7-LE26"
    with httpx.Client(headers={"User-Agent": UA}, timeout=60, follow_redirects=True) as c:
        for plantilla in CANDIDATAS:
            url = plantilla.format(c=codigo)
            try:
                r = c.get(url)
            except httpx.HTTPError as e:
                print(f"{url}\n   error: {e}")
                continue
            tipo = r.headers.get("content-type", "")
            print(f"{url}\n   HTTP {r.status_code} · {tipo} · {len(r.content):,} bytes")
            time.sleep(2)
            if r.status_code == 200 and "json" in tipo:
                data = r.json()
                if isinstance(data, dict) and data.get("status") == 404:
                    print(f"   sin resultados: {data.get('detail')}")
                    continue
                (OUT / f"ocds_{codigo}.json").write_text(
                    json.dumps(data, ensure_ascii=False, indent=2)
                )
                docs = list(documentos(data))
                print(f"   documentos encontrados: {len(docs)}")
                for ruta, d in docs[:10]:
                    print(
                        f"   · {ruta}: {d.get('title') or d.get('description')} -> {d.get('url')}"
                    )
                break


if __name__ == "__main__":
    main()
