"""Compara fichas generadas por el agente con las esperadas (hito H2: ≥ 90% de acierto).

Uso:
    uv run python scripts/evaluar_fichas.py [--esperados evals/esperados] [--salidas evals/salidas]

Cada archivo <codigo>.json de salidas se compara con el de esperados. Ver docs/ficha-analisis.md.
"""

import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS = json.loads((RAIZ / "evals" / "ficha" / "campos.json").read_text())["campos"]
NO_INDICADO = "no indicado"
UMBRAL_TEXTO, UMBRAL_LISTA = 0.75, 0.8


def norm(x) -> str:
    t = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\(p(ag)?\.?\s*\d+\)", " ", t)  # citas inline
    return " ".join(re.sub(r"[^a-z0-9%$ ]+", " ", t).split())


def valor(campo):
    if isinstance(campo, dict) and "valor" in campo:
        return campo["valor"]
    return campo


def es_no_indicado(v) -> bool:
    return isinstance(v, str) and norm(v) == NO_INDICADO or v is None


def sim(a, b) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return float(a == b)
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def a_bool(v):
    if isinstance(v, bool):
        return v
    t = norm(v)
    if t in ("si", "true", "exige", "requiere"):
        return True
    if t in ("no", "false", "no exige", "no requiere"):
        return False
    return None


def f1_listas(esp: list, gen: list, igual) -> float:
    if not esp and not gen:
        return 1.0
    usados, aciertos = set(), 0
    for e in esp:
        for j, g in enumerate(gen):
            if j not in usados and igual(e, g):
                usados.add(j)
                aciertos += 1
                break
    p = aciertos / len(gen) if gen else 0
    r = aciertos / len(esp) if esp else 0
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def _num(x):
    try:
        return float(str(x).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def producto_igual(e, g) -> bool:
    if not isinstance(e, dict) or not isinstance(g, dict):
        return sim(e, g) >= UMBRAL_TEXTO
    if sim(e.get("producto", ""), g.get("producto", "")) < 0.6:
        return False
    ce, cg = _num(e.get("cantidad")), _num(g.get("cantidad"))
    return ce is None or ce == cg


def comparar(defn: dict, esp, gen) -> bool:
    ve, vg = valor(esp), valor(gen)
    if es_no_indicado(ve) or es_no_indicado(vg):
        return es_no_indicado(ve) and es_no_indicado(vg)
    tipo = defn["tipo"]
    if tipo == "bool":
        return a_bool(ve) == a_bool(vg)
    if tipo == "texto":
        return sim(ve, vg) >= UMBRAL_TEXTO
    if tipo in ("lista", "lista_productos"):
        ve = ve if isinstance(ve, list) else [ve]
        vg = vg if isinstance(vg, list) else [vg]
        igual = (
            producto_igual
            if tipo == "lista_productos"
            else (lambda a, b: sim(valor(a), valor(b)) >= UMBRAL_TEXTO)
        )
        return f1_listas(ve, vg, igual) >= UMBRAL_LISTA
    if tipo == "objeto":
        if not isinstance(ve, dict) or not isinstance(vg, dict):
            return sim(json.dumps(ve), json.dumps(vg)) >= UMBRAL_TEXTO
        clave = defn.get("clave")
        if clave and a_bool(ve.get(clave)) != a_bool(vg.get(clave)):
            return False
        for k, x in ve.items():
            if k == clave or x in (None, "", NO_INDICADO) or es_no_indicado(x):
                continue
            if sim(x, vg.get(k, "")) < UMBRAL_TEXTO:
                return False
        return True
    return sim(ve, vg) >= UMBRAL_TEXTO


def cita_ok(esp, gen) -> bool | None:
    """None si el esperado no trae página; True si la generada cita la misma página."""
    pe = (esp.get("fuente") or {}).get("pagina") if isinstance(esp, dict) else None
    if pe is None:
        return None
    pg = (gen.get("fuente") or {}).get("pagina") if isinstance(gen, dict) else None
    return pg == pe


def evaluar(esperada: dict, generada: dict) -> dict:
    res = {}
    for d in CAMPOS:
        e, g = (
            esperada["campos"].get(d["id"], "No indicado"),
            generada.get("campos", {}).get(d["id"], "No indicado"),
        )
        res[d["id"]] = {"acierto": comparar(d, e, g), "cita": cita_ok(e, g)}
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--esperados", default=RAIZ / "evals" / "esperados", type=Path)
    ap.add_argument("--salidas", default=RAIZ / "evals" / "salidas", type=Path)
    a = ap.parse_args(argv)
    pares = [(p, a.salidas / p.name) for p in sorted(a.esperados.glob("*.json"))]
    pares = [(e, s) for e, s in pares if s.exists()]
    if not pares:
        print("No hay pares esperado/salida para comparar.")
        return 1
    por_campo = {d["id"]: [0, 0] for d in CAMPOS}
    citas = [0, 0]
    for e, s in pares:
        esp, gen = json.loads(e.read_text()), json.loads(s.read_text())
        r = evaluar(esp, gen)
        ok = sum(v["acierto"] for v in r.values())
        marca = "" if esp.get("validado_por") else "  (esperado SIN VALIDAR)"
        print(f"{e.stem}: {ok}/{len(r)} campos{marca}")
        for k, v in r.items():
            por_campo[k][0] += v["acierto"]
            por_campo[k][1] += 1
            if v["cita"] is not None:
                citas[0] += v["cita"]
                citas[1] += 1
            if not v["acierto"]:
                print(f"   ✗ {k}")
    total_ok = sum(x[0] for x in por_campo.values())
    total = sum(x[1] for x in por_campo.values())
    print("\nAcierto por campo:")
    for d in CAMPOS:
        ok, n = por_campo[d["id"]]
        print(f"  {d['nombre'][:42]:<42} {ok}/{n}")
    pct = 100 * total_ok / total
    print(f"\nAcierto total: {pct:.1f}% ({total_ok}/{total}) · meta H2: 90%")
    if citas[1]:
        print(
            f"Citas con la página correcta: {100 * citas[0] / citas[1]:.0f}%"
            f" ({citas[0]}/{citas[1]})"
        )
    return 0 if pct >= 90 else 2


if __name__ == "__main__":
    sys.exit(main())
