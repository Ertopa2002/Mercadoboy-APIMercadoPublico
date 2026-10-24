"""Control del cupo diario de llamadas a las APIs de Mercado Público (docs/cupo.md)."""

from collections.abc import Callable
from datetime import date, datetime

from mp_core.config import DAILY_BUDGET, TZ
from mp_core.store import Store

UMBRALES = (0.7, 0.9)


class CupoAgotado(Exception):
    """Se alcanzó el presupuesto interno de llamadas del día."""


class Cupo:
    """Cuenta llamadas por día calendario de Chile y corta al llegar al presupuesto."""

    def __init__(
        self,
        store: Store,
        presupuesto: int = DAILY_BUDGET,
        hoy: Callable[[], date] = lambda: datetime.now(TZ).date(),
    ):
        self.store = store
        self.presupuesto = presupuesto
        self._hoy = hoy

    def _clave(self) -> str:
        return f"cupo:{self._hoy().isoformat()}"

    def usado(self) -> int:
        return int(self.store.get(self._clave()) or 0)

    def consumir(self, n: int = 1) -> int:
        """Registra n llamadas. Lanza CupoAgotado si se pasaría del presupuesto."""
        if self.usado() + n > self.presupuesto:
            raise CupoAgotado(
                f"Cupo diario agotado ({self.presupuesto} llamadas). Se reinicia a las 00:00."
            )
        return self.store.incr(self._clave(), n, ttl_s=2 * 86_400)

    def estado(self) -> dict:
        usado = self.usado()
        pct = usado / self.presupuesto if self.presupuesto else 1.0
        aviso = None
        for u in sorted(UMBRALES, reverse=True):
            if pct >= u:
                aviso = f"Cupo diario sobre el {int(u * 100)}%"
                break
        return {
            "usado": usado,
            "presupuesto": self.presupuesto,
            "porcentaje": round(pct * 100, 1),
            "aviso": aviso,
        }
