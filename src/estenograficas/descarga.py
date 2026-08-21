"""Fase 5: bajar el HTML crudo de las conferencias.

Reglas duras que gobiernan este módulo (CLAUDE.md):

1. **El HTML crudo no se vuelve a descargar.** Si `data/raw/{id}.html` existe,
   no se toca. El parser se reescribe muchas veces; el corpus no.
2. **Reanudable e idempotente.** Checkpoint conforme avanza; correrlo dos veces
   no rehace trabajo.
3. **Nada se descarta en silencio.** Lo que falla va al archivo de rechazos con
   su razón.

Cómo se le saca el HTML a gob.mx: se abre el navegador headful una vez, se
navega a una página para que el reto anti-bot se resuelva y deje su cookie, y
a partir de ahí se usa `context.request`, que **comparte las cookies del
navegador pero devuelve el cuerpo tal como viene por la red**. Así el archivo
guardado son los bytes del servidor y no el DOM serializado por Chromium, que
es lo que daría `page.content()`.
"""

from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import requests

from .descubrimiento import GOBMX, UA, RegistroURL, leer_urls

ESPERA_ENTRE_REQUESTS = 1.0
REINTENTOS = 3
_ARGS_NAVEGADOR = ["--window-position=-2400,-2400", "--window-size=1280,900"]

# Una página válida trae el cuerpo del artículo. El reto anti-bot no.
_SENAL_BUENA = "article-body"
_SENAL_RETO = "Challenge Validation"
_MINIMO_BYTES = 20_000

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
# "... del 18 de agosto de 2026" en el título, o "Presidencia de la República
# | 18 de agosto de 2026" en el encabezado.
_RE_FECHA_TEXTO = re.compile(r"(\d{1,2})\s+de\s+([a-zñ]+)\s+de\s+(\d{4})")


class DescargaInvalida(RuntimeError):
    """Llegó algo que no es una conferencia: el reto, un 404, una página corta."""


def _sin_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c)
    )


def fecha_desde_html(html: str) -> date | None:
    """Saca la fecha del contenido, no del slug.

    Hace falta porque hay slugs sin fecha —la conferencia de Culiacán— y slugs
    con el año truncado. Es también la única forma de detectar que un slug
    miente sobre su propia fecha.
    """
    from bs4 import BeautifulSoup

    sopa = BeautifulSoup(html, "lxml")
    candidatos = []
    h1 = sopa.find("h1")
    if h1:
        candidatos.append(h1.get_text(" ", strip=True))
    for s in sopa.find_all("section"):
        t = s.get_text(" ", strip=True)
        if t.startswith("Presidencia de la Rep") and len(t) < 120:
            candidatos.append(t)
            break

    for texto in candidatos:
        m = _RE_FECHA_TEXTO.search(_sin_acentos(texto))
        if not m:
            continue
        mes = _MESES.get(m.group(2))
        if not mes:
            continue
        try:
            return date(int(m.group(3)), mes, int(m.group(1)))
        except ValueError:
            continue
    return None


def validar(html: str) -> None:
    """Levanta `DescargaInvalida` si lo bajado no sirve. Nunca devuelve nada."""
    if _SENAL_RETO in html:
        raise DescargaInvalida("llegó el reto anti-bot en vez del contenido")
    if len(html) < _MINIMO_BYTES:
        raise DescargaInvalida(f"respuesta demasiado corta: {len(html)} bytes")
    if _SENAL_BUENA not in html:
        raise DescargaInvalida("no trae div.article-body")


# ---------------------------------------------------------------------------
# Fuentes
# ---------------------------------------------------------------------------


class SesionGobmx:
    """Navegador headful con el reto ya resuelto.

    Se abre una vez para toda la corrida. La primera navegación deja la cookie
    del reto en el contexto; de ahí en adelante `context.request` la reutiliza
    y devuelve el cuerpo crudo, sin pasar por el DOM.
    """

    URL_SEMILLA = GOBMX + "/presidencia/archivo/articulos"

    def __init__(self) -> None:
        self._pw = None
        self._nav = None
        self._ctx = None

    def __enter__(self) -> "SesionGobmx":
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._nav = self._pw.chromium.launch(headless=False, args=_ARGS_NAVEGADOR)
        self._ctx = self._nav.new_context(
            locale="es-MX", user_agent=UA, viewport={"width": 1280, "height": 900}
        )
        pagina = self._ctx.new_page()
        pagina.goto(self.URL_SEMILLA, wait_until="domcontentloaded", timeout=90000)
        pagina.wait_for_timeout(2000)
        pagina.close()
        return self

    def __exit__(self, *exc: Any) -> None:
        for cerrar in (self._ctx, self._nav):
            try:
                cerrar and cerrar.close()
            except Exception:
                pass
        try:
            self._pw and self._pw.stop()
        except Exception:
            pass

    def obtener(self, url: str) -> str:
        r = self._ctx.request.get(url, timeout=90000)
        if r.status != 200:
            raise DescargaInvalida(f"HTTP {r.status}")
        return r.text()


