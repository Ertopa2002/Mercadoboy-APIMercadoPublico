"""Exploración de la API de Compra Ágil v2 (S1–S2).

Doc oficial: https://www.chilecompra.cl/api/ (Documentacion_API_Compra_Agil.pdf, mayo 2026).
Base https://api2.mercadopublico.cl, ticket en header `ticket`.

Uso:
    uv run python scripts/probe_compra_agil.py

Gasta ~6 llamadas. Lee MP_TICKET desde el entorno o .env. Resultados en exploracion/.
"""

import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from probe_licitaciones import aplanar, cargar_ticket  # noqa: E402

BASE = "https://api2.mercadopublico.cl"
OUT = Path("exploracion")


def get(cliente: httpx.Client, ruta: str, params: dict | None = None) -> httpx.Response:
    t0 = time.time()
    r = cliente.get(ruta, params=params or {})
    cuota = {k: v for k, v in r.headers.items() if "limit" in k.lower() or "retry" in k.lower()}
    print(
        f"   GET {ruta} {params or ''} -> HTTP {r.status_code} en {time.time() - t0:.1f}s {cuota}"
    )
    time.sleep(1)
    return r


def resumen(items: list[dict]) -> None:
    for it in items[:5]:
        monto = (it.get("montos") or {}).get("monto_disponible_clp")
        inst = it.get("institucion") or {}
        print(
            f"     - {it.get('codigo')}: {str(it.get('nombre'))[:55]} | ${monto} | "
            f"{inst.get('nombre_region')} | docs: {len(it.get('documentos') or [])}"
        )


def main():
    OUT.mkdir(exist_ok=True)
    headers = {"ticket": cargar_ticket(), "Accept": "application/json"}
    with httpx.Client(base_url=BASE, headers=headers, timeout=60) as c:
        print("1) Total de Compras Ágiles publicadas")
        r = get(c, "/v2/compra-agil", {"estado": "publicada", "tamano_pagina": 50})
        if r.status_code != 200:
            print(r.text[:500])
            sys.exit("No respondió /v2/compra-agil; revisa el ticket o la ruta")
        data = r.json()
        pag = data["payload"]["paginacion"]
        print(f"   {pag['total_resultados']} publicadas en {pag['total_paginas']} páginas de 50")
        (OUT / "ca_listado.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
        items = data["payload"]["items"]
        print(f"   Campos del listado: {sorted(aplanar(items[0]).keys()) if items else '-'}")

        print("\n2) Búsqueda 'alimentos' en Los Lagos (10) y Los Ríos (14)")
        r = get(
            c,
            "/v2/compra-agil",
            {"estado": "publicada", "q": "alimentos", "region": [10, 14], "tamano_pagina": 50},
        )
        if r.status_code == 200:
            d = r.json()["payload"]
            print(f"   {d['paginacion']['total_resultados']} resultados")
            resumen(d["items"])

        print("\n3) Cambios de la última hora (sincronización incremental)")
        r = get(c, "/v2/compra-agil", {"ttl_cambio_ms": 3_600_000, "tamano_pagina": 50})
        if r.status_code == 200:
            print(f"   {r.json()['payload']['paginacion']['total_resultados']} cambios")

        if not items:
            return
        codigo = items[0]["codigo"]
        print(f"\n4) Detalle de {codigo} (se prueban las dos rutas que menciona la doc)")
        det = None
        for ruta in (f"/v2/compra-agil/{codigo}", f"/v2/compraagil/{codigo}"):
            r = get(c, ruta)
            if r.status_code == 200 and det is None:
                det = r.json()
        if det:
            (OUT / f"ca_detalle_{codigo}.json").write_text(
                json.dumps(det, ensure_ascii=False, indent=2)
            )
            campos = aplanar(det.get("payload", det))
            ruta = OUT / "ca_campos_detalle.tsv"
            with ruta.open("w") as f:
                f.write("campo\tejemplo\n")
                for k in sorted(campos):
                    f.write(f"{k}\t{str(campos[k])[:120]}\n")
            p = det.get("payload", {})
            print(
                f"   Productos: {len(p.get('productos_solicitados') or [])} · "
                f"Documentos: {len(p.get('documentos') or [])} · campos: {len(campos)} -> {ruta}"
            )


if __name__ == "__main__":
    main()
