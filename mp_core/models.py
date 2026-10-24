"""Modelos tipados del core. Independientes de MCP: los usa el conector y la Etapa 2."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from mp_core.normalize import dias_al_cierre

FICHA_LICITACION = (
    "https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion="
)
FICHA_COMPRA_AGIL = "https://buscador.mercadopublico.cl/ficha?code="


class Comprador(BaseModel):
    codigo_organismo: str | None = None
    organismo: str | None = None
    rut: str | None = None
    unidad: str | None = None
    comuna: str | None = None
    region_codigo: int | None = None
    region: str | None = None


class Item(BaseModel):
    codigo_onu: str | None = None
    categoria: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    cantidad: float | None = None
    unidad: str | None = None


class Documento(BaseModel):
    id: str
    nombre: str
    url: str | None = None


class Organismo(BaseModel):
    codigo: str
    nombre: str


class Proceso(BaseModel):
    """Campos comunes a licitaciones y Compras Ágiles."""

    origen: Literal["licitacion", "compra_agil"]
    codigo: str
    tipo: str | None = None
    nombre: str
    descripcion: str | None = None
    estado: str | None = None
    monto: float | None = None
    moneda: str | None = "CLP"
    monto_visible: bool = True
    fecha_publicacion: datetime | None = None
    fecha_cierre: datetime | None = None
    comprador: Comprador = Field(default_factory=Comprador)
    items: list[Item] = Field(default_factory=list)
    documentos: list[Documento] = Field(default_factory=list)
    detalle_completo: bool = False

    @property
    def url_ficha(self) -> str:
        base = FICHA_COMPRA_AGIL if self.origen == "compra_agil" else FICHA_LICITACION
        return base + self.codigo

    def dias_al_cierre(self, hoy: date | None = None) -> int | None:
        return dias_al_cierre(self.fecha_cierre, hoy)


class Licitacion(Proceso):
    origen: Literal["licitacion"] = "licitacion"
    fecha_fin_preguntas: datetime | None = None
    fecha_publicacion_respuestas: datetime | None = None
    fecha_visita_terreno: datetime | None = None
    fecha_apertura_tecnica: datetime | None = None
    fecha_apertura_economica: datetime | None = None
    fecha_adjudicacion: datetime | None = None
    etapas: int | None = None
    tiene_contrato: bool | None = None
    duracion_contrato: int | None = None
    es_renovable: bool | None = None
    permite_subcontratacion: bool | None = None
    reclamos_organismo: int | None = None


class CompraAgil(Proceso):
    origen: Literal["compra_agil"] = "compra_agil"
    tipo: str | None = "COT"
    convocatoria: str | None = None
    fecha_cierre_segundo_llamado: datetime | None = None
    direccion_entrega: str | None = None
    plazo_entrega_dias: int | None = None
    total_ofertas: int | None = None
    requisitos_medioambientales: bool | None = None
    requisitos_impacto_social: bool | None = None


class PerfilUsuario(BaseModel):
    """Preferencias por defecto de un usuario para filtrar ("mis rubros")."""

    usuario: str
    giros: list[str] = Field(default_factory=list, description="Ej. 'Venta Alimentos'")
    regiones: list[int] = Field(default_factory=list, description="Vacío = todo Chile")
    palabras_clave: list[str] = Field(default_factory=list)
    prefijos_onu: list[str] = Field(
        default_factory=list, description="Ej. '50' = alimentos; '5020' = bebidas"
    )
    tipos: list[str] = Field(default_factory=list, description="Vacío = todos (L1, LE, COT…)")
