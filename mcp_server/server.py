"""Conector MCP de Mercadoboy: herramientas para buscar y analizar compras públicas.

Local (stdio):   uv run python -m mcp_server.server
Las herramientas buscan sobre el índice precargado (no gastan cupo) y piden el detalle en
línea solo cuando hace falta.
"""

from datetime import date
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from mcp_server.contexto import contexto
from mp_core.ficha_web import url_adjuntos_licitacion
from mp_core.filtros import Filtro, contiene, filtrar
from mp_core.giros import GIROS, giro
from mp_core.models import Proceso
from mp_core.normalize import REGIONES, es_compra_agil

INSTRUCCIONES = (
    """Conector de Mercado Público (Chile) para un proveedor del rubro alimentos.
- Para buscar oportunidades usa buscar_licitaciones o buscar_compras_agiles. Por defecto aplican
  el perfil del usuario ("mis rubros"); pasa solo_mis_rubros=false para buscar sin perfil.
- Regiones por código: """
    + ", ".join(f"{k}={v}" for k, v in REGIONES.items())
    + """.
- Presenta los resultados en una tabla: ID, nombre, organismo, monto, cierre y días restantes.
- Los adjuntos no se pueden descargar automáticamente (ChileCompra lo bloquea con captcha):
  entrega siempre el enlace de obtener_adjuntos y pide al usuario que suba el PDF al chat.
- Al analizar bases, cita documento y página de cada dato y marca diferencias entre el portal y
  el documento (ej. plazos). Si un dato no aparece, di "No indicado". Recuerda que la decisión de
  ofertar requiere revisión humana.
"""
)

mcp = MCPServer("mercadoboy", instructions=INSTRUCCIONES)

Codigos = Annotated[list[int] | None, Field(description="Códigos de región 1–16")]


def _resumen(p: Proceso, relevancia: int | None = None, motivos: list[str] | None = None) -> dict:
    r: dict[str, Any] = {
        "codigo": p.codigo,
        "origen": p.origen,
        "tipo": p.tipo,
        "nombre": p.nombre,
        "organismo": p.comprador.organismo,
        "region": p.comprador.region,
        "monto": p.monto if p.monto_visible else None,
        "fecha_publicacion": p.fecha_publicacion.isoformat() if p.fecha_publicacion else None,
        "fecha_cierre": p.fecha_cierre.isoformat() if p.fecha_cierre else None,
        "dias_al_cierre": p.dias_al_cierre(),
        "url_ficha": p.url_ficha,
    }
    if relevancia is not None:
        r["relevancia"], r["motivos"] = relevancia, motivos
    return r


def _buscar(origen: str, solo_mis_rubros: bool, usuario: str, limite: int, **kw) -> dict:
    ctx = contexto()
    filtro = Filtro(origenes=[origen], **{k: v for k, v in kw.items() if v not in (None, [])})
    if solo_mis_rubros and (perfil := ctx.perfiles.get(usuario)):
        filtro.giros = [g for n in perfil.giros if (g := giro(n))]
        filtro.regiones = filtro.regiones or perfil.regiones
    indice = ctx.indice()
    res = filtrar(indice.procesos(), filtro)
    limite = max(1, min(limite, 50))
    return {
        "total": len(res),
        "mostrando": min(limite, len(res)),
        "indice_actualizado": indice.resumen()["actualizado"],
        "aviso_cupo": ctx.cupo.estado()["aviso"],
        "resultados": [_resumen(r.proceso, r.relevancia, r.motivos) for r in res[:limite]],
    }


@mcp.tool()
def buscar_licitaciones(
    palabras_clave: Annotated[list[str] | None, Field(description="Ej. ['alimentos']")] = None,
    regiones: Codigos = None,
    tipos: Annotated[list[str] | None, Field(description="L1, LE, LP, LQ, LR…")] = None,
    monto_min: float | None = None,
    monto_max: float | None = None,
    organismo: Annotated[str | None, Field(description="Parte del nombre del organismo")] = None,
    cierre_hasta: Annotated[date | None, Field(description="AAAA-MM-DD")] = None,
    excluir: list[str] | None = None,
    solo_mis_rubros: bool = True,
    usuario: str = "patricio",
    limite: int = 20,
) -> dict:
    """Busca licitaciones publicadas en el índice precargado, ordenadas por relevancia y cierre."""
    return _buscar(
        "licitacion",
        solo_mis_rubros,
        usuario,
        limite,
        palabras_clave=palabras_clave,
        regiones=regiones,
        tipos=tipos,
        monto_min=monto_min,
        monto_max=monto_max,
        organismo=organismo,
        cierre_hasta=cierre_hasta,
        excluir=excluir,
    )


