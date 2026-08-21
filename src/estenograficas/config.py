"""Resolución de rutas y carga de secretos.

Ninguna ruta absoluta se escribe a mano en el proyecto: todo cuelga de `paths()`.
La raíz se descubre subiendo desde este archivo hasta encontrar `pyproject.toml`,
así que funciona igual con el paquete instalado en editable, desde un notebook,
o desde pytest con otro directorio de trabajo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_MARCADOR = "pyproject.toml"
_VAR_RAIZ = "ESTENOGRAFICAS_ROOT"


def find_root(desde: Path | None = None) -> Path:
    """Devuelve la raíz del repo.

    `ESTENOGRAFICAS_ROOT` la sobreescribe; es lo que usan las pruebas para
    trabajar contra un directorio temporal sin ensuciar el repo real.
    """
    override = os.environ.get(_VAR_RAIZ)
    if override:
        return Path(override).resolve()

    actual = (desde or Path(__file__)).resolve()
    for candidato in [actual, *actual.parents]:
        if (candidato / _MARCADOR).is_file():
            return candidato
    raise RuntimeError(
        f"No se encontró {_MARCADOR} subiendo desde {actual}. "
        f"Definir {_VAR_RAIZ} o correr dentro del repo."
    )


@dataclass(frozen=True)
class Paths:
    root: Path

    # Código y materiales versionados
    @property
    def src(self) -> Path:
        return self.root / "src" / "estenograficas"

    @property
    def tests(self) -> Path:
        return self.root / "tests"

    @property
    def fixtures(self) -> Path:
        return self.root / "fixtures"

    @property
    def notebooks(self) -> Path:
        return self.root / "notebooks"

    # Datos. Todo esto está en .gitignore.
    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def raw(self) -> Path:
        """HTML crudo. Inmutable: se baja una vez y no se sobreescribe."""
        return self.data / "raw"

    @property
    def interim(self) -> Path:
        return self.data / "interim"

    @property
    def gold(self) -> Path:
        """Muestra codificada a mano por el humano."""
        return self.data / "gold"

    @property
    def outputs(self) -> Path:
        return self.data / "outputs"

    @property
    def checkpoints(self) -> Path:
        return self.data / "checkpoints"

    @property
    def env_file(self) -> Path:
        return self.root / ".env"

    # Archivos con nombre fijo, para que no se escriban a mano en cada módulo
    @property
    def urls(self) -> Path:
        return self.interim / "urls.jsonl"

    @property
    def turnos(self) -> Path:
        return self.interim / "turnos.jsonl"

    @property
    def hilos(self) -> Path:
        return self.interim / "hilos.jsonl"

    @property
    def conferencias(self) -> Path:
        return self.interim / "conferencias.jsonl"

    @property
    def preguntas(self) -> Path:
        return self.outputs / "preguntas.jsonl"

    def raw_html(self, conferencia_id: str) -> Path:
        return self.raw / f"{conferencia_id}.html"

    def ensure_dirs(self) -> None:
        """Crea los directorios de datos. Idempotente.

        `data/` está en .gitignore, así que los directorios no viajan en el repo
        y hay que crearlos en cada clon.
        """
        for d in (self.raw, self.interim, self.gold, self.outputs, self.checkpoints):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=None)
def paths() -> Paths:
    return Paths(root=find_root())


def load_env(*, override: bool = False) -> bool:
    """Carga `.env`. Devuelve si el archivo existía. Nunca imprime nada."""
    archivo = paths().env_file
    if not archivo.is_file():
        return False
    load_dotenv(archivo, override=override)
    return True


def gemini_api_key() -> str:
    """Devuelve la key de Gemini.

    Falla ruidosamente si no está. El mensaje de error no incluye el valor,
    ni siquiera truncado: una key en un traceback termina en un log.
    """
    load_env()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY no está definida. Debe estar en el .env de la raíz "
            f"del repo ({paths().env_file}), que está en .gitignore."
        )
    return key
