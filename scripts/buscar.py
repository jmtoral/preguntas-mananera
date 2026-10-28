"""Busca intercambios (pregunta de la prensa + respuesta) por palabras clave.

Existe para una necesidad concreta de reportería: dado un tema de coyuntura,
saber **quién preguntó qué y qué contestó la presidenta**, sin leer 460
versiones estenográficas a mano.

La unidad de salida es el *intercambio*: un turno de pregunta más los turnos de
respuesta que le siguen hasta la siguiente pregunta del mismo hilo. Se conservan
el periodista, el medio, la fecha, la categoría temática y la URL de la versión
estenográfica original, para que cualquier resultado se pueda verificar contra
la fuente.

    python scripts/buscar.py --frase "organismos autonomos" --frase INAI --nombre autonomos

Las frases se comparan sin acentos y sin distinguir mayúsculas, ancladas a
límite de palabra: `INAI` no casa dentro de `inaimputable`. Varias `--frase` son
OR; cada `--y` es un requisito adicional obligatorio.

Por omisión busca en la pregunta y en el asunto temático, no en la respuesta: la
presidenta menciona muchos temas que nadie le preguntó. `--en ambos` incluye la
respuesta, `--en respuesta` busca solo ahí.

`--responde` deja solo los intercambios donde contestó esa persona y, si se
busca en la respuesta, busca **solo en sus palabras**: un intercambio donde
Harfuch dice "revisar" y Sheinbaum no, no cuenta como de Sheinbaum.

    python scripts/buscar.py --frase "revisa*|revise*|reviso" --en respuesta --responde sheinbaum
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from estenograficas.config import paths
from estenograficas.ids import id_estable


# ---------------------------------------------------------------- normalizar

def plano(texto: str) -> str:
    """Minúsculas sin acentos. Para comparar, nunca para mostrar."""
    if not texto:
        return ""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _una(frase: str) -> str:
    """Frase literal, con límite de palabra donde el borde es alfanumérico.

    Los espacios se vuelven flexibles porque el texto trae saltos de línea y
    espacios duros: "organismos autonomos" casa aunque haya un salto en medio.

    Un `*` en un extremo suelta el anclaje de ese lado: `amenaz*` casa con
    "amenaza", "amenazas" y "amenazando". Sin eso hay que enumerar las
    conjugaciones a mano, que es exactamente donde se pierden resultados.
    """
    f = plano(frase).strip()
    abierta_izq = f.startswith("*")
    abierta_der = f.endswith("*")
    f = f.strip("*").strip()
    if not f:
        raise ValueError(f"frase vacía: {frase!r}")
    cuerpo = r"\s+".join(re.escape(p) for p in f.split())
    izq = "" if abierta_izq or not f[:1].isalnum() else r"\b"
    der = "" if abierta_der or not f[-1:].isalnum() else r"\b"
    return izq + cuerpo + der


def patron(frase: str) -> re.Pattern:
    """Un criterio. La barra vertical separa alternativas: casa cualquiera.

    Permite que un requisito obligatorio (`--y`) admita varias formas de decir
    lo mismo: `--y "arancel*|militar|amenaz*"` exige que aparezca alguna de las
    tres, sin volver obligatoria ninguna en particular.
    """
    alternativas = [a for a in frase.split("|") if a.strip()]
    if not alternativas:
        raise ValueError(f"criterio vacío: {frase!r}")
    return re.compile("|".join(f"(?:{_una(a)})" for a in alternativas))


# ------------------------------------------------------------------- cargar

def _leer_jsonl(ruta: Path):
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                yield json.loads(linea)


def cargar_anexos() -> tuple[dict, dict, dict]:
    """Temas, postura y URLs, indexados por la llave estable de `ids.py`.

    La llave es (conferencia, orden) y no el id con número de hilo, porque el
    número de hilo se mueve con cada reparseo (ver `src/estenograficas/ids.py`).
    """
    p = paths()

    temas = {}
    ruta_temas = p.interim / "temas_dos_niveles.jsonl"
    if ruta_temas.is_file():
        for d in _leer_jsonl(ruta_temas):
            temas[id_estable(d["id_pregunta"])] = d

    postura = {}
    ruta_postura = p.outputs / "postura_final.jsonl"
    if ruta_postura.is_file():
        for d in _leer_jsonl(ruta_postura):
            postura[id_estable(d["id_pregunta"])] = d

    urls = {}
    if p.urls.is_file():
        for d in _leer_jsonl(p.urls):
            urls[d["conferencia_id"]] = d.get("url_original") or d.get("url_descarga")

    return temas, postura, urls


def intercambios():
    """Recorre `hilos.jsonl` y produce un intercambio por turno de pregunta.

    Los turnos marcados `ruido` (`INTERVENCIÓN:` y compañía) no abren
    intercambio ni cortan el que va corriendo: son ruido de sala.
    """
    for hilo in _leer_jsonl(paths().hilos):
        actual = None
        for t in hilo["turnos"]:
            if t.get("ruido"):
                continue
            if t["rol"] == "pregunta":
                if actual:
                    yield actual
                # Una pregunta `incierta` es alguien distinto gritando desde el
                # salón: no se le carga al periodista de la tanda (CLAUDE.md).
                incierta = t.get("atribucion") == "incierta"
                actual = {
                    "conferencia_id": hilo["conferencia_id"],
                    "hilo": hilo["hilo"],
                    "orden": t.get("orden"),
                    "periodista": None if incierta else hilo.get("periodista_canonico") or hilo.get("periodista"),
                    "medio": None if incierta else hilo.get("medio"),
                    "atribucion": t.get("atribucion"),
                    "pregunta": t["texto"],
                    "respuestas": [],
                    "quien_por_turno": [],   # paralela a `respuestas`
                    "quien_responde": [],
                }
            elif actual is not None:
                actual["respuestas"].append(t["texto"])
                quien = t.get("quien")
                actual["quien_por_turno"].append(quien or "")
                if quien and quien not in actual["quien_responde"]:
                    actual["quien_responde"].append(quien)
        if actual:
            yield actual


# -------------------------------------------------------------------- buscar

def casa(texto_plano: str, ors: list[re.Pattern], ands: list[re.Pattern]) -> bool:
    if ors and not any(p.search(texto_plano) for p in ors):
        return False
    if ands and not all(p.search(texto_plano) for p in ands):
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--frase", action="append", default=[],
                    help="término o frase; repetible, unidas por OR")
    ap.add_argument("--y", dest="ys", action="append", default=[],
                    help="término obligatorio adicional; repetible")
    ap.add_argument("--en", choices=["pregunta", "respuesta", "ambos"], default="pregunta",
                    help="dónde buscar (por omisión: pregunta + asunto temático)")
    ap.add_argument("--desde", help="fecha mínima, AAAA-MM-DD")
    ap.add_argument("--hasta", help="fecha máxima, AAAA-MM-DD")
    ap.add_argument("--periodista", help="filtra por periodista, subcadena sin acentos")
    ap.add_argument("--medio", help="filtra por medio, subcadena sin acentos")
    ap.add_argument("--responde", help="filtra por quien responde, subcadena sin acentos; "
                    "con --en respuesta/ambos busca solo en sus turnos")
    ap.add_argument("--nombre", help="nombre base de los archivos de salida")
    ap.add_argument("--limite", type=int, default=0,
                    help="máximo de resultados a escribir (0 = todos)")
    ap.add_argument("--listar-asuntos", action="store_true",
                    help="lista los asuntos temáticos que casaron, en vez de escribir resultados")
    args = ap.parse_args()

    if not args.frase and not args.ys:
        ap.error("hace falta al menos una --frase o un --y")

    ors = [patron(f) for f in args.frase]
    ands = [patron(f) for f in args.ys]
    desde = args.desde or ""
    hasta = args.hasta or "9999"
    f_per = plano(args.periodista) if args.periodista else None
    f_med = plano(args.medio) if args.medio else None
    f_resp = plano(args.responde) if args.responde else None

    temas, postura, urls = cargar_anexos()

    hallazgos = []
    revisados = 0
    fuera_de_rango = 0
    asuntos: dict[str, int] = {}

    for ic in intercambios():
        conf = ic["conferencia_id"]
        if not (desde <= conf <= hasta):
            fuera_de_rango += 1
            continue
        revisados += 1

        if f_per and f_per not in plano(ic["periodista"] or ""):
            continue
        if f_med and f_med not in plano(ic["medio"] or ""):
            continue

        llave = f"{conf}-t{ic['orden']}"
        tema = temas.get(llave, {})
        pos = postura.get(llave, {})

        respuesta = "\n\n".join(ic["respuestas"])
        if f_resp:
            suyas = [r for r, q in zip(ic["respuestas"], ic["quien_por_turno"])
                     if f_resp in plano(q)]
            if not suyas:
                continue
            respuesta_buscada = "\n\n".join(suyas)
        else:
            respuesta_buscada = respuesta
        asunto = tema.get("asunto") or ""
        if args.en == "pregunta":
            campo = ic["pregunta"] + "\n" + asunto
        elif args.en == "respuesta":
            campo = respuesta_buscada
        else:
            campo = ic["pregunta"] + "\n" + asunto + "\n" + respuesta_buscada

        if not casa(plano(campo), ors, ands):
            continue

        clave_asunto = asunto or "(sin clasificar)"
        asuntos[clave_asunto] = asuntos.get(clave_asunto, 0) + 1
        hallazgos.append({
            "fecha": conf,
            "periodista": ic["periodista"] or "",
            "medio": ic["medio"] or "",
            "atribucion": ic["atribucion"] or "",
            "categoria": tema.get("categoria") or "",
            "asunto": asunto,
            "postura": pos.get("postura") or "",
            "responde": "; ".join(ic["quien_responde"]),
            "pregunta": ic["pregunta"],
            "respuesta": respuesta,
            "url": urls.get(conf, ""),
        })

    hallazgos.sort(key=lambda h: (h["fecha"], h["periodista"]))
    if args.limite:
        hallazgos = hallazgos[: args.limite]

    # ------------------------------------------------------------- resumen
    print(f"Intercambios revisados: {revisados:,}  (fuera del rango: {fuera_de_rango:,})")
    print(f"Coincidencias: {len(hallazgos):,} en "
          f"{len({h['fecha'] for h in hallazgos})} conferencias")
    if hallazgos:
        por_per: dict[str, int] = {}
        for h in hallazgos:
            k = f"{h['periodista'] or '(sin identificar)'} · {h['medio'] or '?'}"
            por_per[k] = por_per.get(k, 0) + 1
        print("\nQuién preguntó más:")
        for k, v in sorted(por_per.items(), key=lambda x: -x[1])[:15]:
            print(f"  {v:3d}  {k}")

    if args.listar_asuntos:
        print("\nAsuntos que casaron:")
        for k, v in sorted(asuntos.items(), key=lambda x: -x[1])[:60]:
            print(f"  {v:3d}  {k}")
        return 0

    if not args.nombre:
        print("\n(sin --nombre no se escribe nada; agrégalo para generar CSV y Markdown)")
        return 0

    salida = paths().outputs / "busquedas"
    salida.mkdir(parents=True, exist_ok=True)

    ruta_csv = salida / f"{args.nombre}.csv"
    campos = ["fecha", "periodista", "medio", "atribucion", "categoria", "asunto",
              "postura", "responde", "pregunta", "respuesta", "url"]
    with ruta_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(hallazgos)

    ruta_md = salida / f"{args.nombre}.md"
    criterio = " OR ".join(args.frase) or "(sin OR)"
    if args.ys:
        criterio += "  Y  " + " Y ".join(args.ys)
    with ruta_md.open("w", encoding="utf-8") as f:
        f.write(f"# Búsqueda: {args.nombre}\n\n")
        f.write(f"- **Criterio:** {criterio}\n")
        f.write(f"- **Dónde:** {args.en}"
                + (f", solo en turnos de «{args.responde}»" if args.responde else "") + "\n")
        f.write(f"- **Rango:** {args.desde or 'inicio'} a {args.hasta or 'fin'}\n")
        f.write(f"- **Resultados:** {len(hallazgos)} intercambios en "
                f"{len({h['fecha'] for h in hallazgos})} conferencias\n")
        f.write(f"- **Generado:** {dt.date.today().isoformat()} con `scripts/buscar.py`\n")
        f.write("\n> La respuesta es la del turno siguiente en la estenográfica. "
                "Quien responde no siempre es la presidenta: el campo lo dice.\n\n---\n\n")
        for h in hallazgos:
            quien = h["periodista"] or "(periodista sin identificar)"
            medio = f" · {h['medio']}" if h["medio"] else ""
            f.write(f"## {h['fecha']} — {quien}{medio}\n\n")
            if h["asunto"]:
                f.write(f"*{h['asunto']}*\n\n")
            f.write("**PREGUNTA**\n\n")
            f.write("> " + h["pregunta"].replace("\n", "\n> ") + "\n\n")
            if h["respuesta"]:
                f.write(f"**RESPONDE: {h['responde'] or '?'}**\n\n")
                f.write("> " + h["respuesta"].replace("\n", "\n> ") + "\n\n")
            else:
                f.write("*(sin respuesta registrada en la estenográfica)*\n\n")
            if h["url"]:
                f.write(f"[Versión estenográfica completa]({h['url']})\n\n")
            f.write("---\n\n")

    print(f"\nEscrito:\n  {ruta_csv}\n  {ruta_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
