"""Conector MCP en Lambda (ADR 0002 y 0003).

Corre con AWS Lambda Web Adapter: Lambda inicia `run.sh`, que levanta uvicorn con esta app.
Ruta MCP: /<token>/mcp (el token vive en Parameter Store; cualquier otra ruta da 404).
Front de la POC (buscador + dashboard): /<token>/ y /<token>/api/... (web/api.py).
"""

import os

from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server.server import mcp
from mp_core.aws import leer_parametro
from web.api import rutas as rutas_web


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


def _token() -> str:
    if token := os.getenv("MP_TOKEN"):
        return token
    return leer_parametro(os.environ["MP_PARAM_TOKEN"])


TOKEN = _token()

app = mcp.streamable_http_app(
    streamable_http_path=f"/{TOKEN}/mcp",
    stateless_http=True,
    json_response=True,
    # La URL de función es pública y protegida por token; la protección contra DNS rebinding
    # está pensada para servidores en localhost y rechazaría el Host de Lambda.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)
app.router.routes.extend(rutas_web(TOKEN))
