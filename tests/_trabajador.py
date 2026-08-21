"""Proceso de mentiras para matar de verdad.

No es una prueba; es el subproceso que `test_checkpoint.py` lanza y luego mata
a mitad de camino para comprobar que el checkpoint reanuda. Se llama con guion
bajo al frente para que pytest no intente recolectarlo.

Uso: python _trabajador.py <dir_checkpoints> <n_items> <segundos_por_item>

Imprime a stdout, con flush, el id de cada item que termina. El test lee esa
salida para saber cuándo el trabajador ya avanzó lo suficiente como para que
matarlo sea informativo.
"""

import sys
import time
from pathlib import Path

from estenograficas.checkpoint import Checkpoint, ejecutar


def main() -> int:
    base = Path(sys.argv[1])
    n = int(sys.argv[2])
    espera = float(sys.argv[3])

    ck = Checkpoint("demo", base=base)
    items = [f"item-{i:02d}" for i in range(n)]

    def trabajo(item_id: str) -> dict:
        # El item "item-07" falla siempre, a propósito: sirve para comprobar
        # que un rechazo se registra con su razón y no se reintenta solo.
        if item_id == "item-07":
            raise ValueError("fallo deliberado para probar el archivo de rechazos")
        time.sleep(espera)
        return {"largo": len(item_id)}

    for hecho in ejecutar(items, trabajo, ck):
        print(hecho, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
