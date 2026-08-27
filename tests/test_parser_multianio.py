"""Fase 3: el parser contra conferencias de 2024, 2025 y 2026.

Los fixtures HTML vienen de la Wayback Machine porque gob.mx responde con un
reto anti-bot a cualquier cliente que no ejecute JavaScript. Ver HANDOFF.md.

Las aserciones son de invariantes, no de conteos exactos: los conteos de estas
cuatro conferencias no se cuadraron a mano como se hizo con 2026-08-18, y una
prueba que afirme un número que salió del propio parser no prueba nada. Lo que
sí se afirma es lo que tiene que ser cierto en cualquier conferencia.
"""

from __future__ import annotations

import pytest

from estenograficas import config
from estenograficas.parser import (
    identidad_declarada,
    normalizar_espacios,
    parsear,
    parsear_archivo,
    texto_desde_html,
)

# 2026-08-18 es .txt y tiene su propia batería en test_parser.py.
MULTIANIO = ["2024-11-11", "2025-07-02", "2026-02-03", "2026-08-04"]


@pytest.fixture(scope="module")
def confs():
    return {
        f: parsear_archivo(config.paths().fixtures / f"{f}.html") for f in MULTIANIO
    }


@pytest.mark.parametrize("fecha", MULTIANIO)
def test_cada_anio_produce_turnos_e_hilos(confs, fecha) -> None:
    c = confs[fecha]
    assert len(c.turnos) > 50, "una conferencia de 3 horas no tiene 50 turnos"
    assert len(c.hilos) >= 4, "todas las conferencias tienen varias tandas de prensa"
    assert sum(1 for t in c.turnos if t.tipo == "prensa") > 20


@pytest.mark.parametrize("fecha", MULTIANIO)
def test_ningun_video_contamina_ningun_anio(confs, fecha) -> None:
    c = confs[fecha]
    assert c.videos_sin_cerrar == 0
    malas = [
        t.etiqueta
        for t in c.turnos
        if t.etiqueta.upper().startswith(
            ("VOZ", "VOCES", "DERECHOHABIENTE", "MADRE", "PADRE", "TRABAJADOR")
        )
    ]
    assert malas == []


@pytest.mark.parametrize("fecha", MULTIANIO)
def test_el_encabezado_nunca_se_pega_al_primer_turno(confs, fecha) -> None:
    c = confs[fecha]
    assert c.turnos[0].etiqueta.startswith("PRESIDENTA DE MÉXICO")
    assert "Versión estenográfica" not in c.turnos[0].texto
    assert "Presidencia de la Rep" not in c.turnos[0].texto


@pytest.mark.parametrize("fecha", MULTIANIO)
def test_los_nombres_no_traen_muletillas(confs, fecha) -> None:
    """'Soy Yesenia Peralta' no es un nombre; 'Soy' es un verbo."""
    for h in confs[fecha].hilos:
        primera = h.periodista.split()[0]
        assert primera not in {"Soy", "Su", "Mi", "Le", "Les", "Aquí"}, h.periodista
        assert len(h.periodista.split()) >= 2 or h.periodista.isalpha()


@pytest.mark.parametrize("fecha", MULTIANIO)
def test_ningun_hilo_sin_medio(confs, fecha) -> None:
    for h in confs[fecha].hilos:
        assert h.medio, f"{h.periodista} quedó sin medio"
        assert h.periodista_canonico is None  # la canonicalización es fase 7


@pytest.mark.parametrize("fecha", MULTIANIO)
def test_ningun_turno_incierto_trae_periodista(confs, fecha) -> None:
    for h in confs[fecha].hilos:
        for t in h.turnos:
            if t.atribucion == "incierta":
                assert t.quien is None


@pytest.mark.parametrize("fecha", MULTIANIO)
def test_los_hilos_no_se_traslapan(confs, fecha) -> None:
    ordenes = [t.orden for h in confs[fecha].hilos for t in h.turnos]
    assert ordenes == sorted(ordenes)
    assert len(ordenes) == len(set(ordenes))


