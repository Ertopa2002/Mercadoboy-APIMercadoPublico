"""Exploración de la API de Licitaciones (S1–S2).

Consulta las licitaciones publicadas en una fecha, pide el detalle de algunas
y genera la lista de campos disponibles para la matriz de campos.

Uso:
    uv run python scripts/probe_licitaciones.py               # hoy
    uv run python scripts/probe_licitaciones.py 22102026 5    # fecha ddmmaaaa y N detalles

Lee MP_TICKET desde el entorno o desde .env. Nunca imprime el ticket.
Resultados en exploracion/ (no se versiona).
"""

import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

BASE = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
OUT = Path("exploracion")
PAUSA_S = 2.0  # la API rechaza peticiones simultáneas
llamadas = 0


def cargar_ticket() -> str:
    if os.getenv("MP_TICKET"):
        return os.environ["MP_TICKET"]
    env = Path(".env")
    if env.exists():
        for linea in env.read_text().splitlines():
            if linea.startswith("MP_TICKET="):
                return linea.split("=", 1)[1].strip()
    sys.exit("Falta MP_TICKET (variable de entorno o archivo .env)")


def get(params: dict, ticket: str) -> dict:
    global llamadas
    llamadas += 1
    r = httpx.get(BASE, params={**params, "ticket": ticket}, timeout=60)
    time.sleep(PAUSA_S)
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}: {r.text[:200]}")
        r.raise_for_status()
    return r.json()


def aplanar(obj, prefijo="", salida=None):
    """Devuelve {ruta_campo: ejemplo} recorriendo dicts y el primer elemento de cada lista."""
    salida = {} if salida is None else salida
    if isinstance(obj, dict):
        for k, v in obj.items():
            aplanar(v, f"{prefijo}.{k}" if prefijo else k, salida)
    elif isinstance(obj, list):
        if obj:
            aplanar(obj[0], f"{prefijo}[]", salida)
        else:
            salida.setdefault(f"{prefijo}[]", "(lista vacía)")
    else:
        salida.setdefault(prefijo, obj)
    return salida


def main():
    ticket = cargar_ticket()
    hoy = datetime.now(ZoneInfo("America/Santiago")).strftime("%d%m%Y")
    fecha = sys.argv[1] if len(sys.argv) > 1 else hoy
    n_detalle = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    OUT.mkdir(exist_ok=True)

    print(f"1) Listado publicadas del {fecha}")
    t0 = time.time()
    listado = get({"fecha": fecha, "estado": "publicada"}, ticket)
    items = listado.get("Listado", [])
    print(f"   {listado.get('Cantidad', len(items))} procesos en {time.time() - t0:.1f}s")
    (OUT / f"listado_{fecha}.json").write_text(json.dumps(listado, ensure_ascii=False, indent=2))

    tipos = Counter(c.get("CodigoExterno", "").split("-")[-1][:2] for c in items)
    print(f"   Sufijos de código más frecuentes: {tipos.most_common(10)}")
    print(f"   Campos del listado: {sorted(aplanar(items[0]).keys()) if items else '-'}")

    print(f"\n2) Detalle de {n_detalle} procesos")
    campos: dict[str, object] = {}
    for c in items[:n_detalle]:
        codigo = c["CodigoExterno"]
        det = get({"codigo": codigo}, ticket)
        (OUT / f"detalle_{codigo}.json").write_text(json.dumps(det, ensure_ascii=False, indent=2))
        lic = det.get("Listado", [{}])[0]
        print(f"   {codigo}: {lic.get('Nombre', '')[:70]}")
        aplanar(lic, "", campos)

    ruta = OUT / "campos_detalle.tsv"
    with ruta.open("w") as f:
        f.write("campo\tejemplo\n")
        for k in sorted(campos):
            f.write(f"{k}\t{str(campos[k])[:120]}\n")
    print(f"\n3) {len(campos)} campos distintos en el detalle -> {ruta}")
    print(f"\nLlamadas usadas: {llamadas} (cupo diario 10.000)")


if __name__ == "__main__":
    main()
