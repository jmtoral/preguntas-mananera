"""Clasificación temática en dos niveles, y consolidación de asuntos.

**Nivel 1, `categoria`:** una de 18, lista cerrada. Es lo que se tabula.
**Nivel 2, `asunto`:** el caso concreto, con nombres. `"Diálogo con Trump sobre
acusaciones a Rocha Moya"`. Es lo que permite seguir una historia en el tiempo.

Por qué dos niveles y no uno. Con solo etiqueta libre salen ~22 mil cadenas
distintas y no se puede cruzar nada contra postura. Con solo 18 categorías se
pierde de vista que dentro de `seguridad_publica_y_justicia` conviven cinco
historias que no tienen que ver entre sí. Medido: en un mes completo, el 38% de
las preguntas cae bajo un asunto que se repite, y sube al 42% al fusionar los
casi-duplicados que el modelo genera aunque se le pida reutilizar.

**La consolidación es de corpus completo, no por mes** (decisión del humano,
2026-08-27). Un caso vive semanas y cruza de un mes a otro; consolidar por mes
lo partiría en dos y volvería invisible cuánto dura un tema en la conferencia,
que es de lo más interesante que este dataset puede medir. El riesgo de fusionar
de más se controla revisando a mano los grupos grandes.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MODELO = "gemini-2.5-flash"
TEMPERATURA = 0.0
LOTE = 10
MAX_CARACTERES = 900
VOCAB_EN_PROMPT = 140
"""Cuántos asuntos ya usados se le recuerdan al modelo en cada llamada."""

_INSTRUCCION = """Eres un asistente de investigación en análisis de contenido. Clasificas
preguntas de prensa de las conferencias matutinas de la Presidencia de México en DOS niveles.

NIVEL 1 — categoria: elige UNA de esta lista cerrada. No inventes categorías.
{cats}

NIVEL 2 — asunto: el caso concreto del que trata la pregunta, en 4 a 9 palabras.
- Nombra actores y hecho: "Rocha Moya y sus nexos con la delincuencia",
  "Revocación de visas a la familia López Beltrán".
- **REUTILIZA EXACTAMENTE un asunto de la lista de abajo si la pregunta trata del
  mismo caso**, aunque el ángulo sea distinto. Copia la cadena tal cual, sin variar
  ni una palabra. Solo inventa uno nuevo si el caso no está en la lista.
- Es el CASO, no la categoría: "Seguridad en Sinaloa" es demasiado general.
- Escribe SIEMPRE en español. Sin calificar: nada de "cuestiona", "critica",
  "polémico", "escándalo".

ASUNTOS YA USADOS (reutiliza literalmente cuando aplique):
{vocab}

Algunas entradas traen un bloque `CONTEXTO (no clasificar):` antes de
`PREGUNTA:`. El contexto está solo para que entiendas de qué se habla:
**clasifica únicamente lo que viene después de `PREGUNTA:`**. Si la pregunta es
un fragmento suelto, el contexto es lo que te dice de qué caso trata.

Devuelve SOLO JSON:
{{"clasificacion": {{"<id>": {{"categoria": "", "asunto": ""}}, ...}}}}"""

PRESUPUESTO_PENSAMIENTO = 0
"""Apaga el razonamiento interno del modelo.

`gemini-2.5-flash` trae *thinking* encendido por omisión y **esos tokens se
cobran a precio de salida**, que es ocho veces el de entrada. Medido a la mala
el 2026-08-28: una corrida estimada en $1.08 costó cerca de $5. La estimación
suponía salida ≈ 25% de la entrada, o sea ningún pensamiento.

Esto es clasificación con esquema fijo y lista cerrada de categorías: no
necesita cadena de razonamiento. Si algún día una tarea sí la necesita, se sube
aquí y **se vuelve a medir el costo**, no se supone.
"""


class Gasto:
    """Acumula el uso real de tokens. Sustituye estimar por medir."""

    # Precios de gemini-2.5-flash, USD por millón. Si cambian, cambian aquí.
    PRECIO_ENTRADA = 0.30
    PRECIO_SALIDA = 2.50

    def __init__(self) -> None:
        self.entrada = self.salida = self.pensamiento = self.llamadas = 0

    def suma(self, uso: Any) -> None:
        if uso is None:
            return
        self.llamadas += 1
        self.entrada += uso.prompt_token_count or 0
        self.salida += uso.candidates_token_count or 0
        self.pensamiento += getattr(uso, "thoughts_token_count", 0) or 0

    @property
    def usd(self) -> float:
        # Los tokens de pensamiento se facturan como salida.
        return (self.entrada / 1e6 * self.PRECIO_ENTRADA
                + (self.salida + self.pensamiento) / 1e6 * self.PRECIO_SALIDA)

    def resumen(self) -> str:
        return (f"{self.llamadas:,} llamadas · entrada {self.entrada:,} · "
                f"salida {self.salida:,} · pensamiento {self.pensamiento:,} · "
                f"**${self.usd:.2f} USD reales**")


MARCA_PREGUNTA = "PREGUNTA:"
"""Separa el contexto de la pregunta dentro de una entrada del lote.