# ===========================================================================
# Cambios de formato entre años, cada uno con su prueba
# ===========================================================================


def test_los_parrafos_pueden_venir_envueltos_en_divs() -> None:
    """En 2024 los <p> cuelgan de .article-body; desde 2025 van dentro de <div>.

    Mirar solo los hijos directos devuelve la conferencia entera como un
    párrafo: un turno, cero hilos, y ningún error que lo delate.
    """
    ps = "<p><strong>PRESIDENTA:</strong> uno.</p><p><strong>PREGUNTA:</strong> dos.</p>"
    plano = f'<div class="article-body">{ps}</div>'
    envuelto = f'<div class="article-body"><div>{ps}</div></div>'
    assert texto_desde_html(plano) == texto_desde_html(envuelto)
    turnos = parsear(texto_desde_html(envuelto), "x").turnos
    assert [t.etiqueta for t in turnos] == ["PRESIDENTA", "PREGUNTA"]


def test_una_etiqueta_con_espacio_duro_sigue_siendo_etiqueta() -> None:
    """Visto en 2025-07-02: `PREGUNTA:` seguida de \\xa0 en vez de espacio.

    Sin normalizar, ese turno se funde con el anterior y queda atribuido a la
    presidenta. No hay excepción, no hay aviso: solo un turno de menos.
    """
    texto = "PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO: Buenos días.\n\nPREGUNTA:\xa0Bien."
    c = parsear(texto, "x")
    assert len(c.turnos) == 2
    assert c.turnos[1].tipo == "prensa"


def test_el_espacio_duro_se_normaliza_pero_no_se_borra_texto() -> None:
    assert normalizar_espacios("a\xa0b") == "a b"
    assert normalizar_espacios("a b　c") == "a b c"


def test_las_muletillas_de_presentacion_de_los_tres_anios() -> None:
    """Las cinco formas salieron de conferencias reales de 2024, 2025 y 2026."""
    casos = [
        ("Buenos días. Nancy Rodríguez, de Oro Sólido.", "Nancy Rodríguez", "Oro Sólido"),
        ("Gracias. Soy Aissa García, de Telesur.", "Aissa García", "Telesur"),
        (
            "Buenos días, Presidenta. Su servidor, Carlos Pozos, de LM Noticias.",
            "Carlos Pozos",
            "LM Noticias",
        ),
        ("Hola. Mi nombre es Ana Ruiz, de El Sur.", "Ana Ruiz", "El Sur"),
    ]
    for texto, nombre, medio in casos:
        assert identidad_declarada(texto) == (nombre, medio), texto


def test_2026_02_03_recupera_a_carlos_pozos(confs) -> None:
    """Se presentaba con 'Su servidor,' y su hilo entero se perdía."""
    c = confs["2026-02-03"]
    assert "Carlos Pozos" in {h.periodista for h in c.hilos}


def test_una_periodista_aparece_en_dos_conferencias_distintas(confs) -> None:
    """Nancy Flores, de Contralínea, en febrero y en agosto de 2026.

    Sale escrita igual en las dos, pero eso es suerte del muestreo: la
    canonicalización de la fase 7 existe porque en general no pasa.
    """
    feb = {h.periodista for h in confs["2026-02-03"].hilos}
    ago = {h.periodista for h in confs["2026-08-04"].hilos}
    assert "Nancy Flores" in feb & ago


def test_el_cierre_de_documento_esta_en_las_cinco(confs) -> None:
    for fecha, c in confs.items():
        assert c.tenia_fin_de_documento, fecha


# ===========================================================================
# Cambios de formato encontrados al bajar el corpus (fase 5)
# ===========================================================================


def test_interlocutor_es_prensa_no_funcionario() -> None:
    """La forma de octubre de 2024, antes de estandarizar `PREGUNTA`.

    421 turnos en 18 conferencias, todas entre el 2024-10-03 y el 2024-10-29.
    Tratarlos como funcionarios convierte preguntas de periodistas en
    declaraciones de gobierno, que es el peor error posible aquí.
    """
    from estenograficas.parser import clasificar_etiqueta

    for etiqueta in ("INTERLOCUTOR", "INTERLOCUTORA", "INTERLOCUTORES"):
        assert clasificar_etiqueta(etiqueta) == ("prensa", None, None), etiqueta


