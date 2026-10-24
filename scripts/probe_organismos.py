"""Exploración complementaria de la API (S1–S2): activas, organismos y filtro por organismo.

Uso:
    uv run python scripts/probe_organismos.py

Gasta 3 llamadas. Lee MP_TICKET desde el entorno o .env. Resultados en exploracion/.
"""

import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from probe_licitaciones import cargar_ticket  # noqa: E402

BASE = "https://api.mercadopublico.cl/servicios/v1/publico"
OUT = Path("exploracion")


def get(ruta: str, params: dict, ticket: str) -> dict:
    t0 = time.time()
    r = httpx.get(f"{BASE}/{ruta}", params={**params, "ticket": ticket}, timeout=120)
    print(f"   HTTP {r.status_code} en {time.time() - t0:.1f}s")
    time.sleep(2)
    r.raise_for_status()
    return r.json()


def main():
    ticket = cargar_ticket()
    OUT.mkdir(exist_ok=True)
    hoy = datetime.now(ZoneInfo("America/Santiago")).strftime("%d%m%Y")

    print("1) Licitaciones activas (sin fecha)")
    act = get("licitaciones.json", {"estado": "activas"}, ticket)
    items = act.get("Listado", [])
    print(f"   {act.get('Cantidad', len(items))} licitaciones activas")
    if items:
        print(f"   Campos: {sorted(items[0].keys())}")
        cierres = sorted(i.get("FechaCierre") or "" for i in items)
        print(f"   Cierre más próximo: {cierres[0]} · más lejano: {cierres[-1]}")
    (OUT / "activas.json").write_text(json.dumps(act, ensure_ascii=False, indent=2))

    print("\n2) Listado de organismos compradores (Empresas/BuscarComprador)")
    org = get("Empresas/BuscarComprador", {}, ticket)
    lista = org.get("listaEmpresas", org.get("Listado", []))
    print(f"   {len(lista)} organismos · claves: {sorted(org.keys())}")
    if lista:
        print(f"   Ejemplo: {lista[0]}")
    (OUT / "organismos.json").write_text(json.dumps(org, ensure_ascii=False, indent=2))

    print("\n3) Filtro por CodigoOrganismo (organismo de la primera licitación de hoy)")
    listado_hoy = OUT / f"listado_{hoy}.json"
    codigo_org = None
    for det in OUT.glob("detalle_*.json"):
        d = json.loads(det.read_text())["Listado"][0]
        codigo_org = d["Comprador"]["CodigoOrganismo"]
        print(f"   Organismo {codigo_org}: {d['Comprador']['NombreOrganismo']}")
        break
    if codigo_org:
        f = get("licitaciones.json", {"CodigoOrganismo": codigo_org, "estado": "activas"}, ticket)
        n = f.get("Cantidad", len(f.get("Listado", [])))
        print(f"   {n} licitaciones activas de ese organismo")
        for i in f.get("Listado", [])[:5]:
            print(f"   - {i['CodigoExterno']}: {i['Nombre'][:60]}")
    elif not listado_hoy.exists():
        print("   Corre antes scripts/probe_licitaciones.py")

    sufijos = Counter(i["CodigoExterno"].split("-")[-1][:2] for i in items)
    print(f"\nSufijos en activas: {sufijos.most_common(12)}")
    print("\nLlamadas usadas: 3")


if __name__ == "__main__":
    main()
