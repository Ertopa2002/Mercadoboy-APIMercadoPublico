import json
from datetime import date
from pathlib import Path

from mp_core.mappers import (
    compra_agil_desde_api,
    licitacion_desde_detalle,
    licitacion_desde_listado,
)

FIX = Path(__file__).parent / "fixtures"


def cargar(nombre):
    return json.loads((FIX / nombre).read_text())


def test_licitacion_detalle():
    lic = licitacion_desde_detalle(cargar("licitacion_detalle.json")["Listado"][0])
    assert lic.codigo == "1705-26-L126"
    assert lic.tipo == "L1"
    assert lic.monto == 7_000_000
    assert lic.comprador.region_codigo == 3
    assert lic.comprador.region == "Región de Atacama"
    assert lic.fecha_cierre.isoformat().startswith("2026-11-06T15:00")
    assert lic.dias_al_cierre(hoy=date(2026, 10, 24)) == 13
    assert lic.items and lic.items[0].codigo_onu == "20111610"
    assert lic.etapas == 1 and lic.tiene_contrato is False
    assert lic.detalle_completo
    assert lic.url_ficha.endswith("idlicitacion=1705-26-L126")


def test_licitacion_listado():
    lic = licitacion_desde_listado(
        {"CodigoExterno": "3553-37-LE26", "Nombre": " X ", "CodigoEstado": 5, "FechaCierre": None}
    )
    assert lic.tipo == "LE" and lic.nombre == "X" and not lic.detalle_completo


def test_compra_agil_detalle():
    ca = compra_agil_desde_api(cargar("compra_agil_detalle.json")["payload"])
    assert ca.codigo == "3287-534-COT26"
    assert ca.monto == 700_000
    assert ca.comprador.region_codigo == 7
    assert ca.items[0].codigo_onu == "47131703"
    assert ca.direccion_entrega and ca.plazo_entrega_dias == 1
    assert ca.detalle_completo


def test_compra_agil_listado():
    ca = compra_agil_desde_api(cargar("compra_agil_listado_item.json"))
    assert ca.documentos and ca.documentos[0].nombre.endswith(".pdf")
    assert not ca.detalle_completo
    assert ca.url_ficha.endswith(ca.codigo)