def test_asistentes_es_ruido_de_sala() -> None:
    from estenograficas.parser import clasificar_etiqueta

    assert clasificar_etiqueta("ASISTENTES")[0] == "anonimo"


def test_la_etiqueta_se_orienta_por_donde_esta_el_cargo() -> None:
    """En 2026 es CARGO, NOMBRE; en octubre de 2024 es NOMBRE, CARGO.

    Un rsplit a ciegas intercambia los campos en un tercio de los funcionarios.
    """
    from estenograficas.parser import clasificar_etiqueta

    # 2026: cargo primero
    tipo, cargo, quien = clasificar_etiqueta(
        "DIRECTOR GENERAL DEL IMSS, ZOÉ ROBLEDO ABURTO"
    )
    assert (tipo, cargo, quien) == ("funcionario", "DIRECTOR GENERAL DEL IMSS", "ZOÉ ROBLEDO ABURTO")

    # 2024: nombre primero
    tipo, cargo, quien = clasificar_etiqueta(
        "CITLALLI HERNÁNDEZ MORA, SECRETARIA DE LAS MUJERES"
    )
    assert (tipo, cargo, quien) == ("funcionario", "SECRETARIA DE LAS MUJERES", "CITLALLI HERNÁNDEZ MORA")

    tipo, cargo, quien = clasificar_etiqueta(
        "MARIO DELGADO CARRILLO, SECRETARIO DE EDUCACIÓN PÚBLICA"
    )
    assert cargo == "SECRETARIO DE EDUCACIÓN PÚBLICA"
    assert quien == "MARIO DELGADO CARRILLO"


def test_si_los_dos_lados_parecen_cargo_no_se_invierte() -> None:
    """Ante la duda se respeta el orden dominante del corpus, CARGO, NOMBRE."""
    from estenograficas.parser import clasificar_etiqueta

    _, cargo, quien = clasificar_etiqueta(
        "SECRETARIO DE MARINA, ALMIRANTE RAYMUNDO PEDRO MORALES"
    )
    assert cargo == "SECRETARIO DE MARINA"
    assert quien == "ALMIRANTE RAYMUNDO PEDRO MORALES"


# ===========================================================================
# Autopresentaciones que se perdían y acreditaban el hilo a otra persona
# ===========================================================================
# Las tres las encontró el humano leyendo una conferencia parseada. No fallaban
# ruidosamente: el hilo entero de una persona quedaba acreditado al periodista
# anterior, que es peor que dejarlo nulo. 12 casos confirmados en el corpus.


def test_dos_muletillas_seguidas_son_una_sola_presentacion() -> None:
    """`Soy su servidor, X` — el regex solo admitía una muletilla."""
    from estenograficas.parser import identidad_declarada

    assert identidad_declarada(
        "Bien, no me presenté, Presidenta. Soy su servidor, Carlos Pozos, "
        "reportero de LM Noticias."
    ) == ("Carlos Pozos", "LM Noticias")


def test_el_oficio_puede_ir_entre_el_nombre_y_el_medio() -> None:
    """`Carlos Pozos, reportero de LM Noticias` — se exigía `, de` pegado."""
    from estenograficas.parser import identidad_declarada

    casos = [
        ("Carlos Pozos, reportero de LM Noticias.", "Carlos Pozos", "LM Noticias"),
        ("Aurora Castillejos, reportera de Canal 14 SPR.", "Aurora Castillejos", "Canal 14 SPR"),
        ("Soy Ana Ruiz, corresponsal de El Sur.", "Ana Ruiz", "El Sur"),
    ]
    for texto, nombre, medio in casos:
        assert identidad_declarada(texto) == (nombre, medio), texto