def obtener_wayback(url_original: str, cuando: str = "20260101") -> str:
    """Respaldo: la captura de Wayback más cercana a `cuando`.

    `requests` descomprime gzip solo, que es donde la fase 3 ya se tropezó una
    vez guardando 49 KB de binario.
    """
    disp = requests.get(
        "https://archive.org/wayback/available",
        params={"url": url_original, "timestamp": cuando},
        headers={"User-Agent": UA},
        timeout=60,
    )
    disp.raise_for_status()
    snap = (disp.json().get("archived_snapshots") or {}).get("closest") or {}
    if not snap.get("available"):
        raise DescargaInvalida("Wayback no tiene captura de esta URL")
    ts = snap["timestamp"]
    r = requests.get(
        f"https://web.archive.org/web/{ts}id_/{url_original}",
        headers={"User-Agent": UA},
        timeout=120,
    )
    r.raise_for_status()
    return r.text


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------


@dataclass
class Resultado:
    conferencia_id: str
    fuente_usada: str
    bytes: int
    fecha_del_contenido: str | None
    fecha_coincide_con_slug: bool | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _guardar(html: str, destino: Path) -> int:
    """Escribe el HTML sin sobreescribir jamás. El crudo es inmutable."""
    if destino.exists():
        raise DescargaInvalida(f"ya existe {destino.name}; el crudo no se sobreescribe")
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".parcial")
    tmp.write_text(html, encoding="utf-8")
    tmp.replace(destino)  # atómico: nunca queda un .html a medias
    return len(html.encode("utf-8"))


def descargar_una(
    reg: RegistroURL, sesion: SesionGobmx | None, carpeta: Path
) -> Resultado:
    """Baja una conferencia. Levanta la excepción si no se pudo; no la traga."""
    if reg.fuente == "gobmx":
        if sesion is None:
            raise DescargaInvalida("hace falta la sesión de navegador para gob.mx")
        try:
            html = sesion.obtener(reg.url_descarga)
            validar(html)
            fuente = "gobmx"
        except Exception as e:
            # Respaldo: Wayback. Si tampoco, que se rechace con las dos razones.
            try:
                html = obtener_wayback(reg.url_original)
                validar(html)
                fuente = "wayback (respaldo)"
            except Exception as e2:
                raise DescargaInvalida(f"gob.mx: {e} | wayback: {e2}") from e
    else:
        html = requests.get(
            reg.url_descarga, headers={"User-Agent": UA}, timeout=120
        ).text
        validar(html)
        fuente = "wayback"

    f = fecha_desde_html(html)
    if reg.conferencia_id is None and f is None:
        raise DescargaInvalida("sin fecha en el slug y sin fecha en el contenido")

    conferencia_id = (f or date.fromisoformat(reg.conferencia_id)).isoformat()
    coincide = None if reg.conferencia_id is None or f is None else (
        f.isoformat() == reg.conferencia_id
    )

    n = _guardar(html, carpeta / f"{conferencia_id}.html")
    return Resultado(
        conferencia_id=conferencia_id,
        fuente_usada=fuente,
        bytes=n,
        fecha_del_contenido=f.isoformat() if f else None,
        fecha_coincide_con_slug=coincide,
    )


