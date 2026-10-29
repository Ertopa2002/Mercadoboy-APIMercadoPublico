import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx
from tenacity import wait_none

from mp_core.clients import BASE_COMPRA_AGIL, CompraAgilClient, LicitacionesClient, MPError
from mp_core.config import BASE_URL
from mp_core.cupo import Cupo, CupoAgotado
from mp_core.store import MemoryStore

FIX = Path(__file__).parent / "fixtures"
TICKET = "TICKET-SECRETO-123"


def fixture(nombre):
    return json.loads((FIX / nombre).read_text())


def cliente(clase, presupuesto=100):
    cupo = Cupo(MemoryStore(), presupuesto=presupuesto, hoy=lambda: date(2026, 10, 24))
    return clase(TICKET, cupo, espera=wait_none()), cupo


@respx.mock
def test_detalle_licitacion():
    ruta = respx.get(f"{BASE_URL}/licitaciones.json").mock(
        return_value=httpx.Response(200, json=fixture("licitacion_detalle.json"))
    )
    c, cupo = cliente(LicitacionesClient)
    lic = c.detalle("1705-26-L126")
    assert lic.codigo == "1705-26-L126" and lic.monto == 7_000_000
    assert ruta.calls.last.request.url.params["ticket"] == TICKET
    assert cupo.usado() == 1


@respx.mock
def test_detalle_licitacion_inexistente():
    respx.get(f"{BASE_URL}/licitaciones.json").mock(
        return_value=httpx.Response(200, json={"Cantidad": 0, "Listado": []})
    )
    c, _ = cliente(LicitacionesClient)
    assert c.detalle("1-1-L126") is None


@respx.mock
def test_activas_y_organismos():
    respx.get(f"{BASE_URL}/licitaciones.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "Cantidad": 1,
                "Listado": [
                    {
                        "CodigoExterno": "3553-37-LE26",
                        "Nombre": "X",
                        "CodigoEstado": 5,
                        "FechaCierre": None,
                    }
                ],
            },
        )
    )
    respx.get(f"{BASE_URL}/Empresas/BuscarComprador").mock(
        return_value=httpx.Response(
            200, json={"listaEmpresas": [{"CodigoEmpresa": "7202", "NombreEmpresa": "DGAC "}]}
        )
    )
    c, _ = cliente(LicitacionesClient)
    assert c.activas()[0].tipo == "LE"
    assert c.organismos()[0].nombre == "DGAC"


@respx.mock
def test_reintenta_503_y_peticiones_simultaneas():
    respx.get(f"{BASE_URL}/licitaciones.json").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(
                200, json={"Codigo": 10500, "Mensaje": "Hemos detectado peticiones simultáneas"}
            ),
            httpx.Response(200, json=fixture("licitacion_detalle.json")),
        ]
    )
    c, cupo = cliente(LicitacionesClient)
    assert c.detalle("1705-26-L126") is not None
    assert cupo.usado() == 3  # cada intento cuenta


@respx.mock
def test_error_no_expone_ticket():
    respx.get(f"{BASE_URL}/licitaciones.json").mock(return_value=httpx.Response(400))
    c, _ = cliente(LicitacionesClient)
    with pytest.raises(MPError) as e:
        c.detalle("1705-26-L126")
    assert TICKET not in str(e.value)


@respx.mock
def test_agota_reintentos():
    respx.get(f"{BASE_URL}/licitaciones.json").mock(return_value=httpx.Response(504))
    c, _ = cliente(LicitacionesClient)
    with pytest.raises(MPError):
        c.activas()


def test_cupo_agotado_no_llama():
    c, _ = cliente(LicitacionesClient, presupuesto=0)
    with pytest.raises(CupoAgotado):
        c.activas()


@respx.mock
def test_compra_agil_listado_y_detalle():
    item = fixture("compra_agil_listado_item.json")
    lst = respx.get(f"{BASE_COMPRA_AGIL}/v2/compra-agil").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": "OK",
                "payload": {
                    "items": [item],
                    "paginacion": {"total_resultados": 1, "total_paginas": 1},
                },
            },
        )
    )
    respx.get(f"{BASE_COMPRA_AGIL}/v2/compra-agil/3287-534-COT26").mock(
        return_value=httpx.Response(200, json=fixture("compra_agil_detalle.json"))
    )
    respx.get(f"{BASE_COMPRA_AGIL}/v2/compra-agil/NO-EXISTE").mock(return_value=httpx.Response(404))
    c, _ = cliente(CompraAgilClient)
    items, pag = c.listar(regiones=[10, 14], tamano=1)
    req = lst.calls.last.request
    assert req.headers["ticket"] == TICKET
    assert req.url.params["tamano_pagina"] == "10"
    assert req.url.params.get_list("region") == ["10", "14"]
    assert items[0].codigo == item["codigo"] and pag["total_resultados"] == 1
    assert c.detalle("3287-534-COT26").items
    assert c.detalle("NO-EXISTE") is None


def test_cupo_avisos():
    cupo = Cupo(MemoryStore(), presupuesto=10, hoy=lambda: date(2026, 10, 24))
    cupo.consumir(7)
    assert cupo.estado()["aviso"] == "Cupo diario sobre el 70%"
    cupo.consumir(2)
    assert cupo.estado()["aviso"] == "Cupo diario sobre el 90%"
    otro_dia = Cupo(cupo.store, presupuesto=10, hoy=lambda: date(2026, 10, 25))
    assert otro_dia.usado() == 0


def test_httpx_no_registra_urls_con_ticket():
    import logging

    import mp_core.clients  # noqa: F401

    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
