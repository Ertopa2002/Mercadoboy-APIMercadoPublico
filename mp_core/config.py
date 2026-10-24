"""Configuración del core, leída del entorno."""

import os
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.getenv("TZ", "America/Santiago"))
BASE_URL = "https://api.mercadopublico.cl/servicios/v1/publico"
DAILY_BUDGET = int(os.getenv("MP_DAILY_BUDGET", "8000"))


def ticket() -> str:
    """Devuelve el ticket de la API. Nunca se loguea ni se entrega al agente."""
    value = os.getenv("MP_TICKET", "")
    if not value:
        raise RuntimeError("MP_TICKET no está definido")
    return value
