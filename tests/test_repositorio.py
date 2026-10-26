from datetime import datetime

from mp_core.config import TZ
from mp_core.models import CompraAgil, Licitacion, Organismo
from mp_core.normalize import parse_fecha
from mp_core.repositorio import TTL_CERRADO, TTL_DETALLE, Repositorio, ttl_detalle
from mp_core.store import MemoryStore


class FakeLic:
    def __init__(self):
        self.llamadas = 0

    def detalle(self, codigo):
        self.llamadas += 1
        return Licitacion(
            codigo=codigo, nombre="X", fecha_cierre=parse_fecha("2026-11-06T15:00:00")
        )

    def activas(self):
        self.llamadas += 1
        return [Licitacion(codigo="1-1-LE26", nombre="A")]

    def organismos(self):
        self.llamadas += 1
        return [Organismo(codigo="7202", nombre="DGAC")]


class FakeCA:
    def __init__(self):
        self.llamadas = 0

    def detalle(self, codigo):
        self.llamadas += 1
        return CompraAgil(codigo=codigo, nombre="Y")


def test_detalle_usa_cache():
    lic = FakeLic()
    repo = Repositorio(MemoryStore(), lic, FakeCA())
    a = repo.licitacion("1705-26-L126")
    b = repo.licitacion("1705-26-L126")
    assert a == b and lic.llamadas == 1
    assert b.fecha_cierre == parse_fecha("2026-11-06T15:00:00")
    repo.licitacion("1705-26-L126", refrescar=True)
    assert lic.llamadas == 2


def test_invalidar():
    ca = FakeCA()
    repo = Repositorio(MemoryStore(), FakeLic(), ca)
    repo.compra_agil("1-1-COT26")
    repo.invalidar("1-1-COT26")
    repo.compra_agil("1-1-COT26")
    assert ca.llamadas == 2


def test_listas_en_cache():
    lic = FakeLic()
    repo = Repositorio(MemoryStore(), lic)
    assert repo.licitaciones_activas()[0].codigo == "1-1-LE26"
    assert repo.organismos()[0].nombre == "DGAC"
    repo.licitaciones_activas()
    repo.organismos()
    assert lic.llamadas == 2


def test_sin_cliente_y_sin_cache():
    repo = Repositorio(MemoryStore())
    assert repo.licitacion("x") is None and repo.compra_agil("x") is None


def test_ttl_detalle():
    ahora = datetime(2026, 10, 24, 12, tzinfo=TZ)
    abierta = Licitacion(codigo="a", nombre="a", fecha_cierre=parse_fecha("2026-11-06T15:00:00"))
    cerrada = Licitacion(codigo="b", nombre="b", fecha_cierre=parse_fecha("2026-10-20T15:00:00"))
    assert ttl_detalle(abierta, ahora) == TTL_DETALLE
    assert ttl_detalle(cerrada, ahora) == TTL_CERRADO


def test_guardar_desde_precarga():
    repo = Repositorio(MemoryStore())
    repo.guardar_licitacion(Licitacion(codigo="9-9-LP26", nombre="P"))
    assert repo.licitacion("9-9-LP26").nombre == "P"
