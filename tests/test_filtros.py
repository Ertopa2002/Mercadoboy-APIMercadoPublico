from datetime import date

from mp_core.filtros import Filtro, contiene, filtrar, filtro_desde_perfil
from mp_core.giros import giro
from mp_core.models import CompraAgil, Comprador, Item, Licitacion, PerfilUsuario
from mp_core.normalize import parse_fecha


def ca(
    codigo,
    nombre,
    region=13,
    monto=1_000_000,
    items=(),
    cierre="2026-10-28 18:00",
    estado="publicada",
    desc=None,
):
    return CompraAgil(
        codigo=codigo,
        nombre=nombre,
        descripcion=desc,
        estado=estado,
        monto=monto,
        fecha_cierre=parse_fecha(cierre),
        comprador=Comprador(region_codigo=region, organismo="Muni"),
        items=[Item(codigo_onu=c, descripcion=d) for c, d in items],
    )


PROCESOS = [
    ca("1-1-COT26", "ALIMENTOS ACTIVIDADES OFICINA DE LA MUJER", items=[("50181905", "galletas")]),
    ca("2-1-COT26", "ORGANIZADOR MODULAR, SANGUCHERA, COLCHON", items=[("50000000", "sanguchera")]),
    ca(
        "3-1-COT26",
        "Insumos servicio de café",
        items=[("50201706", "Café Haití 250 gr")],
        cierre="2026-10-25 12:00",
    ),
    ca("4-1-COT26", "SERVICIO DE TRASLADO DE ESTUDIANTES", items=[("81102202", "traslado")]),
    ca(
        "5-1-COT26",
        "Arriendo de baños químicos para evento",
        region=10,
        items=[("76111500", "BAÑO QUIMICO PORTATIL")],
    ),
    ca("6-1-COT26", "Compra de alimentos cerrada", estado="cerrada"),
]


def test_contiene_plural_y_tildes():
    assert contiene("ALIMENTOS PARA TALLERES", "alimento")
    assert contiene("Arriendo de baños químicos", "bano quimico")
    assert contiene("BAÑO QUIMICO PORTATIL", "baños químicos")
    assert not contiene("SERVICIO DE TRASLADO", "alimentos")


def test_giro_alimentos_excluye_ruido_solo_rubro():
    res = filtrar(PROCESOS, Filtro(giros=[giro("Venta Alimentos")]))
    codigos = [r.proceso.codigo for r in res]
    assert "1-1-COT26" in codigos and "3-1-COT26" in codigos
    assert "2-1-COT26" not in codigos  # solo calza por código ONU
    assert "4-1-COT26" not in codigos and "6-1-COT26" not in codigos


def test_incluir_solo_rubro():
    res = filtrar(PROCESOS, Filtro(giros=[giro("Venta Alimentos")], incluir_solo_rubro=True))
    assert "2-1-COT26" in [r.proceso.codigo for r in res]


def test_orden_por_relevancia():
    res = filtrar(PROCESOS, Filtro(giros=[giro("Venta Alimentos")]))
    assert res[0].proceso.codigo == "1-1-COT26"  # nombre + productos + ONU
    assert res[0].relevancia >= res[-1].relevancia


def test_banos_quimicos_y_region():
    f = Filtro(palabras_clave=["baños químicos"], regiones=[10])
    res = filtrar(PROCESOS, f)
    assert [r.proceso.codigo for r in res] == ["5-1-COT26"]


def test_monto_cierre_tipo_y_origen():
    lic = Licitacion(
        codigo="9-9-LE26",
        tipo="LE",
        nombre="Alimentos para hospital",
        estado="Publicada",
        monto=50_000_000,
        fecha_cierre=parse_fecha("2026-11-10T15:00:00"),
    )
    todos = [*PROCESOS, lic]
    f = Filtro(palabras_clave=["alimentos"], monto_min=10_000_000)
    assert [r.proceso.codigo for r in filtrar(todos, f)] == ["9-9-LE26"]
    f = Filtro(
        palabras_clave=["alimentos"], cierre_hasta=date(2026, 10, 31), origenes=["compra_agil"]
    )
    assert [r.proceso.codigo for r in filtrar(todos, f)] == ["1-1-COT26"]
    assert (
        filtrar(todos, Filtro(palabras_clave=["alimentos"], tipos=["LE"]))[0].proceso.codigo
        == "9-9-LE26"
    )


def test_excluir():
    f = Filtro(palabras_clave=["alimentos"], excluir=["oficina de la mujer"])
    assert "1-1-COT26" not in [r.proceso.codigo for r in filtrar(PROCESOS, f)]


def test_filtro_desde_perfil():
    perfil = PerfilUsuario(
        usuario="patricio",
        giros=["Venta Alimentos", "Baños químicos"],
        palabras_clave=["alimentos", "baños químicos"],
    )
    f = filtro_desde_perfil(perfil, regiones=[10])
    assert len(f.giros) == 2 and f.regiones == [10]
    assert [r.proceso.codigo for r in filtrar(PROCESOS, f)] == ["5-1-COT26"]
