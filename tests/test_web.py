from datetime import datetime, timedelta

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from mp_core.config import TZ
from mp_core.indice import Indice
from mp_core.models import CompraAgil, Comprador, Documento, Item, Licitacion, PerfilUsuario
from web import api

HOY = datetime.now(TZ).date()  # relativo: los vencidos se ocultan


def _dt(dias: int) -> datetime:
    return datetime.combine(HOY + timedelta(days=dias), datetime.min.time(), TZ).replace(hour=15)


class Ctx:
    def __init__(self):
        rm = Comprador(
            organismo="Municipalidad de Huechuraba",
            region_codigo=13,
            region="Región Metropolitana de Santiago",
        )
        valpo = Comprador(
            organismo="Hospital Carlos van Buren", region_codigo=5, region="Región de Valparaíso"
        )
        self._ix = Indice(
            licitaciones=[
                Licitacion(
                    codigo="1-1-LE26",
                    tipo="LE",
                    nombre="Compra de alimentos para jardines",
                    estado="Publicada",
                    monto=12_000_000,
                    comprador=rm,
                    fecha_publicacion=_dt(0),
                    fecha_cierre=_dt(3),
                    detalle_completo=True,
                ),
                Licitacion(
                    codigo="2-2-L126",
                    tipo="L1",
                    nombre="Instalación eléctrica bodega",
                    estado="Publicada",
                    monto=900_000,
                    comprador=valpo,
                    fecha_publicacion=_dt(-2),
                    fecha_cierre=_dt(10),
                ),
            ],
            compras_agiles=[
                CompraAgil(
                    codigo="3-3-COT26",
                    nombre="Arriendo de baños químicos",
                    estado="publicada",
                    monto=2_000_000,
                    comprador=valpo,
                    fecha_publicacion=_dt(-1),
                    fecha_cierre=_dt(0),
                    items=[Item(codigo_onu="30201706", nombre="Baño portátil")],
                    documentos=[Documento(id="9", nombre="bases.pdf")],
                ),
            ],
        )
        self.perfiles = {
            "patricio": PerfilUsuario(
                usuario="patricio", giros=["Venta Alimentos", "Baños químicos"]
            )
        }
        self.store = None

    def indice(self):
        return self._ix


@pytest.fixture()
def ctx():
    api._cache.clear()
    return Ctx()


def test_buscar_con_perfil_filtra_por_giro(ctx):
    d = api.buscar(ctx, {"perfil": "patricio"})
    assert {r["codigo"] for r in d["resultados"]} == {"1-1-LE26", "3-3-COT26"}
    assert d["resultados"][0]["url_ficha"].startswith("https://")


def test_buscar_sin_perfil_y_filtros(ctx):
    assert api.buscar(ctx, {})["total"] == 3
    assert api.buscar(ctx, {"origen": "compra_agil"})["total"] == 1
    assert api.buscar(ctx, {"regiones": "5"})["total"] == 2
    assert api.buscar(ctx, {"monto_min": "1000000", "monto_max": "5000000"})["total"] == 1
    assert api.buscar(ctx, {"perfil": "patricio", "excluir": "jardines"})["total"] == 1
    assert api.buscar(ctx, {"q": "bodega"})["resultados"][0]["codigo"] == "2-2-L126"


def test_orden_y_paginacion(ctx):
    d = api.buscar(ctx, {"orden": "monto", "por_pagina": "2"})
    assert [r["codigo"] for r in d["resultados"]] == ["1-1-LE26", "3-3-COT26"]
    assert (
        api.buscar(ctx, {"orden": "monto", "por_pagina": "2", "pagina": "2"})["resultados"][0][
            "codigo"
        ]
        == "2-2-L126"
    )
    assert api.buscar(ctx, {"orden": "cierre"})["resultados"][0]["codigo"] == "3-3-COT26"


def test_estadisticas(ctx):
    e = api.estadisticas(ctx, {}, hoy=HOY)
    k = e["kpis"]
    assert (k["total"], k["licitaciones"], k["compras_agiles"]) == (3, 2, 1)
    assert k["cierran_hoy"] == 1 and k["cierran_7_dias"] == 2 and k["publicadas_hoy"] == 1
    assert k["monto_total"] == 14_900_000
    assert len(e["cierres_por_dia"]) == 14 and e["cierres_por_dia"][0]["compra_agil"] == 1
    assert e["por_region"][0] == {"nombre": "Región de Valparaíso", "total": 2, "monto": 2_900_000}
    assert sum(r["total"] for r in e["rangos_monto"]) == 3


def test_rutas_http_con_token(ctx):
    app = Starlette(routes=api.rutas("tok", ctx_fn=lambda: ctx))
    with TestClient(app) as cli:
        assert cli.get("/tok/").status_code == 200
        assert "Mercadoboy" in cli.get("/tok/").text
        assert cli.get("/tok/api/buscar?perfil=patricio").json()["total"] == 2
        assert cli.get("/tok/api/opciones").json()["perfiles"]["patricio"]["giros"]
        assert (
            cli.get("/tok/api/proceso/3-3-cot26").json()["documentos"][0]["nombre"] == "bases.pdf"
        )
        assert cli.get("/tok/api/proceso/NO-EXISTE").status_code == 404
        assert cli.get("/otro/api/buscar").status_code == 404
