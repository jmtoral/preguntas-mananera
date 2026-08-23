"""Resumen temático corto de cada pregunta, con Gemini.

Uso acotado según la regla dura 4: el modelo ve **una pregunta a la vez**,
nunca el documento. Se mandan en lotes pequeños para no hacer una llamada por
renglón, pero cada elemento del lote sigue siendo una pregunta suelta.

**El resumen es del asunto, no de la actitud.** El prompt lo prohíbe
explícitamente: `"Visas revocadas a familiares de López Beltrán"` sí,
`"Cuestiona la versión oficial sobre las visas"` no. La razón no es estética.
Si el resumen califica la pregunta y algún día aparece junto a ella en una
hoja de codificación, ancla al humano justo en el campo que más importa. Y si
alimenta el análisis, mete una lectura del modelo donde debería haber una
descripción.

Cada resumen lleva su procedencia, como pide la regla dura 5: `metodo`,
`modelo` y el fragmento exacto que se le mandó.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from typing import Any

MODELO = "gemini-2.5-flash"
TEMPERATURA = 0.0
LOTE = 10
"""Preguntas por llamada. Cada una sigue siendo un fragmento acotado."""

MAX_CARACTERES = 1200
"""Se recorta la pregunta: el tema está al principio y el resto es costo."""

_INSTRUCCION = """\
Eres un asistente de investigación. Para cada pregunta de prensa que recibas,
escribe UNA etiqueta temática de entre 5 y 10 palabras en español.

Reglas estrictas:
- Describe SOLO el asunto del que trata la pregunta.
- NUNCA califiques la pregunta ni al periodista. Prohibido usar palabras como
  "cuestiona", "critica", "confronta", "elogia", "incómoda", "dura", "blanda",
  "insiste", "reclama".
- Sin verbos de valoración. Usa una frase nominal.
- No inventes datos que no estén en la pregunta.
- Si la pregunta está rota o no se entiende, devuelve exactamente: SIN TEMA

Ejemplos de la forma correcta:
  "Revocación de visas a familiares de López Beltrán"
  "Plan hídrico para Sonora y abasto en Hermosillo"
  "Señalización en cruces ferroviarios con vehículos"

Devuelve SOLO un objeto JSON: {"temas": {"<id>": "<etiqueta>", ...}}
con una entrada por cada id recibido, sin texto adicional.
"""


@dataclass
class Tema:
    id_pregunta: str
    tema: str | None
    metodo: str
    modelo: str
    fragmento: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cliente():
    from google import genai

    from .config import gemini_api_key

    return genai.Client(api_key=gemini_api_key())


def _pedir_lote(cliente, lote: list[tuple[str, str]]) -> dict[str, str]:
    from google.genai import types

    payload = {pid: texto[:MAX_CARACTERES] for pid, texto in lote}
    r = cliente.models.generate_content(
        model=MODELO,
        contents=json.dumps(payload, ensure_ascii=False),
        config=types.GenerateContentConfig(
            system_instruction=_INSTRUCCION,
            temperature=TEMPERATURA,
            response_mime_type="application/json",
        ),
    )
    datos = json.loads(r.text)
    return datos.get("temas", datos)


def resumir(
    preguntas: Iterable[tuple[str, str]],
    lote: int = LOTE,
    espera: float = 0.5,
) -> Iterator[Tema]:
    """Rinde un `Tema` por pregunta. `preguntas` son pares `(id, texto)`.

    Lo que no se pudo resolver sale con `tema=None` y el método lo dice; no se
    inventa una etiqueta ni se descarta el renglón en silencio.
    """
    cliente = _cliente()
    pendientes = list(preguntas)
    for i in range(0, len(pendientes), lote):
        trozo = pendientes[i : i + lote]
        try:
            respuestas = _pedir_lote(cliente, trozo)
        except Exception as e:  # noqa: BLE001 - la razón viaja en el registro
            for pid, texto in trozo:
                yield Tema(pid, None, f"error: {type(e).__name__}", MODELO,
                           texto[:MAX_CARACTERES])
            continue
        for pid, texto in trozo:
            bruto = (respuestas.get(pid) or "").strip()
            valido = bruto and bruto.upper() != "SIN TEMA"
            yield Tema(
                id_pregunta=pid,
                tema=bruto if valido else None,
                metodo="llm" if valido else "sin_tema",
                modelo=MODELO,
                fragmento=texto[:MAX_CARACTERES],
            )
        time.sleep(espera)
