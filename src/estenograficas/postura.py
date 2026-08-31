"""Clasificación de postura: una dimensión, tres valores más un hueco.

El instrumento que contesta la pregunta del proyecto: de las preguntas que la
prensa le hace a la presidenta, cuántas van a favor del gobierno y cuántas en
contra.

Tres valores —`crítica al gobierno`, `afín al gobierno`, `neutral`— más
`no clasificable`, que es un hueco declarado y no una postura. Ver `VALORES`
para por qué se fusionó el cuarto valor que hubo antes.

Las reglas del prompt no las inventó el modelo ni el agente: salieron de la
parada del lote 1, de la codificación a mano. Están también en
`INSTRUCTIVO_CODIFICACION.md`, y las dos versiones tienen que decir lo mismo.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Iterator

MODELO = "gemini-2.5-flash"
TEMPERATURA = 0.0
LOTE = 8
"""Más chico que en temas: la postura es un juicio más fino y los lotes largos
invitan al modelo a despachar los últimos con menos atención."""

PASADAS = 3
PRESUPUESTO_PENSAMIENTO = 0
"""Los tokens de pensamiento se facturan a precio de salida. Ver `Gasto` en
`temas_dos_niveles`: una corrida estimada en $1.08 costó $5 por no apagarlo."""

MAX_CARACTERES = 4000

VALORES = [
    "crítica al gobierno",
    "afín al gobierno",
    "neutral",
    "no clasificable",
]
"""Tres valores más el hueco. Decidido el 2026-08-30 por el humano, después de
codificar las 150 a mano.

Antes había un cuarto valor, `crítica a un tercero`, con el argumento de que
pegarle a la oposición favorece al gobierno **sin ser un halago** y que colapsar
los dos borraría esa distinción. El ejercicio de codificar lo desmintió por dos
lados: el humano lo usó 8 veces de 150 (5.3%) y **el modelo no lo usó ni una vez
en 30**. Una categoría que ni la persona ni la máquina alcanzan con soltura está
mal definida, no mal aplicada.

Y no costó nada fusionarla: los dos valores ya caían en la misma cubeta al
reportar, así que **el resultado es idéntico** —49 preguntas a favor, se cuenten
como 41+8 o como 49—. Lo único que se pierde es poder separar «te halaga» de «le
pega a tu rival», y para eso queda la columna de fragmentos y la capa temática.

El caso que parecía una excepción ya lo cubre la regla 3: si le pegas a un
tercero pero el reclamo aterriza en el gobierno —un gobernador de Morena, un
cártel que el gobierno no controla— es `crítica al gobierno`."""

CUBETAS = {
    "en contra": ["crítica al gobierno"],
    "a favor": ["afín al gobierno"],
    "lo que realmente pregunta": ["neutral"],
}
"""Cómo se reportan. `no clasificable` queda fuera de la base."""

_DEFINICIONES = {
    "crítica al gobierno":
        "la pregunta AFIRMA algo malo del gobierno federal: un fracaso, una "
        "omisión, una contradicción, una versión que contradice la oficial",
    "afín al gobierno":
        "la pregunta AFIRMA algo bueno del gobierno, o algo malo de un rival "
        "suyo —la oposición, un empresario, un gobierno extranjero—",
    "neutral":
        "la pregunta NO AFIRMA NADA: pide un dato, una opinión, una "
        "explicación o una acción, sin dar nada por sentado",
    "no clasificable":
        "no es una intervención de prensa (una cortesía, un saludo), o ni con el "
        "contexto se sabe de qué habla. RARÍSIMO: si entiendes el tema y no hay "
        "carga, eso es neutral, no esto",
}

_REGLAS = """LA PREGUNTA QUE DECIDE TODO: **¿la pregunta AFIRMA algo, o solo pide?**

Hazte siempre esas dos preguntas, en este orden:

  (a) ¿Qué da por sentado esta pregunta? Si no da nada por sentado, es NEUTRAL.
  (b) Si da algo por sentado: ¿eso que afirma deja mal al gobierno, o lo deja
      bien a él y mal a un rival suyo?

