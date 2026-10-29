"""Agrega el conector 'mercadoboy' a Claude Desktop (macOS), sin borrar lo que ya existe.

Uso (en tu Mac, desde la carpeta del repo):
    python3 scripts/configurar_claude_desktop.py

Hace una copia de respaldo del archivo de configuración antes de modificarlo.
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

CONFIG = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
REPO = Path(__file__).resolve().parent.parent


def main():
    uv = shutil.which("uv")
    if not uv:
        sys.exit("No encuentro 'uv'. Instálalo con: brew install uv")
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if CONFIG.exists():
        respaldo = CONFIG.with_suffix(f".json.bak-{datetime.now():%Y%m%d%H%M%S}")
        shutil.copy2(CONFIG, respaldo)
        print(f"Respaldo: {respaldo}")
        texto = CONFIG.read_text().strip()
        data = json.loads(texto) if texto else {}
    data.setdefault("mcpServers", {})["mercadoboy"] = {
        "command": uv,
        "args": ["--directory", str(REPO), "run", "python", "-m", "mcp_server.server"],
    }
    CONFIG.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Listo: conector 'mercadoboy' agregado en {CONFIG}")
    print(f"  uv: {uv}\n  repo: {REPO}")
    print("Ahora cierra Claude Desktop por completo (Cmd+Q) y vuelve a abrirlo.")


if __name__ == "__main__":
    main()
