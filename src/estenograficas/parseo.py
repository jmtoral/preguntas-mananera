"""Fase 6: parseo masivo del corpus. PARADA OBLIGATORIA.

Corre el parser sobre las 460 conferencias de `data/raw/` y escribe los tres
archivos intermedios del contrato: `turnos.jsonl`, `hilos.jsonl` y
`conferencias.jsonl`.

Al terminar imprime el diagnóstico obligatorio y **se detiene**. El humano
tiene que revisar el conjunto de etiquetas antes de que nada siga. La razón
está probada en este mismo proyecto: `INTERLOCUTOR` costó 421 turnos de prensa
clasificados como declaraciones de gobierno sin que nada fallara ni diera un
solo síntoma.

Sobre la idempotencia: esta etapa **reescribe los tres archivos en cada
corrida** en vez de ir agregando. Parsear las 460 toma alrededor de un minuto,
así que reanudar no ahorra nada relevante, y en cambio agregar sobre un archivo
viejo dejaría renglones producidos por una versión anterior del parser
mezclados con los nuevos. Correrla dos veces produce el mismo resultado, que es
lo que exige la regla dura 2. El checkpoint se usa para el archivo de rechazos.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .parser import Conferencia, parsear_archivo

SEMILLA_MUESTRA = 20260821
"""Fija para que el diagnóstico sea reproducible entre corridas."""

# Cómo se anuncia el tema del día en la apertura. Salió de leer las primeras
# 40 conferencias: acierta en ~60%. El resto de las conferencias simplemente
# no anuncian tema, y ahí el campo va nulo. Nulo antes que inventado.
_PATRONES_TEMA = [
    r"vamos a hablar (?:de|del|sobre)\s+([^\.\n;]{3,90})",
    r"hoy vamos a presentar\s+([^\.\n;]{3,90})",
    r"hoy es (?:el )?(?:d[íi]a de )?[‘“\"']?([^\.\n;’”\"']{3,80})",
    r"el tema de hoy es\s+([^\.\n;]{3,90})",
    r"hoy tenemos\s+([^\.\n;]{3,90})",
]
_RE_TEMA = [re.compile(p, re.IGNORECASE) for p in _PATRONES_TEMA]

TURNOS_DE_APERTURA = 6
"""Solo se mira la apertura: el tema se anuncia al principio o no se anuncia."""


def tema_del_dia(conf: Conferencia) -> tuple[str | None, str, str | None]:
    """Devuelve `(tema, metodo, fragmento)`.

    El fragmento es el texto exacto que justifica el campo, como pide la regla
    dura 5: todo campo derivado lleva su procedencia.
    """
    apertura = "\n".join(
        t.texto for t in conf.turnos[:TURNOS_DE_APERTURA] if t.tipo == "funcionario"
    )[:2500]
    for rx in _RE_TEMA:
        m = rx.search(apertura)
        if m:
            tema = " ".join(m.group(1).split()).strip(" ,;:—-")
            if tema:
                return tema, "regex", " ".join(m.group(0).split())[:160]
    return None, "sin_identificar", None


@dataclass
class RegistroConferencia:
    conferencia_id: str
    fecha: str
    tema_dia: str | None
    metodo_tema: str
    fragmento_tema: str | None
    n_turnos: int
    n_hilos: int
    n_prensa: int
    n_preguntas_utiles: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resumir(conf: Conferencia) -> RegistroConferencia:
    tema, metodo, fragmento = tema_del_dia(conf)
    utiles = sum(
        1
        for h in conf.hilos
        for t in h.turnos
        if t.rol == "pregunta" and not t.ruido
    )
    return RegistroConferencia(
        conferencia_id=conf.conferencia_id,
        fecha=conf.conferencia_id,
        tema_dia=tema,
        metodo_tema=metodo,
        fragmento_tema=fragmento,
        n_turnos=len(conf.turnos),
        n_hilos=len(conf.hilos),
        n_prensa=sum(1 for t in conf.turnos if t.tipo == "prensa"),
        n_preguntas_utiles=utiles,
    )


# ---------------------------------------------------------------------------
# Diagnóstico
# ---------------------------------------------------------------------------


def _linea(titulo: str) -> None:
    print("\n" + "=" * 78)
    print(titulo)
    print("=" * 78)


def diagnostico(
    confs: list[Conferencia], registros: list[RegistroConferencia]
) -> None:
    """El diagnóstico que la fase 6 exige antes de la parada."""
    etiquetas = Counter(t.etiqueta for c in confs for t in c.turnos)

    _linea(f"ETIQUETAS DE HABLANTE ÚNICAS: {len(etiquetas)}, por frecuencia")
    print("Las de frecuencia baja son las sospechosas: una etiqueta que aparece")
    print("tres veces en 460 conferencias casi siempre es un error de parseo.\n")
    for et, n in etiquetas.most_common():
        print(f"  {n:>6}  {et[:70]}")

    _linea("ETIQUETAS QUE APARECEN 3 VECES O MENOS")
    raras = [(et, n) for et, n in etiquetas.items() if n <= 3]
    print(f"{len(raras)} etiquetas, {sum(n for _, n in raras)} turnos en total\n")
    for et, n in sorted(raras, key=lambda x: (x[1], x[0])):
        print(f"  {n}x  {et[:72]}")

    _linea("10 TURNOS AL AZAR, CON SU ETIQUETA Y SUS PRIMEROS 200 CARACTERES")
    todos = [(c.conferencia_id, t) for c in confs for t in c.turnos]
    for cid, t in random.Random(SEMILLA_MUESTRA).sample(todos, 10):
        print(f"\n  [{cid} #{t.orden}] {t.etiqueta[:60]}  ({t.tipo})")
        print(f"      {t.texto[:200]!r}")

    _linea("TEMA DEL DÍA")
    con = [r for r in registros if r.tema_dia]
    print(f"con tema identificado : {len(con)} de {len(registros)} "
          f"({100*len(con)/len(registros):.0f}%)")
    print(f"sin tema              : {len(registros) - len(con)}")
    print("\nLos sin tema no son fallos: hay conferencias que no anuncian tema.")
    print("\n15 temas de ejemplo:")
    for r in random.Random(SEMILLA_MUESTRA).sample(con, min(15, len(con))):
        print(f"  {r.fecha}  {r.tema_dia[:66]}")

    _linea("CONFERENCIAS SIN NINGÚN HILO")
    sin = [r for r in registros if r.n_hilos == 0]
    print(f"{len(sin)}: nadie se autopresentó de forma reconocible\n")
    for r in sin:
        print(f"  {r.fecha}  {r.n_turnos} turnos, {r.n_prensa} de prensa")

    _linea("VARIANTES DE LA ETIQUETA DE LA PRESIDENTA")
    for et, n in etiquetas.most_common():
        if "SHEINBAUM" in et.upper():
            print(f"  {n:>6}  {et}")

    _linea("ETIQUETAS SIN COMA QUE NO SON PRENSA NI RUIDO CONOCIDO")
    print("Cargo y nombre sin coma de por medio: `rsplit` no los separa.\n")
    conocidas = {"PREGUNTA", "PREGUNTAS", "INTERLOCUTOR", "INTERLOCUTORA",
                 "INTERLOCUTORES", "INTERVENCIÓN", "INTERVENCION", "ASISTENTES"}
    for et, n in etiquetas.most_common():
        if "," not in et and et.upper() not in conocidas:
            print(f"  {n:>6}  {et[:70]}")

    _linea("TOTALES")
    print(f"  conferencias            : {len(confs)}")
    print(f"  turnos                  : {sum(len(c.turnos) for c in confs)}")
    print(f"  turnos de prensa        : {sum(r.n_prensa for r in registros)}")
    print(f"  hilos                   : {sum(r.n_hilos for r in registros)}")
    print(f"  preguntas útiles (sin ruido): {sum(r.n_preguntas_utiles for r in registros)}")


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------


def main() -> int:
    """`python -m estenograficas.parseo`"""
    from .checkpoint import Checkpoint
    from .config import paths
    from .parser import escribir_jsonl

    p = paths()
    p.ensure_dirs()
    archivos = sorted(p.raw.glob("*.html"))
    if not archivos:
        print(f"No hay nada en {p.raw}. Correr antes: python -m estenograficas.descarga")
        return 1

    ck = Checkpoint("parseo")
    # Se limpia el registro previo: esta etapa reescribe todo en cada corrida,
    # así que arrastrar rechazos viejos mentiría sobre el estado actual.
    for f in (ck.hechos_path, ck.rechazos_path):
        f.unlink(missing_ok=True)

    print(f"parseando {len(archivos)} conferencias...")
    confs: list[Conferencia] = []
    registros: list[RegistroConferencia] = []
    for i, arch in enumerate(archivos, 1):
        try:
            c = parsear_archivo(arch)
            if not c.turnos:
                raise ValueError("cero turnos: el archivo no produjo nada")
            confs.append(c)
            r = resumir(c)
            registros.append(r)
            ck.marcar_hecho(c.conferencia_id, n_turnos=r.n_turnos, n_hilos=r.n_hilos)
        except Exception as e:  # noqa: BLE001 - se registra, no se traga
            ck.marcar_rechazado(arch.stem, razon=f"{type(e).__name__}: {e}")
        if i % 100 == 0:
            print(f"   {i}/{len(archivos)}")

    n_t = escribir_jsonl((t for c in confs for t in c.turnos), p.turnos)
    n_h = escribir_jsonl((h for c in confs for h in c.hilos), p.hilos)
    n_c = escribir_jsonl(registros, p.conferencias)

    print(f"\nescritos:")
    print(f"  {p.turnos.name}: {n_t} renglones")
    print(f"  {p.hilos.name}: {n_h} renglones")
    print(f"  {p.conferencias.name}: {n_c} renglones")
    print(f"  rechazadas: {len(ck.rechazados())}")
    for k, v in ck.rechazados().items():
        print(f"     {k}: {v['razon'][:110]}")

    diagnostico(confs, registros)

    print("\n" + "!" * 78)
    print("PARADA OBLIGATORIA. Revisa la lista de etiquetas antes de que esto siga.")
    print("Una etiqueta rara casi nunca es un hablante real; es un error de parseo,")
    print("y los errores de segmentación no dan síntomas.")
    print("!" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
