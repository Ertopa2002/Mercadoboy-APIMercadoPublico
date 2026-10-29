"""Lambda de precarga por tramos (ADR 0007 y 0009).

Evento: {"tarea": "licitaciones"} o {"tarea": "compras_agiles"}. Cada tarea escribe su propio
archivo del índice en S3, así dos ejecuciones no se pisan. Trabaja hasta ~90 s antes del
límite de la función y deja lo pendiente para la siguiente ejecución.
"""

import logging
import time

from mcp_server.contexto import contexto
from mp_core.giros import giro
from mp_core.indice import Indice
from mp_core.precarga import precargar_compras_agiles, precargar_licitaciones

log = logging.getLogger()
log.setLevel(logging.INFO)
MARGEN_S = 90
# La API v1 responde 429 sobre ~3 peticiones por segundo; cada reintento también cuenta en
# el cupo. Con esta pausa se mantiene bajo el límite.
PAUSA_LICITACIONES_S = 0.4
PAUSA_COMPRA_AGIL_S = 0.2


def handler(event, context):
    tarea = (event or {}).get("tarea", "licitaciones")
    restante_s = context.get_remaining_time_in_millis() / 1000 if context else 840
    hasta = time.monotonic() + max(60, restante_s - MARGEN_S)
    ctx = contexto()
    ctx.repo.lic.pausa_s = PAUSA_LICITACIONES_S
    ctx.repo.ca.pausa_s = PAUSA_COMPRA_AGIL_S
    previo = Indice.cargar(ctx.blobs)
    giros = [g for p in ctx.perfiles.values() for n in p.giros if (g := giro(n))]
    t0 = time.monotonic()
    if tarea == "licitaciones":
        lic, pendientes = precargar_licitaciones(ctx.repo.lic, previo, hasta=hasta, avance=log.info)
        Indice(licitaciones=lic).guardar(ctx.blobs, partes=("lic",))
        resultado = {"licitaciones": len(lic), "pendientes_sin_detalle": pendientes}
    elif tarea == "compras_agiles":
        ca = precargar_compras_agiles(ctx.repo.ca, previo, giros, hasta=hasta, avance=log.info)
        Indice(compras_agiles=ca).guardar(ctx.blobs, partes=("ca",))
        resultado = {"compras_agiles": len(ca)}
    else:
        raise ValueError(f"Tarea desconocida: {tarea}")
    resultado.update(tarea=tarea, segundos=round(time.monotonic() - t0), cupo=ctx.cupo.estado())
    log.info("precarga terminada: %s", resultado)
    return resultado
