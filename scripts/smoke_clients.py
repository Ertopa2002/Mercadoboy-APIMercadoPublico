"""Prueba de humo de los clientes del core contra las APIs reales (4 llamadas).

Uso:
    uv run python scripts/smoke_clients.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from probe_licitaciones import cargar_ticket  # noqa: E402

from mp_core.clients import CompraAgilClient, LicitacionesClient  # noqa: E402
from mp_core.cupo import Cupo  # noqa: E402
from mp_core.store import MemoryStore  # noqa: E402


def main():
    ticket = cargar_ticket()
    cupo = Cupo(MemoryStore())
    lic = LicitacionesClient(ticket, cupo)
    ca = CompraAgilClient(ticket, cupo)

    activas = lic.activas()
    print(f"Licitaciones activas: {len(activas)} · ej. {activas[0].codigo} ({activas[0].tipo})")
    d = lic.detalle(activas[0].codigo)
    print(
        f"Detalle: {d.nombre[:60]} | ${d.monto} | {d.comprador.region} | "
        f"cierre en {d.dias_al_cierre()} días | {len(d.items)} ítems"
    )

    items, pag = ca.listar(regiones=[13], tamano=10)
    print(f"Compras Ágiles publicadas en RM: {pag.get('total_resultados')} · ej. {items[0].codigo}")
    det = ca.detalle("2793-1032-COT26")
    if det:
        print(
            f"2793-1032-COT26: ${det.monto} | entrega {det.plazo_entrega_dias} día(s) | "
            f"{len(det.items)} producto(s) en la API | docs: {[x.nombre for x in det.documentos]}"
        )
    print(f"\nCupo: {cupo.estado()}")


if __name__ == "__main__":
    main()
