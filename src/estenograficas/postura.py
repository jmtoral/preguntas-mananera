"""Clasificación de postura: una dimensión, cuatro valores.

El instrumento que contesta la pregunta del proyecto: de las preguntas que la
prensa le hace a la presidenta, cuántas van a favor del gobierno y cuántas en
contra.

**Se codifica fino y se reporta grueso.** Cuatro valores al clasificar; al
reportar se colapsan en tres cubetas (`CUBETAS`). Colapsar después se puede,
desagregar no.

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
    "crítica a un tercero",
    "neutral",
    "no clasificable",
]

CUBETAS = {
    "en contra": ["crítica al gobierno"],
    "a favor": ["afín al gobierno", "crítica a un tercero"],
    "lo que realmente pregunta": ["neutral"],
}
"""Cómo se reportan los cuatro valores. `no clasificable` queda fuera de la base."""

_DEFINICIONES = {
    "crítica al gobierno":
        "pone en aprieto al gobierno federal: señala contradicción, fracaso, "
        "omisión u opacidad, o contrapone su versión con otra",
    "afín al gobierno":
        "lo halaga, da por buena su versión, le ofrece plataforma para lucirse, "
        "o le pide algo tratándolo como interlocutor benévolo",
    "crítica a un tercero":
        "le pega a la oposición, a un actor externo, a un empresario o a la "
        "prensa: la premisa ya da por culpable al tercero",
    "neutral":
        "pide un dato o una explicación sin carga en ninguna dirección",
    "no clasificable":
        "no es una pregunta, o es un fragmento que ni con su contexto se entiende",
}

_REGLAS = """REGLAS DE DECISIÓN, en orden de prioridad:

1. LA CARGA ESTÁ EN LA PREMISA, NO EN EL TEMA. Lee lo que la pregunta da por
   sentado. «¿Hay algún dato de avance sobre la credencialización?» es neutral.
   «Hay avances importantes, ¿cuál es el mensaje que envía?» es afín al
   gobierno. Mismo tema, signo distinto, y la diferencia está entera en la
   premisa.

2. ¿QUIÉN DA EL GOLPE? Si lo da la pregunta —la premisa ya da por culpable al
   tercero— es «crítica a un tercero». Si la pregunta solo tiende la mano para
   que lo dé el gobierno, es «afín al gobierno». «¿Qué tanto daño ha hecho este
   cártel inmobiliario encabezado por el dirigente del PAN?» golpea: crítica a
   un tercero. «¿Cuál es su opinión sobre si el feminismo es compatible con la
   derecha?» tiende la mano: afín al gobierno.

3. SI HABLA DE UN TERCERO PERO LE RECLAMA AL GOBIERNO, ES CRÍTICA AL GOBIERNO.
   La prueba: ¿quién queda mal si la pregunta tiene razón? «Esos casos de
   García Luna están estancados» habla de García Luna y reclama al gobierno
   actual: crítica al gobierno.

4. LAS PETICIONES SON «AFÍN AL GOBIERNO», salvo que traigan reproche. Pedir
   algo trata al gobierno como interlocutor benévolo. Pero «llevamos tres años
   pidiéndolo y nada» es crítica al gobierno: el reproche manda.

5. CRÍTICA NO QUIERE DECIR GROSERA. Incorporar una crítica ajena y pedir
   cuentas por ella —«hay quien percibe que hay prisa, ¿por qué la prisa?»— es
   crítica al gobierno aunque el tono sea amable.

6. SI NO ES UNA PREGUNTA, o es un fragmento que ni con el contexto se entiende,
   es «no clasificable». No adivines."""

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


def _prompt(pasada: int) -> str:
    vals = "\n".join(f"- {v}: {_DEFINICIONES[v]}" for v in _orden_valores(pasada))
    return _INSTRUCCION.format(valores=vals, reglas=_REGLAS)


def clasificar_postura(
    items: Iterable[tuple[str, str, str]],
    ck: Any,
    pasada: int = 0,
    lote: int = LOTE,
    trabajadores: int = 6,
    gasto: Any = None,
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
    sistema = _prompt(pasada)
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
