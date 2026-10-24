"""Giros (rubros de negocio) y cómo se reconocen en los procesos.

Un giro combina prefijos de código ONU de los productos con palabras clave. Los códigos ONU
vienen mal asignados con frecuencia (evals/extraccion_marca_vencimiento.md), por eso nunca se
usan solos.
"""

from pydantic import BaseModel, Field


class Giro(BaseModel):
    nombre: str
    prefijos_onu: list[str] = Field(default_factory=list)
    palabras: list[str] = Field(default_factory=list)


GIROS: dict[str, Giro] = {
    "venta alimentos": Giro(
        nombre="Venta Alimentos",
        prefijos_onu=["50", "90101603"],  # segmento 50 = alimentos y bebidas; catering
        palabras=[
            "alimentos",
            "abarrotes",
            "colaciones",
            "coffee break",
            "galletas",
            "jugos",
            "agua mineral",
            "cafe",
            "azucar",
            "lacteos",
            "congelados",
            "carnes",
            "frutas",
            "verduras",
            "snack",
            "cafeteria",
            "banqueteria",
        ],
    ),
    "banos quimicos": Giro(
        nombre="Baños químicos",
        prefijos_onu=[],  # se completan con los códigos vistos en procesos reales
        palabras=[
            "bano quimico",
            "banos quimicos",
            "bano portatil",
            "banos portatiles",
            "caseta sanitaria",
            "modulo sanitario",
        ],
    ),
}


def giro(nombre: str) -> Giro | None:
    from mp_core.normalize import sin_tildes

    return GIROS.get(sin_tildes(nombre).strip())
