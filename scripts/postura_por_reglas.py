"""Capa de reglas sobre la postura, por mandato explícito del humano (2026-08-30).

    «Todas las tandas que digan explícitamente "prian", "prianismo" etc. son a
    favor; todo lo que diga "oposición" es a favor; todo lo que diga neoliberal,
    viejo régimen, es afín. Todo lo que venga de los reporteros identificados
    [por la fuente externa] como adherentes al régimen es afín. No es científica
    esa clasificación, pero es correcta. Te mandato a que clasifiques de esa
    forma.»

El humano reconoce que no es una clasificación científica y la ordena de todos
modos. Se implementa **como capa aparte**, no sobreescribiendo nada: cada
pregunta conserva su etiqueta del modelo, recibe la etiqueta por regla, y se
registra **qué regla disparó**. Así las dos versiones se pueden reportar y
auditar, y revertir la decisión no cuesta nada.

DOS COSAS QUE HAY QUE DECIR AL PUBLICAR, medidas antes de aplicar:

1. **La regla de «oposición» arrastra falsos positivos.** La palabra no siempre
   nombra al bloque político —«una oposición de un sector de la población de
   Milpa Alta» es gente oponiéndose a una obra— y aparece dentro de críticas al
   gobierno: «la oposición también podría criticar que su gobierno está
   reinterpretando estas cifras». Son 238 preguntas y solo el 44% ya eran afín
   para el modelo.

2. **La regla por periodista vuelve circular cualquier hallazgo sobre
   periodistas.** Son 4,385 preguntas, el 19.5% del corpus. Si un periodista es
   afín por estar en una lista, no se puede después reportar como hallazgo que
   ese periodista hace preguntas afines: lo decidió la lista, no el dato. Los
   conteos por periodista deben publicarse **solo** con la capa del modelo.

La lista de periodistas se lee en tiempo de ejecución desde `assets/`, que está
en `.gitignore`. Ningún nombre de esa lista queda escrito en el repositorio.

    python scripts/postura_por_reglas.py [--sin-oposicion] [--sin-periodistas]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from estenograficas.config import paths  # noqa: E402

AFIN = "afín al gobierno"

LEXICO = {
    "prian": r"\bpri+an\w*",
    "oposicion": r"\boposici[oó]n\w*|\bopositor\w*",
    "neoliberal": r"\bneoliberal\w*",
    "viejo_regimen": r"\bviejo\s+r[eé]gimen\b|\bantiguo\s+r[eé]gimen\b",
    # Expresidentes de PRI y PAN. Mandato del humano del 2026-08-30.
    # `Salinas` captura también a Ricardo Salinas Pliego, que no es
    # expresidente pero sí un rival del gobierno, así que la regla se sostiene
    # bajo el mismo criterio. Queda dicho para que no parezca un descuido.
    "expresidentes": (r"\bCalder[oó]n\b|\bPe[ñn]a\s+Nieto\b|\bVicente\s+Fox\b"
                      r"|\bZedillo\b|\bSalinas\b"),
}
LISTA_EXTERNA = Path("assets") / "orientacion_externa_2026-08-28.csv"


def periodistas_afines() -> set[str]:
    """Nombres marcados a favor por la fuente externa. Nunca se escriben a disco."""
    if not LISTA_EXTERNA.exists():
        print(f"no está {LISTA_EXTERNA}; se omite la regla por periodista",
              file=sys.stderr)
        return set()
    filas = [l for l in LISTA_EXTERNA.read_text(encoding="utf-8").splitlines()
             if l and not l.startswith("#")]
    return {r["clave"] for r in csv.DictReader(filas)
            if r["nivel"] == "periodista"
            and r["orientacion_fuente"] == "a_favor_del_gobierno"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sin-oposicion", action="store_true",
                    help="omitir la regla léxica de «oposición», la de más ruido")
    ap.add_argument("--sin-periodistas", action="store_true",
                    help="omitir la regla por periodista, la que vuelve circular "
                         "cualquier conteo por periodista")
    args = ap.parse_args()

    p = paths()
    lex = {k: re.compile(v, re.I) for k, v in LEXICO.items()
           if not (args.sin_oposicion and k == "oposicion")}
    afines = set() if args.sin_periodistas else periodistas_afines()

    preguntas = {}
    for linea in p.hilos.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        h = json.loads(linea)
        for t in h["turnos"]:
            if t["rol"] == "pregunta" and not t["ruido"]:
                preguntas[f'{h["conferencia_id"]}-h{h["hilo"]}-t{t["orden"]}'] = (
                    " ".join(t["texto"].split()), h["periodista"])

    modelo = {}
    for linea in (p.interim / "postura.jsonl").read_text(encoding="utf-8").splitlines():
        if linea.strip():
            r = json.loads(linea)
            modelo[r["id_pregunta"]] = (r["postura"], r["fragmento"])

    salida = p.outputs / "postura_final.jsonl"
    salida.parent.mkdir(parents=True, exist_ok=True)
    cuenta, volteadas = Counter(), Counter()
    with salida.open("w", encoding="utf-8") as f:
        for pid, (texto, periodista) in sorted(preguntas.items()):
            del_modelo, fragmento = modelo.get(pid, (None, ""))
            reglas = [k for k, rx in lex.items() if rx.search(texto)]
            if periodista and periodista in afines:
                reglas.append("periodista_en_lista_externa")
            final, metodo = (AFIN, "regla") if reglas else (del_modelo, "llm")
            if reglas and del_modelo and del_modelo != AFIN:
                volteadas[del_modelo] += 1
            cuenta[final] += 1
            f.write(json.dumps({
                "id_pregunta": pid,
                "postura": final,
                "metodo": metodo,
                "reglas": reglas,
                "postura_modelo": del_modelo,
                "fragmento_modelo": fragmento,
            }, ensure_ascii=False) + "\n")

    total = sum(cuenta.values())
    con_regla = sum(1 for _ in ())  # se recalcula abajo
    con_regla = sum(v for k, v in Counter(
        "regla" if any(rx.search(t) for rx in lex.values())
        or (per and per in afines) else "llm"
        for t, per in preguntas.values()).items() if k == "regla")

    print(f"escrito: {salida}")
    print(f"  {total:,} preguntas · {con_regla:,} decididas por regla "
          f"({100*con_regla/total:.1f}%)\n")
    base = sum(v for k, v in cuenta.items()
               if k in (AFIN, "crítica al gobierno", "neutral"))
    for k in (AFIN, "crítica al gobierno", "neutral"):
        print(f"  {k:22}{cuenta[k]:8,}{100*cuenta[k]/base:7.1f}%")
    print(f"\n  volteadas por las reglas: {sum(volteadas.values()):,}")
    for k, v in volteadas.most_common():
        print(f"      {v:6,}  el modelo decía «{k}»")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
