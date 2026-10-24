"""Almacenamiento clave-valor con expiración (caché, contador de cupo, precarga).

Interfaz única con implementaciones intercambiables (ADR 0004): memoria para desarrollo y
tests; DynamoDB en AWS (se agrega en el bloque de infraestructura).
"""

import time
from collections.abc import Callable
from typing import Any, Protocol


class Store(Protocol):
    def get(self, key: str) -> Any | None: ...

    def put(self, key: str, value: Any, ttl_s: int | None = None) -> None: ...

    def incr(self, key: str, amount: int = 1, ttl_s: int | None = None) -> int: ...

    def delete(self, key: str) -> None: ...


class MemoryStore:
    """Implementación en memoria. Respeta la expiración con un reloj inyectable."""

    def __init__(self, reloj: Callable[[], float] = time.time):
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._reloj = reloj

    def _vigente(self, key: str) -> tuple[Any, float | None] | None:
        item = self._data.get(key)
        if item is None:
            return None
        if item[1] is not None and item[1] <= self._reloj():
            del self._data[key]
            return None
        return item

    def get(self, key: str) -> Any | None:
        item = self._vigente(key)
        return item[0] if item else None

    def put(self, key: str, value: Any, ttl_s: int | None = None) -> None:
        expira = self._reloj() + ttl_s if ttl_s else None
        self._data[key] = (value, expira)

    def incr(self, key: str, amount: int = 1, ttl_s: int | None = None) -> int:
        item = self._vigente(key)
        if item is None:
            self.put(key, amount, ttl_s)
            return amount
        nuevo = int(item[0]) + amount
        self._data[key] = (nuevo, item[1])
        return nuevo

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
