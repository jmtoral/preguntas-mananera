"""Clasifica la postura de las preguntas. Reanudable y medido.

    python scripts/clasificar_postura.py --oro --pasadas 1 --dry
    python scripts/clasificar_postura.py --oro          # las 150 codificadas
    python scripts/clasificar_postura.py                # el corpus completo

**El corpus completo no debe correrse antes de que las 150 estén codificadas a
mano.** Si se clasifican las 21 mil primero, la calibración deja de ser a
ciegas y el alfa mide otra cosa. El script lo verifica y se niega.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from estenograficas.checkpoint import Checkpoint  # noqa: E402
from estenograficas.config import paths  # noqa: E402
from estenograficas.postura import (  # noqa: E402
    LOTE,
    PASADAS,
    clasificar_postura,
)
from estenograficas.temas_dos_niveles import Gasto  # noqa: E402

MIN_CARACTERES = 12
CORTA = 200
CONTEXTO_MAX = 600


def universo(p) -> list[tuple[str, str, str]]:
    """`(id, pregunta, contexto)` para todas las preguntas útiles."""
    out = []
    for linea in p.hilos.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        h = json.loads(linea)
        turnos = h["turnos"]
        for i, t in enumerate(turnos):
            if t["rol"] != "pregunta" or t["ruido"]:
                continue
            texto = t["texto"]
            if len(texto.strip()) < MIN_CARACTERES:
                continue
            ctx = ""
            if len(texto) < CORTA:
                for u in reversed(turnos[max(0, i - 2):i]):
                    s = " ".join(u["texto"].split())
                    if s:
                        ctx = s[-CONTEXTO_MAX:]
                        break
            out.append((f'{h["conferencia_id"]}-h{h["hilo"]}-t{t["orden"]}',
                        " ".join(texto.split()), ctx))
    return out


def ids_de_oro(p) -> tuple[set[str], int]:
    """Ids de la muestra de oro y cuántas están codificadas."""
    import csv

    import pandas as pd

    llave = list(csv.DictReader(
        open(p.gold / "muestra_oro_LLAVE_no_abrir.csv", encoding="utf-8")))
    ids = {r["id_pregunta"] for r in llave}
    hoja = p.gold / "muestra_oro_hoja.xlsx"
    n = 0
    if hoja.exists():
        d = pd.concat([pd.read_excel(hoja, sheet_name=s)
                       for s in ("lote 1", "lote 2")])
        n = int(d["postura"].notna().sum())
    return ids, n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--oro", action="store_true",
                    help="solo las 150 de la muestra de oro")
    ap.add_argument("--lote1", action="store_true",
                    help="solo los 30 del lote 1, para probar el prompt")
    ap.add_argument("--pasadas", type=int, default=PASADAS)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    p = paths()
    todo = universo(p)
    oro, codificadas = ids_de_oro(p)

    if args.lote1:
        import csv
        lote1 = {r["id_pregunta"] for r in csv.DictReader(
            open(p.gold / "muestra_oro_LLAVE_no_abrir.csv", encoding="utf-8"))
            if r["lote"] == "1"}
        items = [x for x in todo if x[0] in lote1]
        etiqueta = "lote 1 de la muestra de oro"
    elif args.oro:
        items = [x for x in todo if x[0] in oro]
        etiqueta = "muestra de oro"
    else:
        if codificadas < len(oro):
            print(f"ALTO: la muestra de oro va en {codificadas} de {len(oro)}.\n"
                  "El modelo no corre sobre el corpus antes de que esté codificada "
                  "a mano: si no, la calibración deja de ser a ciegas.\n"
                  "Usa --oro o --lote1 mientras tanto.", file=sys.stderr)
            return 1
        items = todo
        etiqueta = "corpus completo"

    ck = Checkpoint("postura")
    ya = ck.procesados()
    faltan = sum(1 for i, _, _ in items for k in range(args.pasadas)
                 if f"{i}#{k}" not in ya)
    chars = sum(len(q) + len(c) for _, q, c in items) * args.pasadas
    llamadas = faltan / LOTE
    tok_in = chars / 3.6 + 1400 * llamadas
    tok_out = 30 * faltan + 20 * llamadas
    costo = tok_in / 1e6 * 0.30 + tok_out / 1e6 * 2.50

    print(f"universo        : {etiqueta}, {len(items):,} preguntas")
    print(f"pasadas         : {args.pasadas} (perturbadas entre sí)")
    print(f"clasificaciones : {faltan:,} por hacer")
    print(f"costo estimado  : ${costo:.2f} USD  (pensamiento apagado)")
    if args.dry:
        print("\n(--dry: no se llamó a la API)")
        return 0

    gasto = Gasto()
    salida = p.interim / "postura.jsonl"
    n, t0 = 0, time.time()
    with open(salida, "a", encoding="utf-8") as f:
        for pasada in range(args.pasadas):
            for c in clasificar_postura(items, ck, pasada=pasada, gasto=gasto):
                f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
                n += 1
                if n % 100 == 0:
                    f.flush()
                    print(f"   {n:,} · pasada {pasada} · {time.time()-t0:.0f}s"
                          f" · ${gasto.usd:.2f}", flush=True)
    print(f"\nnuevas: {n:,}   rechazadas: {len(ck.rechazados()):,}")
    print(f"GASTO REAL: {gasto.resumen()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
