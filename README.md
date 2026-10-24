# Mercadoboy – API Mercado Público con IA (POC)

POC de un agente de IA que busca licitaciones y Compras Ágiles en Mercado Público y analiza sus bases, mediante un conector MCP propio desplegado en AWS Lambda.

## Estructura

| Carpeta | Contenido |
| --- | --- |
| `mp_core/` | Cliente de APIs de Mercado Público, modelos, filtros, adjuntos, extracción de texto, caché y control de cupo. Sin dependencia de MCP. |
| `mcp_server/` | Las 7 herramientas MCP; solo llaman a `mp_core`. |
| `analysis/` | Esquema de la ficha de bases, instrucciones del agente y plantillas. |
| `evals/` | Licitaciones de referencia y script de evaluación de la ficha. |
| `infra/` | Terraform por ambiente (`dev`, `pilot`). |
| `docs/adr/` | Decisiones técnicas registradas. |
| `tests/` | Tests con pytest. |

## Requisitos

- Python 3.12 y [uv](https://docs.astral.sh/uv/)
- Ticket de la API de Mercado Público (no se versiona; ver `.env.example`)

## Uso local

```bash
uv sync                 # instala dependencias
cp .env.example .env    # y completa MP_TICKET
uv run ruff check .     # lint
uv run pytest           # tests
```

## Decisiones técnicas

Ver [docs/adr](docs/adr/).
