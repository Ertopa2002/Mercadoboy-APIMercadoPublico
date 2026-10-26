"""Acceso a datos con caché: las herramientas MCP (y la Etapa 2) piden datos aquí, no a los
clientes directamente. La precarga escribe en el mismo store.

Duraciones (checklist S2–S4):
- listados: 1 hora
- detalle de un proceso: 6 horas, salvo que ya haya cerrado (se guarda 7 días)
- organismos: 24 horas
"""

from datetime import datetime, timedelta
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

from mp_core.clients import CompraAgilClient, LicitacionesClient
from mp_core.config import TZ
from mp_core.models import CompraAgil, Licitacion, Organismo, Proceso
from mp_core.store import Store

TTL_LISTADO = 3_600
TTL_DETALLE = 6 * 3_600
TTL_CERRADO = 7 * 86_400
TTL_ORGANISMOS = 86_400

M = TypeVar("M", bound=BaseModel)


def ttl_detalle(p: Proceso, ahora: datetime | None = None) -> int:
    ahora = ahora or datetime.now(TZ)
    if p.fecha_cierre and p.fecha_cierre < ahora - timedelta(hours=1):
        return TTL_CERRADO
    return TTL_DETALLE


class Repositorio:
    def __init__(
        self,
        store: Store,
        licitaciones: LicitacionesClient | None = None,
        compras_agiles: CompraAgilClient | None = None,
    ):
        self.store = store
        self.lic = licitaciones
        self.ca = compras_agiles

    # --- utilidades de caché -------------------------------------------------
    def _leer(self, clave: str, tipo: type[M]) -> M | None:
        raw = self.store.get(clave)
        return tipo.model_validate(raw) if raw is not None else None

    def _leer_lista(self, clave: str, tipo: type[M]) -> list[M] | None:
        raw = self.store.get(clave)
        return TypeAdapter(list[tipo]).validate_python(raw) if raw is not None else None

    def _guardar(self, clave: str, valor: BaseModel | list[BaseModel], ttl: int) -> None:
        if isinstance(valor, list):
            data = [v.model_dump(mode="json") for v in valor]
        else:
            data = valor.model_dump(mode="json")
        self.store.put(clave, data, ttl)

    def invalidar(self, codigo: str) -> None:
        self.store.delete(f"lic:det:{codigo}")
        self.store.delete(f"ca:det:{codigo}")

    # --- licitaciones --------------------------------------------------------
    def licitacion(self, codigo: str, refrescar: bool = False) -> Licitacion | None:
        clave = f"lic:det:{codigo}"
        if not refrescar and (lic := self._leer(clave, Licitacion)):
            return lic
        if not self.lic:
            return None
        lic = self.lic.detalle(codigo)
        if lic:
            self._guardar(clave, lic, ttl_detalle(lic))
        return lic

    def guardar_licitacion(self, lic: Licitacion) -> None:
        """Usado por la precarga."""
        self._guardar(f"lic:det:{lic.codigo}", lic, ttl_detalle(lic))

    def licitaciones_activas(self, refrescar: bool = False) -> list[Licitacion]:
        clave = "lic:activas"
        if not refrescar and (lst := self._leer_lista(clave, Licitacion)) is not None:
            return lst
        lst = self.lic.activas() if self.lic else []
        self._guardar(clave, lst, TTL_LISTADO)
        return lst

    # --- compras ágiles ------------------------------------------------------
    def compra_agil(self, codigo: str, refrescar: bool = False) -> CompraAgil | None:
        clave = f"ca:det:{codigo}"
        if not refrescar and (ca := self._leer(clave, CompraAgil)):
            return ca
        if not self.ca:
            return None
        ca = self.ca.detalle(codigo)
        if ca:
            self._guardar(clave, ca, ttl_detalle(ca))
        return ca

    def guardar_compra_agil(self, ca: CompraAgil) -> None:
        self._guardar(f"ca:det:{ca.codigo}", ca, ttl_detalle(ca))

    # --- organismos ----------------------------------------------------------
    def organismos(self, refrescar: bool = False) -> list[Organismo]:
        clave = "org:lista"
        if not refrescar and (lst := self._leer_lista(clave, Organismo)) is not None:
            return lst
        lst = self.lic.organismos() if self.lic else []
        self._guardar(clave, lst, TTL_ORGANISMOS)
        return lst
