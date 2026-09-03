"""Rearma temas_dos_niveles.jsonl desde el checkpoint. No usa la API.

Correr esto SIEMPRE al terminar una corrida, y también si el proceso murió a
medias: el checkpoint hace fsync por renglón pero el .jsonl se vacía por lotes,
así que el .jsonl puede ir atrás. El checkpoint es la fuente de verdad.
"""
import json

from estenograficas.checkpoint import Checkpoint
from estenograficas.config import paths
from estenograficas.temas_dos_niveles import (
    MAX_CARACTERES,
    reconstruir_desde_checkpoint,
    textos_por_id,
)

p = paths()
ck = Checkpoint("temas_dos_niveles")
textos = textos_por_id(p.hilos)
filas = reconstruir_desde_checkpoint(ck, textos)

# Los ids del checkpoint pueden apuntar a preguntas que ya no existen: cuando el
# parser se corrige y parte un hilo en dos, los turnos siguientes se renumeran y
# el id viejo queda huérfano. Pasó el 2026-08-30 al arreglar el tope de longitud
# del medio: 4,161 renglones quedaron señalando a la nada, sin texto que los
# respalde. Sin este filtro se cuelan al dataset y contaminan cualquier conteo,
# y encima sin fragmento de procedencia, que es lo que la regla dura 5 exige.
#
# **No se borran del checkpoint**: son la bitácora de lo que se pagó, y el
# checkpoint es append-only a propósito. Solo se excluyen de la salida.
# El id es `conferencia-hNN-tNN`, y de esas tres partes **solo el número de
# hilo se mueve** al recorregir el parser: si una conferencia gana una tanda,
# todas las siguientes se renumeran. El `orden` del turno no se mueve, porque
# los turnos no cambiaron. Así que antes de declarar huérfana una fila se
# intenta reencontrarla por `(conferencia, orden)`, que sí es estable.
#
# Esto no es un parche cosmético: sin él, corregir el parser tira a la basura
# clasificaciones ya pagadas. La corrida del 2026-09-03 iba a perder 8,162.
def _estable(pid: str) -> str:
    conf, _, resto = pid.rpartition("-h")
    return f"{conf}-t{resto.split('-t')[-1]}" if resto else pid


por_estable = {_estable(k): k for k in textos}
recuperadas = 0
for c in filas:
    if c.id_pregunta in textos:
        continue
    nuevo_id = por_estable.get(_estable(c.id_pregunta))
    if nuevo_id:
        c.id_pregunta = nuevo_id
        c.fragmento = (textos[nuevo_id] or "")[:MAX_CARACTERES]
        recuperadas += 1

huerfanas = [c for c in filas if c.id_pregunta not in textos]
filas = [c for c in filas if c.id_pregunta in textos]

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
print(f"  reencontradas por (conferencia, orden) tras re-parsear: {recuperadas:,}")
print(f"  huérfanas excluidas (ya no existen ni así): {len(huerfanas):,}")
