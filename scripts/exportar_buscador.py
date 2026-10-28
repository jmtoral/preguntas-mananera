"""Arma el buscador web: una página autocontenida con el corpus adentro.

Existe para que alguien que no programa pueda hacer las búsquedas de
`scripts/buscar.py` desde el navegador. La página no llama a ningún servidor:
el corpus entero viaja comprimido dentro del HTML, así que funciona offline y
no hay nada que mantener corriendo.

    python scripts/exportar_buscador.py [--hasta 2026-09-30]

Escribe `data/outputs/buscador.html`. La plantilla es
`assets/buscador_plantilla.html` y lleva dos marcadores: `{{DATOS}}` (el corpus
en gzip+base64) y `{{TEMAS}}` (las coyunturas guardadas de `TEMAS`).

**La postura NO se exporta, a propósito.** Reprobó la compuerta de validación
—57% de acuerdo, kappa 0.34— y en una herramienta que se usa sin nadie al lado
que lo advierta, una columna así se cita. Categoría y asunto sí van: son
descriptivos y sirven para descubrir vocabulario.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from buscar import cargar_anexos, intercambios, plano  # noqa: E402
from revisar import INFINITIVO, RANGO, SUJETOS, hallazgos  # noqa: E402
from estenograficas.config import paths  # noqa: E402


# Coyunturas guardadas. Cada lista son términos ya calibrados contra el corpus:
# se probaron con `buscar.py --listar-asuntos` antes de quedarse aquí.
TEMAS = {
    "Organismos autónomos": [
        "organismos autónomos", "órganos autónomos", "INAI", "Cofece", "Ifetel",
        "IFT", "Instituto Federal de Telecomunicaciones", "Coneval", "Mejoredu",
        "Transparencia para el Pueblo", "Plataforma Nacional de Transparencia",
    ],
    "Elección judicial": [
        "elección judicial", "reforma judicial", "Poder Judicial", "jueces electos",
        "ministros electos", "acordeones", "comité de evaluación", "insaculación",
        "tómbola", "elección de jueces", "elección de ministros",
    ],
    "Muerte del Mencho": [
        "Mencho", "Nemesio Oseguera", "Oseguera Cervantes",
    ],
    "Trump y las amenazas": [
        "Trump", "arancel*", "intervención militar", "narcoterror*",
        "unilateral", "injerencia", "soberanía",
    ],
    "Huachicol fiscal": [
        "huachicol*", "combustible robado", "robo de combustible", "Marina huachicol",
    ],
    "Ayotzinapa": [
        "Ayotzinapa", "43 normalistas", "normalistas desaparecidos",
    ],
}


# Revisar primero: es el verbo que se pidió; los demás por orden de frecuencia en el corpus.
VERBOS = ["revisar"] + [v for v in dict.fromkeys(INFINITIVO.values()) if v != "revisar"]


def construir(hasta: str | None = None) -> dict:
    """Corpus en forma columnar: los repetidos se guardan una vez."""
    temas, _postura, urls = cargar_anexos()

    listas: dict[str, list[str]] = {"confs": [], "per": [], "med": [], "cat": [], "resp": [],
                                    "quien": []}
    indices: dict[str, dict[str, int]] = {k: {} for k in listas}

    def idx(campo: str, valor: str) -> int:
        d = indices[campo]
        if valor not in d:
            d[valor] = len(listas[campo])
            listas[campo].append(valor)
        return d[valor]

    filas = []
    # La vista «Lo que prometió revisar»: una entrada por oración de Sheinbaum
    # con el verbo, apuntando a la fila de su intercambio. La forma es la de
    # `scripts/revisar.py`, así que las cifras de la página y del script son las mismas.
    revisar = []
    for ic in intercambios():
        conf = ic["conferencia_id"]
        if hasta and conf > hasta:
            continue
        tema = temas.get(f"{conf}-t{ic['orden']}", {})
        filas.append([
            idx("confs", conf),
            idx("per", ic["periodista"] or ""),
            idx("med", ic["medio"] or ""),
            idx("cat", tema.get("categoria") or ""),
            tema.get("asunto") or "",
            idx("resp", "; ".join(ic["quien_responde"])),
            ic["pregunta"],
            # Turno por turno con su hablante, no fundidos: así el buscador
            # puede buscar solo en lo que dijo una persona.
            [[idx("quien", q), r] for q, r in zip(ic["quien_por_turno"], ic["respuestas"])],
        ])
        for q, r in zip(ic["quien_por_turno"], ic["respuestas"]):
            if "sheinbaum" in plano(q):
                revisar += [[len(filas) - 1, RANGO.index(f), o, VERBOS.index(v), SUJETOS.index(su) if su else -1]
                            for o, v, f, su in hallazgos(r)]

    # Las filas salen ya ordenadas por conferencia y turno; el buscador ordena
    # por fecha y desempata por esta posición, así que no se reordenan aquí.
    return {
        "confs": listas["confs"],
        "urls": [urls.get(c, "") for c in listas["confs"]],
        "per": listas["per"],
        "med": listas["med"],
        "cat": listas["cat"],
        "resp": listas["resp"],
        "quien": listas["quien"],
        "rows": filas,
        "revisar": {"formas": RANGO, "verbos": VERBOS, "sujetos": SUJETOS, "filas": revisar},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hasta", help="última conferencia que entra (AAAA-MM-DD); por omisión, todas")
    args = ap.parse_args()

    plantilla = paths().root / "assets" / "buscador_plantilla.html"
    if not plantilla.is_file():
        raise SystemExit(f"Falta la plantilla: {plantilla}")

    datos = construir(args.hasta)
    crudo = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    comprimido = gzip.compress(crudo, 9)
    b64 = base64.b64encode(comprimido).decode("ascii")

    html = plantilla.read_text(encoding="utf-8")
    for marcador in ("{{DATOS}}", "{{TEMAS}}"):
        if marcador not in html:
            raise SystemExit(f"La plantilla no trae el marcador {marcador}")

    html = html.replace("{{TEMAS}}", json.dumps(TEMAS, ensure_ascii=False, indent=2))
    html = html.replace("{{DATOS}}", b64)

    destino = paths().outputs / "buscador.html"
    destino.write_text(html, encoding="utf-8")

    print(f"Intercambios:  {len(datos['rows']):,}")
    print(f"Conferencias:  {len(datos['confs']):,}  ({datos['confs'][0]} a {datos['confs'][-1]})")
    print(f"JSON crudo:    {len(crudo) / 1e6:.2f} MB")
    print(f"Comprimido:    {len(comprimido) / 1e6:.2f} MB")
    print(f"Página final:  {destino.stat().st_size / 1e6:.2f} MB  (tope del artefacto: 16 MB)")
    print(f"\nEscrito: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
