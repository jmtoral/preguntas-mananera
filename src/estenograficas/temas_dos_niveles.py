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

Devuelve SOLO JSON:
{{"clasificacion": {{"<id>": {{"categoria": "", "asunto": ""}}, ...}}}}"""


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
    """
    from collections import Counter

    frec = Counter(a for a in asuntos if a)
    nombres = list(frec)
    padre = {n: n for n in nombres}

    def raiz(x: str) -> str:
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    bolsas = {n: _bolsa(n) for n in nombres}
    for i, a in enumerate(nombres):
        A = bolsas[a]
        if not A:
            continue
        for b in nombres[i + 1 :]:
            B = bolsas[b]
            if not B:
                continue
            if len(A & B) / len(A | B) >= umbral_jaccard:
                ra, rb = raiz(a), raiz(b)
                if ra != rb:
                    padre[rb] = ra

    grupos: dict[str, list[str]] = {}
    for n in nombres:
        grupos.setdefault(raiz(n), []).append(n)

    mapa = {}
    for miembros in grupos.values():
        rep = max(miembros, key=lambda m: (frec[m], -len(m)))
        for m in miembros:
            mapa[m] = rep
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
) -> Iterator[Clasificacion]:
    """Igual que `clasificar` pero con varias peticiones a la vez.

    El vocabulario se comparte con un candado y se actualiza al cerrar cada
    lote. El checkpoint se escribe desde el hilo que consume, no desde los
    trabajadores, para que siga habiendo un solo escritor.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from google import genai
    from google.genai import types

    from .config import gemini_api_key

    cliente = genai.Client(api_key=gemini_api_key())
    vocab = vocab if vocab is not None else []
    candado = threading.Lock()
    ya = ck.procesados()
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
                    ),
                )
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
                    pid, cat, asu, None, "llm", MODELO, texto[:MAX_CARACTERES]
                )
