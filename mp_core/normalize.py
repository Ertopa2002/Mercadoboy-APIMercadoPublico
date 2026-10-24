"""Normalización de datos de Mercado Público: fechas, códigos, regiones y textos."""

import re
import unicodedata
from datetime import date, datetime

from mp_core.config import TZ

REGIONES: dict[int, str] = {
    1: "Tarapacá",
    2: "Antofagasta",
    3: "Atacama",
    4: "Coquimbo",
    5: "Valparaíso",
    6: "O'Higgins",
    7: "Maule",
    8: "Biobío",
    9: "Araucanía",
    10: "Los Lagos",
    11: "Aysén",
    12: "Magallanes",
    13: "Metropolitana",
    14: "Los Ríos",
    15: "Arica y Parinacota",
    16: "Ñuble",
}

_CODIGO = re.compile(
    r"^(?P<unidad>\d+)-(?P<correlativo>\d+)-(?P<tipo>[A-Z]{1,3}\d?)(?P<anio>\d{2})$"
)


def sin_tildes(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar textos."""
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def limpiar(texto: str | None) -> str | None:
    """Quita espacios sobrantes; devuelve None si queda vacío."""
    if texto is None:
        return None
    t = re.sub(r"\s+", " ", str(texto)).strip()
    return t or None


def parse_fecha(valor: str | None) -> datetime | None:
    """Convierte las fechas de ambas APIs a datetime con zona America/Santiago.

    Formatos vistos: '2026-11-06T15:00:00', '2026-10-23T14:46:15.877', '2026-10-26 10:00',
    '2026-10-23T17:10:00.313Z'. Ojo: en Compra Ágil el sufijo Z aparece en horas que son
    locales (fecha_ultimo_cambio 17:10Z para una compra publicada a las 17:08 locales),
    así que se ignora y toda fecha se interpreta como hora de Chile.
    """
    if not valor:
        return None
    v = str(valor).strip().rstrip("Z").replace(" ", "T")
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ)


def dias_al_cierre(cierre: datetime | None, hoy: date | None = None) -> int | None:
    """Días corridos desde hoy (Santiago) hasta la fecha de cierre. Negativo si ya cerró."""
    if cierre is None:
        return None
    hoy = hoy or datetime.now(TZ).date()
    return (cierre.astimezone(TZ).date() - hoy).days


def partes_codigo(codigo: str) -> dict[str, str] | None:
    """Separa un código de Mercado Público. '3553-37-LE26' -> tipo 'LE', año '26'.

    Sirve para licitaciones (L1, LE, LP, LR, O1, CO…) y Compras Ágiles (COT).
    """
    m = _CODIGO.match(codigo.strip().upper())
    return m.groupdict() if m else None


def tipo_desde_codigo(codigo: str) -> str | None:
    p = partes_codigo(codigo)
    return p["tipo"] if p else None


def es_compra_agil(codigo: str) -> bool:
    return tipo_desde_codigo(codigo) == "COT"


_ALIAS_REGION: list[tuple[str, int]] = [
    ("arica", 15),
    ("tarapaca", 1),
    ("antofagasta", 2),
    ("atacama", 3),
    ("coquimbo", 4),
    ("valparaiso", 5),
    ("higgins", 6),
    ("libertador", 6),
    ("maule", 7),
    ("nuble", 16),
    ("biobio", 8),
    ("bio bio", 8),
    ("araucania", 9),
    ("los rios", 14),
    ("los lagos", 10),
    ("aysen", 11),
    ("magallanes", 12),
    ("metropolitana", 13),
    ("santiago", 13),
]


def region_codigo(nombre: str | None) -> int | None:
    """'Región de Atacama ' -> 3. Compara sin tildes, mayúsculas ni apóstrofos."""
    if not nombre:
        return None
    n = sin_tildes(nombre)
    for clave, codigo in _ALIAS_REGION:
        if clave in n:
            return codigo
    return None
