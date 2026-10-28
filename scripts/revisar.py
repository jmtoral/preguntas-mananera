"""Qué dijo la presidenta que iba a "revisar". Pedido de Nayeli Roldán, 2026-10-05.

Toma cada intercambio donde **la propia Sheinbaum** usa el verbo revisar en su
respuesta (no Harfuch ni Ebrard, ni la pregunta), parte su turno en oraciones y
clasifica cada oración por la forma gramatical que rodea al verbo:

    en_curso    estamos revisando, se está revisando, lo está revisando
    hecho       ya lo revisamos, ya se revisó, hemos revisado
    encargo     que lo revise la Conagua, que se revise
    necesidad   hay que revisar, habría que revisarlo, tiene que revisarse
    compromiso  lo revisamos, vamos a revisar, lo voy a revisar, se va a revisar
    otra        todo lo demás: descripciones, generalidades, otros sujetos

`metodo` es regex, y la oración va completa como fragmento que lo justifica.
"Lo revisamos" es presente con valor de futuro en el habla de la mañanera ("con
gusto lo revisamos"), por eso cuenta como compromiso; si va precedido de "ya"
es un hecho. Nada de esto mide si la revisión ocurrió: mide qué se dijo.

El "qué" se toma del asunto temático de la pregunta (`temas_dos_niveles.jsonl`,
clasificación automática), no de la oración: es para agrupar, y la oración está
al lado para leerla.

    python scripts/revisar.py
"""

from __future__ import annotations

import collections
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from buscar import cargar_anexos, intercambios, plano  # noqa: E402
from estenograficas.config import paths  # noqa: E402

# Todas las conjugaciones y enclíticos de revisar; deja fuera "revisión" y "revista".
VERBO = re.compile(r"\b(?:revisa\w*|revise\w*|reviso)\b")

# Primera regla que casa gana; el orden importa ("ya lo revisamos" no es compromiso).
FORMAS = [
    ("hecho", r"\bya\s+(?:\w+\s+){0,2}revis|\bhemos\s+revisado"),
    ("en_curso", r"\b(?:estamos|esta|estan|estoy|seguimos|sigue|siguen|estado|estuvimos"
                 r"|va a estar|van a estar|vamos a estar)\s+(?:\w+\s+)?revisand"),
    ("encargo", r"\bque\s+(?:\w+\s+){0,4}(?:revise\w*|revisara\w*|puedan?\s+revis)"
                r"|\bpara que\s+(?:\w+\s+){0,2}revis|\b(?:instru|pedi|pido|pedimos|solicit)\w*\s+(?:\w+\s+){0,4}revis"),
    ("necesidad", r"\b(?:hay que|habria que|tiene que|tienen que|tenemos que|tendria que|tendriamos que|tendrian que"
                  r"|debe|deben|debemos|deberia|necesitamos|importante)\s+(?:\w+\s+)?revis"),
    ("compromiso", r"\b(?:vamos a|voy a|va a|van a|podemos|se puede|puedo)\s+(?:\w+\s+){0,2}revis"
                   r"|\b(?:lo|la|los|las)\s+(?:\w+\s+)?(?:revisamos|reviso|revisaremos)\b"
                   r"|(?:^|entonces,?\s+|gusto\s+)revisamos\s+(?:el|la|los|las|este|esta|ese|esa|eso|esto|su|sus)\b"),
]
FORMAS = [(k, re.compile(p)) for k, p in FORMAS]
PROMESA = {"en_curso", "encargo", "necesidad", "compromiso"}
# Del más comprometido al menos: un intercambio toma la forma más alta que tuvo.
RANGO = ["compromiso", "en_curso", "encargo", "necesidad", "hecho", "otra"]


def forma(oracion: str) -> str:
    p = plano(oracion)
    for k, rx in FORMAS:
        if rx.search(p):
            return k
    return "otra"


def oraciones(texto: str):
    for o in re.split(r"(?<=[.?!…])\s+|\n+", texto):
        if VERBO.search(plano(o)):
            yield " ".join(o.split())