Existe porque el 42% de las preguntas del corpus tienen menos de 120 caracteres
y son repreguntas que **no se sostienen solas**: «¿Habrá alguna fecha en
particular?». Mandadas sin contexto, el modelo devuelve categoría vacía —medido:
1,502 de un tirón—. Mandarlas con su turno previo es lo que la regla dura 4
permite explícitamente, y en la prueba de la hoja de ejemplo recuperó 3 de 3.
"""


def con_contexto(texto: str, contexto: str) -> str:
    """Arma la entrada del lote con su contexto rotulado."""
    if not contexto:
        return texto
    return f"CONTEXTO (no clasificar): {contexto}\n{MARCA_PREGUNTA} {texto}"


def solo_pregunta(entrada: str) -> str:
    """Quita el contexto para guardar el fragmento de procedencia.

    El campo `fragmento` debe justificar la clasificación con el texto de la
    pregunta, no con el del turno anterior.
    """
    i = entrada.find(MARCA_PREGUNTA)
    return entrada[i + len(MARCA_PREGUNTA):].strip() if i != -1 else entrada


@dataclass
class Clasificacion:
    id_pregunta: str
    categoria: str | None
    asunto: str | None
    asunto_canonico: str | None
    metodo: str
    modelo: str
    fragmento: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def cargar_taxonomia(ruta: Path) -> tuple[list[str], str]:
    """Devuelve (claves válidas, bloque de texto para el prompt)."""
    tax = json.loads(ruta.read_text(encoding="utf-8"))
    cats = tax["categorias"]
    claves = [c["clave"] for c in cats]
    texto = "\n".join(f"- {c['clave']}: {c['definicion'][:110]}" for c in cats)
    return claves, texto


def clasificar(
    preguntas: Iterable[tuple[str, str]],
    claves: list[str],
    cats_txt: str,
    ck: Any,
    vocab: list[str] | None = None,
    lote: int = LOTE,
    espera: float = 0.3,
) -> Iterator[Clasificacion]:
    """Clasifica en dos niveles, marcando el checkpoint conforme avanza.

    `vocab` entra y sale mutado: es la memoria de asuntos entre llamadas, y hay
    que conservarla entre corridas o cada relanzada inventaría nombres nuevos
    para casos que ya tenían uno.

    Una pregunta que el modelo no devuelve **se rechaza con su razón**, no se
    pierde: en la prueba de mayo un lote falló y se cayeron 5 de 405 sin que
    nada lo dijera.
    """
    from google import genai
    from google.genai import types

    from .config import gemini_api_key

    cliente = genai.Client(api_key=gemini_api_key())
    vocab = vocab if vocab is not None else []
    pendientes = [(i, t) for i, t in preguntas if i not in ck.procesados()]

    for k in range(0, len(pendientes), lote):
        trozo = pendientes[k : k + lote]
        payload = {i: t[:MAX_CARACTERES] for i, t in trozo}
        vt = "\n".join(f"- {a}" for a in vocab[-VOCAB_EN_PROMPT:]) or "(todavía ninguno)"
        datos: dict[str, Any] = {}
        error = ""
        for intento in range(3):
            try:
                r = cliente.models.generate_content(
                    model=MODELO,
                    contents=json.dumps(payload, ensure_ascii=False),
                    config=types.GenerateContentConfig(
                        system_instruction=_INSTRUCCION.format(cats=cats_txt, vocab=vt),
                        temperature=TEMPERATURA,
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=PRESUPUESTO_PENSAMIENTO
                        ),
                    ),
                )
                datos = json.loads(r.text).get("clasificacion", {})
                error = ""
                break
            except Exception as e:  # noqa: BLE001 - la razón se registra
                error = f"{type(e).__name__}: {e}"
                time.sleep(2**intento)

        for pid, texto in trozo:
            v = datos.get(pid) or {}
            cat = v.get("categoria")
            asu = " ".join((v.get("asunto") or "").split()) or None
            if not cat or cat not in claves:
                ck.marcar_rechazado(
                    pid, razon=error or f"categoría inválida o ausente: {cat!r}"
                )
                continue
            if asu and asu not in vocab:
                vocab.append(asu)
            c = Clasificacion(pid, cat, asu, None, "llm", MODELO, texto[:MAX_CARACTERES])
            ck.marcar_hecho(pid, categoria=cat, asunto=asu)
            yield c
        time.sleep(espera)


# ---------------------------------------------------------------------------
# Consolidación de asuntos (opción B: sobre todo el corpus)
# ---------------------------------------------------------------------------

_VACIAS = set(
    "de la el los las en y a con con por para del al su sus un una unos unas "
    "sobre que se le lo ante tras entre".split()
)


def _bolsa(s: str) -> set[str]:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]{4,}", s) if w not in _VACIAS}


def consolidar(
    asuntos: Iterable[str], umbral_jaccard: float = 0.5
) -> dict[str, str]:
    """Mapa `asunto crudo -> asunto canónico`, sobre TODO el corpus.

    Fusiona por solapamiento de palabras significativas. Es deliberadamente
    conservador: exige que la mitad del vocabulario coincida. El representante
    de cada grupo es el más frecuente, no el más largo ni el primero.

    Sin modelo y sin red: es comparación de cadenas. Los embeddings ayudarían
    con los sinónimos, pero aquí los casi-duplicados son literalmente paráfrasis
    con las mismas palabras clave (`Acuerdo comercial México-Unión Europea` /
    `Renovación acuerdo comercial con Unión Europea`), que es donde una medida
    de solapamiento basta y no cuesta nada.

    **Cada miembro se compara contra el representante, no contra cualquier otro
    miembro.** La versión anterior usaba union-find, que fusiona por cadenas: si
    A se parece a B y B a C, los tres quedan juntos aunque A y C no compartan
    una sola palabra. Medido sobre el corpus completo, eso produjo 6 grupos
    encadenados de 502, pero uno tenía 204 miembros y pegaba
    `Regulación redes sociales` con `Reclutamiento crimen organizado` a través
    de la frase puente `Regulación redes sociales crimen organizado`, con
    Jaccard 0.00 entre los extremos. Un grupo así envenena cualquier conteo por
    asunto sin dar señal de que algo salió mal.

    El costo de la corrección es que el resultado depende del orden en que se
    eligen los representantes. Se recorre de más frecuente a menos frecuente y,
    a frecuencia igual, alfabéticamente, para que dos corridas sobre el mismo
    corpus den el mismo mapa.
    """
    from collections import Counter

    frec = Counter(a for a in asuntos if a)
    # Orden determinista: primero el más frecuente; los empates, alfabéticos.
    nombres = sorted(frec, key=lambda n: (-frec[n], n))
    bolsas = {n: _bolsa(n) for n in nombres}

    # Índice invertido palabra -> posiciones de representantes que la contienen.
    # Jaccard >= umbral exige al menos una palabra en común, así que basta con
    # mirar a los representantes que comparten alguna: sobre el corpus completo
    # baja el trabajo de ~40 millones de comparaciones a unos cientos de miles.
    # Se recorren los candidatos en orden de inserción para que el resultado sea
    # el mismo que daría la comparación exhaustiva.
    representantes: list[str] = []
    indice: dict[str, list[int]] = {}
    mapa: dict[str, str] = {}
    for n in nombres:
        A = bolsas[n]
        if not A:  # sin palabras significativas: nunca se fusiona
            mapa[n] = n
            continue
        candidatos = sorted({i for w in A for i in indice.get(w, ())})
        for i in candidatos:
            B = bolsas[representantes[i]]
            if len(A & B) / len(A | B) >= umbral_jaccard:
                mapa[n] = representantes[i]
                break
        else:
            pos = len(representantes)
            representantes.append(n)
            for w in A:
                indice.setdefault(w, []).append(pos)
            mapa[n] = n
    return mapa


# ---------------------------------------------------------------------------
# Reconstrucción: el checkpoint es la fuente de verdad
# ---------------------------------------------------------------------------


def reconstruir_desde_checkpoint(ck: Any, textos: dict[str, str]) -> list[Clasificacion]:
    """Rearma el JSONL de salida a partir del checkpoint.

    Existe porque el checkpoint hace `fsync` por renglón pero el archivo de
    salida se vacía por lotes, así que si el proceso muere entre dos vaciados
    quedan renglones marcados como hechos que nunca llegaron al `.jsonl`. Al
    reanudar se saltarían por estar en `procesados()` y **faltarían para
    siempre**. Medido en la corrida real: 12 renglones de desfase.

    El checkpoint guarda `categoria` y `asunto`, que es lo que cuesta dinero.
    El `fragmento` se recupera de `hilos.jsonl` por id y no requiere la API.
    """
    salida = []
    for pid, r in sorted(ck.hechos().items()):
        salida.append(
            Clasificacion(
                id_pregunta=pid,
                categoria=r.get("categoria"),
                asunto=r.get("asunto"),
                asunto_canonico=None,
                metodo="llm",
                modelo=MODELO,
                fragmento=(textos.get(pid) or "")[:MAX_CARACTERES],
            )
        )
    return salida


def textos_por_id(ruta_hilos: Path) -> dict[str, str]:
    """Mapa `id_pregunta -> texto`, para reconstruir sin volver a llamar a la API."""
    out = {}
    for linea in ruta_hilos.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        h = json.loads(linea)
        for t in h["turnos"]:
            if t["rol"] == "pregunta":
                out[f'{h["conferencia_id"]}-h{h["hilo"]}-t{t["orden"]}'] = t["texto"]
    return out


# ---------------------------------------------------------------------------
# Versión concurrente
# ---------------------------------------------------------------------------

TRABAJADORES = 6
"""Peticiones simultáneas.

