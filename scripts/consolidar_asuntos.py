"""Consolida los asuntos de nivel 2 y deja el mapa en `data/interim/`.

Corre DESPUÉS de `reconstruir_temas.py`, nunca antes: la fuente de verdad es el
checkpoint, y `reconstruir_temas.py` reescribe el JSONL desde ahí.

No toca `temas_dos_niveles.jsonl`. El mapa vive aparte, en
`mapa_consolidacion.json`, para que el asunto crudo que produjo el modelo se
conserve siempre y la consolidación se pueda rehacer con otro umbral sin volver
a pagar la clasificación.

    python scripts/consolidar_asuntos.py [--umbral 0.5] [--minimo 3]
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from estenograficas.config import paths  # noqa: E402
from estenograficas.temas_dos_niveles import _bolsa, consolidar  # noqa: E402


def jaccard(a: str, b: str) -> float:
    A, B = _bolsa(a), _bolsa(b)
    return len(A & B) / max(1, len(A | B))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--umbral", type=float, default=0.5,
                    help="Jaccard mínimo contra el representante (0.5 por omisión)")
    ap.add_argument("--minimo", type=int, default=3,
                    help="variantes mínimas para listar un grupo en el reporte")
    args = ap.parse_args()

    p = paths()
    origen = p.interim / "temas_dos_niveles.jsonl"
    if not origen.exists():
        print(f"falta {origen}; corre antes reconstruir_temas.py", file=sys.stderr)
        return 1

    filas = [json.loads(l) for l in origen.read_text(encoding="utf-8").splitlines() if l.strip()]
    crudos = [f["asunto"] for f in filas if f.get("asunto")]

    t0 = time.time()
    mapa = consolidar(crudos, umbral_jaccard=args.umbral)
    seg = time.time() - t0

    grupos: dict[str, set[str]] = collections.defaultdict(set)
    for crudo, canon in mapa.items():
        grupos[canon].add(crudo)
    fusionan = {k: sorted(v) for k, v in grupos.items() if len(v) > 1}

    conferencias: dict[str, set[str]] = collections.defaultdict(set)
    frecuencia: collections.Counter[str] = collections.Counter()
    for f in filas:
        a = f.get("asunto")
        if not a:
            continue
        canon = mapa.get(a, a)
        conferencias[canon].add(f["id_pregunta"].split("-h")[0])
        frecuencia[canon] += 1

    # Invariante que la versión con union-find no cumplía. Si esto truena, el
    # algoritmo volvió a fusionar por cadenas y los conteos por asunto no valen.
    for canon, miembros in fusionan.items():
        for m in miembros:
            assert jaccard(m, canon) >= args.umbral, f"{m!r} no se parece a {canon!r}"

    una = sum(1 for c in conferencias.values() if len(c) == 1)
    semana = sum(
        1 for c in conferencias.values()
        if len(c) > 1
        and (dt.date.fromisoformat(max(c)) - dt.date.fromisoformat(min(c))).days >= 7
    )

    destino = p.interim / "mapa_consolidacion.json"
    destino.write_text(
        json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"consolidado en {seg:.1f}s con umbral {args.umbral}")
    print(f"  asuntos crudos     : {len(set(crudos)):,}")
    print(f"  asuntos canónicos  : {len(grupos):,}  ({len(fusionan)} grupos fusionan)")
    print(f"  grupo más grande   : {max(len(v) for v in fusionan.values())} variantes")
    print(f"  en una sola conf.  : {una:,} ({100 * una / len(conferencias):.0f}%)")
    print(f"  duran 7 días o más : {semana:,}")
    print(f"  mapa escrito en    : {destino}")

    print(f"\ngrupos con {args.minimo} variantes o más:")
    for canon in sorted(fusionan, key=lambda k: (-len(fusionan[k]), k)):
        miembros = fusionan[canon]
        if len(miembros) < args.minimo:
            continue
        print(f"\n[{len(miembros)} variantes · {frecuencia[canon]} preguntas · "
              f"{len(conferencias[canon])} conferencias] {canon}")
        for m in miembros:
            if m != canon:
                print(f"     + {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
