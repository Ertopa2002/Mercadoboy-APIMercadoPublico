"""Arma las dependencias del conector según el entorno.

- Local: memoria + índice en exploracion/blobs + ticket desde .env
- AWS (variables MP_TABLA y MP_BUCKET): DynamoDB + S3 + ticket desde Parameter Store
"""

import json
import os
import time
from functools import lru_cache
from pathlib import Path

from mp_core import config
from mp_core.clients import CompraAgilClient, LicitacionesClient
from mp_core.cupo import Cupo
from mp_core.indice import BlobStore, Indice, LocalBlobStore
from mp_core.models import PerfilUsuario
from mp_core.repositorio import Repositorio
from mp_core.store import MemoryStore, Store

RAIZ = Path(__file__).resolve().parent.parent
REVISAR_INDICE_CADA_S = 300


def _cargar_env() -> None:
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text().splitlines():
            if "=" in linea and not linea.startswith("#"):
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def en_aws() -> bool:
    return bool(os.getenv("MP_TABLA") and os.getenv("MP_BUCKET"))


def stores() -> tuple[Store, BlobStore]:
    if en_aws():
        from mp_core.aws import DynamoStore, S3BlobStore, leer_parametro

        if not os.getenv("MP_TICKET") and os.getenv("MP_PARAM_TICKET"):
            os.environ["MP_TICKET"] = leer_parametro(os.environ["MP_PARAM_TICKET"])
        return DynamoStore(os.environ["MP_TABLA"]), S3BlobStore(os.environ["MP_BUCKET"])
    _cargar_env()
    return MemoryStore(), LocalBlobStore(RAIZ / "exploracion" / "blobs")


class Contexto:
    def __init__(self):
        self.store, self.blobs = stores()
        self.cupo = Cupo(self.store)
        ticket = config.ticket()
        self.repo = Repositorio(
            self.store,
            LicitacionesClient(ticket, self.cupo),
            CompraAgilClient(ticket, self.cupo),
        )
        self._indice: Indice | None = None
        self._version: str | None = None
        self._revisado = 0.0
        self.perfiles = {
            k: PerfilUsuario.model_validate(v)
            for k, v in json.loads((RAIZ / "config" / "perfiles.json").read_text()).items()
        }

    def indice(self) -> Indice:
        """Índice en memoria; se recarga si la precarga lo actualizó (revisa cada 5 min)."""
        ahora = time.monotonic()
        if self._indice is None or ahora - self._revisado > REVISAR_INDICE_CADA_S:
            self._revisado = ahora
            version = Indice.version(self.blobs)
            if self._indice is None or version != self._version:
                self._indice, self._version = Indice.cargar(self.blobs), version
        return self._indice


@lru_cache(maxsize=1)
def contexto() -> Contexto:
    return Contexto()
