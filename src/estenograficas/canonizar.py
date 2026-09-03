"""Canonización de nombres de periodista y de medio.

Dos problemas distintos que la estenográfica mezcla:

**Los nombres se escriben mal.** «Hans Salazar» aparece 66 veces y «Han Salazar»
una; «Yareth Arciniega» 59 y «Yarteh Arciniega» una. Son erratas de captura.

**El medio no es uno solo.** Un reportero que representa a un grupo enumera sus
cabeceras: «Diario Basta, Tabasco Hoy, Campeche Hoy y Quintana Roo Hoy, de
Grupo Cantón». Contarlo como una sola cadena vuelve invisibles a los cuatro; la
decisión del proyecto (2026-09-03) es que **cada cabecera cuente su
intervención**, así que un turno puede sumar a varios medios a la vez.

**La fusión automática es deliberadamente tímida.** Solo une cuando una
variante es rara y la otra frecuente, que es la firma de una errata. Cuando las
dos son frecuentes —«Sandra Aguilar» 24 y «Sandra Aguilera» 11— **no las toca**
y las reporta: pueden ser dos personas, y unirlas borraría a una. Esa decisión
es humana y vive en `config/canonico_periodistas.csv`.

**Las correcciones humanas mandan sobre todo lo demás.** Hay errores que ningún
algoritmo puede ver: la estenográfica escribe «Yareth Arciniega» siempre, en
las 59 ocurrencias, y el nombre real es «Yaneth». Eso solo lo sabe quien
conoce la fuente.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable

RARO = 2
"""Máximo de apariciones para considerar que una variante es una errata."""

DISTANCIA = 2
"""Ediciones máximas entre dos claves para fusionarlas."""

# Fragmentos que aparecen al enumerar cabeceras pero no son un medio: estados,
# ciudades y coletillas. Sin esta lista, «Quatro Media Telecomunicaciones,
# Veracruz» produciría un medio llamado «Veracruz».
_NO_ES_MEDIO = {
    "veracruz", "sonora", "chiapas", "hidalgo", "tabasco", "puebla", "oaxaca",
    "michoacan", "guerrero", "morelos", "queretaro", "yucatan", "campeche",
    "durango", "sinaloa", "chihuahua", "coahuila", "zacatecas", "colima",
    "tlaxcala", "nayarit", "tamaulipas", "guanajuato", "jalisco", "cdmx",
    "ciudad de mexico", "mexicali", "tijuana", "monterrey", "quintana roo",
    "san luis potosi", "baja california", "estado de mexico", "nuevo leon",
    "aguascalientes", "nacional", "mexico", "y del", "asi como", "entre otros",
    "tambien", "ademas", "etcetera", "etc", "otros medios",
    # Más lugares vistos como continuación: «…, de Máxima FM, en Ciudad Juárez».
    "cancun", "puerto vallarta", "ciudad juarez", "los angeles", "san diego",
    "hermosillo", "culiacan", "acapulco", "merida", "cuernavaca", "toluca",
    "leon", "torreon", "saltillo", "villahermosa", "tuxtla gutierrez", "tepic",
    "la paz", "el paso", "todo el pais", "el pais", "linea", "en linea",
    # Plataformas: dónde se publica, no quién publica.
    "youtube", "facebook", "twitter", "instagram", "tiktok", "whatsapp",
    "telegram", "redes sociales", "internet", "radio", "television", "prensa",
}

# Palabras de discurso que preceden a la cabecera y no forman parte del nombre:
# «…y **también** Altavoz Radio», «**en** La Red», «**mi canal** Lord Molécula».
# Se quitan, no se descarta el fragmento: detrás hay un medio real. Quitar el
# `en` es seguro en las 17 apariciones del corpus —todas son lugar, plataforma
# o `en La Red`— y donde deja un lugar, `_NO_ES_MEDIO` lo descarta después.
_ARRANQUES = re.compile(
    r"^(?:(?:y\s+)?(?:ya\s+)?(?:tambi[eé]n|as[ií]\s+como|adem[aá]s(?:\s+de)?)\s+"
    r"|(?:en|desde|para|dentro\s+de)\s+"
    r"|(?:mi|su|el|los)\s+canal(?:es)?(?:\s+de\s+redes\s+sociales)?\s+"
    r"|(?:el\s+)?portal(?:\s+de\s+noticias)?\s+)+", re.I)

# Un fragmento que es una oración, no un nombre. Tres firmas, todas verificadas
# sobre el corpus: la subordinada de relativo («que se transmite en Chihuahua»,
# «que dirige la maestra…»), el verbo conjugado dentro, y la coletilla
# descriptiva («con 90 estaciones en todo el país»).
#
# `sin`, `es`, `asi`, `somos` y `ya` **NO** están aquí, aunque parezcan del
# mismo tipo: `Sin Embargo`, `Sin Línea`, `Sin Censura TV`, `Es ahora AM`,
# `Así lo dice La Mont`, `Somos Más` y `Ya es Noticia México` son medios reales
# y sumaban 90 intervenciones. En español los nombres de medios empiezan así.
_ES_ORACION = re.compile(
    r"^(?:que|con|cuyo|cuya|donde|quien)\b"
    r"|\b(?:se\s+transmite|transmite|transmitimos|cubre|cubrimos|pertenece|"
    r"pertenecen|dirige|dirijo|conduce|conduzco|escribo|colaboro|trabajo|"
    r"represento|representamos|hacemos|estamos|seguramente|conoce)\b", re.I)
MAX_PALABRAS_MEDIO = 8
"""Más palabras que esto y el fragmento es una descripción, no una cabecera."""

_ACRONIMO = re.compile(r"[A-ZÁÉÍÓÚÑ]{2,}\d*")
"""`AFP`, `CNN`, `SPR`, `MVS`, `TV4`. Cortos y perfectamente válidos."""

# Los dos puntos también separan: «Grupo Healy: El Imparcial, La Crónica…».
_SEPARADORES = re.compile(r"\s*[;,:]\s*|\s+y\s+|\s+e\s+|\s*/\s*|\s*\|\s*")
# Lo que se quita del fragmento es el resto del conector, no el nombre. La
# conjunción sobrevive cuando el separador que actuó fue la coma: «La Crónica,
# de Mexicali, y Frontera» deja el fragmento «y Frontera».
#
# El artículo NO se quita aquí: `El Imparcial` y `La Crónica` se llaman así, y
# recortarlos deja «imparcial» en minúscula en las tarjetas. El artículo se
# ignora al COMPARAR, en `clave()`, que es donde estorba.
_PREFIJOS = re.compile(r"^(?:y\s+|e\s+|de\s+la\s+|de\s+el\s+|del\s+|de\s+)+", re.I)

# Palabras que describen el soporte y que la gente antepone o no a la misma
# cabecera: «revista Contralínea» y «Contralínea», «periódico Diario Cambio» y
# «Diario Cambio». Se ignoran al comparar. `diario`, `grupo` y `canal` NO
# están aquí a propósito: son parte del nombre en `Diario Basta`,
# `Grupo Cantón` y `Canal Once`, y quitarlas fusionaría cabeceras distintas.
_DESCRIPTORES = r"(?:revista|periodico|portal|semanario|agencia|sitio)"
_AL_COMPARAR = re.compile(
    r"^(?:(?:la|el|los|las)\s+)?(?:" + _DESCRIPTORES + r"\s+)?"
    r"(?:(?:la|el|los|las)\s+)?")


def _plano(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def clave(s: str) -> str:
    """Forma normalizada para COMPARAR, no para mostrar.

    Ignora acentos, mayúsculas, artículo inicial y descriptor de soporte, que
    es lo que hace que la misma cabecera se escriba de cinco maneras.
    """
    return _AL_COMPARAR.sub("", _plano(s)).replace(" ", "") or _plano(s).replace(" ", "")


_ATONAS = {"de", "del", "la", "el", "los", "las", "y", "e", "en", "a", "al",
           "para", "por", "con", "un", "una"}


def _mayusculas(s: str) -> int:
    """Cuántas palabras con carga semántica llevan mayúscula inicial."""
    return sum(1 for p in s.split() if p.lower() not in _ATONAS and p[:1].isupper())


def _capitalizar(s: str) -> str:
    """Primera letra en mayúscula, el resto intacto.

    `revista Contralínea` es la única grafía que existe para ese medio, así
    que no hay de dónde escoger una mejor; se arregla al mostrar. Se toca solo
    el primer carácter: `NoticiasDeFrente` y `elCEO` se escriben así.
    """
    return s[:1].upper() + s[1:] if s else s


def _distancia(a: str, b: str, tope: int = DISTANCIA) -> int:
    if abs(len(a) - len(b)) > tope:
        return tope + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _manuales(ruta: Path) -> dict[str, str]:
    """Mapa `variante -> canónico` declarado a mano. Manda sobre lo automático."""
    if not ruta.exists():
        return {}
    # Los comentarios se quitan ANTES de que el lector vea el archivo. Si se
    # dejan, la primera línea `#` se toma como cabecera, ninguna columna se
    # llama `variante`, y la tabla entera queda vacía **sin un solo aviso**:
    # las correcciones humanas dejan de aplicarse y el conteo sigue corriendo.
    lineas = [l for l in ruta.read_text(encoding="utf-8-sig").splitlines()
              if l.strip() and not l.lstrip().startswith("#")]
    filas = list(csv.DictReader(lineas))
    if filas and "variante" not in filas[0]:
        raise ValueError(f"{ruta} no tiene columna `variante`: {list(filas[0])}")
    return {r["variante"].strip(): r["canonico"].strip() for r in filas
            if r.get("variante") and r.get("canonico")}


def canonizar_nombres(
    frec: Counter, manual: dict[str, str] | None = None
) -> tuple[dict[str, str], list[tuple[str, int, str, int]]]:
    """Devuelve `(mapa, dudosos)`.

    `mapa` lleva cada variante a su forma canónica. `dudosos` son los pares
    parecidos donde **las dos** formas son frecuentes: no se fusionan, se
    reportan para que una persona decida. Unirlos a ciegas puede borrar a
    alguien que sí existe.
    """
    manual = manual or {}
    mapa = {n: manual.get(n, n) for n in frec}
    nombres = sorted(frec, key=lambda x: (-frec[x], x))
    claves = {n: clave(n) for n in nombres}
    dudosos: list[tuple[str, int, str, int]] = []

    for i, a in enumerate(nombres):
        if a in manual:
            continue
        for b in nombres[i + 1:]:
            if b in manual or mapa[b] != b:
                continue
            ka, kb = claves[a], claves[b]
            if ka == kb:
                mapa[b] = mapa[a]
                continue
            if min(len(ka), len(kb)) <= 8 or _distancia(ka, kb) > DISTANCIA:
                continue
            if frec[b] <= RARO < frec[a]:
                mapa[b] = mapa[a]          # errata sobre una forma establecida
            else:
                dudosos.append((a, frec[a], b, frec[b]))
    return mapa, dudosos


def partir_medios(cadena: str | None) -> list[str]:
    """Separa una declaración de medio en las cabeceras que nombra.

    «Diario Basta, Tabasco Hoy, Campeche Hoy y Quintana Roo Hoy, de Grupo
    Cantón» son cinco entidades y cada una cuenta su intervención. Se descartan
    los fragmentos que son un lugar o una coletilla, no un medio.
    """
    if not cadena:
        return []
    partes, vistos = [], set()
    for trozo in _SEPARADORES.split(cadena):
        t = _PREFIJOS.sub("", trozo.strip(" .-—·")).strip()
        t = _ARRANQUES.sub("", t).strip(" .-—·…")
        # Corto **no** quiere decir inválido: `AFP`, `CNN`, `SPR`, `MVS` y
        # `TV4` son cabeceras de tres letras. El corte por longitud a secas
        # las borraba todas. Se admite el acrónimo y se rechaza el resto.
        if len(t) < 4 and not _ACRONIMO.fullmatch(t):
            continue
        if _plano(t) in _NO_ES_MEDIO:
            continue
        if _ES_ORACION.search(_plano(t)) or len(t.split()) > MAX_PALABRAS_MEDIO:
            continue
        k = clave(t)
        if k and k not in vistos:
            vistos.add(k)
            partes.append(t)
    return partes or ([cadena.strip()] if cadena.strip() else [])


def canonizar_medios(
    cadenas: Iterable[str], manual: dict[str, str] | None = None
) -> dict[str, str]:
    """Mapa `cabecera -> forma canónica`, por clave normalizada.

    El representante de cada grupo es la grafía más frecuente, no la más larga:
    lo que la gente dice más veces es lo que hay que mostrar.
    """
    manual = manual or {}
    frec: Counter[str] = Counter()
    for c in cadenas:
        frec.update(partir_medios(c))
    por_clave: dict[str, Counter] = {}
    for nombre, n in frec.items():
        por_clave.setdefault(clave(nombre), Counter())[nombre] = n
    mapa = {}
    for variantes in por_clave.values():
        # Una cabecera que en 460 conferencias NUNCA se escribió con una
        # mayúscula no es un nombre, es una descripción: `un medio público`,
        # `estaciones de radio`, `corresponsal en el sureste`, `bueno`.
        #
        # El candado tiene que mirar el corpus entero y no la cadena suelta,
        # porque los medios reales sí aparecen en minúscula a veces —
        # `corazón de la capital` 18 veces, `codigolibre`, `aguaquemada`— y
        # **siempre** tienen un gemelo con mayúsculas: `Corazón de la Capital`,
        # `Código Libre`, `AguaQuemada`. Juzgar cada grafía por separado
        # borraba esos medios; juzgar el grupo los conserva.
        if not any(c.isupper() for v in variantes for c in v):
            continue
        # La grafía que se muestra es la mejor capitalizada, y la frecuencia
        # solo desempata. `El imparcial` aparece 22 veces y `El Imparcial` 21:
        # por frecuencia ganaría la errata. Se cuentan las palabras con
        # mayúscula, ignorando artículos y preposiciones, que nunca la llevan.
        rep = max(variantes.most_common(), key=lambda par: (_mayusculas(par[0]), par[1]))[0]
        rep = _capitalizar(manual.get(rep, rep))
        for v in variantes:
            mapa[v] = manual.get(v, rep)
    return mapa


def cargar(config: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Las dos tablas de correcciones humanas."""
    return (_manuales(config / "canonico_periodistas.csv"),
            _manuales(config / "canonico_medios.csv"))


