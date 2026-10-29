"""Clientes de las APIs de Mercado Público: Licitaciones (v1) y Compra Ágil (v2).

- Cada intento de llamada consume cupo (docs/cupo.md).
- Reintentos con espera exponencial ante 429, 5xx, timeouts y el rechazo por peticiones
  simultáneas de la API v1.
- El ticket nunca aparece en errores ni logs.
"""

import logging
import time
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mp_core.config import BASE_URL
from mp_core.cupo import Cupo
from mp_core.mappers import (
    compra_agil_desde_api,
    licitacion_desde_detalle,
    licitacion_desde_listado,
)
from mp_core.models import CompraAgil, Licitacion, Organismo

log = logging.getLogger(__name__)

# httpx registra cada URL en nivel INFO, y la API v1 exige el ticket como parámetro de la URL:
# se silencia para que el ticket nunca llegue a los logs (CloudWatch, consola).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

BASE_COMPRA_AGIL = "https://api2.mercadopublico.cl"
REINTENTABLES = {429, 500, 502, 503, 504}


class MPError(Exception):
    """Error al consultar Mercado Público (sin datos sensibles en el mensaje)."""


class _Reintentable(MPError):
    pass


class _Base:
    def __init__(
        self,
        ticket: str,
        cupo: Cupo,
        http: httpx.Client | None = None,
        intentos: int = 4,
        espera: Callable | None = None,
        pausa_s: float = 0.0,
    ):
        self._ticket = ticket
        self.cupo = cupo
        self.http = http or httpx.Client(timeout=60)
        self.intentos = intentos
        self.espera = espera or wait_exponential(multiplier=2, min=2, max=30)
        self.pausa_s = pausa_s

    def _enviar(self, url: str, params: dict, headers: dict) -> httpx.Response:
        raise NotImplementedError

    def _get(self, url: str, params: dict | None = None, headers: dict | None = None) -> Any:
        """GET con cupo y reintentos. Devuelve el JSON, o None si es 404."""
        etiqueta = url.split("mercadopublico.cl")[-1]
        for intento in Retrying(
            stop=stop_after_attempt(self.intentos),
            wait=self.espera,
            retry=retry_if_exception_type(_Reintentable),
            reraise=True,
        ):
            with intento:
                self.cupo.consumir()
                try:
                    r = self._enviar(url, params or {}, headers or {})
                except httpx.TransportError as e:
                    raise _Reintentable(f"{etiqueta}: error de red ({type(e).__name__})") from None
                finally:
                    if self.pausa_s:
                        time.sleep(self.pausa_s)
                if r.status_code == 404:
                    return None
                if r.status_code in REINTENTABLES:
                    raise _Reintentable(f"{etiqueta}: HTTP {r.status_code}")
                if r.status_code != 200:
                    raise MPError(f"{etiqueta}: HTTP {r.status_code}")
                data = r.json()
                if isinstance(data, dict) and "simult" in str(data.get("Mensaje", "")).lower():
                    raise _Reintentable(f"{etiqueta}: peticiones simultáneas")
                return data
        return None  # pragma: no cover


class LicitacionesClient(_Base):
    """API v1: licitaciones.json y Empresas/BuscarComprador. Ticket como parámetro."""

    def _enviar(self, url, params, headers):
        return self.http.get(url, params={**params, "ticket": self._ticket}, headers=headers)

    def _listado(self, params: dict) -> list[Licitacion]:
        data = self._get(f"{BASE_URL}/licitaciones.json", params) or {}
        return [licitacion_desde_listado(x) for x in data.get("Listado") or []]

    def publicadas_por_fecha(self, fecha: date, estado: str = "publicada") -> list[Licitacion]:
        return self._listado({"fecha": fecha.strftime("%d%m%Y"), "estado": estado})

    def activas(self) -> list[Licitacion]:
        return self._listado({"estado": "activas"})

    def por_organismo(self, codigo_organismo: str, estado: str = "activas") -> list[Licitacion]:
        return self._listado({"CodigoOrganismo": codigo_organismo, "estado": estado})

    def detalle(self, codigo: str) -> Licitacion | None:
        data = self._get(f"{BASE_URL}/licitaciones.json", {"codigo": codigo}) or {}
        listado = data.get("Listado") or []
        return licitacion_desde_detalle(listado[0]) if listado else None

    def organismos(self) -> list[Organismo]:
        data = self._get(f"{BASE_URL}/Empresas/BuscarComprador") or {}
        return [
            Organismo(codigo=str(o["CodigoEmpresa"]), nombre=o["NombreEmpresa"].strip())
            for o in data.get("listaEmpresas") or []
        ]


class CompraAgilClient(_Base):
    """API Compra Ágil v2. Ticket en el header `ticket`."""

    def _enviar(self, url, params, headers):
        return self.http.get(url, params=params, headers={**headers, "ticket": self._ticket})

    def listar(
        self,
        estado: str = "publicada",
        regiones: list[int] | None = None,
        pagina: int = 1,
        tamano: int = 50,
        ordenar_por: str | None = None,
    ) -> tuple[list[CompraAgil], dict]:
        """Una página del listado. `tamano` entre 10 y 50 (lo exige la API)."""
        params: dict[str, Any] = {
            "estado": estado,
            "numero_pagina": pagina,
            "tamano_pagina": max(10, min(50, tamano)),
        }
        if regiones:
            params["region"] = regiones
        if ordenar_por:
            params["ordenar_por"] = ordenar_por
        data = self._get(f"{BASE_COMPRA_AGIL}/v2/compra-agil", params) or {}
        payload = data.get("payload") or {}
        items = [compra_agil_desde_api(x) for x in payload.get("items") or []]
        return items, payload.get("paginacion") or {}

    def detalle(self, codigo: str) -> CompraAgil | None:
        data = self._get(f"{BASE_COMPRA_AGIL}/v2/compra-agil/{codigo}")
        if not data or not data.get("payload"):
            return None
        return compra_agil_desde_api(data["payload"])
