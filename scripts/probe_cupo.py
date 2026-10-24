"""Estimación de volumen diario para dimensionar el cupo (S1–S2).

Uso:
    uv run python scripts/probe_cupo.py

Gasta 2 llamadas: Compras Ágiles publicadas en las últimas 24 h y licitaciones publicadas ayer.
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from probe_licitaciones import cargar_ticket  # noqa: E402


def main():
    ticket = cargar_ticket()
    ahora = datetime.now(UTC)
    desde = (ahora - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hasta = ahora.strftime("%Y-%m-%dT%H:%M:%SZ")
    r = httpx.get(
        "https://api2.mercadopublico.cl/v2/compra-agil",
        params={"publicado_desde": desde, "publicado_hasta": hasta, "tamano_pagina": 10},
        headers={"ticket": ticket},
        timeout=60,
    )
    ca = r.json()["payload"]["paginacion"]["total_resultados"] if r.status_code == 200 else r.text
    print(f"Compras Ágiles publicadas en las últimas 24 h: {ca} (HTTP {r.status_code})")

    if "--solo-ca" in sys.argv:
        return
    ayer = (datetime.now(ZoneInfo("America/Santiago")) - timedelta(days=1)).strftime("%d%m%Y")
    r = httpx.get(
        "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json",
        params={"fecha": ayer, "estado": "publicada", "ticket": ticket},
        timeout=60,
    )
    lic = r.json().get("Cantidad") if r.status_code == 200 else r.text
    print(f"Licitaciones publicadas el {ayer}: {lic} (HTTP {r.status_code})")


if __name__ == "__main__":
    main()
