"""Pruebas de la descarga (fase 5). Sin red.

Lo que se prueba aquí es lo que protege el corpus: que una respuesta mala no
se guarde como si fuera buena, que el crudo no se sobreescriba nunca, y que
la fecha salga del contenido cuando el slug no la trae o miente.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from estenograficas.checkpoint import Checkpoint
from estenograficas.descarga import (
    DescargaInvalida,
    Resultado,
    _guardar,
    descargar,
    fecha_desde_html,
    validar,
)
from estenograficas.descubrimiento import RegistroURL

RELLENO = "x" * 30_000
BUENA = f'<html><h1>Versión estenográfica. Conferencia del 18 de agosto de 2026</h1><div class="article-body"><p>{RELLENO}</p></div></html>'


# ===========================================================================
# Validación: que lo malo no se guarde como bueno
# ===========================================================================


def test_el_reto_antibot_no_pasa_por_conferencia() -> None:
    """El modo de falla más caro: guardar 464 páginas de reto y no notarlo."""
    reto = "<html><title>Challenge Validation</title>" + RELLENO + "</html>"
    with pytest.raises(DescargaInvalida, match="reto anti-bot"):
        validar(reto)


def test_una_respuesta_corta_no_pasa() -> None:
    with pytest.raises(DescargaInvalida, match="demasiado corta"):
        validar('<html><div class="article-body">poquito</div></html>')


def test_sin_article_body_no_pasa() -> None:
    with pytest.raises(DescargaInvalida, match="article-body"):
        validar("<html><body>" + RELLENO + "</body></html>")


def test_una_pagina_buena_pasa() -> None:
    validar(BUENA)  # no levanta


# ===========================================================================
# La fecha sale del contenido
# ===========================================================================


def test_la_fecha_sale_del_titulo() -> None:
    assert fecha_desde_html(BUENA) == date(2026, 8, 18)


def test_la_fecha_sale_del_encabezado_si_no_esta_en_el_titulo() -> None:
    html = (
        "<html><h1>Conferencia de prensa</h1>"
        "<section><p>Presidencia de la República | 3 de octubre de 2024</p></section>"
        f'<div class="article-body">{RELLENO}</div></html>'
    )
    assert fecha_desde_html(html) == date(2024, 10, 3)


def test_sin_fecha_en_el_contenido_devuelve_none() -> None:
    html = f'<html><h1>Conferencia</h1><div class="article-body">{RELLENO}</div></html>'
    assert fecha_desde_html(html) is None


def test_un_mes_mal_escrito_no_se_adivina() -> None:
    html = f"<html><h1>Conferencia del 3 de octubrr de 2024</h1><div class='article-body'>{RELLENO}</div></html>"
    assert fecha_desde_html(html) is None


# ===========================================================================
# El crudo es inmutable
# ===========================================================================


def test_no_sobreescribe_un_archivo_existente(tmp_path: Path) -> None:
    """Regla dura 1. El parser se reescribe muchas veces; el corpus no."""
    destino = tmp_path / "2026-08-18.html"
    destino.write_text("el original", encoding="utf-8")
    with pytest.raises(DescargaInvalida, match="no se sobreescribe"):
        _guardar(BUENA, destino)
    assert destino.read_text(encoding="utf-8") == "el original"


def test_guardar_escribe_de_forma_atomica(tmp_path: Path) -> None:
    """Se escribe a .parcial y se renombra: nunca queda un .html a medias."""
    destino = tmp_path / "a.html"
    _guardar(BUENA, destino)
    assert destino.read_text(encoding="utf-8") == BUENA
    assert list(tmp_path.glob("*.parcial")) == []


# ===========================================================================
# Reanudación e idempotencia
# ===========================================================================


class _FuenteFalsa:
    """Sustituye a la sesión de navegador; cuenta cuántas veces la llaman."""

    def __init__(self, respuestas: dict[str, str]) -> None:
        self.respuestas = respuestas
        self.llamadas: list[str] = []

    def obtener(self, url: str) -> str:
        self.llamadas.append(url)
        if url not in self.respuestas:
            raise DescargaInvalida("404")
        return self.respuestas[url]


def _reg(fecha: str | None, slug: str, url: str = "u") -> RegistroURL:
    return RegistroURL(fecha, slug, url, url, "gobmx")


def _descargar_con(monkeypatch, regs, ck, carpeta, fuente):
    """Corre `descargar` sustituyendo la sesión real por una falsa."""
    import estenograficas.descarga as d

    monkeypatch.setattr(d, "SesionGobmx", lambda: _CtxFalso(fuente))
    return list(d.descargar(regs, ck, carpeta, espera=0))


class _CtxFalso:
    def __init__(self, fuente):
        self.fuente = fuente

    def __enter__(self):
        return self.fuente

    def __exit__(self, *a):
        return False


def test_no_vuelve_a_pedir_lo_ya_bajado(tmp_path, monkeypatch) -> None:
    regs = [_reg("2026-08-18", "slug-a", "u-a")]
    fuente = _FuenteFalsa({"u-a": BUENA})
    ck = Checkpoint("d", base=tmp_path / "ck")
    raw = tmp_path / "raw"

    salida = _descargar_con(monkeypatch, regs, ck, raw, fuente)
    assert len(salida) == 1 and isinstance(salida[0][1], Resultado)
    assert len(fuente.llamadas) == 1

    salida2 = _descargar_con(monkeypatch, regs, ck, raw, fuente)
    assert salida2 == []
    assert len(fuente.llamadas) == 1, "volvió a pedir algo que ya tenía"


def test_lo_que_falla_queda_en_rechazos_con_su_razon(tmp_path, monkeypatch) -> None:
    """Regla dura 3: nada se descarta en silencio."""
    regs = [_reg("2026-08-18", "slug-a", "u-a"), _reg("2026-08-19", "slug-b", "u-b")]
    fuente = _FuenteFalsa({"u-a": BUENA})  # u-b no existe
    ck = Checkpoint("d", base=tmp_path / "ck")

    # Sin red: el respaldo de Wayback también debe fallar.
    import estenograficas.descarga as d

    monkeypatch.setattr(
        d, "obtener_wayback", lambda *a, **k: (_ for _ in ()).throw(DescargaInvalida("sin captura"))
    )
    _descargar_con(monkeypatch, regs, ck, tmp_path / "raw", fuente)

    assert set(ck.hechos()) == {"slug-a"}
    assert set(ck.rechazados()) == {"slug-b"}
    assert "404" in ck.rechazados()["slug-b"]["razon"]
    assert "sin captura" in ck.rechazados()["slug-b"]["razon"]


def test_la_fecha_del_contenido_manda_sobre_el_slug(tmp_path, monkeypatch) -> None:
    """La conferencia de Culiacán no trae fecha en el slug y sí en el texto."""
    regs = [_reg(None, "slug-culiacan", "u-c")]
    fuente = _FuenteFalsa({"u-c": BUENA})
    ck = Checkpoint("d", base=tmp_path / "ck")
    raw = tmp_path / "raw"

    salida = _descargar_con(monkeypatch, regs, ck, raw, fuente)
    res = salida[0][1]
    assert isinstance(res, Resultado)
    assert res.conferencia_id == "2026-08-18"
    assert (raw / "2026-08-18.html").is_file()


def test_se_detecta_cuando_el_slug_miente_sobre_su_fecha(tmp_path, monkeypatch) -> None:
    """El slug dice una fecha y el contenido otra. Se guarda la del contenido."""
    regs = [_reg("2026-01-01", "slug-mentiroso", "u-m")]
    fuente = _FuenteFalsa({"u-m": BUENA})  # el contenido dice 2026-08-18
    ck = Checkpoint("d", base=tmp_path / "ck")
    raw = tmp_path / "raw"

    res = _descargar_con(monkeypatch, regs, ck, raw, fuente)[0][1]
    assert res.fecha_coincide_con_slug is False
    assert res.conferencia_id == "2026-08-18"
    assert (raw / "2026-08-18.html").is_file()
    assert not (raw / "2026-01-01.html").exists()
