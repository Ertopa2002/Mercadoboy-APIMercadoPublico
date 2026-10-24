"""Muestra de productos de Compras Ágiles de alimentos para probar la extracción con IA
de marca, "o similar" y vencimiento desde la descripción.

Uso:
    uv run python scripts/muestra_productos_ca.py [max_compras]

Revisa 4 páginas del listado (200 compras), filtra por palabras de alimentos en el nombre y
pide el detalle de hasta 20 (por defecto). Gasta ~24 llamadas y tarda ~3 minutos.
Guarda evals/muestra_productos_ca.json (sí se versiona: es insumo de evaluación).
"""

import json
import sys
import time
import unicodedata
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from probe_licitaciones import cargar_ticket  # noqa: E402

BASE = "https://api2.mercadopublico.cl"
PALABRAS = [
    "aliment",
    "abarrote",
    "congelad",
    "leche",
    "agua mineral",
    "jugo",
    "cafe",
    "te ",
    "azucar",
    "galleta",
    "colacion",
    "pan ",
    "carne",
    "pollo",
    "fruta",
    "verdura",
    "yogur",
    "queso",
    "arroz",
    "aceite",
    "conserva",
    "cafeteria",
    "snack",
    "coffee",
    "comestible",
]


def normal(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c)) + " "


def main():
    maximo = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    headers = {"ticket": cargar_ticket(), "Accept": "application/json"}
    candidatas = []
    with httpx.Client(base_url=BASE, headers=headers, timeout=90) as c:
        for pagina in range(1, 5):
            r = c.get(
                "/v2/compra-agil",
                params={
                    "estado": "publicada",
                    "tamano_pagina": 50,
                    "numero_pagina": pagina,
                    "ordenar_por": "FechaPublicacion",
                },
            )
            time.sleep(1)
            r.raise_for_status()
            for it in r.json()["payload"]["items"]:
                if any(p in normal(it["nombre"]) for p in PALABRAS):
                    candidatas.append(it["codigo"])
        print(f"{len(candidatas)} de alimentos en 200; detalle de {min(maximo, len(candidatas))}")

        muestra = []
        for codigo in candidatas[:maximo]:
            r = c.get(f"/v2/compra-agil/{codigo}")
            time.sleep(1)
            if r.status_code != 200:
                print(f"  {codigo}: HTTP {r.status_code}")
                continue
            p = r.json()["payload"]
            muestra.append(
                {
                    "codigo": codigo,
                    "nombre": p.get("nombre"),
                    "descripcion": p.get("descripcion"),
                    "productos": [
                        {
                            k: x.get(k)
                            for k in (
                                "codigo_producto",
                                "nombre",
                                "descripcion",
                                "cantidad",
                                "unidad_medida",
                            )
                        }
                        for x in p.get("productos_solicitados") or []
                    ],
                }
            )
            print(f"  {codigo}: {len(muestra[-1]['productos'])} prod. · {p.get('nombre', '')[:45]}")

    destino = Path("evals/muestra_productos_ca.json")
    destino.write_text(json.dumps(muestra, ensure_ascii=False, indent=2))
    total = sum(len(m["productos"]) for m in muestra)
    print(f"\n{len(muestra)} compras, {total} productos -> {destino}")


if __name__ == "__main__":
    main()
