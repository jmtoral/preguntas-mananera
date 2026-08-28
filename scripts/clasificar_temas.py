"""Clasifica el corpus completo en dos niveles. Reanudable: si se corta,
relanzar este mismo archivo y retoma desde el checkpoint sin volver a pagar
lo hecho. Al terminar, correr scripts/reconstruir_temas.py.

Sobre el universo: entran **todas** las preguntas útiles, sin filtro de
longitud. La primera versión traía `120 < len(texto) < 1500` y eso dejaba fuera
10,139 preguntas —el 45%— sin escribirlas a rechazos, o sea descartadas en
silencio, contra la regla dura 3.

Y no era un descarte inocuo. Las cortas son las **repreguntas**: «¿Tienen algún
número de fallecidos?», «¿Hay algún avance sobre por qué se abrió fuego?». Ésas
son justo la cuarta dimensión del libro de códigos, `insistencia`. Las largas
—604, el 3%— son los turnos de tres preguntas de los periodistas que están
hasta arriba de todos los conteos. El sesgo iba en las dos direcciones y
ninguna era aleatoria.

Lo que sí se excluye, y a propósito, son los saludos: `PREGUNTA: Buenos días,
Presidenta.` Eso ya lo marca el parser como `ruido` y ahí sigue el criterio.
"""
import json, sys, time
from pathlib import Path
from estenograficas.checkpoint import Checkpoint
from estenograficas.config import paths
from estenograficas.temas_dos_niveles import cargar_taxonomia, clasificar_paralelo

ANIOS = ("2024", "2025", "2026")   # corpus completo
MIN_CARACTERES = 12
"""Piso mínimo. Debajo de esto no hay pregunta que clasificar: son restos como
`Millán.` o `Sí.` que el filtro de ruido no atrapó. Se escriben a rechazos con
su razón, no se tiran."""

p = paths()
claves, cats_txt = cargar_taxonomia(p.interim / "taxonomia_temas_candidata.json")
hilos = [json.loads(l) for l in p.hilos.read_text(encoding="utf-8").splitlines() if l.strip()]

preg, muy_cortas = [], []
for h in hilos:
    if not h["conferencia_id"].startswith(ANIOS):
        continue
    for t in h["turnos"]:
        if t["rol"] != "pregunta" or t["ruido"]:
            continue
        pid = f'{h["conferencia_id"]}-h{h["hilo"]}-t{t["orden"]}'
        if len(t["texto"].strip()) < MIN_CARACTERES:
            muy_cortas.append((pid, t["texto"]))
        else:
            preg.append((pid, t["texto"]))
preg.sort()

ck = Checkpoint("temas_dos_niveles")

# Nada se descarta en silencio: las que ni siquiera se mandan al modelo quedan
# registradas con su razón, igual que las que el modelo rechaza.
ya = ck.procesados()
nuevas_cortas = [(k, v) for k, v in muy_cortas if k not in ya]
for pid, texto in nuevas_cortas:
    ck.marcar_rechazado(pid, f"texto de {len(texto.strip())} caracteres, debajo del mínimo")

print(f"preguntas a clasificar: {len(preg):,}", flush=True)
print(f"debajo del mínimo, a rechazos: {len(muy_cortas):,} "
      f"({len(nuevas_cortas):,} nuevas)", flush=True)

vp = p.interim / "vocab_asuntos.json"
vocab = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else []
print(f"ya procesadas: {len(ck.procesados()):,}   vocabulario previo: {len(vocab):,}", flush=True)

salida = p.interim / "temas_dos_niveles.jsonl"
n = 0
t0 = time.time()
with open(salida, "a", encoding="utf-8") as f:
    for c in clasificar_paralelo(preg, claves, cats_txt, ck, vocab=vocab):
        f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
        n += 1
        if n % 50 == 0:
            f.flush(); vp.write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
            print(f"   {n} nuevas · {len(vocab)} asuntos · {time.time()-t0:.0f}s", flush=True)
vp.write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
print(f"\nnuevas: {n}   hechas: {len(ck.hechos())}   rechazadas: {len(ck.rechazados())}", flush=True)
