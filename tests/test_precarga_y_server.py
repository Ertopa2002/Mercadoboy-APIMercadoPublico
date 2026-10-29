from mcp_server import server
from mp_core.cupo import Cupo
from mp_core.giros import giro
from mp_core.indice import Indice, LocalBlobStore
from mp_core.models import CompraAgil, Comprador, Item, Licitacion, PerfilUsuario
from mp_core.normalize import parse_fecha
from mp_core.precarga import precargar
from mp_core.repositorio import Repositorio
from mp_core.store import MemoryStore


class FakeLic:
    def __init__(self):
        self.detalles = 0

    def activas(self):
        return [Licitacion(codigo=f"{i}-1-LE26", nombre=f"L{i}", estado="5") for i in range(5)]

    def detalle(self, codigo):
        self.detalles += 1
        return Licitacion(
            codigo=codigo,
            nombre="Compra de alimentos",
            estado="Publicada",
            detalle_completo=True,
            comprador=Comprador(region_codigo=13),
            fecha_cierre=parse_fecha("2030-01-01T15:00:00"),
        )

    def organismos(self):
        return []


class FakeCA:
    def __init__(self):
        self.detalles = 0

    def listar(self, pagina=1, tamano=50, ordenar_por=None, **_):
        items = [
            CompraAgil(
                codigo="1-1-COT26",
                nombre="ALIMENTOS OFICINA DE LA MUJER",
                estado="publicada",
                monto=3_790_000,
                comprador=Comprador(region_codigo=13, organismo="Muni Huechuraba"),
            ),
            CompraAgil(codigo="2-1-COT26", nombre="Traslado de escolares", estado="publicada"),
        ]
        return (items if pagina == 1 else []), {"total_paginas": 1}

    def detalle(self, codigo):
        self.detalles += 1
        return CompraAgil(
            codigo=codigo,
            nombre="ALIMENTOS OFICINA DE LA MUJER",
            estado="publicada",
            detalle_completo=True,
            items=[Item(codigo_onu="50181905")],
            comprador=Comprador(region_codigo=13, organismo="Muni Huechuraba"),
        )


def test_precarga_incremental():
    lic, ca = FakeLic(), FakeCA()
    giros = [giro("Venta Alimentos")]
    i1 = precargar(lic, ca, Indice(), giros, max_detalles_lic=3)
    assert sum(x.detalle_completo for x in i1.licitaciones) == 3
    assert ca.detalles == 1  # solo la de alimentos
    precargar(lic, ca, i1, giros, max_detalles_lic=10)
    assert lic.detalles == 5 and ca.detalles == 1  # reutiliza lo conocido


def test_indice_persistencia(tmp_path):
    blobs = LocalBlobStore(tmp_path)
    i = precargar(FakeLic(), FakeCA(), Indice(), [giro("Venta Alimentos")])
    i.guardar(blobs)
    j = Indice.cargar(blobs)
    assert j.resumen()["licitaciones"] == 5 and j.por_codigo("1-1-COT26")


class Ctx:
    def __init__(self, indice):
        self.store = MemoryStore()
        self.cupo = Cupo(self.store)
        self.repo = Repositorio(self.store, FakeLic(), FakeCA())
        self.perfiles = {"patricio": PerfilUsuario(usuario="patricio", giros=["Venta Alimentos"])}
        self._indice = indice

    def indice(self):
        return self._indice


def test_herramientas(monkeypatch):
    indice = precargar(FakeLic(), FakeCA(), Indice(), [giro("Venta Alimentos")])
    ctx = Ctx(indice)
    monkeypatch.setattr(server, "contexto", lambda: ctx)
    r = server.buscar_compras_agiles()
    assert r["total"] == 1 and r["resultados"][0]["codigo"] == "1-1-COT26"
    assert r["resultados"][0]["url_ficha"].endswith("1-1-COT26")
    r = server.buscar_licitaciones(regiones=[13])
    assert r["total"] == 5
    assert (
        server.buscar_compras_agiles(palabras_clave=["traslado"], solo_mis_rubros=False)["total"]
        == 1
    )
    d = server.detalle_compra_agil("1-1-cot26")
    assert d["codigo"] == "1-1-COT26" and d["items"]
    a = server.obtener_adjuntos("1-1-COT26")
    assert "url_ficha" in a and "instruccion" in a
    assert server.perfil_usuario()["detalle_giros"]
    assert "cupo" in server.estado_cupo()