Este criterio es deliberadamente **textual**. No preguntes «¿a quién le sirve
esta pregunta?»: casi toda pregunta le da micrófono al gobierno y ese criterio
no se puede aplicar dos veces igual. Pregunta qué **dice** el texto.

REGLAS DE DECISIÓN, en orden de prioridad:

1. PEDIR NO ES AFIRMAR. Pedir un dato, una opinión, una explicación o una
   acción **no afirma nada**: es NEUTRAL. «¿Hay algún dato de avance sobre la
   credencialización?», «¿podría incluirse educación en empatía animal?»,
   «¿cuál es su opinión sobre X?» — las tres son neutrales, por más amable que
   sea el tono y por más que la respuesta pueda lucir al gobierno.

   En cambio «Hay avances importantes, ¿cuál es el mensaje que envía?» **sí
   afirma**: da por hecho que hay avances. Afín al gobierno.

2. **QUE EL TEMA SEA FEO NO VUELVE CRÍTICA A LA PREGUNTA.** Es el error más
   frecuente y el más caro. Preguntar por un desastre, un homicidio, un
   desabasto o una crisis **no afirma que el gobierno falló**: afirma que el
   hecho ocurrió, y eso no es un reproche.

   «¿Cuántos fallecidos hay?», «¿hay algún avance sobre por qué se abrió
   fuego?», «hay adeudos con la industria farmacéutica, ¿a cuánto ascienden?»
   son NEUTRALES: piden el dato de una situación mala que nadie discute.

   Para que sea crítica al gobierno, la pregunta tiene que afirmar que **el
   gobierno** hizo mal, omitió, se contradijo o escondió algo. «¿Por qué no se
   ha hecho nada?» sí. «¿Qué se está haciendo?» no.

3. AFIRMAR ALGO MALO DE UN RIVAL DEL GOBIERNO ES «AFÍN AL GOBIERNO».
   «¿Qué tanto daño ha hecho este cártel inmobiliario encabezado por el
   dirigente del PAN?» da por probado el cargo contra la oposición: afín.
   Pero «¿cuál es su opinión sobre lo que hizo el PAN?» no afirma nada:
   neutral.

4. SI AFIRMA ALGO MALO DE UN TERCERO PERO EL RECLAMO ATERRIZA EN EL GOBIERNO,
   ES CRÍTICA AL GOBIERNO. La prueba: ¿quién queda mal si la pregunta tiene
   razón? «Esos casos de García Luna están estancados» habla de García Luna y
   deja mal al gobierno actual: crítica al gobierno.

5. UNA PETICIÓN CON REPROCHE SÍ AFIRMA. «Llevamos tres años pidiéndolo y nada»
   afirma una omisión: crítica al gobierno. La petición sola, no.

6. CRÍTICA NO QUIERE DECIR GROSERA, Y AFIRMAR NO ES SOLO AFIRMAR EN PRIMERA
   PERSONA. Incorporar una afirmación ajena cuenta: «hay quien percibe que hay
   prisa, ¿por qué la prisa?» afirma que hay prisa. Crítica al gobierno aunque
   el tono sea amable. Igual «se han acercado a nosotros los productores»:
   afirma que hay un problema.

7. «NO CLASIFICABLE» ES RARÍSIMO. Menos de una de cada veinte. Resérvalo para
   turnos que no son intervención de prensa —«Ok, muchas gracias», «Buenos
   días»— o para fragmentos donde ni con el contexto se sabe de qué se habla.

   **No lo uses porque la pregunta sea corta.** Un tercio de este corpus son
   repreguntas de pocas palabras —«¿Podrían ser virtuales las clases?», «¿Y de
   ser necesario, que asistan a declarar?»— y todas son clasificables: el
   contexto dice de qué tratan y la pregunta dice con qué carga.

   **Y sobre todo: no confundas «no le veo carga» con «no puedo clasificar».**
   Que una pregunta no empuje hacia ningún lado no es un hueco, es exactamente
   la definición de «neutral». Si entiendes de qué habla y no carga contra
   nadie ni le sirve a nadie, es NEUTRAL, no «no clasificable»."""

_INSTRUCCION = """Eres un asistente de investigación en análisis de contenido.
Clasificas la POSTURA de preguntas de prensa de las conferencias matutinas de
la Presidencia de México. Una sola dimensión, un solo valor por pregunta.

