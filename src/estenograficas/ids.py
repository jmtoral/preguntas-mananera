"""Identidad de una pregunta a través de los reparseos.

El id de una pregunta es `conferencia-hNN-tNN`: conferencia, número de hilo y
orden del turno. De esas tres partes **solo el número de hilo se mueve**. Si
el parser mejora y una conferencia gana una tanda, todas las siguientes se
renumeran, y cada clasificación ya pagada queda apuntando a la nada.

El `orden` del turno no se mueve: es la posición del turno dentro de la
conferencia, y los turnos no cambian cuando cambia la detección de
autopresentaciones. Por eso `(conferencia, orden)` sirve de llave estable.

Medido el 2026-09-03, al arreglar el regex de autopresentación: 8,162 filas de
temas y 7,414 de postura quedaron huérfanas de golpe. Todas se reencontraron
por esta llave, sin volver a llamar a la API. Sin esto, cada corrección del
parser cuesta dinero.
"""

from __future__ import annotations

import re
from typing import Iterable

_ID = re.compile(r"^(?P<conf>.+?)-h(?P<hilo>\d+)-t(?P<orden>\d+)$")


def id_estable(id_pregunta: str) -> str:
    """Llave que sobrevive a un reparseo: conferencia y orden del turno.

    Si el id no tiene la forma esperada se devuelve tal cual, para que un
    formato nuevo falle al comparar en vez de fusionarse con otro por error.
    """
    m = _ID.match(id_pregunta)
    return f'{m["conf"]}-t{m["orden"]}' if m else id_pregunta


def remapear(ids_actuales: Iterable[str]) -> dict[str, str]:
    """Mapa `llave estable -> id actual`, para reencontrar ids viejos."""
    return {id_estable(i): i for i in ids_actuales}
