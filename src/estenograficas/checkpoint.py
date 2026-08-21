"""Checkpointing para procesos largos.

Implementa las reglas duras 2 y 3 de CLAUDE.md:

- **Idempotencia y reanudación.** Un registro append-only de qué items ya se
  procesaron. Correr una etapa dos veces no rehace trabajo hecho.
- **Nada se descarta en silencio.** Lo que no se pudo procesar va a un archivo
  de rechazos con su razón, no al vacío.

Durabilidad: cada registro se escribe, se hace flush y se hace `os.fsync` antes
de devolver el control. Eso es lo que hace que el checkpoint sobreviva a que el
proceso muera de golpe, que es el caso que importa: una descarga de 460 páginas
se interrumpe por corte de luz, por Ctrl-C, o porque alguien cerró la terminal.

El costo es abrir el archivo una vez por item. Frente a un request de red con
espera de un segundo, o frente a parsear una conferencia, es ruido; y a cambio
no hay estado en memoria que perder.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

from .config import paths


class CheckpointCorrupto(RuntimeError):
    """Una línea ilegible en medio del registro, no al final.

    Al final es una escritura interrumpida y es esperable. En medio significa
    que el archivo se dañó de otra forma y no se debe adivinar qué decía.
    """


def _leer_jsonl(archivo: Path) -> tuple[list[dict[str, Any]], int]:
    """Lee un JSONL tolerando una última línea truncada.

    Devuelve los registros y cuántas líneas se descartaron por truncamiento
    (0 o 1). El descarte se reporta al llamador; no se silencia.
    """
    if not archivo.is_file():
        return [], 0

    lineas = archivo.read_text(encoding="utf-8").splitlines()
    registros: list[dict[str, Any]] = []
    truncadas = 0
    for i, linea in enumerate(lineas):
        if not linea.strip():
            continue
        try:
            registros.append(json.loads(linea))
        except json.JSONDecodeError as e:
            es_ultima = i == len(lineas) - 1
            if es_ultima:
                # Escritura interrumpida a media línea. Ese item simplemente
                # no quedó marcado y se va a reprocesar, que es lo correcto.
                truncadas = 1
            else:
                raise CheckpointCorrupto(
                    f"{archivo}: línea {i + 1} ilegible y no es la última. "
                    f"No se adivina su contenido."
                ) from e
    return registros, truncadas


class Checkpoint:
    """Registro append-only de items hechos y rechazados de una etapa.

    Los ids de item son cadenas y deben ser estables entre corridas: la fecha
    de la conferencia, no el índice del bucle.
    """

    def __init__(self, nombre: str, *, base: Path | None = None) -> None:
        self.nombre = nombre
        self.base = base if base is not None else paths().checkpoints
        self.base.mkdir(parents=True, exist_ok=True)
        self.hechos_path = self.base / f"{nombre}.hechos.jsonl"
        self.rechazos_path = self.base / f"{nombre}.rechazos.jsonl"
        self.lineas_truncadas = 0

    # -- escritura ---------------------------------------------------------

    def _append(self, archivo: Path, registro: dict[str, Any]) -> None:
        linea = json.dumps(registro, ensure_ascii=False) + "\n"
        with open(archivo, "a", encoding="utf-8") as f:
            f.write(linea)
            f.flush()
            os.fsync(f.fileno())

    def marcar_hecho(self, item_id: str, **extra: Any) -> None:
        self._append(self.hechos_path, {"id": item_id, "ts": time.time(), **extra})

    def marcar_rechazado(self, item_id: str, razon: str, **extra: Any) -> None:
        """Registra un item que no se pudo procesar, con su razón.

        Un item rechazado cuenta como procesado: no se reintenta solo. Para
        reintentarlo hay que borrar su renglón a propósito, que es justo la
        fricción que queremos.
        """
        self._append(
            self.rechazos_path,
            {"id": item_id, "ts": time.time(), "razon": razon, **extra},
        )

    # -- lectura -----------------------------------------------------------

    def _cargar(self, archivo: Path) -> dict[str, dict[str, Any]]:
        registros, truncadas = _leer_jsonl(archivo)
        self.lineas_truncadas += truncadas
        # El último registro de un id gana, por si algo se reprocesó a mano.
        return {r["id"]: r for r in registros}

    def hechos(self) -> dict[str, dict[str, Any]]:
        return self._cargar(self.hechos_path)

    def rechazados(self) -> dict[str, dict[str, Any]]:
        return self._cargar(self.rechazos_path)

    def procesados(self) -> set[str]:
        return set(self.hechos()) | set(self.rechazados())

    def pendientes(self, items: Iterable[str]) -> list[str]:
        """Los items que faltan, en el orden dado y sin duplicados."""
        ya = self.procesados()
        vistos: set[str] = set()
        out = []
        for i in items:
            if i not in ya and i not in vistos:
                vistos.add(i)
                out.append(i)
        return out

    def resumen(self) -> dict[str, int]:
        return {
            "hechos": len(self.hechos()),
            "rechazados": len(self.rechazados()),
            "lineas_truncadas": self.lineas_truncadas,
        }

    def __repr__(self) -> str:
        r = self.resumen()
        return (
            f"<Checkpoint {self.nombre!r} hechos={r['hechos']} "
            f"rechazados={r['rechazados']}>"
        )


def ejecutar(
    items: Iterable[str],
    trabajo: Callable[[str], dict[str, Any] | None],
    ck: Checkpoint,
) -> Iterator[str]:
    """Corre `trabajo` sobre los items pendientes, marcando conforme avanza.

    Existe para que ninguna etapa reinvente el manejo de fallas y termine
    tirando registros en silencio. Si `trabajo` levanta una excepción, el item
    se rechaza con el tipo y el mensaje, y el proceso sigue. Lo que devuelva
    `trabajo` (si es un dict) se guarda como metadatos del item hecho.

    Rinde el id de cada item terminado, para poder reportar avance.
    """
    for item_id in ck.pendientes(items):
        try:
            extra = trabajo(item_id) or {}
        except Exception as e:  # noqa: BLE001 - la razón se registra, no se traga
            ck.marcar_rechazado(item_id, razon=f"{type(e).__name__}: {e}")
            continue
        ck.marcar_hecho(item_id, **extra)
        yield item_id
