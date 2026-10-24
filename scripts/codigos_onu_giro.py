"""Identifica los códigos ONU que usan los compradores para un giro (ej. baños químicos).

Uso:
    uv run python scripts/codigos_onu_giro.py "baños químicos" [paginas]

Recorre las Compras Ágiles publicadas más recientes (por defecto 30 páginas de 50 = 1.500),
busca la frase en el nombre y pide el detalle de hasta 15 coincidencias; además revisa las
licitaciones activas guardadas en exploracion/activas.json. Gasta ~50 llamadas (~4 min).
Resultado: conteo de códigos ONU en exploracion/onu_<frase>.json.
"""

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
from probe_licitaciones import cargar_ticket  # noqa: E402

from mp_core.clients import CompraAgilClient, LicitacionesClient  # noqa: E402
from mp_core.cupo import Cupo  # noqa: E402
from mp_core.filtros import contiene  # noqa: E402
from mp_core.store import MemoryStore  # noqa: E402


def main():
    frase = sys.argv[1] if len(sys.argv) > 1 else "baños químicos"
    paginas = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    ticket = cargar_ticket()
    cupo = Cupo(MemoryStore())
    ca = CompraAgilClient(ticket, cupo, pausa_s=0.5)
    lic = LicitacionesClient(ticket, cupo, pausa_s=1)

    coincidencias = []
    for pag in range(1, paginas + 1):
        items, _ = ca.listar(pagina=pag, ordenar_por="FechaPublicacion")
        coincidencias += [x.codigo for x in items if contiene(x.nombre, frase)]
        if not items:
            break
    print(f"Compras Ágiles con '{frase}' en el nombre: {len(coincidencias)} de ~{paginas * 50}")

    conteo, ejemplos = Counter(), {}
    for codigo in coincidencias[:15]:
        d = ca.detalle(codigo)
        for it in d.items if d else []:
            conteo[it.codigo_onu] += 1
            ejemplos.setdefault(it.codigo_onu, f"{it.nombre} | {(it.descripcion or '')[:70]}")

    activas = Path("exploracion/activas.json")
    if activas.exists():
        for x in json.loads(activas.read_text())["Listado"]:
            if contiene(x["Nombre"], frase):
                d = lic.detalle(x["CodigoExterno"])
                time.sleep(1)
                for it in d.items if d else []:
                    conteo[it.codigo_onu] += 1
                    ejemplos.setdefault(
                        it.codigo_onu, f"{it.nombre} | {(it.descripcion or '')[:70]}"
                    )

    print("\nCódigos ONU encontrados:")
    for cod, n in conteo.most_common():
        print(f"  {cod} ×{n}: {ejemplos[cod]}")
    salida = Path(f"exploracion/onu_{frase.replace(' ', '_')}.json")
    salida.write_text(
        json.dumps(
            {"frase": frase, "codigos": conteo, "ejemplos": ejemplos}, ensure_ascii=False, indent=2
        )
    )
    print(f"\nCupo usado: {cupo.estado()['usado']} -> {salida}")


if __name__ == "__main__":
    main()
