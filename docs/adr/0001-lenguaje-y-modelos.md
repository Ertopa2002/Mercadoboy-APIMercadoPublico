# 0001 – Python 3.12 con Pydantic v2

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
El core debe reutilizarse en la Etapa 2 (API REST) y ser simple de mantener.

## Decisión
Python 3.12, modelos tipados con Pydantic v2, httpx como cliente HTTP y tenacity para reintentos. Dependencias con uv.

## Consecuencias
Mismo lenguaje para core, conector e ingesta futura. Lambda soporta Python 3.12 de forma nativa.
