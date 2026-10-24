from datetime import date

import pytest

from mp_core.normalize import (
    dias_al_cierre,
    es_compra_agil,
    parse_fecha,
    partes_codigo,
    region_codigo,
    tipo_desde_codigo,
)


@pytest.mark.parametrize(
    ("codigo", "tipo"),
    [
        ("1705-26-L126", "L1"),
        ("3553-37-LE26", "LE"),
        ("1116005-8-LP26", "LP"),
        ("1052047-802-L126", "L1"),
        ("5517-467-COT26", "COT"),
        ("1234-5-O126", "O1"),
        ("1234-5-B226", "B2"),
    ],
)
def test_tipo_desde_codigo(codigo, tipo):
    assert tipo_desde_codigo(codigo) == tipo


def test_partes_codigo_invalido():
    assert partes_codigo("no-es-un-codigo") is None
    assert es_compra_agil("3287-534-COT26")
    assert not es_compra_agil("3553-37-LE26")


@pytest.mark.parametrize(
    "valor",
    [
        "2026-11-06T15:00:00",
        "2026-10-23T14:46:15.877",
        "2026-10-26 10:00",
        "2026-10-23T17:10:00.313Z",
    ],
)
def test_parse_fecha_formatos(valor):
    dt = parse_fecha(valor)
    assert dt is not None
    assert str(dt.tzinfo) == "America/Santiago"


def test_parse_fecha_z_se_trata_como_local():
    assert parse_fecha("2026-10-23T17:10:00.313Z").hour == 17


def test_parse_fecha_vacia():
    assert parse_fecha(None) is None
    assert parse_fecha("basura") is None


def test_dias_al_cierre():
    cierre = parse_fecha("2026-11-06T15:00:00")
    assert dias_al_cierre(cierre, hoy=date(2026, 10, 24)) == 13
    assert dias_al_cierre(cierre, hoy=date(2026, 11, 7)) == -1
    assert dias_al_cierre(None) is None


@pytest.mark.parametrize(
    ("nombre", "codigo"),
    [
        ("Región de Atacama ", 3),
        ("Región del Maule ", 7),
        ("Región Metropolitana de Santiago", 13),
        ("Región de Los Lagos", 10),
        ("Región de Los Ríos", 14),
        ("Región del Biobío", 8),
        ("Región de Ñuble", 16),
        ("Región de Arica y Parinacota", 15),
        ("Región del Libertador General Bernardo O´Higgins", 6),
    ],
)
def test_region_codigo(nombre, codigo):
    assert region_codigo(nombre) == codigo
