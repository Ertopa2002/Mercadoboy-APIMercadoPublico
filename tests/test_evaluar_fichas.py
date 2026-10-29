import copy
import importlib.util
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ev", RAIZ / "scripts" / "evaluar_fichas.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

ESP = json.loads((RAIZ / "evals" / "esperados" / "2793-1032-COT26.json").read_text())


def test_ficha_identica_100():
    r = ev.evaluar(ESP, copy.deepcopy(ESP))
    assert all(v["acierto"] for v in r.values())
    assert all(v["cita"] in (True, None) for v in r.values())


def test_no_indicado_vs_dato_es_error():
    gen = copy.deepcopy(ESP)
    gen["campos"]["programa_integridad"] = {"valor": True, "fuente": {"pagina": 2}}
    gen["campos"]["plazo_lugar_entrega"] = "No indicado"
    r = ev.evaluar(ESP, gen)
    assert not r["programa_integridad"]["acierto"]
    assert not r["plazo_lugar_entrega"]["acierto"]


def test_tolera_redaccion_y_orden():
    gen = copy.deepcopy(ESP)
    prods = gen["campos"]["productos"]["valor"]
    prods.reverse()
    prods[0]["producto"] = prods[0]["producto"].upper()
    gen["campos"]["plazo_lugar_entrega"]["valor"] = "2 dias"
    assert ev.evaluar(ESP, gen)["productos"]["acierto"]
    assert ev.evaluar(ESP, gen)["plazo_lugar_entrega"]["acierto"]


def test_productos_faltantes_o_cantidad_mal():
    gen = copy.deepcopy(ESP)
    gen["campos"]["productos"]["valor"] = gen["campos"]["productos"]["valor"][:5]
    assert not ev.evaluar(ESP, gen)["productos"]["acierto"]
    gen = copy.deepcopy(ESP)
    for p in gen["campos"]["productos"]["valor"]:
        p["cantidad"] = 1
    assert not ev.evaluar(ESP, gen)["productos"]["acierto"]


def test_objeto_por_clave():
    d = {"id": "muestras", "tipo": "objeto", "clave": "exige"}
    esp = {"valor": {"exige": True, "lugar": "Bodega central"}}
    assert ev.comparar(d, esp, {"valor": {"exige": "Sí", "lugar": "bodega central, Santiago"}})
    assert not ev.comparar(d, esp, {"valor": {"exige": False}})


def test_cita_pagina_incorrecta():
    gen = copy.deepcopy(ESP)
    gen["campos"]["plazo_lugar_entrega"]["fuente"]["pagina"] = 1
    assert ev.evaluar(ESP, gen)["plazo_lugar_entrega"]["cita"] is False


def test_cli(tmp_path, capsys):
    (tmp_path / "e").mkdir()
    (tmp_path / "s").mkdir()
    (tmp_path / "e" / "x.json").write_text(json.dumps(ESP))
    (tmp_path / "s" / "x.json").write_text(json.dumps(ESP))
    assert ev.main(["--esperados", str(tmp_path / "e"), "--salidas", str(tmp_path / "s")]) == 0
    assert "Acierto total: 100.0%" in capsys.readouterr().out
