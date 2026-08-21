"""Pruebas del descubrimiento de URLs (fase 4).

Sin red: lo que toca gob.mx y Wayback se ejercita a mano y queda documentado
en HANDOFF.md. Aquí se prueba lo que se puede romper en silencio: la lectura
de fechas desde slugs con errata y la fusión de las dos fuentes.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from estenograficas import config
from estenograficas.descubrimiento import (
    RegistroURL,
    conteo_por_mes,
    escribir_urls,
    fecha_de_slug,
    fusionar,
    huecos,
    leer_urls,
    resumen,
)

BASE = "version-estenografica-conferencia-de-prensa-de-la-presidenta-claudia-sheinbaum-pardo"


def _reg(fecha: str | None, fuente: str, slug: str = "x") -> RegistroURL:
    return RegistroURL(
        conferencia_id=fecha, slug=slug, url_descarga="u", url_original="u", fuente=fuente
    )


# ===========================================================================
# Fechas desde slugs con errata
# ===========================================================================


def test_fecha_de_slug_caso_normal() -> None:
    assert fecha_de_slug(f"{BASE}-del-18-de-agosto-de-2026") == date(2026, 8, 18)


def test_fecha_de_slug_sin_cero_a_la_izquierda() -> None:
    """El archivo mezcla '-del-7-' y '-del-07-'."""
    assert fecha_de_slug(f"{BASE}-del-7-de-febrero-de-2025") == date(2025, 2, 7)
    assert fecha_de_slug(f"{BASE}-del-07-de-febrero-de-2025") == date(2025, 2, 7)


@pytest.mark.parametrize(
    "slug,esperada",
    [
        # sufijo numérico del CMS, visto en el archivo real
        (f"{BASE}-del-17-de-marzo-de-2026-421610", date(2026, 3, 17)),
        (f"{BASE}-del-08-de-enero-de-2026-416354", date(2026, 1, 8)),
        # backslash pegado al final, visto en el archivo real
        (f"{BASE}-del-18-de-noviembre-de-2025%5C", date(2025, 11, 18)),
        # query string
        (f"{BASE}-del-02-de-enero-de-2026?idiom=es", date(2026, 1, 2)),
    ],
)
def test_fecha_de_slug_con_erratas_reales(slug, esperada) -> None:
    """CLAUDE.md advierte que los slugs traen erratas. Estas son reales."""
    assert fecha_de_slug(slug) == esperada


def test_un_slug_ilegible_da_none_y_no_revienta() -> None:
    """Año truncado, visto en el archivo real. No se adivina el año."""
    assert fecha_de_slug(f"{BASE}-del-30-de-marzo-de-202") is None
    assert fecha_de_slug("cualquier-otra-cosa") is None


def test_un_dia_imposible_da_none() -> None:
    assert fecha_de_slug(f"{BASE}-del-31-de-febrero-de-2025") is None


def test_el_mes_mal_escrito_no_se_inventa() -> None:
    assert fecha_de_slug(f"{BASE}-del-10-de-marso-de-2025") is None


# ===========================================================================
# Fusión de fuentes
# ===========================================================================


def test_gobmx_gana_sobre_wayback_en_la_misma_fecha() -> None:
    """gob.mx es la página original; Wayback es una copia."""
    salida = fusionar([_reg("2026-08-18", "wayback")], [_reg("2026-08-18", "gobmx")])
    assert len(salida) == 1
    assert salida[0].fuente == "gobmx"


def test_el_orden_de_los_argumentos_no_cambia_el_resultado() -> None:
    a = fusionar([_reg("2026-08-18", "wayback")], [_reg("2026-08-18", "gobmx")])
    b = fusionar([_reg("2026-08-18", "gobmx")], [_reg("2026-08-18", "wayback")])
    assert [r.fuente for r in a] == [r.fuente for r in b] == ["gobmx"]


def test_wayback_aporta_las_fechas_que_gobmx_no_tiene() -> None:
    salida = fusionar(
        [_reg("2026-08-18", "gobmx")],
        [_reg("2026-08-18", "wayback"), _reg("2025-01-15", "wayback")],
    )
    assert {r.conferencia_id for r in salida} == {"2026-08-18", "2025-01-15"}


def test_lo_que_no_trae_fecha_se_conserva_completo() -> None:
    """No se puede deduplicar algo cuya identidad todavía no se conoce."""
    salida = fusionar([_reg(None, "gobmx", "a"), _reg(None, "wayback", "b")])
    assert len(salida) == 2


def test_la_salida_va_ordenada_por_fecha() -> None:
    salida = fusionar(
        [_reg("2026-01-05", "gobmx"), _reg("2024-10-03", "gobmx"), _reg("2025-06-01", "gobmx")]
    )
    assert [r.conferencia_id for r in salida] == ["2024-10-03", "2025-06-01", "2026-01-05"]


# ===========================================================================
# Diagnóstico
# ===========================================================================


def test_conteo_por_mes() -> None:
    regs = [_reg("2025-01-05", "gobmx"), _reg("2025-01-06", "gobmx"), _reg("2025-02-03", "gobmx")]
    assert conteo_por_mes(regs) == {"2025-01": 2, "2025-02": 1}


def test_los_huecos_solo_cuentan_dias_habiles() -> None:
    # 2024-10-05 es sábado y 2024-10-06 domingo: no deben aparecer.
    faltan = huecos([_reg("2024-10-03", "gobmx")], hasta=date(2024, 10, 7))
    assert date(2024, 10, 5) not in faltan
    assert date(2024, 10, 6) not in faltan
    assert date(2024, 10, 3) not in faltan
    assert date(2024, 10, 4) in faltan


def test_resumen_cuenta_por_fuente_y_cobertura() -> None:
    regs = [_reg("2024-10-01", "gobmx"), _reg("2024-10-02", "wayback"), _reg(None, "gobmx")]
    r = resumen(regs, hasta=date(2024, 10, 2))
    assert r["por_fuente"] == {"gobmx": 2, "wayback": 1}
    assert r["sin_fecha_en_slug"] == 1
    assert r["dias_habiles"] == 2
    assert r["dias_sin_url"] == 0
    assert r["cobertura"] == 100.0


# ===========================================================================
# Persistencia
# ===========================================================================


def test_escribir_y_leer_conserva_todo(tmp_path) -> None:
    regs = [
        RegistroURL("2026-08-18", "slug-con-acentos-ñ", "u1", "u2", "wayback", "2026", "200"),
        RegistroURL(None, "otro", "u3", "u4", "gobmx"),
    ]
    destino = tmp_path / "urls.jsonl"
    assert escribir_urls(regs, destino) == 2
    assert leer_urls(destino) == regs
    # UTF-8 legible, no escapes
    assert "ñ" in destino.read_text(encoding="utf-8")


def test_leer_un_archivo_que_no_existe_da_lista_vacia(tmp_path) -> None:
    assert leer_urls(tmp_path / "no-existe.jsonl") == []


# ===========================================================================
# El archivo real, si ya se corrió el descubrimiento
# ===========================================================================


def test_el_urls_jsonl_real_es_coherente() -> None:
    destino = config.paths().urls
    if not destino.is_file():
        pytest.skip("todavía no se corrió el descubrimiento")
    regs = leer_urls(destino)
    assert len(regs) > 400, "el corpus ronda las 460 conferencias"

    fechas = [r.conferencia_id for r in regs if r.conferencia_id]
    assert len(fechas) == len(set(fechas)), "hay fechas repetidas"
    assert min(fechas) >= "2024-10-01", "hay conferencias previas al sexenio"

    for r in regs:
        assert r.fuente in ("gobmx", "wayback")
        assert r.url_descarga.startswith("http")
        assert "conferencia-de-prensa-de-la-presidenta" in r.slug
