"""Pruebas del checkpointing.

La que importa es `test_reanuda_tras_matar_el_proceso`: lanza un proceso real,
lo mata sin darle oportunidad de limpiar, y comprueba que la siguiente corrida
retoma donde se quedó sin rehacer trabajo. Las demás cubren idempotencia,
rechazos y la línea truncada que deja una escritura interrumpida.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from estenograficas.checkpoint import Checkpoint, CheckpointCorrupto, ejecutar

TRABAJADOR = Path(__file__).parent / "_trabajador.py"
N_ITEMS = 20


def _lanzar(base: Path, n: int = N_ITEMS, espera: float = 0.15) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, str(TRABAJADOR), str(base), str(n), str(espera)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


# -- lo esencial -----------------------------------------------------------


@pytest.mark.lento
def test_reanuda_tras_matar_el_proceso(tmp_path: Path) -> None:
    """Interrupción real: se mata el proceso, no se simula la interrupción."""
    base = tmp_path / "checkpoints"

    # 1. Primera corrida, matada a mitad.
    proc = _lanzar(base)
    primeros: list[str] = []
    try:
        for _ in range(5):
            linea = proc.stdout.readline()
            assert linea, "el trabajador murió antes de reportar avance"
            primeros.append(linea.strip())
        # kill() en Windows es TerminateProcess y en POSIX es SIGKILL: en los
        # dos casos el proceso muere sin correr finally, sin cerrar archivos y
        # sin vaciar buffers. Si el checkpoint sobrevive esto, sobrevive todo.
        proc.kill()
    finally:
        proc.wait(timeout=30)

    assert proc.returncode != 0, "se esperaba una muerte violenta, no una salida limpia"

    ck = Checkpoint("demo", base=base)
    tras_muerte = ck.hechos()
    assert len(tras_muerte) >= 5, "el avance previo a la muerte no quedó en disco"
    assert len(tras_muerte) < N_ITEMS, "murió demasiado tarde; la prueba no probó nada"
    assert set(primeros) <= set(tras_muerte), (
        "hay items que el trabajador reportó pero que no quedaron en el checkpoint"
    )

    # 2. Segunda corrida, completa. Solo debe tocar lo que faltaba.
    proc2 = _lanzar(base)
    salida, err = proc2.communicate(timeout=120)
    assert proc2.returncode == 0, err
    segunda = [l for l in salida.splitlines() if l.strip()]

    assert not (set(segunda) & set(tras_muerte)), (
        f"la segunda corrida rehizo trabajo ya hecho: "
        f"{sorted(set(segunda) & set(tras_muerte))}"
    )

    ck2 = Checkpoint("demo", base=base)
    # item-07 falla siempre; los otros 19 se completan entre las dos corridas.
    assert len(ck2.hechos()) == N_ITEMS - 1
    assert set(ck2.rechazados()) == {"item-07"}
    assert len(ck2.procesados()) == N_ITEMS

    # 3. Tercera corrida: no queda nada por hacer.
    proc3 = _lanzar(base)
    salida3, err3 = proc3.communicate(timeout=120)
    assert proc3.returncode == 0, err3
    assert salida3.strip() == "", f"rehizo trabajo estando completo: {salida3!r}"

    ck3 = Checkpoint("demo", base=base)
    assert len(ck3.hechos()) == N_ITEMS - 1, "correrlo de más duplicó registros"


@pytest.mark.lento
def test_correrlo_dos_veces_da_lo_mismo(tmp_path: Path) -> None:
    """Idempotencia, regla dura 2: dos corridas seguidas, mismo resultado."""
    base = tmp_path / "checkpoints"

    p1 = _lanzar(base, n=6, espera=0.0)
    p1.communicate(timeout=120)
    estado_1 = Checkpoint("demo", base=base).resumen()

    p2 = _lanzar(base, n=6, espera=0.0)
    salida2, _ = p2.communicate(timeout=120)
    estado_2 = Checkpoint("demo", base=base).resumen()

    assert estado_1 == estado_2
    assert salida2.strip() == ""


# -- rechazos: regla dura 3 ------------------------------------------------


def test_lo_que_falla_queda_registrado_con_su_razon(tmp_path: Path) -> None:
    ck = Checkpoint("r", base=tmp_path)

    def trabajo(item_id: str) -> dict:
        if item_id == "b":
            raise ValueError("texto vacío")
        return {}

    hechos = list(ejecutar(["a", "b", "c"], trabajo, ck))

    assert hechos == ["a", "c"]
    rechazado = ck.rechazados()["b"]
    assert "ValueError" in rechazado["razon"]
    assert "texto vacío" in rechazado["razon"]


def test_un_rechazado_no_se_reintenta_solo(tmp_path: Path) -> None:
    """Un rechazo cuenta como procesado. Reintentar es un acto deliberado."""
    ck = Checkpoint("r", base=tmp_path)
    ck.marcar_rechazado("x", razon="lo que sea")
    assert ck.pendientes(["x", "y"]) == ["y"]


# -- lectura del registro --------------------------------------------------


def test_pendientes_respeta_el_orden_y_quita_duplicados(tmp_path: Path) -> None:
    ck = Checkpoint("p", base=tmp_path)
    ck.marcar_hecho("b")
    assert ck.pendientes(["a", "b", "c", "a"]) == ["a", "c"]


def test_una_ultima_linea_truncada_se_tolera_y_se_reporta(tmp_path: Path) -> None:
    """Escritura interrumpida a media línea: ese item se reprocesa, no rompe."""
    ck = Checkpoint("t", base=tmp_path)
    ck.marcar_hecho("a")
    with open(ck.hechos_path, "a", encoding="utf-8") as f:
        f.write('{"id": "b", "ts": 17')  # cortada por la mitad, sin newline

    ck2 = Checkpoint("t", base=tmp_path)
    assert set(ck2.hechos()) == {"a"}
    assert ck2.lineas_truncadas == 1
    assert ck2.pendientes(["a", "b"]) == ["b"]


def test_una_linea_rota_en_medio_es_un_error(tmp_path: Path) -> None:
    """En medio no es una escritura interrumpida: es corrupción y no se adivina."""
    ck = Checkpoint("t", base=tmp_path)
    ck.marcar_hecho("a")
    with open(ck.hechos_path, "a", encoding="utf-8") as f:
        f.write("basura no json\n")
    ck.marcar_hecho("c")

    with pytest.raises(CheckpointCorrupto):
        Checkpoint("t", base=tmp_path).hechos()


def test_los_metadatos_del_trabajo_se_guardan(tmp_path: Path) -> None:
    ck = Checkpoint("m", base=tmp_path)
    list(ejecutar(["a"], lambda i: {"largo": 7}, ck))
    assert ck.hechos()["a"]["largo"] == 7


def test_los_registros_se_escriben_en_utf8_legible(tmp_path: Path) -> None:
    """Nada de \\u00f1: los ids y razones traen acentos y hay que poder leerlos."""
    ck = Checkpoint("u", base=tmp_path)
    ck.marcar_rechazado("2024-11-05", razon="versión estenográfica vacía")
    crudo = ck.rechazos_path.read_text(encoding="utf-8")
    assert "versión estenográfica vacía" in crudo
    assert json.loads(crudo.splitlines()[0])["id"] == "2024-11-05"
