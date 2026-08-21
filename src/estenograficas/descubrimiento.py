"""Fase 4: armar la lista de URLs de versiones estenográficas.

Dos fuentes, porque ninguna sola alcanza:

- **Wayback Machine.** Cubre el 80% de octubre de 2024 a enero de 2026, pero
  se desploma al 22% de febrero de 2026 en adelante: el archivo todavía no
  alcanza a rastrear lo reciente.
- **gob.mx con navegador.** El sitio responde un reto anti-bot a cualquier
  cliente que no ejecute JavaScript, así que necesita Playwright.

**Las URLs no se construyen por fecha.** `CLAUDE.md` lo prohíbe y la medición
de cobertura lo confirmó: hay slugs con el año truncado (`-de-202`), con un
backslash pegado (`%5C`) y con sufijo numérico (`-421610`). Se descubren
recorriendo listados y se conservan tal como vienen.

La fecha que sale del slug es **provisional**. La canónica sale del contenido
en la fase 5; aquí solo sirve para agrupar y para detectar huecos.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

import requests

Fuente = Literal["wayback", "gobmx"]

CDX = "https://web.archive.org/cdx/search/cdx"
PREFIJO_SLUG = (
    "gob.mx/presidencia/es/articulos/"
    "version-estenografica-conferencia-de-prensa-de-la-presidenta-"
    "claudia-sheinbaum-pardo-del-"
)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

INICIO_SEXENIO = date(2024, 10, 1)

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
_RE_FECHA_SLUG = re.compile(r"-del?-(\d{1,2})-de-([a-zñ]+)-(?:de-)?(\d{4})")


def _sin_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c)
    )


def fecha_de_slug(slug: str) -> date | None:
    """Fecha provisional a partir del slug, o None si no se puede leer.

    None no es un fallo del que haya que recuperarse aquí: significa que esa
    URL necesita que la fase 5 le saque la fecha del contenido. Se conserva.
    """
    s = _sin_acentos(slug.split("?")[0])
    m = _RE_FECHA_SLUG.search(s)
    if not m:
        return None
    mes = _MESES.get(m.group(2))
    if not mes:
        return None
    try:
        return date(int(m.group(3)), mes, int(m.group(1)))
    except ValueError:
        return None


@dataclass
class RegistroURL:
    """Un renglón de `data/interim/urls.jsonl`."""

    conferencia_id: str | None      # fecha provisional del slug, o None
    slug: str
    url_descarga: str               # de dónde se baja
    url_original: str               # la URL canónica en gob.mx
    fuente: Fuente
    timestamp: str | None = None    # marca de captura, solo Wayback
    statuscode: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Wayback
# ---------------------------------------------------------------------------

# Ventanas cortas a propósito: la CDX devuelve 504 con rangos grandes.
_VENTANAS = [
    ("20241001", "20241231"),
    ("20250101", "20250630"),
    ("20250701", "20251231"),
    ("20260101", "20260630"),
    ("20260701", "20261231"),
]


def _cdx(desde: str, hasta: str, intentos: int = 3) -> list[list[str]]:
    """Una consulta a la CDX, con reintentos.

    **No se usa `collapse` ni `filter=statuscode:200`**, y las dos omisiones
    son deliberadas: `statuscode:200` tira las capturas *revisit*, que sí
    tienen contenido, y `collapse=urlkey` devuelve una sola captura por URL,
    a veces un 404 aunque exista un 200 de la misma página. Las dos cosas
    subestiman la cobertura. Se filtra después, por fecha.
    """
    params = {
        "url": PREFIJO_SLUG,
        "matchType": "prefix",
        "output": "json",
        "fl": "timestamp,original,statuscode",
        "from": desde,
        "to": hasta,
    }
    for i in range(intentos):
        try:
            r = requests.get(CDX, params=params, headers={"User-Agent": UA}, timeout=300)
            r.raise_for_status()
            datos = r.json()
            return datos[1:] if datos else []
        except Exception:
            if i == intentos - 1:
                raise
            time.sleep(5 * (i + 1))
    return []


def urls_wayback(ventanas: Iterable[tuple[str, str]] | None = None) -> list[RegistroURL]:
    """Descubre las conferencias archivadas, una por fecha.

    De todas las capturas de una misma fecha se queda la más temprana que no
    sea 4xx ni 5xx. Las fechas donde solo hay capturas de error se descartan
    aquí y las tiene que cubrir gob.mx.
    """
    por_fecha: dict[date, RegistroURL] = {}
    sin_fecha: list[RegistroURL] = []

    for desde, hasta in ventanas or _VENTANAS:
        for ts, url, sc in _cdx(desde, hasta):
            if sc and sc[:1] in ("4", "5"):
                continue
            slug = url.split("/articulos/", 1)[-1]
            f = fecha_de_slug(slug)
            reg = RegistroURL(
                conferencia_id=f.isoformat() if f else None,
                slug=slug,
                url_descarga=f"https://web.archive.org/web/{ts}id_/{url}",
                url_original=url,
                fuente="wayback",
                timestamp=ts,
                statuscode=sc or None,
            )
            if f is None:
                sin_fecha.append(reg)
            elif f not in por_fecha or ts < (por_fecha[f].timestamp or "9"):
                por_fecha[f] = reg
        time.sleep(1)

    return [por_fecha[f] for f in sorted(por_fecha)] + sin_fecha


# ---------------------------------------------------------------------------
# Diagnóstico
# ---------------------------------------------------------------------------


def dias_habiles(desde: date, hasta: date) -> list[date]:
    n = (hasta - desde).days + 1
    return [d for d in (desde + timedelta(i) for i in range(n)) if d.weekday() < 5]


def conteo_por_mes(registros: Iterable[RegistroURL]) -> dict[str, int]:
    conteo: dict[str, int] = {}
    for r in registros:
        if r.conferencia_id:
            mes = r.conferencia_id[:7]
            conteo[mes] = conteo.get(mes, 0) + 1
    return dict(sorted(conteo.items()))


def huecos(registros: Iterable[RegistroURL], hasta: date) -> list[date]:
    """Días hábiles del sexenio sin ninguna URL descubierta.

    No todos son conferencias perdidas: hay festivos y giras. La lista es
    material para revisar, no una lista de fallos.
    """
    cubiertas = {r.conferencia_id for r in registros if r.conferencia_id}
    return [d for d in dias_habiles(INICIO_SEXENIO, hasta) if d.isoformat() not in cubiertas]


def resumen(registros: list[RegistroURL], hasta: date) -> dict[str, Any]:
    por_fuente: dict[str, int] = {}
    for r in registros:
        por_fuente[r.fuente] = por_fuente.get(r.fuente, 0) + 1
    hab = dias_habiles(INICIO_SEXENIO, hasta)
    faltan = huecos(registros, hasta)
    return {
        "urls": len(registros),
        "por_fuente": por_fuente,
        "sin_fecha_en_slug": sum(1 for r in registros if r.conferencia_id is None),
        "dias_habiles": len(hab),
        "dias_cubiertos": len(hab) - len(faltan),
        "dias_sin_url": len(faltan),
        "cobertura": round(100 * (len(hab) - len(faltan)) / len(hab), 1) if hab else 0.0,
    }


# ---------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------


def fusionar(*fuentes: Iterable[RegistroURL]) -> list[RegistroURL]:
    """Une varias fuentes dejando una URL por fecha.

    **gob.mx gana sobre Wayback** cuando las dos tienen la misma fecha: es la
    página original, no una copia con la fecha de captura de por medio. Lo que
    no trae fecha en el slug se conserva completo; no se puede deduplicar algo
    cuya identidad todavía no se conoce.
    """
    prioridad = {"gobmx": 0, "wayback": 1}
    mejor: dict[str, RegistroURL] = {}
    sueltos: list[RegistroURL] = []
    for grupo in fuentes:
        for r in grupo:
            if r.conferencia_id is None:
                sueltos.append(r)
                continue
            previo = mejor.get(r.conferencia_id)
            if previo is None or prioridad[r.fuente] < prioridad[previo.fuente]:
                mejor[r.conferencia_id] = r
    return [mejor[k] for k in sorted(mejor)] + sueltos


def escribir_urls(registros: Iterable[RegistroURL], destino: Path) -> int:
    destino.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(destino, "w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
            n += 1
    return n


def leer_urls(origen: Path) -> list[RegistroURL]:
    if not origen.is_file():
        return []
    return [
        RegistroURL(**json.loads(l))
        for l in origen.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