def descargar(
    registros: Iterable[RegistroURL],
    ck: Any,
    carpeta: Path,
    espera: float = ESPERA_ENTRE_REQUESTS,
) -> Iterator[tuple[str, Resultado | str]]:
    """Baja todo lo pendiente, marcando el checkpoint conforme avanza.

    Rinde `(clave, resultado_o_razon)` por cada intento nuevo. Las claves son
    el slug, no la fecha: una URL sin fecha en el slug también necesita clave.
    """
    pendientes = [r for r in registros if r.slug not in ck.procesados()]
    if not pendientes:
        return

    necesita_navegador = any(r.fuente == "gobmx" for r in pendientes)
    sesion_ctx = SesionGobmx() if necesita_navegador else None

    def _correr(sesion: SesionGobmx | None) -> Iterator[tuple[str, Resultado | str]]:
        for reg in pendientes:
            destino = carpeta / f"{reg.conferencia_id}.html" if reg.conferencia_id else None
            if destino is not None and destino.exists():
                # Ya está en disco de una corrida anterior sin checkpoint.
                ck.marcar_hecho(reg.slug, conferencia_id=reg.conferencia_id, ya_estaba=True)
                yield reg.slug, "ya estaba en disco"
                continue

            ultimo = ""
            for intento in range(REINTENTOS):
                try:
                    res = descargar_una(reg, sesion, carpeta)
                    ck.marcar_hecho(reg.slug, **res.to_dict())
                    yield reg.slug, res
                    break
                except Exception as e:
                    ultimo = f"{type(e).__name__}: {e}"
                    if isinstance(e, DescargaInvalida) and "ya existe" in str(e):
                        break
                    time.sleep(2 ** intento)  # backoff
            else:
                ck.marcar_rechazado(reg.slug, razon=ultimo)
                yield reg.slug, ultimo
                continue
            if ultimo and "ya existe" in ultimo:
                ck.marcar_rechazado(reg.slug, razon=ultimo)
                yield reg.slug, ultimo
            time.sleep(espera)

    if sesion_ctx is None:
        yield from _correr(None)
    else:
        with sesion_ctx as sesion:
            yield from _correr(sesion)


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------


def main() -> int:
    """`python -m estenograficas.descarga`"""
    from .checkpoint import Checkpoint
    from .config import paths

    p = paths()
    p.ensure_dirs()
    registros = leer_urls(p.urls)
    if not registros:
        print(f"No hay {p.urls}. Correr antes: python -m estenograficas.descubrimiento")
        return 1

    ck = Checkpoint("descarga")
    print(f"== {len(registros)} URLs; {len(ck.procesados())} ya procesadas ==")

    ok = fallos = 0
    discrepancias: list[str] = []
    t0 = time.time()
    for clave, salida in descargar(registros, ck, p.raw):
        if isinstance(salida, Resultado):
            ok += 1
            if salida.fecha_coincide_con_slug is False:
                discrepancias.append(clave)
            if ok % 25 == 0:
                print(f"   {ok} bajadas, {fallos} fallos, {time.time()-t0:.0f}s")
        elif salida == "ya estaba en disco":
            ok += 1
        else:
            fallos += 1
            print(f"   FALLO {clave[:70]}: {salida[:110]}")

    hechos, rechazados = ck.hechos(), ck.rechazados()
    total = len(hechos) + len(rechazados)
    print("\n" + "=" * 60)
    print(f"exitosas   : {len(hechos)}")
    print(f"rechazadas : {len(rechazados)}")
    print(f"tasa de éxito: {100 * len(hechos) / total:.1f}%" if total else "sin datos")

    archivos = sorted(p.raw.glob("*.html"))
    peso = sum(f.stat().st_size for f in archivos)
    print(f"archivos en data/raw/: {len(archivos)}  ({peso / 1e6:.0f} MB)")

    por_fuente: dict[str, int] = {}
    for r in hechos.values():
        f = r.get("fuente_usada", "?")
        por_fuente[f] = por_fuente.get(f, 0) + 1
    print(f"por fuente: {por_fuente}")

    malas = [r for r in hechos.values() if r.get("fecha_coincide_con_slug") is False]
    print(f"\nslugs cuya fecha NO coincide con el contenido: {len(malas)}")
    for r in malas[:20]:
        print(f"   {r['id']} -> contenido dice {r.get('fecha_del_contenido')}")

    if rechazados:
        print(f"\nfallos, en {ck.rechazos_path}:")
        for k, r in list(rechazados.items())[:20]:
            print(f"   {k[:60]}: {r['razon'][:100]}")

    print("\n" + "!" * 60)
    print("RESPALDA data/raw/ FUERA DEL REPO ANTES DE SEGUIR.")
    print("Es el activo caro del proyecto y no está en git.")
    print("!" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
