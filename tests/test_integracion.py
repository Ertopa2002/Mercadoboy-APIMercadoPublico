"""Tests contra las APIs reales. Consumen cupo (~6 llamadas): correr a mano, de noche.

    uv run pytest -m integration

Se saltan solos si no hay MP_TICKET (variable de entorno o .env).
"""

import os
from pathlib import Path

import pytest

from mp_core.clients import CompraAgilClient, LicitacionesClient
from mp_core.cupo import Cupo
from mp_core.store import MemoryStore


def _ticket() -> str | None:
    if os.getenv("MP_TICKET"):
        return os.environ["MP_TICKET"]
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for linea in env.read_text().splitlines():
            if linea.startswith("MP_TICKET=") and linea.split("=", 1)[1].strip():
                return linea.split("=", 1)[1].strip()
    return None


TICKET = _ticket()
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not TICKET, reason="sin MP_TICKET"),
]


@pytest.fixture(scope="module")
def clientes():
    cupo = Cupo(MemoryStore())
    return LicitacionesClient(TICKET, cupo), CompraAgilClient(TICKET, cupo), cupo


def test_licitaciones_activas_y_detalle(clientes):
    lic, _, _ = clientes
    activas = lic.activas()
    assert len(activas) > 1000
    det = lic.detalle(activas[0].codigo)
    assert det and det.detalle_completo and det.comprador.organismo


def test_organismos(clientes):
    lic, _, _ = clientes
    assert len(lic.organismos()) > 500


def test_compra_agil_listado_y_detalle(clientes):
    _, ca, _ = clientes
    items, pag = ca.listar(regiones=[13], tamano=10)
    assert items and pag.get("total_resultados", 0) > 0
    det = ca.detalle(items[0].codigo)
    assert det and det.detalle_completo


def test_cupo_contabilizado(clientes):
    *_, cupo = clientes
    assert cupo.usado() >= 1
