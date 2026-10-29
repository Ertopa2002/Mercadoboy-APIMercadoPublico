"""Front de la POC en local, sobre el índice de exploracion/blobs (no gasta cupo).

Uso:  uv run python scripts/web_local.py   ->   http://127.0.0.1:8000/dev/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # raíz del repo

import uvicorn  # noqa: E402
from starlette.applications import Starlette  # noqa: E402

from web.api import rutas  # noqa: E402

app = Starlette(routes=rutas("dev"))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
