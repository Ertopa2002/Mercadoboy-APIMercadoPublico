"""Filtros locales sobre procesos precargados (las APIs no filtran por región, monto, rubro ni
palabra clave de forma confiable; ver docs/matriz-campos.md)."""

import re
from datetime import date

from pydantic import BaseModel, Field

from mp_core.giros import Giro
from mp_core.models import PerfilUsuario, Proceso
from mp_core.normalize import sin_tildes

ESTADOS_PUBLICADA = {"publicada", "5"}  # Compra Ágil: 'publicada'; licitaciones: Estado o código 5


class Filtro(BaseModel):
    origenes: list[str] = Field(default_factory=list, description="licitacion, compra_agil")
    regiones: list[int] = Field(default_factory=list)
    tipos: list[str] = Field(default_factory=list, description="L1, LE, LP, COT…")
    monto_min: float | None = None
    monto_max: float | None = None
    codigo_organismo: str | None = None
    organismo: str | None = Field(None, description="Texto contenido en el nombre del organismo")
    solo_publicadas: bool = True
    cierre_desde: date | None = None
    cierre_hasta: date | None = None
    palabras_clave: list[str] = Field(default_factory=list)
    excluir: list[str] = Field(default_factory=list)
    giros: list[Giro] = Field(default_factory=list)
    incluir_solo_rubro: bool = Field(
        False, description="Incluir procesos que calzan solo por código ONU (más ruido)"
    )


class Resultado(BaseModel):
    proceso: Proceso
    relevancia: int
    motivos: list[str]


def _raiz(palabra: str) -> str:
    """Raíz simple para plurales: 'alimentos'->'alimento', 'quimicos'->'quimico'."""
    p = sin_tildes(palabra.strip())
    if len(p) > 5 and p.endswith("es") and not p.endswith("ies"):
        return p[:-2]
    if len(p) > 4 and p.endswith("s"):
        return p[:-1]
    return p


def contiene(texto: str, frase: str) -> bool:
    """Todas las palabras de la frase aparecen en el texto (en cualquier orden), por raíz."""
    t = sin_tildes(texto)
    tokens = [_raiz(x) for x in re.findall(r"\w+", sin_tildes(frase)) if len(x) > 2]
    return bool(tokens) and all(re.search(rf"\b{re.escape(tok)}", t) for tok in tokens)


def _textos(p: Proceso) -> tuple[str, str]:
    """(nombre, resto) para distinguir dónde aparece la palabra."""
    resto = " ".join(
        filter(None, [p.descripcion] + [f"{i.nombre or ''} {i.descripcion or ''}" for i in p.items])
    )
    return p.nombre or "", resto


def _calza_rubro(p: Proceso, prefijos: list[str]) -> bool | None:
    if not prefijos:
        return False
    codigos = [i.codigo_onu for i in p.items if i.codigo_onu]
    if not codigos:
        return None  # sin detalle: no se sabe
    return any(c.startswith(pref) for c in codigos for pref in prefijos)


def evaluar(p: Proceso, f: Filtro) -> Resultado | None:
    """Devuelve el resultado con relevancia y motivos, o None si no pasa el filtro."""
    if f.origenes and p.origen not in f.origenes:
        return None
    if f.regiones and p.comprador.region_codigo not in f.regiones:
        return None
    if f.tipos and (p.tipo or "") not in f.tipos:
        return None
    if f.monto_min is not None and (p.monto is None or p.monto < f.monto_min):
        return None
    if f.monto_max is not None and (p.monto is None or p.monto > f.monto_max):
        return None
    if f.codigo_organismo and p.comprador.codigo_organismo != f.codigo_organismo:
        return None
    if f.organismo and not contiene(p.comprador.organismo or "", f.organismo):
        return None
    if f.solo_publicadas and sin_tildes(p.estado or "") not in ESTADOS_PUBLICADA:
        return None
    cierre = p.fecha_cierre.date() if p.fecha_cierre else None
    if f.cierre_desde and (cierre is None or cierre < f.cierre_desde):
        return None
    if f.cierre_hasta and (cierre is None or cierre > f.cierre_hasta):
        return None

    nombre, resto = _textos(p)
    if any(contiene(f"{nombre} {resto}", x) for x in f.excluir):
        return None

    palabras = list(f.palabras_clave)
    prefijos: list[str] = []
    for g in f.giros:
        palabras += g.palabras
        prefijos += g.prefijos_onu
    if not palabras and not prefijos:
        return Resultado(proceso=p, relevancia=1, motivos=["sin filtro de rubro o palabra"])

    en_nombre = [x for x in palabras if contiene(nombre, x)]
    en_resto = [x for x in palabras if x not in en_nombre and contiene(resto, x)]
    rubro = _calza_rubro(p, prefijos)

    motivos, relevancia = [], 0
    if en_nombre:
        relevancia += 3
        motivos.append(f"palabra en el nombre: {', '.join(en_nombre[:3])}")
    if en_resto:
        relevancia += 2
        motivos.append(f"palabra en descripción o productos: {', '.join(en_resto[:3])}")
    if rubro:
        relevancia += 1
        motivos.append("código ONU del giro")
    if relevancia == 0 or (relevancia == 1 and not f.incluir_solo_rubro):
        return None
    return Resultado(proceso=p, relevancia=relevancia, motivos=motivos)


def filtrar(procesos: list[Proceso], f: Filtro) -> list[Resultado]:
    """Aplica el filtro y ordena por relevancia y luego por cierre más próximo."""
    res = [r for p in procesos if (r := evaluar(p, f))]
    lejano = date(9999, 1, 1)
    return sorted(
        res,
        key=lambda r: (
            -r.relevancia,
            r.proceso.fecha_cierre.date() if r.proceso.fecha_cierre else lejano,
        ),
    )


def filtro_desde_perfil(perfil: PerfilUsuario, **cambios) -> Filtro:
    """Filtro por defecto de 'mis rubros' a partir del perfil del usuario."""
    from mp_core.giros import giro

    base = Filtro(
        regiones=perfil.regiones,
        tipos=perfil.tipos,
        palabras_clave=perfil.palabras_clave,
        giros=[g for n in perfil.giros if (g := giro(n))],
    )
    return base.model_copy(update=cambios)