# ----------------------------------------------------- verbos de indagación
# Además de "revisar", la presidenta usa otros verbos de indagación en gerundio
# ("se está viendo legalmente qué procede"). Solo cuentan en construcción de
# gerundio con estar o seguir: "vamos a ver" es muletilla y "estamos trabajando"
# es demasiado genérico (1,517 oraciones), así que quedan fuera.
#
# La categoría se llama neutral, `en_curso`: el corpus no dice si es evasión.
# Quién actúa se guarda aparte, porque "lo está analizando el canciller" y
# "estamos analizando" no afirman lo mismo.
INFINITIVO = {
    "viendo": "ver", "analizando": "analizar", "investigando": "investigar",
    "evaluando": "evaluar", "estudiando": "estudiar", "valorando": "valorar",
    "consultando": "consultar", "checando": "checar", "verificando": "verificar",
    "averiguando": "averiguar", "revisando": "revisar",
}
SUJETOS = ["nosotros", "impersonal", "tercero"]
PROCESO = re.compile(
    r"\b(?P<pre>se\s+(?:esta|estan|sigue|siguen)"
    r"|(?:lo|la|los|las|le)\s+(?:estamos|esta|estan|seguimos|sigue|siguen)"
    r"|estamos|seguimos|estoy|esta|estan|sigue|siguen)"
    r"\s+(?:\w+\s+){0,2}(?P<g>" + "|".join(INFINITIVO) + r")\b"
)
# "estudiantes que están estudiando": el verbo es el oficio, no una indagación.
NO_ES_INDAGACION = re.compile(r"\bestudiantes?\b")


def _sujeto(pre: str) -> str:
    if pre.startswith("se "):
        return "impersonal"
    if re.search(r"\b(?:estamos|seguimos|estoy)\b", pre):
        return "nosotros"
    return "tercero"


def hallazgos(texto: str):
    """Una tupla (oración, verbo, forma, sujeto) por oración y verbo.

    Para "revisar" la forma es la de `forma()`, sin cambios; el sujeto solo se
    llena cuando hay gerundio. Los verbos nuevos son siempre `en_curso`.
    """
    for o in re.split(r"(?<=[.?!…])\s+|\n+", texto):
        p = plano(o)
        o = " ".join(o.split())
        dicho = set()
        for m in PROCESO.finditer(p):
            v = INFINITIVO[m["g"]]
            if v == "estudiar" and NO_ES_INDAGACION.search(p):
                continue
            if v in dicho:
                continue
            dicho.add(v)
            yield o, v, (forma(o) if v == "revisar" else "en_curso"), _sujeto(m["pre"])
        if "revisar" not in dicho and VERBO.search(p):
            yield o, "revisar", forma(o), ""


def demo() -> None:
    casos = {
        "Con gusto lo revisamos.": "compromiso",
        "Se está revisando con la Secretaría.": "en_curso",
        "Ya lo revisamos y no hay nada.": "hecho",
        "Que lo revise la Conagua.": "encargo",
        "Pues hay que revisarlo.": "necesidad",
        "Lo vamos a empezar a revisar.": "compromiso",
        "Entonces, revisamos este caso.": "compromiso",
        "Nosotros hemos estado revisando las tendencias.": "en_curso",
        "Y a Medio Ambiente también, para que pueda revisarlo.": "encargo",
        "Se instruye a la Agencia revisar los permisos.": "encargo",
        "Tendría que revisarse quién lo promovió.": "necesidad",
        "Le pedimos a la fiscal Ernestina Godoy que pueda revisarlo.": "encargo",
        "Lo que pedimos es que la Fiscalía del estado revise qué ocurrió.": "encargo",
        "Revisamos todos los días la seguridad.": "otra",
        "Si revisan que hay suficiente información, dictar una orden.": "otra",
    }
    for o, esperado in casos.items():
        assert forma(o) == esperado, (o, forma(o), esperado)

    # (verbo, forma, sujeto) de la primera coincidencia; None si no debe contar.
    proceso = {
        "Se está viendo legalmente qué procede.": ("ver", "en_curso", "impersonal"),
        "Estamos analizando el proyecto.": ("analizar", "en_curso", "nosotros"),
        "Lo está evaluando el canciller.": ("evaluar", "en_curso", "tercero"),
        "Se sigue investigando.": ("investigar", "en_curso", "impersonal"),
        "Estamos revisando.": ("revisar", "en_curso", "nosotros"),
        "Con gusto lo revisamos.": ("revisar", "compromiso", ""),
        "Son 200 mil estudiantes que están estudiando en las Benito Juárez.": None,
        "Vamos a ver qué pasa.": None,
        "Estamos trabajando en eso.": None,
    }
    for o, esperado in proceso.items():
        h = next(hallazgos(o), None)
        assert (h[1:] if h else None) == esperado, (o, h, esperado)