def aplicar(hilos: list[dict], config: Path | None = None) -> list[dict]:
    """Canoniza `periodista` y `medio` sobre los hilos, en el sitio.

    Añade además `medios`, la lista de cabeceras que la persona nombró en ese
    hilo. **Un hilo puede sumar a varias**: quien representa a un grupo
    enumera sus periódicos y cada uno cuenta su intervención, que es la
    decisión del proyecto del 2026-09-03. Por eso la suma de intervenciones
    por medio es mayor que el número de hilos, y no es un error.

    `medio` conserva la cabecera principal —la primera que se nombra— para
    todo lo que necesite un solo valor por hilo.
    """
    config = config or Path("config")
    mp, mm = cargar(config)
    frec = Counter(h["periodista"] for h in hilos if h.get("periodista"))
    nombres, _ = canonizar_nombres(frec, mp)
    medios = canonizar_medios([h["medio"] for h in hilos if h.get("medio")], mm)
    for h in hilos:
        if h.get("periodista"):
            h["periodista"] = nombres.get(h["periodista"], h["periodista"])
        # Lo que no está en el mapa fue descartado por `canonizar_medios` como
        # descripción y no como cabecera. Se omite, no se deja pasar crudo.
        cabeceras = [medios[c] for c in partir_medios(h.get("medio")) if c in medios]
        h["medios"] = cabeceras
        h["medio"] = cabeceras[0] if cabeceras else h.get("medio")
    return hilos
