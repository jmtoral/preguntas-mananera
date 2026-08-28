"""Clasifica el corpus completo en dos niveles. Reanudable: si se corta,
relanzar este mismo archivo y retoma desde el checkpoint sin volver a pagar
lo hecho. Al terminar, correr scripts/reconstruir_temas.py."""
import json, sys, time
from pathlib import Path
from estenograficas.checkpoint import Checkpoint
from estenograficas.config import paths
from estenograficas.temas_dos_niveles import cargar_taxonomia, clasificar

MESES = ("2024","2025","2026")   # corpus completo
p = paths()
claves, cats_txt = cargar_taxonomia(p.interim / "taxonomia_temas_candidata.json")
hilos = [json.loads(l) for l in p.hilos.read_text(encoding="utf-8").splitlines() if l.strip()]

preg = []
for h in hilos:
    if not h["conferencia_id"].startswith(MESES): continue
    for t in h["turnos"]:
        if t["rol"] == "pregunta" and not t["ruido"] and 120 < len(t["texto"]) < 1500:
            preg.append((f'{h["conferencia_id"]}-h{h["hilo"]}-t{t["orden"]}', t["texto"]))
preg.sort()
print(f"preguntas del corpus completo: {len(preg)}", flush=True)

ck = Checkpoint("temas_dos_niveles")
vp = p.interim / "vocab_asuntos.json"
vocab = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else []
print(f"ya procesadas: {len(ck.procesados())}   vocabulario previo: {len(vocab)}", flush=True)

salida = p.interim / "temas_dos_niveles.jsonl"
n = 0
t0 = time.time()
with open(salida, "a", encoding="utf-8") as f:
    for c in clasificar(preg, claves, cats_txt, ck, vocab=vocab):
        f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
        n += 1
        if n % 50 == 0:
            f.flush(); vp.write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
            print(f"   {n} nuevas · {len(vocab)} asuntos · {time.time()-t0:.0f}s", flush=True)
vp.write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
print(f"\nnuevas: {n}   hechas: {len(ck.hechos())}   rechazadas: {len(ck.rechazados())}", flush=True)
