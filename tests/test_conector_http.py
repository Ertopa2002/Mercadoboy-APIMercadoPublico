import importlib

import pytest
from starlette.testclient import TestClient

HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("MP_TOKEN", "tok123")
    import aws_lambda.conector as c

    return importlib.reload(c).app


def test_ruta_con_token_lista_herramientas(app):
    with TestClient(app) as cli:
        init = cli.post(
            "/tok123/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            },
        )
        assert init.status_code == 200, init.text
        r = cli.post(
            "/tok123/mcp", headers=HEADERS, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        assert r.status_code == 200, r.text
        nombres = {t["name"] for t in r.json()["result"]["tools"]}
        assert {"buscar_compras_agiles", "obtener_adjuntos"} <= nombres


def test_sin_token_404_y_health(app):
    with TestClient(app, base_url="https://abc.lambda-url.us-east-1.on.aws") as cli:
        assert cli.post("/mcp", headers=HEADERS, json={}).status_code == 404
        assert cli.post("/otro/mcp", headers=HEADERS, json={}).status_code == 404
        assert cli.get("/health").json() == {"ok": True}


def test_front_web_montado_bajo_token(app):
    with TestClient(app) as cli:
        assert cli.get("/tok123/").status_code == 200
        assert cli.get("/api/buscar").status_code == 404