def test_un_nombre_de_una_palabra_solo_cuenta_tras_muletilla() -> None:
    """`Soy Jonás, de Siker` daba el periodista "Soy Jonás".

    Con muletilla explícita el nombre de una palabra es legítimo; sin ella se
    exigen dos o más, o el regex encontraría nombres por todo el texto.
    """
    from estenograficas.parser import identidad_declarada

    assert identidad_declarada("Hola. Soy Jonás, de Siker.") == ("Jonás", "Siker")
    # sin muletilla, una sola palabra no basta
    assert identidad_declarada("Hola. Jonás, de Siker.") is None


def test_el_ancla_de_oracion_sigue_filtrando_el_falso_positivo() -> None:
    """La flexibilidad nueva no debe reabrir el caso de López Beltrán."""
    from estenograficas.parser import identidad_declarada

    assert identidad_declarada(
        "Se acusa a Andrés Manuel López Beltrán, de encabezar una red de huachicol."
    ) is None
    assert identidad_declarada(
        "…a Estados Unidos, de Cambridge Analytica, precisamente de la manipulación."
    ) is None


def test_ningun_periodista_del_corpus_arrastra_muletilla() -> None:
    """Barrido sobre las cinco conferencias de muestra."""
    from estenograficas.parser import parsear_archivo

    malas = {"Soy", "Su", "Mi", "Le", "Les", "Aquí", "Servidor", "Servidora"}
    for ruta in sorted(config.paths().fixtures.iterdir()):
        if ruta.suffix.lower() not in (".html", ".txt"):
            continue
        for h in parsear_archivo(ruta).hilos:
            assert h.periodista.split()[0] not in malas, (ruta.stem, h.periodista)


def test_la_presentacion_puede_empezar_a_media_oracion() -> None:
    """`Por cierto, soy X, de Y` — solo cuando hay muletilla explícita.

    Sin muletilla el ancla sigue siendo el inicio de oración, porque ahí es
    donde vive el falso positivo de López Beltrán.
    """
    from estenograficas.parser import identidad_declarada

    assert identidad_declarada(
        "Muchas gracias. Por cierto, soy Gregorio Varela, de Cinco Radio. No me presenté."
    ) == ("Gregorio Varela", "Cinco Radio")
    assert identidad_declarada(
        'Presidenta con "A", su servidor Carlos Pozos, reportero de Lord Molécula.'
    ) == ("Carlos Pozos", "Lord Molécula")


def test_conectores_alternativos_al_de() -> None:
    """`para` en vez de `de`, y un `soy` colado antes del oficio."""
    from estenograficas.parser import identidad_declarada

    assert identidad_declarada("Gracias. Manuel Pedrero, para Los Reporteros MX.") == (
        "Manuel Pedrero", "Los Reporteros MX")
    assert identidad_declarada(
        "Hola. Olga Ojeda Lajud, soy corresponsal del Diario del Istmo."
    ) == ("Olga Ojeda Lajud", "Diario del Istmo")
    assert identidad_declarada(
        "Bienvenida. Mi nombre es Yadira Llaven, soy reportera de La Jornada de Oriente."
    ) == ("Yadira Llaven", "La Jornada de Oriente")


def test_el_ancla_suave_no_abre_la_puerta_a_la_prosa() -> None:
    """La coma solo cuenta como ancla si viene una muletilla detrás."""
    from estenograficas.parser import identidad_declarada

    assert identidad_declarada("Preguntar por Israel Vallarta, Presidenta.") is None
    assert identidad_declarada("Se trata de Marina del Pilar, de Baja California.") is None
    assert identidad_declarada(
        "Se acusa a Andrés Manuel López Beltrán, de encabezar una red de huachicol."
    ) is None


def test_ningun_periodista_del_corpus_parece_prosa() -> None:
    """Barrido: ningún nombre debe contener `del` / `de la` / `de los`."""
    import re

    from estenograficas.parser import parsear_archivo

    prosa = re.compile(r"\b(?:del|de la|de los)\b")
    for ruta in sorted(config.paths().fixtures.iterdir()):
        if ruta.suffix.lower() not in (".html", ".txt"):
            continue
        for h in parsear_archivo(ruta).hilos:
            assert not prosa.search(h.periodista), (ruta.stem, h.periodista)
