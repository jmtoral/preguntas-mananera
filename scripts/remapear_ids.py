"""Reencuentra las filas que quedaron huérfanas después de reparsear.

Correr esto después de cada cambio del parser que altere el número de hilos.
No llama a la API: solo reescribe el `id_pregunta` de cada fila al id nuevo
del mismo turno, encontrado por `(conferencia, orden)`.

    python scripts/remapear_ids.py --dry
    python scripts/remapear_ids.py

Lo que no se pueda reencontrar **se conserva y se reporta**, no se borra: una
fila huérfana de verdad significa que ese turno desapareció del corpus, y eso
es un hallazgo sobre el parser, no basura que barrer.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from estenograficas.config import paths
from estenograficas.ids import id_estable, remapear
from estenograficas.temas_dos_niveles import textos_por_id


def procesar(ruta: Path, vivos: dict[str, str], dry: bool) -> tuple[int, int, int]:
    filas = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    por_estable = remapear(vivos)
    ok = recuperadas = perdidas = 0
    for f in filas:
        pid = f.get("id_pregunta")
        if pid in vivos:
            ok += 1
            continue
        nuevo = por_estable.get(id_estable(pid or ""))
        if nuevo:
            f["id_pregunta"] = nuevo
            recuperadas += 1
        else:
            perdidas += 1
    if not dry and recuperadas:
        shutil.copy2(ruta, ruta.with_suffix(ruta.suffix + ".antes_remapeo"))
        tmp = ruta.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for f in filas:
                fh.write(json.dumps(f, ensure_ascii=False) + "\n")
        tmp.replace(ruta)
    return ok, recuperadas, perdidas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry", action="store_true", help="solo reporta, no escribe")
    args = ap.parse_args()

    p = paths()
    vivos = textos_por_id(p.hilos)
    print(f"corpus actual: {len(vivos):,} preguntas\n")

    objetivos = [
        p.outputs / "postura_final.jsonl",
        p.interim / "postura.jsonl",
        p.interim / "temas_dos_niveles.jsonl",
    ]
    for ruta in objetivos:
        if not ruta.exists():
            print(f"{ruta.name:26} no existe")
            continue
        ok, rec, perd = procesar(ruta, vivos, args.dry)
        marca = "" if args.dry else "  (escrito)" if rec else ""
        print(f"{ruta.name:26} intactas {ok:>6} · recuperadas {rec:>6} · "
              f"sin reencontrar {perd:>5}{marca}")
    if args.dry:
        print("\n--dry: no se escribió nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