Medido: un lote de 10 tarda ~15 s y uno de 25 tarda ~33 s, o sea ~1.4 s por
pregunta pase lo que pase con el tamaño del lote. El cuello no es la entrada
sino la **salida**, que el modelo escribe token por token. Agrandar el lote no
sirve; solapar peticiones sí. Con 6 en paralelo, 4.6 horas se vuelven ~45 min.

El costo es el vocabulario: es estado compartido y secuencial. Cada trabajador
ve una foto con unos segundos de retraso y va a inventar nombres nuevos para
casos que otro acaba de nombrar. Se acepta a sabiendas: la reutilización ya
rendía poco (30%) y `consolidar()` existe justo para fusionar casi-duplicados.
"""


def clasificar_paralelo(
    preguntas: Iterable[tuple[str, str]],
    claves: list[str],
    cats_txt: str,
    ck: Any,
    vocab: list[str] | None = None,
    lote: int = LOTE,
    trabajadores: int = TRABAJADORES,
    reintentar: set[str] | None = None,
    gasto: "Gasto | None" = None,
) -> Iterator[Clasificacion]:
    """Igual que `clasificar` pero con varias peticiones a la vez.

    El vocabulario se comparte con un candado y se actualiza al cerrar cada
    lote. El checkpoint se escribe desde el hilo que consume, no desde los
    trabajadores, para que siga habiendo un solo escritor.

    `reintentar` son ids ya rechazados que **sí** hay que volver a intentar: los
    que fallaron por créditos agotados o por servicio caído no fallaron por el
    dato, y sin esto quedarían fuera para siempre porque `procesados()` incluye
    los rechazos. El rechazo anterior se conserva en el archivo —es la bitácora—
    y el intento nuevo escribe su propio renglón.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from google import genai
    from google.genai import types

    from .config import gemini_api_key

    cliente = genai.Client(api_key=gemini_api_key())
    vocab = vocab if vocab is not None else []
    candado = threading.Lock()
    ya = ck.procesados() - (reintentar or set())
    pendientes = [(i, t) for i, t in preguntas if i not in ya]
    trozos = [pendientes[k : k + lote] for k in range(0, len(pendientes), lote)]

    def trabajo(trozo: list[tuple[str, str]]):
        with candado:
            vt = "\n".join(f"- {a}" for a in vocab[-VOCAB_EN_PROMPT:]) or "(todavía ninguno)"
        payload = {i: t[:MAX_CARACTERES] for i, t in trozo}
        error = ""
        for intento in range(3):
            try:
                r = cliente.models.generate_content(
                    model=MODELO,
                    contents=json.dumps(payload, ensure_ascii=False),
                    config=types.GenerateContentConfig(
                        system_instruction=_INSTRUCCION.format(cats=cats_txt, vocab=vt),
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
            except Exception as e:  # noqa: BLE001
                error = f"{type(e).__name__}: {e}"
                time.sleep(2**intento)
        return trozo, {}, error

    with ThreadPoolExecutor(max_workers=trabajadores) as pool:
        futuros = [pool.submit(trabajo, t) for t in trozos]
        for fut in as_completed(futuros):
            trozo, datos, error = fut.result()
            for pid, texto in trozo:
                v = datos.get(pid) or {}
                cat = v.get("categoria")
                asu = " ".join((v.get("asunto") or "").split()) or None
                if not cat or cat not in claves:
                    ck.marcar_rechazado(
                        pid, razon=error or f"categoría inválida o ausente: {cat!r}"
                    )
                    continue
                if asu:
                    with candado:
                        if asu not in vocab:
                            vocab.append(asu)
                ck.marcar_hecho(pid, categoria=cat, asunto=asu)
                yield Clasificacion(
                    pid, cat, asu, None, "llm", MODELO,
                    solo_pregunta(texto)[:MAX_CARACTERES],
                )
