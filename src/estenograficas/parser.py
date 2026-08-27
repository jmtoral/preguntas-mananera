"""Parser de versiones estenográficas: texto plano a turnos y a hilos.

Implementa las trampas del formato documentadas en CLAUDE.md. Cada una tiene su
función y su prueba; ninguna es un caso especial metido para que algo deje de
fallar.

El orden importa y no es negociable:

1. Quitar los bloques de video, porque adentro hay hablantes etiquetados que no
   son parte de la conferencia.
2. Separar el encabezado del artículo, que precede al primer turno.
3. Partir en turnos por etiqueta de hablante.
4. Sacar los apartes fuera de micrófono a un campo aparte.
5. Armar hilos y propagar la identidad del periodista hacia adelante.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Tipo = Literal["prensa", "funcionario", "anonimo"]
Rol = Literal["pregunta", "respuesta"]
Atribucion = Literal["declarada", "propagada", "incierta"]


# ---------------------------------------------------------------------------
# 1. Videos
# ---------------------------------------------------------------------------

# Un bloque de video abre con (INICIA VIDEO) y cierra con (FINALIZA VIDEO).
# Entre los dos hay etiquetas como VOZ MUJER: o DERECHOHABIENTE, NOMBRE: que
# son testimonios grabados, no diálogo de la conferencia.
# Un bloque abre y cierra con un paréntesis, pero las formas son muchas más que
# `(INICIA VIDEO)`. Contadas sobre las 460 conferencias: 431 `(INICIA VIDEO)`
# pero también ~160 `(PROYECCIÓN DE VIDEO ...)`, con la sección entre comillas
# pegada dentro del mismo paréntesis, más `(INICIA AUDIO)`. Y los cierres son
# `FINALIZA`, `FINALIZAN`, `CONCLUYE` y `TERMINA`. Con solo la forma canónica
# quedaban 475 cierres contra 431 aperturas: 44 bloques sin abrir, cuyo
# contenido sobrevivía a la limpieza.
#
# `VIDEO\b` con frontera de palabra a propósito: `(ENLACE VIDEOLLAMADA)`
# aparece 818 veces y NO es un video proyectado, es alguien participando a
# distancia, que sí forma parte del diálogo de la conferencia.
# `PROYECCIÓN DE VIDEO` NO va aquí, aunque parezca una apertura. Se probó:
# suele ser una marca suelta que anuncia que se proyectó algo, sin cierre que
# le corresponda, así que tratarla como apertura hace que el bloque se coma
# todo hasta el siguiente `(FINALIZA VIDEO)`, que puede estar mucho más
# adelante. Medido sobre las 460: **borraba 787 turnos, 239 de ellos de
# prensa**. Las apariciones de `VOZ MUJER` que sobreviven cerca de esas marcas
# son un problema menor que perder preguntas reales.
_ABRE_V = (
    r"\(\s*(?:INICIA|INICIAN|COMIENZA|EMPIEZA)"
    r"[^)]{0,60}?(?:V[IÍ]DEOS?|AUDIOS?)\b[^)]{0,60}\)"
)
_CIERRA_V = (
    r"\(\s*(?:FINALIZA|FINALIZAN|CONCLUYE|CONCLUYEN|TERMINA|TERMINAN)"
    r"[^)]{0,60}?(?:V[IÍ]DEOS?|AUDIOS?)\b[^)]{0,60}\)"
)
_VIDEO = re.compile(
    _ABRE_V + r".*?" + _CIERRA_V, re.IGNORECASE | re.DOTALL
)
_VIDEO_ABRE = re.compile(_ABRE_V, re.IGNORECASE)


# Espacios Unicode que el CMS mete y que rompen la detección de etiquetas.
# Visto en 2025-07-02: `PREGUNTA:` seguida de espacio duro en vez de espacio.
# La etiqueta no casa, el turno se funde con el anterior, y no hay error: el
# conteo de turnos sale más bajo y nadie se entera. Uno en cinco conferencias
# de muestra; en 460 son decenas de turnos de prensa atribuidos a la presidenta.
_ESPACIOS_RAROS = dict.fromkeys(
    map(ord, "              　"),
    " ",
)


def normalizar_espacios(texto: str) -> str:
    """Convierte espacios Unicode exóticos en espacio normal."""
    return texto.translate(_ESPACIOS_RAROS)


def quitar_videos(texto: str) -> tuple[str, int, int]:
    """Elimina los bloques de video.

    Devuelve el texto limpio, cuántos bloques se quitaron y cuántas aperturas
    quedaron sin cerrar. Lo segundo importa: un video sin cierre significa que
    todo lo que sigue se perdería, y eso hay que reportarlo, no tragárselo.
    """
    limpio, n = _VIDEO.subn("\n\n", texto)
    huerfanos = len(_VIDEO_ABRE.findall(limpio))
    return limpio, n, huerfanos


# ---------------------------------------------------------------------------
# 2. Etiquetas de hablante
# ---------------------------------------------------------------------------

# Todo mayúsculas, al inicio de línea, terminando en dos puntos. Admite acentos,
# dígitos, comas, puntos, paréntesis y guiones porque los cargos los traen:
# "DIRECTOR GENERAL INSTITUTO MEXICANO DEL SEGURO SOCIAL (IMSS), ZOÉ ROBLEDO".
# Tres formas de romper esta etiqueta, las tres encontradas en el corpus real
# y las tres silenciosas: el turno se funde con el anterior y solo se nota
# porque el conteo sale más bajo.
#
# 1. `PREGUNTA:\xa0Bien.` — espacio duro. Se resuelve normalizando antes.
# 2. `...PARDO:Ah, ok.` y `...PARDO :—` — sin espacio después de los dos
#    puntos, o con espacio antes. **253 turnos de prensa traían la respuesta
#    del gobierno metida adentro** por esto.
# 3. `SECRETARIO DE SALUD, DAVID KERSHENOBICH (enlace videollamada):` — el
#    paréntesis viene en minúsculas y no cabía en el juego de caracteres.
#
# El `(?!//)` evita tragarse un `HTTPS://`, que también son mayúsculas con
# dos puntos al inicio de línea.
_ETIQUETA = re.compile(
    r"^(?P<etiqueta>[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ0-9 ,\.\(\)/º°'’\-]{2,150}?"
    r"(?:\s*\([^)\n]{0,45}\))?)"
    r"[ \t]*:(?!//)[ \t]*",
    re.MULTILINE,
)

# Etiquetas de prensa. `INTERLOCUTOR` e `INTERLOCUTORA` son la forma que se usó
# en octubre de 2024, antes de que se estandarizara `PREGUNTA`: 421 turnos en 18
# conferencias, todas entre el 2024-10-03 y el 2024-10-29. Sin ellas, esos 421
# turnos de periodistas se contaban como intervenciones de funcionarios, que es
# el error más caro posible en un proyecto que mide qué pregunta la prensa.
_PRENSA = {
    "PREGUNTA", "PREGUNTAS",
    "INTERLOCUTOR", "INTERLOCUTORA", "INTERLOCUTORES", "INTERLOCUTORAS",
}
# `ASISTENTES` es el pleno coreando; no es un hablante.
_RUIDO_DE_SALA = {
    "INTERVENCIÓN", "INTERVENCION", "INTERVENCIONES", "ASISTENTES",
}

# Palabras que denotan un cargo. Sirven para orientar la etiqueta: en 2026 el
# formato es `CARGO, NOMBRE` pero en octubre de 2024 es `NOMBRE, CARGO`
# (`CITLALLI HERNÁNDEZ MORA, SECRETARIA DE LAS MUJERES`). Sobre las 90 primeras
# conferencias son 116 al derecho contra 60 al revés: un `rsplit` a ciegas
# intercambia cargo y nombre en un tercio de los funcionarios.
_PALABRAS_DE_CARGO = (
    "SECRETARI", "SUBSECRETARI", "DIRECTOR", "DIRECTORA", "TITULAR",
    "PRESIDENT", "COORDINADOR", "GOBERNADOR", "COMISIONAD", "JEFE", "JEFA",
    "CONSEJER", "VOCERO", "VOCERA", "ALMIRANTE", "GENERAL", "PROCURADOR",
    "FISCAL", "EMBAJADOR", "MAGISTRAD", "MINISTR", "RECTOR", "GERENTE",
    "ENCARGAD", "SUBDIRECTOR", "ADMINISTRADOR",
)


def _tiene_cargo(s: str) -> bool:
    return any(p in s for p in _PALABRAS_DE_CARGO)
# Sobrevivientes de un bloque de video mal cerrado. No deberían aparecer; si
# aparecen es señal de que la limpieza de videos falló y hay que enterarse.
_VOCES_DE_VIDEO = re.compile(
    r"^(VOZ|VOCES|DERECHOHABIENTE|MADRE|PADRE|PACIENTE|TRABAJADOR|BENEFICIARI)",
)


def _sin_acentos_may(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.upper()) if not unicodedata.combining(c)
    )


def clasificar_etiqueta(etiqueta: str) -> tuple[Tipo, str | None, str | None]:
    """Devuelve (tipo, cargo, hablante) a partir de la etiqueta cruda.

    El cargo y el nombre vienen separados por coma y se parten con rsplit, que
    es lo correcto porque el cargo puede traer comas propias pero el nombre va
    siempre al final.
    """
    et = etiqueta.strip()
    plano = _sin_acentos_may(et)

    if plano in {_sin_acentos_may(p) for p in _PRENSA}:
        return "prensa", None, None
    if plano in {_sin_acentos_may(r) for r in _RUIDO_DE_SALA}:
        return "anonimo", None, None
    if _VOCES_DE_VIDEO.match(plano):
        return "anonimo", None, None

    if "," in et:
        izquierda, derecha = (p.strip() for p in et.rsplit(",", 1))
        izq_plano, der_plano = _sin_acentos_may(izquierda), _sin_acentos_may(derecha)
        # Se orienta por dónde está el cargo, no por la posición. Si solo el
        # lado derecho nombra un cargo, la etiqueta viene NOMBRE, CARGO.
        if _tiene_cargo(der_plano) and not _tiene_cargo(izq_plano):
            return "funcionario", derecha, izquierda
        return "funcionario", izquierda, derecha

    # Mayúsculas, con dos puntos, sin coma y sin ser prensa ni ruido conocido.
    # Puede ser un funcionario sin cargo o una etiqueta que no conocemos; se
    # deja como funcionario sin cargo y el diagnóstico de la fase 6 lo delata.
    return "funcionario", None, et


# ---------------------------------------------------------------------------
# 3. Apartes fuera de micrófono
# ---------------------------------------------------------------------------

# Un aparte ocupa su propio párrafo, entero entre rayas: "—A ver, acá—."
# Las rayas que abren y cierran DENTRO de una oración son otra cosa: un inciso
# hablado ("—si me dan la siguiente—"), que sí es parte del discurso y no se
# toca. La diferencia es el párrafo completo, y por eso se evalúa por párrafo.
#
# Solo raya (—) y semirraya (–). El guion normal queda fuera a propósito: se usa
# en rangos y palabras compuestas y meterlo aquí genera falsos apartes.
_APARTE = re.compile(r"^[—–]\s*(?P<dentro>.+?)\s*[—–]\s*[\.\,]?\s*$", re.DOTALL)

# Cierre de documento de los boletines de Presidencia, al final del archivo.
# Parece un aparte —párrafo entero entre rayas— y no lo es.
_FIN_DE_DOCUMENTO = re.compile(r"\n\s*[—–-]\s*0{2,}\s*[—–-]\s*$")


def quitar_fin_de_documento(texto: str) -> tuple[str, bool]:
    """Quita el marcador `—000—` del final. Devuelve si estaba."""
    limpio, n = _FIN_DE_DOCUMENTO.subn("\n", texto)
    return limpio, bool(n)


def extraer_apartes(texto: str) -> tuple[str, list[str]]:
    """Separa los apartes del cuerpo del turno.

    Contaminan cualquier conteo de palabras por hablante, así que viven en su
    propio campo en vez de borrarse.
    """
    parrafos = texto.split("\n\n")
    cuerpo: list[str] = []
    apartes: list[str] = []
    for p in parrafos:
        limpio = p.strip()
        if not limpio:
            continue
        m = _APARTE.match(limpio)
        if m and "\n\n" not in limpio:
            apartes.append(m.group("dentro").strip())
        else:
            cuerpo.append(limpio)
    return "\n\n".join(cuerpo).strip(), apartes


# ---------------------------------------------------------------------------
# 4. Ruido: lo que no es una pregunta
# ---------------------------------------------------------------------------

# Cortesías puras y marcas de inaudible. Se exige que TODO el texto encaje:
# "¿No se le censura?" es corto pero es una pregunta, y filtrar por longitud
# se la llevaría.
_CORTESIAS = [
    r"\(\s*inaudible\s*\)",
    r"(muchas\s+|muchísimas\s+)?gracias(\s*,?\s*(presidenta|presidente|señora\s+presidenta))?",
    r"buen(os|as)\s+(días|tardes|noches)(\s*,?\s*(presidenta|presidente))?",
    r"bien",
    r"sí|si|no",
    r"de\s+acuerdo",
    r"así\s+es",
    r"con\s+permiso",
    r"adelante",
]
_RUIDO = re.compile(
    r"^(?:" + r"|".join(f"(?:{c})" for c in _CORTESIAS) + r")[\s\.\,;!¡]*$",
    re.IGNORECASE,
)


def es_ruido(texto: str) -> bool:
    """True si el turno es cortesía o marca de inaudible, no contenido."""
    t = texto.strip()
    if not t:
        return True
    # Se parte en oraciones para atrapar "Buenos días, Presidenta. Gracias."
    partes = [p for p in re.split(r"(?<=[\.\!\?])\s+", t) if p.strip()]
    return all(_RUIDO.match(p.strip()) for p in partes)


# ---------------------------------------------------------------------------
# 5. Turnos
# ---------------------------------------------------------------------------


@dataclass
class Turno:
    conferencia_id: str
    orden: int
    etiqueta: str
    cargo: str | None
    hablante: str | None
    tipo: Tipo
    texto: str
    apartes: list[str] = field(default_factory=list)

    @property
    def es_ruido(self) -> bool:
        return es_ruido(self.texto)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def separar_encabezado(texto: str) -> tuple[str, str]:
    """Parte el documento en (encabezado, cuerpo).

    El encabezado del artículo —título, subtítulo, caption duplicado— precede
    al primer turno y no debe quedar pegado a la primera intervención.
    """
    m = _ETIQUETA.search(texto)
    if not m:
        return texto, ""
    return texto[: m.start()].strip(), texto[m.start() :]


def partir_turnos(texto: str, conferencia_id: str) -> list[Turno]:
    """Parte el cuerpo en turnos de habla, uno por etiqueta de hablante."""
    marcas = list(_ETIQUETA.finditer(texto))
    turnos: list[Turno] = []
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        crudo = texto[m.end() : fin].strip()
        etiqueta = m.group("etiqueta").strip()
        tipo, cargo, hablante = clasificar_etiqueta(etiqueta)
        cuerpo, apartes = extraer_apartes(crudo)
        turnos.append(
            Turno(
                conferencia_id=conferencia_id,
                orden=len(turnos),
                etiqueta=etiqueta,
                cargo=cargo,
                hablante=hablante,
                tipo=tipo,
                texto=cuerpo,
                apartes=apartes,
            )
        )
    return turnos


# ---------------------------------------------------------------------------
# 6. Identidad declarada
# ---------------------------------------------------------------------------

# La autopresentación es SU PROPIA ORACIÓN: empieza tras un punto (o al inicio
# del turno) y termina en punto. Esa es la diferencia entre
#   "Gracias, Presidenta. Dalila Escobar, de Proceso."          <- periodista
# y
#   "...acusan a Andrés Manuel López Beltrán, de encabezar una red..."
# donde el "de" introduce un verbo, no un medio. Sin el ancla de oración el
# regex encuentra seis periodistas en una conferencia que tiene cuatro.
_NOMBRE = r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+(?:\s+(?:de|del|la|los)\s+)?(?:\s*[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+){1,3}"

# Muletillas con las que se abre la presentación. Sin esto, "Soy" queda dentro
# del nombre ("Soy Yesenia Peralta") y "Su servidor, Carlos Pozos, de LM
# Noticias" no se detecta en absoluto, porque el nombre no arranca la oración.
# Las cinco formas salieron de las conferencias de 2024, 2025 y 2026.
# Se admiten UNA O DOS muletillas seguidas: `Soy su servidor, Carlos Pozos…`
# es una sola presentación, no dos. Con una sola alternativa el regex no casa
# y el hilo entero de esa persona se le acredita al periodista anterior.
_MULETILLA = (
    r"(?:(?:[Ss]oy|[Ss]u\s+servidora?|[Mm]i\s+nombre\s+es|[Ll]es?\s+habla|"
    r"[Aa]quí)\s*,?\s+){1,2}"
)

# El oficio se mete entre el nombre y el medio: `Carlos Pozos, reportero de LM
# Noticias`, `Aurora Castillejos, reportera de Canal 14`. Exigir `, de` pegado
# al nombre pierde esas presentaciones enteras.
_OFICIO = (
    r"(?:reporter[oa]|corresponsal|conductor[a]?|periodista|colaborador[a]?|"
    r"director[a]?|editor[a]?|enviad[oa]\s+especial|columnista|"
    r"analista|comentarista)"
)

# Un nombre de una sola palabra solo se acepta si viene precedido de muletilla
# explícita (`Soy Jonás`). Sin ese ancla, aceptar nombres de una palabra
# dispara falsos positivos por todo el texto. Y sin esta rama, el regex lee
# `Soy Jonás` como un nombre de dos palabras y el periodista queda registrado
# como "Soy Jonás".
_PALABRA_NOMBRE = r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+"
_MEDIO = r"(?P<medio>[^\.\!\?\n]{2,70}?)\s*[\.\!\?]"
_CONECTOR = r"\s*,\s*(?:" + _OFICIO + r"\s+)?(?:de|del)\s+(?:la\s+|el\s+)?"

_IDENTIDAD = re.compile(
    r"(?:^|(?<=[\.\!\?])\s|^\s*)"
    r"(?:"
    #  a) con muletilla: el nombre puede ser de una sola palabra
    + _MULETILLA + r"(?P<nombre>" + _PALABRA_NOMBRE + r"(?:\s+(?:de|del|la|los)\s+)?"
    r"(?:\s*" + _PALABRA_NOMBRE + r"){0,3})"
    r"|"
    #  b) sin muletilla: se exigen dos o más palabras
    r"(?P<nombre2>" + _NOMBRE + r")"
    r")"
    + _CONECTOR + _MEDIO,
    re.MULTILINE,
)

VENTANA_IDENTIDAD = 300
"""Solo se miran los primeros 300 caracteres: regla dura 4 de CLAUDE.md."""


MARCA_REDACTADA = "[identificación removida]"


def redactar_identificacion(texto: str) -> tuple[str, bool]:
    """Quita la autopresentación del periodista del texto de la pregunta.

    El 10% de las preguntas —las 2,149 que abren hilo— dicen el medio dentro de
    su propio texto: `"Buenos días. Carlos Navarro, de Heraldo Media Group.
    Presidenta, ¿qué tiene de distinto…"`. Guardar el medio en una columna
    aparte no sirve de nada si sigue estando en el texto que el humano lee: la
    codificación dejaría de ser a ciegas y el análisis "descubriría" lo que se
    metió por esa ventana.

    Se reemplaza solo la oración de la presentación, no el turno completo, para
    conservar la pregunta y no perder la categoría de preguntas de apertura.
    Devuelve `(texto, se_redactó)`.
    """
    m = _IDENTIDAD.search(texto[:VENTANA_IDENTIDAD])
    if not m:
        return texto, False
    return texto[: m.start()] + MARCA_REDACTADA + texto[m.end() :], True


def identidad_declarada(texto: str) -> tuple[str, str] | None:
    """Extrae (nombre, medio) de la autopresentación, o None.

    Mira únicamente los primeros `VENTANA_IDENTIDAD` caracteres. Un periodista
    que se presenta lo hace al abrir; un nombre propio que aparece a la mitad
    del turno es alguien de quien se habla, no quien habla.
    """
    m = _IDENTIDAD.search(texto[:VENTANA_IDENTIDAD])
    if not m:
        return None
    medio = re.sub(r"\s+", " ", m.group("medio")).strip(" ,;")
    nombre = m.group("nombre") or m.group("nombre2")
    return " ".join(nombre.split()), medio


# ---------------------------------------------------------------------------
# 7. Hilos
# ---------------------------------------------------------------------------

LARGO_INTERJECCION = 200
"""Un turno más largo que esto no es un grito desde el salón."""


@dataclass
class TurnoDeHilo:
    rol: Rol
    quien: str | None
    texto: str
    atribucion: Atribucion
    ruido: bool
    orden: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Hilo:
    conferencia_id: str
    hilo: int
    periodista: str | None
    medio: str | None
    periodista_canonico: str | None
    metodo_identificacion: str
    turnos: list[TurnoDeHilo]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["turnos"] = [t.to_dict() for t in self.turnos]
        return d


def _rachas_de_prensa(turnos: list[Turno]) -> set[int]:
    """Índices de turnos de prensa que caen en una racha sin respuesta.

    Turnos de prensa seguidos, cortos y sin funcionario de por medio suelen ser
    gente distinta interrumpiendo desde el salón, no el mismo periodista. No se
    les puede atribuir autoría.

    El ruido de sala (INTERVENCIÓN) no rompe la racha: también viene del pleno.
    """
    inciertos: set[int] = set()
    racha: list[int] = []

    def cerrar() -> None:
        if len(racha) >= 2 and all(
            len(turnos[i].texto) <= LARGO_INTERJECCION for i in racha
        ):
            inciertos.update(racha)
        racha.clear()

    for i, t in enumerate(turnos):
        if t.tipo == "prensa":
            racha.append(i)
        elif t.tipo == "anonimo":
            continue  # ruido de sala: no suma a la racha pero tampoco la corta
        else:
            cerrar()
    cerrar()
    return inciertos


def armar_hilos(turnos: list[Turno]) -> list[Hilo]:
    """Agrupa los turnos en hilos, uno por tanda de periodista.

    Un hilo abre cuando un turno de prensa trae autopresentación y se extiende
    hasta la siguiente. Lo que ocurre antes del primer hilo es la exposición
    de la conferencia y no pertenece a ninguno.

    La identidad se propaga hacia adelante dentro del hilo, salvo en los turnos
    marcados inciertos, que se quedan sin periodista. Nulo antes que inventado.
    """
    inciertos = _rachas_de_prensa(turnos)

    aperturas: list[tuple[int, str, str]] = []
    for i, t in enumerate(turnos):
        if t.tipo != "prensa" or i in inciertos:
            continue
        ident = identidad_declarada(t.texto)
        if ident:
            aperturas.append((i, ident[0], ident[1]))

    hilos: list[Hilo] = []
    for n, (inicio, nombre, medio) in enumerate(aperturas):
        fin = aperturas[n + 1][0] if n + 1 < len(aperturas) else len(turnos)
        del_hilo: list[TurnoDeHilo] = []
        for i in range(inicio, fin):
            t = turnos[i]
            de_prensa = t.tipo in ("prensa", "anonimo")
            if i == inicio:
                atribucion: Atribucion = "declarada"
            elif not de_prensa:
                atribucion = "declarada"  # el funcionario responde con su nombre
            elif i in inciertos or t.tipo == "anonimo":
                atribucion = "incierta"
            else:
                atribucion = "propagada"

            if de_prensa:
                quien = None if atribucion == "incierta" else nombre
            else:
                quien = t.hablante

            del_hilo.append(
                TurnoDeHilo(
                    rol="pregunta" if de_prensa else "respuesta",
                    quien=quien,
                    texto=t.texto,
                    atribucion=atribucion,
                    ruido=t.es_ruido,
                    orden=t.orden,
                )
            )
        hilos.append(
            Hilo(
                conferencia_id=turnos[inicio].conferencia_id,
                hilo=n,
                periodista=nombre,
                medio=medio,
                periodista_canonico=None,
                metodo_identificacion="regex",
                turnos=del_hilo,
            )
        )
    return hilos


# ---------------------------------------------------------------------------
# 8. Entrada de alto nivel
# ---------------------------------------------------------------------------


@dataclass
class Conferencia:
    conferencia_id: str
    encabezado: str
    turnos: list[Turno]
    hilos: list[Hilo]
    bloques_video: int
    videos_sin_cerrar: int
    tenia_fin_de_documento: bool

    @property
    def etiquetas(self) -> dict[str, int]:
        from collections import Counter

        return dict(Counter(t.etiqueta for t in self.turnos).most_common())

    @property
    def turnos_fuera_de_hilo(self) -> int:
        en_hilos = {th.orden for h in self.hilos for th in h.turnos}
        return len(self.turnos) - len(en_hilos)


def parsear(texto: str, conferencia_id: str) -> Conferencia:
    """Parsea una conferencia completa. Sin red, sin modelo, sin estado."""
    limpio, n_videos, huerfanos = quitar_videos(normalizar_espacios(texto))
    limpio, tenia_fin = quitar_fin_de_documento(limpio)
    encabezado, cuerpo = separar_encabezado(limpio)
    turnos = partir_turnos(cuerpo, conferencia_id)
    hilos = armar_hilos(turnos)
    return Conferencia(
        conferencia_id=conferencia_id,
        encabezado=encabezado,
        turnos=turnos,
        hilos=hilos,
        bloques_video=n_videos,
        videos_sin_cerrar=huerfanos,
        tenia_fin_de_documento=tenia_fin,
    )


def texto_desde_html(html: str) -> str:
    """Extrae el texto de la versión estenográfica de la página de gob.mx.

    La estructura es estable: `h1` con el título, `h2` con el subtítulo, una
    `section` con "Presidencia de la República | fecha", el caption de la
    imagen principal, y `div.article-body` con un `<p>` por párrafo, donde la
    etiqueta de hablante va en `<strong>`.

    El encabezado se conserva a propósito en vez de tirarlo aquí: separarlo es
    trabajo de `separar_encabezado`, y así el parser ve la misma entrada venga
    de HTML o del .txt de un fixture viejo.
    """
    from bs4 import BeautifulSoup

    sopa = BeautifulSoup(html, "lxml")

    partes: list[str] = []
    for sel in ("h1", "h2"):
        el = sopa.find(sel)
        if el:
            partes.append(el.get_text(" ", strip=True))

    cuerpo = sopa.find(class_="article-body")
    if cuerpo is None:
        raise ValueError("no se encontró div.article-body; el formato cambió")

    # La línea de "Presidencia de la República | fecha" vive en una section
    # anterior al cuerpo. Se busca acotado para no barrer el pie de página.
    for s in sopa.find_all("section"):
        t = s.get_text(" ", strip=True)
        if t.startswith("Presidencia de la Rep") and len(t) < 120:
            partes.append(t)
            break

    img = sopa.find(class_="imagen-principal")
    if img:
        partes.append(img.get_text(" ", strip=True))

    # Un <br> sí separa palabras; se vuelve espacio antes de unir.
    for br in cuerpo.find_all("br"):
        br.replace_with(" ")

    # Búsqueda recursiva, no solo hijos directos: en 2024 los <p> cuelgan
    # directo de .article-body, pero desde 2025 el CMS los envuelve en uno o
    # más <div>. Mirar solo el primer nivel devuelve la conferencia entera
    # como un párrafo, y de ahí un solo turno y cero hilos, sin error visible.
    #
    # `get_text("")` sin separador, no `get_text(" ")`. Dentro de un párrafo
    # todo es texto en línea, y meter un espacio entre fragmentos parte las
    # palabras que envuelven cursivas: `el periódico <em>La Jornada</em>,`
    # salía como `el periódico La Jornada , donde`. Eran 616 espacios espurios
    # en 5,844 turnos, justo pegados al nombre del medio, que es lo que la
    # fase 7 tiene que agrupar.
    for p in cuerpo.find_all("p"):
        t = " ".join(p.get_text("").split())
        if t:
            partes.append(t)

    return "\n\n".join(partes)


def parsear_archivo(ruta: Path) -> Conferencia:
    """Parsea un fixture. El id sale del nombre: 2026-08-18.txt o .html."""
    crudo = ruta.read_text(encoding="utf-8", errors="replace")
    texto = texto_desde_html(crudo) if ruta.suffix.lower() in (".html", ".htm") else crudo
    return parsear(texto, ruta.stem)


def escribir_jsonl(registros: Iterable[Any], destino: Path) -> int:
    """Escribe dicts o dataclases con to_dict() a JSONL. Devuelve cuántos."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(destino, "w", encoding="utf-8") as f:
        for r in registros:
            d = r.to_dict() if hasattr(r, "to_dict") else r
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            n += 1
    return n
