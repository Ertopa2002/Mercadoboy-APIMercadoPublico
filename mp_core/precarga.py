"""Precarga del índice (ADR 0007 y 0009). En AWS la ejecuta una Lambda programada por tramos
(máx. ~13 min cada uno); en local, un script.

Licitaciones: listado de activas (1 llamada) + detalle de los códigos sin detalle, hasta el
tope o hasta el límite de tiempo. Lo que no alcanzó queda para el tramo siguiente.
Compras Ágiles: listado de publicadas (~182 páginas; ya trae región, monto, organismo y
documentos) + detalle solo de las que calzan con algún giro de los perfiles.
"""

import logging
import time
from collections.abc import Callable

from mp_core.clients import CompraAgilClient, LicitacionesClient
from mp_core.cupo import CupoAgotado
from mp_core.filtros import Filtro, evaluar
from mp_core.giros import Giro
from mp_core.indice import Indice
from mp_core.models import CompraAgil, Licitacion

log = logging.getLogger(__name__)
Avance = Callable[[str], None]


def _vencido(hasta: float | None) -> bool:
    return hasta is not None and time.monotonic() >= hasta


def precargar_licitaciones(
    cliente: LicitacionesClient,
    previo: Indice,
    max_detalles: int = 6_000,
    hasta: float | None = None,
    avance: Avance = lambda _: None,
) -> tuple[list[Licitacion], int]:
    """Devuelve (licitaciones, pendientes_sin_detalle)."""
    conocidas = {x.codigo: x for x in previo.licitaciones if x.detalle_completo}
    activas = cliente.activas()
    resultado: list[Licitacion] = []
    pedidos, detener = 0, False
    for lic in activas:
        if lic.codigo in conocidas:
            resultado.append(conocidas[lic.codigo])
            continue
        if not detener and (pedidos >= max_detalles or _vencido(hasta)):
            detener = True
        if detener:
            resultado.append(lic)
            continue
        try:
            det = cliente.detalle(lic.codigo)
        except CupoAgotado:
            log.warning("Cupo agotado durante la precarga de licitaciones")
            detener, det = True, None
        pedidos += 1
        resultado.append(det or lic)
        if pedidos % 200 == 0:
            avance(f"licitaciones: {pedidos} detalles")
    pendientes = sum(1 for x in resultado if not x.detalle_completo)
    avance(
        f"licitaciones: {len(activas)} activas, {pedidos} detalles nuevos, {pendientes} pendientes"
    )
    return resultado, pendientes


def precargar_compras_agiles(
    cliente: CompraAgilClient,
    previo: Indice,
    giros: list[Giro],
    max_paginas: int = 400,
    max_detalles: int = 300,
    hasta: float | None = None,
    avance: Avance = lambda _: None,
) -> list[CompraAgil]:
    conocidas = {x.codigo: x for x in previo.compras_agiles if x.detalle_completo}
    vistas: list[CompraAgil] = []
    pagina, completo = 1, False
    while pagina <= max_paginas and not _vencido(hasta):
        items, pag = cliente.listar(pagina=pagina, tamano=50, ordenar_por="FechaPublicacion")
        vistas += items
        if not items or pagina >= int(pag.get("total_paginas") or 0):
            completo = True
            break
        pagina += 1
        if pagina % 25 == 0:
            avance(f"compras ágiles: página {pagina}")
    filtro = Filtro(giros=giros, solo_publicadas=False)
    resultado, pedidos = [], 0
    for ca in vistas:
        if ca.codigo in conocidas:
            resultado.append(conocidas[ca.codigo])
        elif giros and pedidos < max_detalles and not _vencido(hasta) and evaluar(ca, filtro):
            pedidos += 1
            try:
                resultado.append(cliente.detalle(ca.codigo) or ca)
            except CupoAgotado:
                max_detalles = pedidos
                resultado.append(ca)
        else:
            resultado.append(ca)
    if not completo:  # listado cortado por tiempo: conserva las anteriores no revisadas
        vistos = {x.codigo for x in resultado}
        resultado += [x for x in previo.compras_agiles if x.codigo not in vistos]
    avance(
        f"compras ágiles: {len(vistas)} revisadas ({'completo' if completo else 'parcial'}), "
        f"{pedidos} detalles nuevos"
    )
    return resultado


def precargar(
    lic: LicitacionesClient,
    ca: CompraAgilClient,
    previo: Indice,
    giros: list[Giro],
    max_detalles_lic: int = 6_000,
    max_paginas_ca: int = 400,
    max_detalles_ca: int = 300,
    avance: Avance = lambda _: None,
) -> Indice:
    """Precarga completa (uso local, sin límite de tiempo)."""
    licitaciones, _ = precargar_licitaciones(lic, previo, max_detalles_lic, avance=avance)
    compras = precargar_compras_agiles(
        ca, previo, giros, max_paginas_ca, max_detalles_ca, avance=avance
    )
    return Indice(licitaciones=licitaciones, compras_agiles=compras)