Este trabajo mide y describe, no adjetiva. Aplica las categorías como las
aplicaría alguien con la posición política contraria.

VALORES POSIBLES:
{valores}

{reglas}

El bloque CONTEXTO está solo para entender de qué se habla: **clasifica
únicamente la PREGUNTA**, no el contexto ni la respuesta que vino después.

Para cada pregunta devuelve el valor y el FRAGMENTO TEXTUAL EXACTO de la
pregunta que justifica tu decisión: entre tres y doce palabras, copiadas tal
cual. Si el valor es «no clasificable», el fragmento va vacío.

Devuelve SOLO JSON:
{{"clasificacion": {{"<id>": {{"postura": "", "fragmento": ""}}, ...}}}}"""


@dataclass
class Postura:
    id_pregunta: str
    pasada: int
    postura: str | None
    fragmento: str
    metodo: str
    modelo: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _orden_valores(pasada: int) -> list[str]:
    """Perturbación 1: el orden en que se listan las categorías.

    Tres corridas con el mismo prompt y temperatura cero coinciden por
    construcción, y esa «consistencia» no mide nada. Perturbar el orden hace que
    el desacuerdo signifique fragilidad real de la clasificación.
    `no clasificable` se queda al final siempre: no es una postura, es un hueco.
    """
    reales = VALORES[:-1]
    if pasada == 0:
        orden = list(reales)
    elif pasada == 1:
        orden = list(reversed(reales))
    else:
        orden = list(reales)
        random.Random(1000 + pasada).shuffle(orden)
    return orden + [VALORES[-1]]


def arma_entrada(pregunta: str, contexto: str, pasada: int) -> str:
    """Perturbación 2: dónde va el contexto respecto de la pregunta."""
    p = f"PREGUNTA: {pregunta[:MAX_CARACTERES]}"
    if not contexto:
        return p
    c = f"CONTEXTO (no clasificar): {contexto}"
    return f"{p}\n{c}" if pasada == 1 else f"{c}\n{p}"


def ejemplos_del_humano(p: Any, n: int = 10, semilla: int = 7) -> tuple[str, set[str]]:
    """Bloque de ejemplos con las decisiones REALES del humano, y qué códigos usó.

    Las reglas escritas son mi paráfrasis de su criterio; los ejemplos son su
    criterio. Contra un desacuerdo sistemático —el modelo lee `crítica al
    gobierno` en el 24% y el humano en el 11%— mostrar casos pesa más que
    describir la regla.

    **Salen solo del lote 1**, que es el conjunto reservado para ajustar. Los
    120 del lote 2 no se tocan: de ahí sale el alfa que se publica. Devuelve
    también los códigos usados para poder medir fuera de ellos.
    """
    import csv

    import pandas as pd

    llave = {r["codigo"]: r["id_pregunta"] for r in csv.DictReader(
        open(p.gold / "muestra_oro_LLAVE_no_abrir.csv", encoding="utf-8"))}
    d = pd.read_excel(p.gold / "recodificacion_lote1.xlsx", sheet_name="recodificación")
    filas = [r for _, r in d.iterrows()
             if pd.notna(r["postura"]) and r["postura"] != "no clasificable"]

    # Reparto equilibrado entre valores: si se muestrea al azar, `crítica al
    # gobierno` casi no aparece —es el 10%— y es justo la que el modelo falla.
    por_valor: dict[str, list] = {}
    for r in filas:
        por_valor.setdefault(r["postura"], []).append(r)
    rnd = random.Random(semilla)
    elegidas = []
    for v in sorted(por_valor):
        rnd.shuffle(por_valor[v])
        elegidas += por_valor[v][: max(2, n // len(por_valor))]
    rnd.shuffle(elegidas)

    bloque, codigos = [], set()
    for r in elegidas:
        q = " ".join(str(r["PREGUNTA A CODIFICAR"]).split())[:300]
        ctx = " ".join(str(r["lo que se dijo antes"]).split())[-180:]
        bloque.append(f"CONTEXTO: …{ctx}\nPREGUNTA: {q}\n→ {r['postura']}")
        codigos.add(r["codigo"])
    texto = ("EJEMPLOS RESUELTOS por el investigador. Cuando dudes, imita estos "
             "antes que tu propio criterio:\n\n" + "\n\n".join(bloque))
    return texto, codigos


def _prompt(pasada: int, ejemplos: str = "") -> str:
    vals = "\n".join(f"- {v}: {_DEFINICIONES[v]}" for v in _orden_valores(pasada))
    base = _INSTRUCCION.format(valores=vals, reglas=_REGLAS)
    return f"{base}\n\n{ejemplos}" if ejemplos else base


def clasificar_postura(
    items: Iterable[tuple[str, str, str]],
    ck: Any,
    pasada: int = 0,
    lote: int = LOTE,
    trabajadores: int = 6,
    gasto: Any = None,
    ejemplos: str = "",
) -> Iterator[Postura]:
    """Clasifica `(id, pregunta, contexto)` en una pasada.

    El checkpoint usa `id#pasada`, así que las tres pasadas conviven sin
    pisarse y cada una se puede reanudar por separado.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from google import genai
    from google.genai import types

    from .config import gemini_api_key

    cliente = genai.Client(api_key=gemini_api_key())
    candado = threading.Lock()
    sistema = _prompt(pasada, ejemplos)
    ya = ck.procesados()
    pend = [(i, q, c) for i, q, c in items if f"{i}#{pasada}" not in ya]
    trozos = [pend[k : k + lote] for k in range(0, len(pend), lote)]

    def trabajo(trozo):
        payload = {i: arma_entrada(q, c, pasada) for i, q, c in trozo}
        error = ""
        for intento in range(3):
            try:
                r = cliente.models.generate_content(
                    model=MODELO,
                    contents=json.dumps(payload, ensure_ascii=False),
                    config=types.GenerateContentConfig(
                        system_instruction=sistema,
                        temperature=TEMPERATURA,
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=PRESUPUESTO_PENSAMIENTO
                        ),
                    ),
                )
                if gasto is not None:
                    with candado:
                        gasto.suma(getattr(r, "usage_metadata", None))
                return trozo, json.loads(r.text).get("clasificacion", {}), ""
            except Exception as e:  # noqa: BLE001 - la razón se registra
                error = f"{type(e).__name__}: {e}"
                time.sleep(2**intento)
        return trozo, {}, error

    with ThreadPoolExecutor(max_workers=trabajadores) as pool:
        futuros = [pool.submit(trabajo, t) for t in trozos]
        for fut in as_completed(futuros):
            trozo, datos, error = fut.result()
            for pid, _, _ in trozo:
                clave = f"{pid}#{pasada}"
                v = datos.get(pid) or {}
                val = (v.get("postura") or "").strip()
                if val not in VALORES:
                    ck.marcar_rechazado(
                        clave, razon=error or f"postura inválida: {val!r}"
                    )
                    continue
                frag = " ".join((v.get("fragmento") or "").split())
                ck.marcar_hecho(clave, postura=val, fragmento=frag)
                yield Postura(pid, pasada, val, frag, "llm", MODELO)


def consenso(votos: list[str]) -> tuple[str | None, bool]:
    """Devuelve `(valor, coinciden_las_tres)`.

    **Las que no coinciden NO se resuelven por mayoría en silencio**: se marcan
    para revisión. Que dos de tres digan lo mismo no vuelve confiable el dato;
    significa que la pregunta es ambigua, y eso es información, no un empate
    que haya que romper.
    """
    if not votos:
        return None, False
    unanime = len(set(votos)) == 1
    mayoria = max(set(votos), key=votos.count)
    return (mayoria if votos.count(mayoria) > len(votos) / 2 else None), unanime


def a_cubeta(valor: str | None) -> str | None:
    for cubeta, valores in CUBETAS.items():
        if valor in valores:
            return cubeta
    return None