@mcp.tool()
def buscar_compras_agiles(
    palabras_clave: Annotated[list[str] | None, Field(description="Ej. ['baños químicos']")] = None,
    regiones: Codigos = None,
    monto_min: float | None = None,
    monto_max: float | None = None,
    organismo: Annotated[str | None, Field(description="Parte del nombre del organismo")] = None,
    cierre_hasta: Annotated[date | None, Field(description="AAAA-MM-DD")] = None,
    excluir: list[str] | None = None,
    solo_mis_rubros: bool = True,
    usuario: str = "patricio",
    limite: int = 20,
) -> dict:
    """Busca Compras Ágiles (cotizaciones COT) publicadas en el índice precargado."""
    return _buscar(
        "compra_agil",
        solo_mis_rubros,
        usuario,
        limite,
        palabras_clave=palabras_clave,
        regiones=regiones,
        monto_min=monto_min,
        monto_max=monto_max,
        organismo=organismo,
        cierre_hasta=cierre_hasta,
        excluir=excluir,
    )


def _detalle(p: Proceso) -> dict:
    d = p.model_dump(mode="json", exclude_none=True)
    d["dias_al_cierre"] = p.dias_al_cierre()
    d["url_ficha"] = p.url_ficha
    return d


@mcp.tool()
def detalle_licitacion(codigo: Annotated[str, Field(description="Ej. 3553-37-LE26")]) -> dict:
    """Ficha completa de una licitación: comprador, fechas y plazos, ítems, contrato, etapas."""
    lic = contexto().repo.licitacion(codigo.strip().upper())
    return _detalle(lic) if lic else {"error": f"No existe la licitación {codigo}"}


@mcp.tool()
def detalle_compra_agil(codigo: Annotated[str, Field(description="Ej. 2793-1032-COT26")]) -> dict:
    """Ficha completa de una Compra Ágil: productos, cantidades, entrega, presupuesto, adjuntos.

    Ojo: la lista de productos de la API suele ser resumida; el listado real está en el PDF.
    """
    ca = contexto().repo.compra_agil(codigo.strip().upper())
    return _detalle(ca) if ca else {"error": f"No existe la Compra Ágil {codigo}"}


@mcp.tool()
def obtener_adjuntos(codigo: str) -> dict:
    """Enlaces para que el usuario descargue los adjuntos en su navegador y los suba al chat."""
    ctx, codigo = contexto(), codigo.strip().upper()
    if es_compra_agil(codigo):
        ca = ctx.repo.compra_agil(codigo)
        if not ca:
            return {"error": f"No existe la Compra Ágil {codigo}"}
        return {
            "codigo": codigo,
            "documentos": [d.nombre for d in ca.documentos],
            "url_ficha": ca.url_ficha,
            "instruccion": "Abre la ficha, descarga los PDF y súbelos al chat para analizarlos.",
        }
    lic = ctx.repo.licitacion(codigo)
    if not lic:
        return {"error": f"No existe la licitación {codigo}"}
    return {
        "codigo": codigo,
        "url_ficha": lic.url_ficha,
        "url_adjuntos": url_adjuntos_licitacion(codigo, ctx.store),
        "instruccion": "Abre el enlace de adjuntos (pide un captcha), descarga las bases y "
        "anexos y súbelos al chat para analizarlos.",
    }


@mcp.tool()
def buscar_organismo(nombre: str, limite: int = 10) -> dict:
    """Busca organismos compradores por nombre y devuelve su código."""
    orgs = [o for o in contexto().repo.organismos() if contiene(o.nombre, nombre)]
    return {"total": len(orgs), "organismos": [o.model_dump() for o in orgs[:limite]]}


@mcp.tool()
def perfil_usuario(usuario: str = "patricio") -> dict:
    """Perfil por defecto del usuario: giros, palabras clave, regiones y tipos ("mis rubros")."""
    perfil = contexto().perfiles.get(usuario)
    if not perfil:
        return {"error": f"No hay perfil para {usuario}", "disponibles": list(contexto().perfiles)}
    giros = [g.model_dump() for n in perfil.giros if (g := giro(n))]
    return {**perfil.model_dump(), "detalle_giros": giros, "giros_disponibles": list(GIROS)}


@mcp.tool()
def estado_cupo() -> dict:
    """Llamadas usadas hoy a la API de Mercado Público y estado del índice precargado."""
    ctx = contexto()
    return {"cupo": ctx.cupo.estado(), "indice": ctx.indice().resumen()}


if __name__ == "__main__":
    mcp.run()
