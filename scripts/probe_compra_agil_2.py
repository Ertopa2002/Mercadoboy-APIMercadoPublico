"""Segunda exploración de Compra Ágil: aísla el 504 de q+region y prueba cambio_desde en UTC.

Uso:
    uv run python scripts/probe_compra_agil_2.py

Gasta ~5 llamadas.
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from probe_compra_agil import BASE, get  # noqa: E402
from probe_licitaciones import cargar_ticket  # noqa: E402


def total(r: httpx.Response) -> str:
    if r.status_code != 200:
        return f"error {r.status_code}"
    return str(r.json()["payload"]["paginacion"]["total_resultados"])


def main():
    headers = {"ticket": cargar_ticket(), "Accept": "application/json"}
    ahora = datetime.now(UTC)
    desde = (ahora - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    pruebas = [
        ("q sola", {"estado": "publicada", "q": "alimentos", "tamano_pagina": 50}),
        ("region sola (10)", {"estado": "publicada", "region": 10, "tamano_pagina": 50}),
        ("q + 1 region", {"estado": "publicada", "q": "alimentos", "region": 10}),
        ("cambio_desde 3 h (UTC)", {"cambio_desde": desde, "tamano_pagina": 50}),
        ("ttl 3 h", {"ttl_cambio_ms": 3 * 3_600_000, "tamano_pagina": 50}),
    ]
    with httpx.Client(base_url=BASE, headers=headers, timeout=60) as c:
        for nombre, params in pruebas:
            print(f"\n{nombre}")
            r = get(c, "/v2/compra-agil", params)
            print(f"   resultados: {total(r)}")


if __name__ == "__main__":
    main()
