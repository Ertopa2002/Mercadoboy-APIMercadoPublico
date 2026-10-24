"""Conversión de las respuestas de las APIs de Mercado Público a los modelos del core."""

from typing import Any

from mp_core.models import CompraAgil, Comprador, Documento, Item, Licitacion
from mp_core.normalize import REGIONES, limpiar, parse_fecha, region_codigo, tipo_desde_codigo


def _num(v: Any) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> int | None:
    n = _num(v)
    return int(n) if n is not None else None


def _bool01(v: Any) -> bool | None:
    n = _int(v)
    return None if n is None else n == 1


def licitacion_desde_listado(raw: dict) -> Licitacion:
    """Fila del listado (licitaciones.json por fecha o estado): solo 4 campos."""
    codigo = raw["CodigoExterno"]
    return Licitacion(
        codigo=codigo,
        tipo=tipo_desde_codigo(codigo),
        nombre=limpiar(raw.get("Nombre")) or codigo,
        estado=str(raw.get("CodigoEstado")) if raw.get("CodigoEstado") is not None else None,
        fecha_cierre=parse_fecha(raw.get("FechaCierre")),
    )


def licitacion_desde_detalle(raw: dict) -> Licitacion:
    """Elemento de Listado[] de licitaciones.json?codigo=…"""
    c = raw.get("Comprador") or {}
    f = raw.get("Fechas") or {}
    region = limpiar(c.get("RegionUnidad"))
    items = [
        Item(
            codigo_onu=str(i.get("CodigoProducto") or "") or None,
            categoria=limpiar(i.get("Categoria")),
            nombre=limpiar(i.get("NombreProducto")),
            descripcion=limpiar(i.get("Descripcion")),
            cantidad=_num(i.get("Cantidad")),
            unidad=limpiar(i.get("UnidadMedida")),
        )
        for i in (raw.get("Items") or {}).get("Listado") or []
    ]
    codigo = raw["CodigoExterno"]
    return Licitacion(
        codigo=codigo,
        tipo=limpiar(raw.get("Tipo")) or tipo_desde_codigo(codigo),
        nombre=limpiar(raw.get("Nombre")) or codigo,
        descripcion=limpiar(raw.get("Descripcion")),
        estado=limpiar(raw.get("Estado")),
        monto=_num(raw.get("MontoEstimado")),
        moneda=limpiar(raw.get("Moneda")) or "CLP",
        monto_visible=_int(raw.get("VisibilidadMonto")) != 0,
        fecha_publicacion=parse_fecha(f.get("FechaPublicacion")),
        fecha_cierre=parse_fecha(f.get("FechaCierre") or raw.get("FechaCierre")),
        fecha_fin_preguntas=parse_fecha(f.get("FechaFinal")),
        fecha_publicacion_respuestas=parse_fecha(f.get("FechaPubRespuestas")),
        fecha_visita_terreno=parse_fecha(f.get("FechaVisitaTerreno")),
        fecha_apertura_tecnica=parse_fecha(f.get("FechaActoAperturaTecnica")),
        fecha_apertura_economica=parse_fecha(f.get("FechaActoAperturaEconomica")),
        fecha_adjudicacion=parse_fecha(f.get("FechaAdjudicacion")),
        comprador=Comprador(
            codigo_organismo=limpiar(c.get("CodigoOrganismo")),
            organismo=limpiar(c.get("NombreOrganismo")),
            rut=limpiar(c.get("RutUnidad")),
            unidad=limpiar(c.get("NombreUnidad")),
            comuna=limpiar(c.get("ComunaUnidad")),
            region_codigo=region_codigo(region),
            region=region,
        ),
        items=items,
        etapas=_int(raw.get("Etapas")),
        tiene_contrato=_bool01(raw.get("Contrato")),
        duracion_contrato=_int(raw.get("TiempoDuracionContrato")) or None,
        es_renovable=_bool01(raw.get("EsRenovable")),
        permite_subcontratacion=_bool01(raw.get("SubContratacion")),
        reclamos_organismo=_int(raw.get("CantidadReclamos")),
        detalle_completo=True,
    )


def compra_agil_desde_api(raw: dict) -> CompraAgil:
    """Item del listado (`payload.items[]`) o `payload` del detalle de Compra Ágil v2."""
    inst = raw.get("institucion") or {}
    fechas = raw.get("fechas") or {}
    conv = raw.get("convocatoria") or {}
    montos = raw.get("presupuesto") or raw.get("montos") or {}
    entrega = raw.get("entrega") or {}
    resumen = raw.get("resumen") or {}
    flags = raw.get("flags") or {}
    region_cod = _int(inst.get("region"))
    productos = raw.get("productos_solicitados")
    return CompraAgil(
        codigo=raw["codigo"],
        nombre=limpiar(raw.get("nombre")) or raw["codigo"],
        descripcion=limpiar(raw.get("descripcion")),
        estado=(raw.get("estado") or {}).get("codigo"),
        monto=_num(montos.get("monto_disponible_clp") or montos.get("monto_disponible")),
        moneda="CLP",
        fecha_publicacion=parse_fecha(fechas.get("fecha_publicacion")),
        fecha_cierre=parse_fecha(fechas.get("fecha_cierre")),
        fecha_cierre_segundo_llamado=parse_fecha(
            conv.get("fecha_cierre_segundo_llamado") or fechas.get("fecha_cierre_segundo_llamado")
        ),
        convocatoria=limpiar(conv.get("descripcion")),
        comprador=Comprador(
            organismo=limpiar(inst.get("organismo_comprador")),
            rut=limpiar(inst.get("rut")),
            unidad=limpiar(inst.get("unidad_compra")),
            region_codigo=region_cod,
            region=limpiar(inst.get("nombre_region")) or REGIONES.get(region_cod or 0),
        ),
        items=[
            Item(
                codigo_onu=str(p.get("codigo_producto") or "") or None,
                nombre=limpiar(p.get("nombre")),
                descripcion=limpiar(p.get("descripcion")),
                cantidad=_num(p.get("cantidad")),
                unidad=limpiar(p.get("unidad_medida")),
            )
            for p in productos or []
        ],
        documentos=[
            Documento(id=str(d.get("id")), nombre=d.get("nombre") or "")
            for d in raw.get("documentos") or []
        ],
        direccion_entrega=limpiar(entrega.get("direccion_entrega")),
        plazo_entrega_dias=_int(entrega.get("plazo_entrega_dias")),
        total_ofertas=_int(resumen.get("total_ofertas_recibidas")),
        requisitos_medioambientales=flags.get("considera_requisitos_medioambientales"),
        requisitos_impacto_social=flags.get("considera_requisitos_impacto_social_economico"),
        detalle_completo=productos is not None,
    )