def main() -> int:
    demo()
    temas, _postura, urls = cargar_anexos()
    filas = []
    for ic in intercambios():
        conf = ic["conferencia_id"]
        tema = temas.get(f"{conf}-t{ic['orden']}", {})
        for r, q in zip(ic["respuestas"], ic["quien_por_turno"]):
            if "sheinbaum" not in plano(q):
                continue
            for o, verbo, forma_o, sujeto in hallazgos(r):
                filas.append({
                    "fecha": conf,
                    "orden": ic["orden"],
                    "periodista": ic["periodista"] or "",
                    "medio": ic["medio"] or "",
                    "categoria": tema.get("categoria") or "",
                    "asunto": tema.get("asunto") or "",
                    "verbo": verbo,
                    "sujeto": sujeto,
                    "forma": forma_o,
                    "metodo": "regex",
                    "oracion": o,
                    "pregunta": " ".join(ic["pregunta"].split()),
                    "url": urls.get(conf, ""),
                })

    salida = paths().outputs / "busquedas"
    salida.mkdir(parents=True, exist_ok=True)
    ruta = salida / "sheinbaum_revisar.csv"
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    # Un intercambio cuenta una vez; su forma es la "más prometedora" que tuvo.
    por_ic: dict[tuple, dict] = {}
    for fl in filas:
        k = (fl["fecha"], fl["orden"])
        if k not in por_ic or RANGO.index(fl["forma"]) < RANGO.index(por_ic[k]["forma"]):
            por_ic[k] = fl

    print(f"Oraciones de Sheinbaum con alguno de los verbos: {len(filas):,}")
    print(f"Intercambios (preguntas) donde los usa: {len(por_ic):,} "
          f"en {len({k[0] for k in por_ic})} conferencias")
    print("\nPor verbo (oraciones):")
    for k, n in collections.Counter(f["verbo"] for f in filas).most_common():
        print(f"  {n:5d}  {k}")
    print("\nPor sujeto (oraciones con gerundio):")
    for k, n in collections.Counter(f["sujeto"] or "(sin gerundio)" for f in filas).most_common():
        print(f"  {n:5d}  {k}")
    print("\nPor forma (intercambio contado una vez, por su forma más comprometida):")
    for k, n in collections.Counter(d["forma"] for d in por_ic.values()).most_common():
        print(f"  {n:5d}  {k}")

    prom = [d for d in por_ic.values() if d["forma"] in PROMESA]
    print(f"\nCon promesa o revisión en curso: {len(prom):,}")
    print("\nPor categoría temática de la pregunta:")
    for k, n in collections.Counter(d["categoria"] or "(sin clasificar)" for d in prom).most_common():
        print(f"  {n:5d}  {k}")
    print("\nAsuntos más frecuentes:")
    for k, n in collections.Counter(d["asunto"] or "(sin clasificar)" for d in prom).most_common(40):
        print(f"  {n:5d}  {k}")
    print(f"\nEscrito: {ruta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
