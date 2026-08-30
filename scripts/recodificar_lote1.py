"""Arma la hoja para recodificar el lote 1 con el libro de códigos final.

Sirve para dos cosas a la vez:

1. **Mide la consistencia del humano consigo mismo.** Si no coincide con lo que
   puso la primera vez, las categorías están vagas y ningún clasificador lo
   arregla. Era la fase que faltaba.
2. **Da un conjunto de ajuste limpio para el prompt.** El lote 1 se codificó
   antes de que quedaran fijas la regla del golpe, la de peticiones y la fusión
   del cuarto valor, así que no es consistente con el libro de códigos vigente.

**La hoja sale en blanco y en otro orden.** Ver la respuesta anterior mediría
memoria, no criterio; y el orden original es en sí mismo una pista. Las
respuestas viejas se conservan intactas en `muestra_oro_hoja.xlsx`, que este
script no toca.

    python scripts/recodificar_lote1.py
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from estenograficas.config import paths  # noqa: E402
from estenograficas.postura import VALORES  # noqa: E402

SEMILLA = 20260830


def main() -> int:
    import pandas as pd
    from openpyxl import Workbook
    from openpyxl.worksheet.datavalidation import DataValidation

    p = paths()
    lote1 = {r["codigo"] for r in csv.DictReader(
        open(p.gold / "muestra_oro_LLAVE_no_abrir.csv", encoding="utf-8"))
        if r["lote"] == "1"}

    d = pd.read_excel(p.gold / "muestra_oro_hoja.xlsx", sheet_name="lote 1")
    filas = [r for _, r in d.iterrows() if r["codigo"] in lote1]
    random.Random(SEMILLA).shuffle(filas)   # el orden original es una pista

    wb = Workbook()
    ws = wb.active
    ws.title = "recodificación"
    ws.append(["codigo", "lo que se dijo antes", "PREGUNTA A CODIFICAR",
               "lo que siguió", "postura", "fragmento que te hizo decidir",
               "notas / dudas"])
    for r in filas:
        ws.append([r["codigo"], r["lo que se dijo antes"],
                   r["PREGUNTA A CODIFICAR"], r["lo que siguió"], "", "", ""])

    dv = DataValidation(type="list", formula1='"' + ",".join(VALORES) + '"',
                        allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)
    dv.add(f"E2:E{len(filas) + 1}")
    for col, ancho in zip("ABCDEFG", (9, 50, 68, 44, 21, 36, 30)):
        ws.column_dimensions[col].width = ancho
    ws.freeze_panes = "E2"
    for fila in ws.iter_rows(min_row=1, max_row=len(filas) + 1):
        for celda in fila:
            celda.alignment = celda.alignment.copy(wrap_text=True, vertical="top")

    destino = p.gold / "recodificacion_lote1.xlsx"
    n = 2
    while destino.exists():
        try:
            destino.rename(destino)  # ¿está abierta en Excel?
            break
        except PermissionError:
            destino = p.gold / f"recodificacion_lote1_v{n}.xlsx"
            n += 1
    wb.save(destino)

    print(f"hoja  : {destino}")
    print(f"        {len(filas)} preguntas, en blanco y en otro orden")
    print(f"valores: {', '.join(VALORES)}")
    print("\nTus respuestas de la primera vuelta siguen en muestra_oro_hoja.xlsx.")
    print("No las mires antes de recodificar: eso mediría memoria, no criterio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
