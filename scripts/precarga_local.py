"""Construye el índice precargado en local (exploracion/blobs/indice/procesos.json.gz).

Uso:
    uv run python scripts/precarga_local.py                 # prueba: 200 detalles, 40 páginas
    uv run python scripts/precarga_local.py --completa      # todo (~5.500 llamadas, horas)

Es incremental: si ya existe un índice, reutiliza el detalle conocido y solo pide lo nuevo.
"""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server.contexto import contexto  # noqa: E402
from mp_core.giros import giro  # noqa: E402
from mp_core.indice import Indice  # noqa: E402
from mp_core.precarga import precargar  # noqa: E402


def main():
    logging.basicConfig(level=logging.WARNING)
    completa = "--completa" in sys.argv
    ctx = contexto()
    previo = Indice.cargar(ctx.blobs)
    print(f"Índice previo: {previo.resumen()}")
    giros = [g for p in ctx.perfiles.values() for n in p.giros if (g := giro(n))]
    t0 = time.time()
    nuevo = precargar(
        ctx.repo.lic,
        ctx.repo.ca,
        previo,
        giros,
        max_detalles_lic=6_000 if completa else 200,
        max_paginas_ca=400 if completa else 40,
        max_detalles_ca=300 if completa else 60,
        avance=lambda m: print(f"  {m} · {time.time() - t0:.0f}s · cupo {ctx.cupo.usado()}"),
    )
    nuevo.guardar(ctx.blobs)
    print(f"\nÍndice nuevo: {nuevo.resumen()}")
    print(f"Llamadas usadas: {ctx.cupo.usado()} · {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
