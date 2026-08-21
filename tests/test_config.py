"""Pruebas de la resolución de rutas y la carga de secretos."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from estenograficas import config


def test_la_raiz_se_encuentra_desde_el_paquete() -> None:
    raiz = config.find_root()
    assert (raiz / "pyproject.toml").is_file()
    assert (raiz / "CLAUDE.md").is_file()


def test_la_raiz_no_depende_del_directorio_de_trabajo(tmp_path, monkeypatch) -> None:
    """Correr pytest desde otro lado no debe mover las rutas."""
    esperada = config.find_root()
    monkeypatch.chdir(tmp_path)
    config.paths.cache_clear()
    try:
        assert config.find_root() == esperada
    finally:
        config.paths.cache_clear()


def test_la_variable_de_entorno_sobreescribe_la_raiz(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ESTENOGRAFICAS_ROOT", str(tmp_path))
    assert config.find_root() == tmp_path.resolve()


def test_sin_marcador_falla_ruidosamente(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("ESTENOGRAFICAS_ROOT", raising=False)
    with pytest.raises(RuntimeError, match="pyproject.toml"):
        config.find_root(desde=tmp_path / "hondo" / "adentro")


def test_las_rutas_de_datos_cuelgan_de_la_raiz() -> None:
    p = config.paths()
    assert p.raw == p.root / "data" / "raw"
    assert p.turnos == p.root / "data" / "interim" / "turnos.jsonl"
    assert p.conferencias == p.root / "data" / "interim" / "conferencias.jsonl"
    assert p.preguntas == p.root / "data" / "outputs" / "preguntas.jsonl"
    assert p.raw_html("2026-08-18") == p.root / "data" / "raw" / "2026-08-18.html"


def test_ensure_dirs_es_idempotente(tmp_path) -> None:
    p = config.Paths(root=tmp_path)
    p.ensure_dirs()
    p.ensure_dirs()
    for d in (p.raw, p.interim, p.gold, p.outputs, p.checkpoints):
        assert d.is_dir()


def test_ninguna_ruta_absoluta_hardcodeada_en_el_paquete() -> None:
    """CLAUDE.md: ninguna ruta absoluta escrita a mano."""
    import re

    sospechoso = re.compile(r"""["'][A-Za-z]:[\\/]|["']/(?:home|Users|mnt)/""")
    for archivo in (config.paths().src).rglob("*.py"):
        texto = archivo.read_text(encoding="utf-8")
        assert not sospechoso.search(texto), f"ruta absoluta en {archivo.name}"


# -- secretos --------------------------------------------------------------


def test_la_key_de_gemini_carga_desde_el_env() -> None:
    p = config.paths()
    if not p.env_file.is_file():
        pytest.skip(".env no existe en esta máquina")
    key = config.gemini_api_key()
    # No se asevera nada sobre el valor más allá de que existe y tiene forma.
    assert len(key) > 20


def test_el_error_de_key_faltante_no_filtra_el_valor(monkeypatch, tmp_path) -> None:
    """Una key en un traceback termina en un log. El mensaje no la incluye."""
    monkeypatch.setenv("ESTENOGRAFICAS_ROOT", str(tmp_path))  # sin .env
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    config.paths.cache_clear()
    try:
        with pytest.raises(RuntimeError) as exc:
            config.gemini_api_key()
        assert "GEMINI_API_KEY no está definida" in str(exc.value)
        assert "AIza" not in str(exc.value)
    finally:
        config.paths.cache_clear()


def test_el_env_esta_ignorado_por_git() -> None:
    """La regresión más cara posible: commitear la key."""
    import subprocess

    raiz = config.find_root()
    r = subprocess.run(
        ["git", "check-ignore", "-q", ".env"], cwd=raiz, capture_output=True
    )
    assert r.returncode == 0, ".env NO está en .gitignore"
