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

**Las cortas van con su contexto.** Medido: mandadas solas, 1,502 devolvieron
categoría vacía porque no se sostienen por sí mismas. Mandar el turno previo es
lo que la regla dura 4 permite explícitamente —fragmentos acotados, no el
documento entero— y en la prueba de la hoja de ejemplo recuperó 3 de 3.

**Reintenta lo que falló por dinero o por el servidor, no por el dato.** El
2026-08-28 se agotaron los créditos a media corrida y 3,237 preguntas quedaron
rechazadas con `RESOURCE_EXHAUSTED`. Ésas no fallaron por ser lo que son.
"""
import json, re, sys, time
from pathlib import Path
from estenograficas.checkpoint import Checkpoint
from estenograficas.config import paths
from estenograficas.temas_dos_niveles import (
    Gasto,
    cargar_taxonomia,
    clasificar_paralelo,
    con_contexto,
)

ANIOS = ("2024", "2025", "2026")   # corpus completo
MIN_CARACTERES = 12
"""Piso mínimo. Debajo de esto no hay pregunta que clasificar: son restos como
`Millán.` o `Sí.` que el filtro de ruido no atrapó. Se escriben a rechazos con
su razón, no se tiran."""

CORTA = 200
"""Debajo de esto la pregunta va acompañada de su turno previo."""

CONTEXTO_MAX = 600
"""Tope del contexto. Más que esto y el contexto pesa más que la pregunta."""

# Razones de rechazo que se reintentan. Dos familias:
#  - fallos de infraestructura: no fallaron por el dato.
#  - fallos por falta de contexto: el modelo dijo «pregunta incompleta» o «no es
#    una pregunta» porque la recibió suelta. Ahora va con su turno previo, así
#    que merecen otro intento. Las que sigan sin serlo se rechazan de nuevo con
#    su razón, que es lo correcto: son turnos como «Ok, muchas gracias».
REINTENTABLES = ("RESOURCE_EXHAUSTED", "UNAVAILABLE", "DEADLINE_EXCEEDED",
                 "INTERNAL", "ausente: None", "ServerError", "Timeout",
                 "incompleta", "No es una pregunta", "no es una pregunta",
                 "sin contexto", "no_aplica", "informacion_insuficiente",
                 "ausente: ''", "preámbulo")

p = paths()
claves, cats_txt = cargar_taxonomia(p.interim / "taxonomia_temas_candidata.json")
hilos = [json.loads(l) for l in p.hilos.read_text(encoding="utf-8").splitlines() if l.strip()]

preg, muy_cortas = [], []
for h in hilos:
    if not h["conferencia_id"].startswith(ANIOS):
        continue
    turnos = h["turnos"]
    for i, t in enumerate(turnos):
        if t["rol"] != "pregunta" or t["ruido"]:
            continue
        pid = f'{h["conferencia_id"]}-h{h["hilo"]}-t{t["orden"]}'
        texto = t["texto"]
        if len(texto.strip()) < MIN_CARACTERES:
            muy_cortas.append((pid, texto))
            continue
        ctx = ""
        if len(texto) < CORTA:
            for u in reversed(turnos[max(0, i - 2):i]):
                s = " ".join(u["texto"].split())
                if s:
                    ctx = s[-CONTEXTO_MAX:]
                    break
        preg.append((pid, con_contexto(texto, ctx)))
preg.sort()

ck = Checkpoint("temas_dos_niveles")

# Nada se descarta en silencio: las que ni siquiera se mandan al modelo quedan
# registradas con su razón, igual que las que el modelo rechaza.
ya = ck.procesados()
nuevas_cortas = [(k, v) for k, v in muy_cortas if k not in ya]
for pid, texto in nuevas_cortas:
    ck.marcar_rechazado(pid, f"texto de {len(texto.strip())} caracteres, debajo del mínimo")

hechos = set(ck.hechos())
# Un id rechazado que después salió bien está en los dos archivos. Sin restar
# `hechos` se volvería a mandar y se pagaría dos veces por lo mismo.
reintentar = {
    pid for pid, r in ck.rechazados().items()
    if any(x in (r.get("razon") or "") for x in REINTENTABLES)
} - hechos
con_ctx = sum(1 for _, t in preg if t.startswith("CONTEXTO"))
ya_todo = ck.procesados() - reintentar
faltan = [(i, t) for i, t in preg if i not in ya_todo]

print(f"preguntas en el universo : {len(preg):,}  ({con_ctx:,} con contexto)", flush=True)
print(f"debajo del mínimo        : {len(muy_cortas):,} "
      f"({len(nuevas_cortas):,} nuevas a rechazos)", flush=True)
print(f"ya hechas                : {len(hechos):,}", flush=True)
print(f"se reintentan            : {len(reintentar):,} "
      f"(fallaron por créditos, servidor o respuesta vacía)", flush=True)
print(f"POR CLASIFICAR AHORA     : {len(faltan):,}", flush=True)

chars = sum(len(t) for _, t in faltan)
tok_in = chars / 3.6 + 3500 * len(faltan) / 10
tok_out = chars / 3.6 * 0.25 + 40 * len(faltan) / 10
print(f"costo estimado           : ${tok_in/1e6*0.30 + tok_out/1e6*2.50:.2f} USD "
      f"(sin pensamiento; se apagó con thinking_budget=0)", flush=True)

if "--dry" in sys.argv:
    print("\n(--dry: no se llamó a la API)")
    raise SystemExit(0)

vp = p.interim / "vocab_asuntos.json"
vocab = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else []
print(f"vocabulario previo       : {len(vocab):,}\n", flush=True)

salida = p.interim / "temas_dos_niveles.jsonl"
gasto = Gasto()
n = 0
t0 = time.time()
with open(salida, "a", encoding="utf-8") as f:
    for c in clasificar_paralelo(preg, claves, cats_txt, ck, vocab=vocab,
                                 reintentar=reintentar, gasto=gasto):
        f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
        n += 1
        if n % 100 == 0:
            f.flush(); vp.write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
            print(f"   {n:,} nuevas · {len(vocab):,} asuntos · {time.time()-t0:.0f}s"
                  f" · ${gasto.usd:.2f} gastados", flush=True)
vp.write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
print(f"\nnuevas: {n:,}   hechas: {len(ck.hechos()):,}   "
      f"rechazadas: {len(ck.rechazados()):,}", flush=True)
