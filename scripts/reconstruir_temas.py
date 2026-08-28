"""Rearma temas_dos_niveles.jsonl desde el checkpoint. No usa la API.

Correr esto SIEMPRE al terminar una corrida, y también si el proceso murió a
medias: el checkpoint hace fsync por renglón pero el .jsonl se vacía por lotes,
así que el .jsonl puede ir atrás. El checkpoint es la fuente de verdad.
"""
import json

from estenograficas.checkpoint import Checkpoint
from estenograficas.config import paths
from estenograficas.temas_dos_niveles import reconstruir_desde_checkpoint, textos_por_id

p = paths()
ck = Checkpoint("temas_dos_niveles")
textos = textos_por_id(p.hilos)
filas = reconstruir_desde_checkpoint(ck, textos)

dest = p.interim / "temas_dos_niveles.jsonl"
tmp = dest.with_suffix(".tmp")
with open(tmp, "w", encoding="utf-8") as f:
    for c in filas:
        f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")

try:
    tmp.replace(dest)
    destino = dest.name
except PermissionError:
    destino = tmp.name
    print(f"OJO: {dest.name} está abierto por la corrida en marcha.")
    print(f"     Lo reconstruido quedó en {tmp.name}; volver a correr esto al terminar.")

print(f"reconstruidos {len(filas)} renglones en {destino}")
print(f"  del checkpoint : {len(ck.hechos())} hechas, {len(ck.rechazados())} rechazadas")
sin = sum(1 for c in filas if not c.fragmento)
print(f"  sin fragmento recuperable: {sin}")
