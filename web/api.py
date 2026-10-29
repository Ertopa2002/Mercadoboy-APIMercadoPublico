"""API del front de la POC: buscador y dashboard sobre el índice precargado.

No llama a la API de Mercado Público (no gasta cupo): todo sale del índice en memoria.
Rutas, bajo el mismo token que el conector MCP:
    /<token>/                  página (buscador + dashboard)
    /<token>/api/opciones      regiones, giros, tipos y perfiles para los filtros
    /<token>/api/buscar        resultados paginados
    /<token>/api/estadisticas  métricas del dashboard para el mismo filtro
    /<token>/api/proceso/{c}   ficha resumida desde el índice
    /<token>/api/adjuntos/{c}  enlace a adjuntos (licitaciones: lee la ficha web, con caché)
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from mp_core.config import TZ
from mp_core.filtros import Filtro, Resultado, filtrar
from mp_core.giros import GIROS, giro
from mp_core.models import Proceso
from mp_core.normalize import REGIONES, es_compra_agil

STATIC = Path(__file__).parent / "static"
RANGOS_MONTO = [
    ("< $1M", 0, 1_000_000),
    ("$1M – 5M", 1_000_000, 5_000_000),
    ("$5M – 20M", 5_000_000, 20_000_000),
    ("$20M – 100M", 20_000_000, 100_000_000),
    ("> $100M", 100_000_000, float("inf")),
]
ORDENES = {"relevancia", "cierre", "monto", "publicacion"}
NO_FILTRAN = {"orden", "pagina", "por_pagina"}
_cache: dict[tuple, list[Resultado]] = {}


def _filtrados(ctx, q: dict) -> list[Resultado]:
    """filtrar() cuesta ~1 s sobre miles de procesos: se recuerda por índice y filtro, así
    paginar, reordenar o pasar al dashboard no recalcula."""
    indice = ctx.indice()
    clave = (id(indice), tuple(sorted((k, v) for k, v in q.items() if k not in NO_FILTRAN)))
    if clave not in _cache:
        if len(_cache) > 64 or any(k[0] != id(indice) for k in _cache):
            _cache.clear()
        res = filtrar(indice.procesos(), filtro_desde_query(q, ctx.perfiles))
        # El estado puede seguir "publicada" unas horas tras el cierre: se ocultan los vencidos.
        _cache[clave] = [r for r in res if (r.proceso.dias_al_cierre() or 0) >= 0]
    return _cache[clave]


def _ctx():
    from mcp_server.contexto import contexto

    return contexto()


# --- parámetros -----------------------------------------------------------------
def _lista(q: dict, k: str) -> list[str]:
    return [x.strip() for x in (q.get(k) or "").split(",") if x.strip()]


def _num(q: dict, k: str) -> float | None:
    try:
        return float(q[k]) if q.get(k) not in (None, "") else None
    except ValueError:
        return None


def _fecha(q: dict, k: str) -> date | None:
    try:
        return date.fromisoformat(q[k]) if q.get(k) else None
    except ValueError:
        return None


def filtro_desde_query(q: dict, perfiles: dict) -> Filtro:
    """Traduce la query string del front a un Filtro de mp_core."""
    origen = q.get("origen") or "todos"
    giros = [g for n in _lista(q, "giros") if (g := giro(n))]
    regiones = [int(r) for r in _lista(q, "regiones") if r.isdigit()]
    if (perfil := perfiles.get(q.get("perfil") or "")) is not None:
        if not giros:
            giros = [g for n in perfil.giros if (g := giro(n))]
        regiones = regiones or perfil.regiones
    return Filtro(
        origenes=[origen] if origen in ("licitacion", "compra_agil") else [],
        regiones=regiones,
        tipos=[t.upper() for t in _lista(q, "tipos")],
        monto_min=_num(q, "monto_min"),
        monto_max=_num(q, "monto_max"),
        organismo=(q.get("organismo") or "").strip() or None,
        cierre_desde=_fecha(q, "cierre_desde"),
        cierre_hasta=_fecha(q, "cierre_hasta"),
        palabras_clave=_lista(q, "q"),
        excluir=_lista(q, "excluir"),
        giros=giros,
        incluir_solo_rubro=q.get("solo_rubro") in ("1", "true", "si"),
    )


def _ordenar(res: list[Resultado], orden: str) -> list[Resultado]:
    lejos = datetime.max.replace(tzinfo=TZ)
    if orden == "cierre":
        return sorted(res, key=lambda r: r.proceso.fecha_cierre or lejos)
    if orden == "monto":
        return sorted(res, key=lambda r: -(r.proceso.monto or 0))
    if orden == "publicacion":
        return sorted(res, key=lambda r: r.proceso.fecha_publicacion or lejos, reverse=True)
    return res  # filtrar() ya ordena por relevancia y cierre


def _fila(r: Resultado) -> dict[str, Any]:
    p = r.proceso
    return {
        "codigo": p.codigo,
        "origen": p.origen,
        "tipo": p.tipo,
        "nombre": p.nombre,
        "organismo": p.comprador.organismo,
        "region": p.comprador.region,
        "region_codigo": p.comprador.region_codigo,
        "monto": p.monto if p.monto_visible else None,
        "fecha_publicacion": p.fecha_publicacion.isoformat() if p.fecha_publicacion else None,
        "fecha_cierre": p.fecha_cierre.isoformat() if p.fecha_cierre else None,
        "dias_al_cierre": p.dias_al_cierre(),
        "relevancia": r.relevancia,
        "motivos": r.motivos,
        "documentos": len(p.documentos),
        "url_ficha": p.url_ficha,
    }


# --- lógica (testeable sin HTTP) -----------------------------------------------
def opciones(ctx) -> dict:
    procesos = ctx.indice().procesos()
    tipos = sorted({p.tipo for p in procesos if p.tipo})
    return {
        "regiones": [{"codigo": k, "nombre": v} for k, v in REGIONES.items()],
        "giros": [g.nombre for g in GIROS.values()],
        "tipos": tipos,
        "perfiles": {k: v.model_dump() for k, v in ctx.perfiles.items()},
        "indice": ctx.indice().resumen(),
    }


def buscar(ctx, q: dict) -> dict:
    res = _ordenar(
        _filtrados(ctx, q),
        q.get("orden") if q.get("orden") in ORDENES else "relevancia",
    )
    por_pagina = max(1, min(int(_num(q, "por_pagina") or 25), 100))
    pagina = max(1, int(_num(q, "pagina") or 1))
    ini = (pagina - 1) * por_pagina
    return {
        "total": len(res),
        "pagina": pagina,
        "por_pagina": por_pagina,
        "resultados": [_fila(r) for r in res[ini : ini + por_pagina]],
        "indice": ctx.indice().resumen(),
    }


def estadisticas(ctx, q: dict, hoy: date | None = None) -> dict:
    hoy = hoy or datetime.now(TZ).date()
    procs: list[Proceso] = [r.proceso for r in _filtrados(ctx, q)]
    lic = [p for p in procs if p.origen == "licitacion"]
    montos = [p.monto for p in procs if p.monto and p.monto_visible]

    def cierre(p: Proceso) -> date | None:
        return p.fecha_cierre.date() if p.fecha_cierre else None

    # Cierres próximos y publicaciones recientes, por día y origen
    dias_cierre = [hoy + timedelta(days=i) for i in range(14)]
    dias_pub = [hoy - timedelta(days=i) for i in range(13, -1, -1)]
    c_cierre: dict[date, Counter] = defaultdict(Counter)
    c_pub: dict[date, Counter] = defaultdict(Counter)
    for p in procs:
        if (d := cierre(p)) and hoy <= d <= dias_cierre[-1]:
            c_cierre[d][p.origen] += 1
        if p.fecha_publicacion and (d := p.fecha_publicacion.date()) >= dias_pub[0]:
            c_pub[d][p.origen] += 1

    def serie(dias, conteo):
        return [
            {
                "fecha": d.isoformat(),
                "licitacion": conteo[d]["licitacion"],
                "compra_agil": conteo[d]["compra_agil"],
            }
            for d in dias
        ]

    reg: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
    org: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
    for p in procs:
        for agr, clave in (
            (reg, p.comprador.region or "Sin región"),
            (org, p.comprador.organismo or "Sin organismo"),
        ):
            agr[clave][0] += 1
            agr[clave][1] += (p.monto or 0) if p.monto_visible else 0

    def top(agr, n=None):
        filas = sorted(
            ((k, v) for k, v in agr.items() if not k.startswith("Sin ")), key=lambda kv: -kv[1][0]
        )
        return [{"nombre": k, "total": int(v[0]), "monto": v[1]} for k, v in filas[:n]]

    rangos = [
        {"rango": n, "total": sum(1 for m in montos if lo <= m < hi)} for n, lo, hi in RANGOS_MONTO
    ]
    rangos.append({"rango": "Sin monto", "total": len(procs) - len(montos)})
    return {
        "kpis": {
            "total": len(procs),
            "licitaciones": len(lic),
            "compras_agiles": len(procs) - len(lic),
            "monto_total": sum(montos),
            "cierran_hoy": sum(1 for p in procs if cierre(p) == hoy),
            "cierran_7_dias": sum(
                1 for p in procs if (d := cierre(p)) and hoy <= d < hoy + timedelta(days=7)
            ),
            "publicadas_hoy": sum(
                1 for p in procs if p.fecha_publicacion and p.fecha_publicacion.date() == hoy
            ),
            "organismos": len([k for k in org if not k.startswith("Sin ")]),
            "sin_detalle": sum(1 for p in procs if not p.comprador.region),
        },
        "cierres_por_dia": serie(dias_cierre, c_cierre),
        "publicadas_por_dia": serie(dias_pub, c_pub),
        "por_region": top(reg),
        "por_organismo": top(org, 10),
        "por_tipo": [
            {"tipo": k, "total": v} for k, v in Counter(p.tipo or "?" for p in procs).most_common()
        ],
        "rangos_monto": rangos,
        "indice": ctx.indice().resumen(),
    }


def proceso(ctx, codigo: str) -> dict | None:
    p = ctx.indice().por_codigo(codigo.strip().upper())
    if not p:
        return None
    d = p.model_dump(mode="json", exclude_none=True)
    d["dias_al_cierre"], d["url_ficha"] = p.dias_al_cierre(), p.url_ficha
    return d


def adjuntos(ctx, codigo: str) -> dict:
    from mp_core.ficha_web import url_adjuntos_licitacion

    codigo = codigo.strip().upper()
    if es_compra_agil(codigo):
        p = ctx.indice().por_codigo(codigo)
        return {
            "codigo": codigo,
            "url": p.url_ficha if p else None,
            "documentos": [d.nombre for d in p.documentos] if p else [],
        }
    return {"codigo": codigo, "url": url_adjuntos_licitacion(codigo, ctx.store)}


# --- HTTP ------------------------------------------------------------------------
def _json(data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})


def rutas(token: str, ctx_fn=_ctx) -> list[Route]:
    base = f"/{token}"

    def pagina(_: Request) -> Response:
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(
            html, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
        )

    def api_opciones(_: Request):
        return _json(opciones(ctx_fn()))

    def api_buscar(req: Request):
        return _json(buscar(ctx_fn(), dict(req.query_params)))

    def api_estadisticas(req: Request):
        return _json(estadisticas(ctx_fn(), dict(req.query_params)))

    def api_proceso(req: Request):
        d = proceso(ctx_fn(), req.path_params["codigo"])
        return _json(d) if d else _json({"error": "No está en el índice"}, 404)

    def api_adjuntos(req: Request):
        return _json(adjuntos(ctx_fn(), req.path_params["codigo"]))

    return [
        Route(base, lambda _: RedirectResponse(f"{base}/"), methods=["GET"]),
        Route(f"{base}/", pagina, methods=["GET"]),
        Route(f"{base}/api/opciones", api_opciones, methods=["GET"]),
        Route(f"{base}/api/buscar", api_buscar, methods=["GET"]),
        Route(f"{base}/api/estadisticas", api_estadisticas, methods=["GET"]),
        Route(f"{base}/api/proceso/{{codigo}}", api_proceso, methods=["GET"]),
        Route(f"{base}/api/adjuntos/{{codigo}}", api_adjuntos, methods=["GET"]),
    ]
