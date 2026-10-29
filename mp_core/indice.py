"""Índice de procesos vigentes para buscar sin llamar a la API (ADR 0009).

Son miles de procesos (~5.100 licitaciones + ~9.000 Compras Ágiles): no caben en un registro de
DynamoDB (400 KB), así que el índice completo se guarda como un archivo JSON comprimido en S3
(en local, en disco) y la función lo carga en memoria. La precarga lo reconstruye.
"""

import gzip
from datetime import datetime
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field, TypeAdapter

from mp_core.config import TZ
from mp_core.models import CompraAgil, Licitacion

CLAVE_LICITACIONES = "indice/licitaciones.json.gz"
CLAVE_COMPRAS_AGILES = "indice/compras_agiles.json.gz"


class BlobStore(Protocol):
    def leer(self, clave: str) -> bytes | None: ...

    def escribir(self, clave: str, data: bytes) -> None: ...

    def version(self, clave: str) -> str | None: ...


class LocalBlobStore:
    def __init__(self, carpeta: str | Path = "exploracion/blobs"):
        self.carpeta = Path(carpeta)

    def leer(self, clave: str) -> bytes | None:
        p = self.carpeta / clave
        return p.read_bytes() if p.exists() else None

    def escribir(self, clave: str, data: bytes) -> None:
        p = self.carpeta / clave
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def version(self, clave: str) -> str | None:
        p = self.carpeta / clave
        return str(p.stat().st_mtime_ns) if p.exists() else None


class Indice(BaseModel):
    actualizado: datetime | None = None
    licitaciones: list[Licitacion] = Field(default_factory=list)
    compras_agiles: list[CompraAgil] = Field(default_factory=list)

    def procesos(self) -> list[Licitacion | CompraAgil]:
        return [*self.licitaciones, *self.compras_agiles]

    def por_codigo(self, codigo: str) -> Licitacion | CompraAgil | None:
        for p in self.procesos():
            if p.codigo == codigo:
                return p
        return None

    def resumen(self) -> dict:
        return {
            "actualizado": self.actualizado.isoformat() if self.actualizado else None,
            "licitaciones": len(self.licitaciones),
            "licitaciones_con_detalle": sum(1 for x in self.licitaciones if x.detalle_completo),
            "compras_agiles": len(self.compras_agiles),
        }

    # --- persistencia (dos archivos: cada precarga escribe el suyo) ------------
    @staticmethod
    def _gz(modelos: list) -> bytes:
        return gzip.compress(
            ("[" + ",".join(m.model_dump_json(exclude_none=True) for m in modelos) + "]").encode()
        )

    def guardar(self, blobs: BlobStore, partes: tuple[str, ...] = ("lic", "ca")) -> None:
        self.actualizado = datetime.now(TZ)
        if "lic" in partes:
            blobs.escribir(CLAVE_LICITACIONES, self._gz(self.licitaciones))
        if "ca" in partes:
            blobs.escribir(CLAVE_COMPRAS_AGILES, self._gz(self.compras_agiles))

    @classmethod
    def cargar(cls, blobs: BlobStore) -> "Indice":
        lic = blobs.leer(CLAVE_LICITACIONES)
        ca = blobs.leer(CLAVE_COMPRAS_AGILES)
        return cls(
            actualizado=datetime.now(TZ) if (lic or ca) else None,
            licitaciones=_LIC.validate_json(gzip.decompress(lic)) if lic else [],
            compras_agiles=_CA.validate_json(gzip.decompress(ca)) if ca else [],
        )

    @staticmethod
    def version(blobs: BlobStore) -> str:
        return f"{blobs.version(CLAVE_LICITACIONES)}|{blobs.version(CLAVE_COMPRAS_AGILES)}"


_LIC = TypeAdapter(list[Licitacion])
_CA = TypeAdapter(list[CompraAgil])
