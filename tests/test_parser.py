"""Pruebas del parser contra `fixtures/2026-08-18.txt`. Sin red.

La prueba de aceptación de la fase 2 son los cuatro periodistas, pero por sí
sola no prueba lo difícil: en esta conferencia hay 65 turnos `PREGUNTA:` y solo
4 autopresentaciones, así que 61 turnos dependen de la propagación hacia
adelante y un parser que parta mal los hilos puede seguir encontrando los 4
nombres. Las aserciones de segmentación son las que muerden.
"""

from __future__ import annotations

import pytest

from estenograficas import config
from estenograficas.parser import (
    Turno,
    armar_hilos,
    clasificar_etiqueta,
    es_ruido,
    extraer_apartes,
    identidad_declarada,
    parsear_archivo,
    quitar_fin_de_documento,
    quitar_videos,
)

CONFERENCIA_ID = "2026-08-18"
PERIODISTAS_ESPERADOS = {
    "Nancy Rodríguez",
    "Javier Tovar",
    "Dalila Escobar",
    "Hans Salazar",
}


@pytest.fixture(scope="module")
def conf():
    return parsear_archivo(config.paths().fixtures / f"{CONFERENCIA_ID}.txt")


# ===========================================================================
# Prueba de aceptación
# ===========================================================================


def test_los_cuatro_periodistas(conf) -> None:
    assert {h.periodista for h in conf.hilos} == PERIODISTAS_ESPERADOS


def test_cada_periodista_con_su_medio(conf) -> None:
    medios = {h.periodista: h.medio for h in conf.hilos}
    assert medios["Javier Tovar"] == "Agencia France-Presse"
    assert medios["Dalila Escobar"] == "Proceso"
    assert medios["Hans Salazar"] == "Noticiero en Redes"
    # Nancy Rodríguez se presenta con dos medios a la vez; se guarda tal cual
    # y la canonicalización es problema de la fase 7, no del parser.
    assert medios["Nancy Rodríguez"] == "Oro Sólido y de Empuje Migrante"


def test_no_inventa_periodistas_de_mas(conf) -> None:
    """El regex ingenuo encuentra seis en esta conferencia; hay cuatro.

    Se cuela con 'Andrés Manuel López Beltrán, de encabezar una red de
    huachicol', donde el 'de' introduce un verbo y no un medio. El ancla de
    oración es lo que los separa.
    """
    assert len(conf.hilos) == 4
    nombres = [h.periodista for h in conf.hilos]
    assert "Andrés Manuel López Beltrán" not in nombres
    assert "Estados Unidos" not in nombres


def test_la_autopresentacion_debe_ser_su_propia_oracion() -> None:
    assert identidad_declarada("Gracias, Presidenta. Dalila Escobar, de Proceso.") == (
        "Dalila Escobar",
        "Proceso",
    )
    # Nombre a media oración: se habla DE alguien, no habla alguien.
    assert (
        identidad_declarada(
            "Se acusa a Andrés Manuel López Beltrán, de encabezar una red de huachicol."
        )
        is None
    )


def test_a_media_conversacion_un_nombre_no_es_una_presentacion() -> None:
    """Fuera de la ventana de apertura hace falta muletilla, no basta la forma."""
    relleno = "palabra " * 60  # ~480 caracteres
    assert identidad_declarada(relleno + "Fulano Mengano, de El Universal.") is None


def test_hay_quien_se_presenta_al_despedirse() -> None:
    """Hay quien cierra su turno con `Muchas gracias. Soy Fulano, de Tal`.

    Cinco personas en el corpus se identifican al final del turno, fuera de la
    ventana de apertura. Sin mirar la cola, sus tandas se le acreditan al
    periodista anterior: el error es doble, uno pierde y otro gana.
    """
    relleno = "Le quiero preguntar por el servicio de agua. " * 12  # ~530 car.
    assert identidad_declarada(
        relleno + "\n\nMuchas gracias.\n\nSoy Gino Ascencio, de Informate y más."
    ) == (
        "Gino Ascencio",
        "Informate y más",
    )


def test_hay_presentaciones_sin_conector() -> None:
    """`Eduardo Esquivel Ancona, Domo de Cristal.` — sin `de` que la ancle.

    No es un caso aislado: dos personas con este estilo valen 19 tandas en
    seis meses. Se acepta por la forma, con candados, porque no hay otra cosa.
    """
    assert identidad_declarada(
        "Buenos días. Eduardo Esquivel Ancona, Domo de Cristal. Mi primera pregunta."
    ) == ("Eduardo Esquivel Ancona", "Domo de Cristal")


def test_la_rama_sin_conector_no_se_traga_lugares_ni_cargos() -> None:
    """Los candados de la rama sin conector, que es la que puede inventar gente."""
    # Preposición o adverbio capitalizado al inicio de oración.
    assert identidad_declarada("En Culiacán, Sinaloa, la situación es distinta.") is None
    assert identidad_declarada("Sobre Chilpancingo, Guerrero, quiero preguntar.") is None
    assert (
        identidad_declarada("Históricamente Baja California, Morena ha ganado ahí.")
        is None
    )
    # Un cargo no es un medio.
    assert identidad_declarada("Buenos días. Claudia Sheinbaum, Presidenta de México.") is None
    # El medio primero y la persona después: no se registra el medio como persona.
    assert identidad_declarada("Canal del Congreso, Elizabeth Robles. Buenos días.") is None


def test_la_muletilla_no_se_queda_pegada_al_nombre() -> None:
    """Sin consumirla, el periodista se registra como `Soy Jonathan Lozada`."""
    nombre, _ = identidad_declarada("Soy Jonathan Lozada, Máxima FM, de Chiapas.")
    assert nombre == "Jonathan Lozada"


def test_el_medio_puede_cerrar_en_otro_cargo_y_no_solo_en_punto() -> None:
    """`…, de Noticias del Movimiento Conciencia y colaboradora del programa…`

    Sin punto a la vista dentro de cien caracteres, exigirlo perdía los 12
    turnos de esa persona.
    """
    assert identidad_declarada(
        "Buenos días a todos los presentes. Elideth Fernández, de Noticias del "
        "Movimiento Conciencia y colaboradora del programa Iztaccíhuatl en El "
        "Sendero de la Luna, así como de otros espacios"
    ) == ("Elideth Fernández", "Noticias del Movimiento Conciencia")


def test_el_conector_admite_las_formas_verbales() -> None:
    """`y soy del periódico X`, `y escribo para Y`: sin ellas se pierde el hilo."""
    assert identidad_declarada(
        "Me presento, mi nombre es Viridiana Venta y soy del periódico Diario Cambio."
    ) == ("Viridiana Venta", "periódico Diario Cambio")
    assert identidad_declarada(
        "Perdón, mi nombre es Elsbeth Lenz, y escribo para La Política en rosa. Hola."
    ) == ("Elsbeth Lenz", "La Política en rosa")


# ===========================================================================
# Segmentación: lo que la prueba de los cuatro nombres NO cubre
# ===========================================================================


def test_los_hilos_van_en_orden_y_no_se_traslapan(conf) -> None:
    ordenes = [t.orden for h in conf.hilos for t in h.turnos]
    assert ordenes == sorted(ordenes), "los turnos de los hilos se desordenaron"
    assert len(ordenes) == len(set(ordenes)), "un turno quedó en dos hilos"


def test_reparto_de_turnos_por_hilo(conf) -> None:
    """Cuadrado a mano contra el texto: 4 hilos, 142 turnos, 17 de exposición."""
    por_hilo = [len(h.turnos) for h in conf.hilos]
    assert por_hilo == [22, 12, 62, 46]
    assert sum(por_hilo) == 142
    assert len(conf.turnos) == 159
    # Los 17 restantes son la exposición previa a la primera pregunta.
    assert conf.turnos_fuera_de_hilo == 17


def test_todos_los_turnos_de_prensa_estan_contados(conf) -> None:
    de_prensa = [t for t in conf.turnos if t.tipo == "prensa"]
    assert len(de_prensa) == 65
    # Los 2 que quedan fuera de hilo son el saludo de apertura del pleno,
    # antes de que ningún periodista se presente.
    en_hilos = {th.orden for h in conf.hilos for th in h.turnos}
    fuera = [t for t in de_prensa if t.orden not in en_hilos]
    assert len(fuera) == 2
    assert all(t.es_ruido for t in fuera), [t.texto for t in fuera]


def test_ningun_turno_incierto_trae_periodista(conf) -> None:
    """Nulo antes que inventado."""
    inciertos = [t for h in conf.hilos for t in h.turnos if t.atribucion == "incierta"]
    assert inciertos, "no se detectó ninguna interjección; la regla no se ejercitó"
    assert all(t.quien is None for t in inciertos)


def test_la_racha_de_preguntas_seguidas_queda_incierta(conf) -> None:
    """Turnos PREGUNTA consecutivos sin respuesta: gente distinta desde el salón.

    En esta conferencia hay exactamente una racha, de tres turnos cortos.
    """
    textos = [
        t.texto for h in conf.hilos for t in h.turnos if t.atribucion == "incierta"
    ]
    assert "A lo mejor no la han informado." in textos
    assert "¿Quiénes?" in textos
    assert "¿De quiénes?" in textos


def test_una_racha_de_turnos_largos_no_es_interjeccion() -> None:
    """Dos preguntas largas seguidas son el mismo periodista, no un grito."""
    largo = "Presidenta, quisiera preguntarle sobre " + "el tema " * 40
    turnos = [
        Turno(CONFERENCIA_ID, 0, "PREGUNTA", None, None, "prensa",
              "Buenos días. Fulana Mengana, de El Universal. " + largo),
        Turno(CONFERENCIA_ID, 1, "PREGUNTA", None, None, "prensa", largo),
    ]
    hilos = armar_hilos(turnos)
    assert len(hilos) == 1
    assert [t.atribucion for t in hilos[0].turnos] == ["declarada", "propagada"]
    assert hilos[0].turnos[1].quien == "Fulana Mengana"


# ===========================================================================
# Trampas del formato
# ===========================================================================


def test_los_videos_desaparecen_con_sus_hablantes(conf) -> None:
    """3 bloques, y con ellos las 18 etiquetas que contaminan."""
    assert conf.bloques_video == 3
    assert conf.videos_sin_cerrar == 0
    contaminantes = [
        t
        for t in conf.turnos
        if t.etiqueta.upper().startswith(("VOZ", "DERECHOHABIENTE", "MADRE", "PADRE"))
    ]
    assert contaminantes == []
    for prohibida in ("VOZ MUJER", "VOZ HOMBRE", "DERECHOHABIENTE", "MADRE DEL PACIENTE"):
        assert prohibida not in conf.etiquetas


def test_un_video_sin_cerrar_se_reporta() -> None:
    texto = "A: hola.\n\n(INICIA VIDEO)\n\nVOZ MUJER: algo.\n"
    _, n, huerfanos = quitar_videos(texto)
    assert n == 0
    assert huerfanos == 1, "un video sin cierre debe delatarse, no pasar callado"


def test_intervencion_no_parte_hilos(conf) -> None:
    """5 ocurrencias, ninguna corta un hilo en dos."""
    interv = [t for t in conf.turnos if t.etiqueta.upper().startswith("INTERVEN")]
    assert len(interv) == 5
    assert all(t.tipo == "anonimo" for t in interv)
    # 4 caen dentro del hilo de Hans Salazar y ninguna abre uno nuevo.
    assert len(conf.hilos) == 4
    en_hilos = {th.orden for h in conf.hilos for th in h.turnos}
    dentro = [t for t in interv if t.orden in en_hilos]
    assert len(dentro) == 4
    for h in conf.hilos:
        for th in h.turnos:
            if th.orden in {t.orden for t in dentro}:
                assert th.atribucion == "incierta"
                assert th.quien is None


def test_los_apartes_salen_del_texto(conf) -> None:
    con_apartes = [t for t in conf.turnos if t.apartes]
    assert con_apartes, "no se detectó ningún aparte"
    todos = [a for t in conf.turnos for a in t.apartes]
    assert "A ver, acá" in todos
    assert "Adelante, adelante, adelante" in todos
    # Y ya no están en el texto, que es el punto: contaminan el conteo de
    # palabras por hablante.
    for t in conf.turnos:
        for a in t.apartes:
            assert a not in t.texto


def test_un_inciso_dentro_de_la_oracion_no_es_aparte() -> None:
    """'—si me dan la siguiente—' es habla al micrófono, no un aparte."""
    texto = "Y estamos muy contentos de presentarles —si me dan la siguiente— cómo evolucionó."
    cuerpo, apartes = extraer_apartes(texto)
    assert apartes == []
    assert cuerpo == texto


def test_el_parrafo_entero_entre_rayas_si_es_aparte() -> None:
    cuerpo, apartes = extraer_apartes("Vamos con esto.\n\n—A ver, acá—.\n\nSigo.")
    assert apartes == ["A ver, acá"]
    assert cuerpo == "Vamos con esto.\n\nSigo."


def test_el_cierre_de_documento_no_es_un_aparte(conf) -> None:
    """`—000—` cierra los boletines de Presidencia y parece un aparte."""
    assert conf.tenia_fin_de_documento
    assert "000" not in [a for t in conf.turnos for a in t.apartes]


def test_quitar_fin_de_documento_solo_al_final() -> None:
    limpio, tenia = quitar_fin_de_documento("texto\n\n—000—")
    assert tenia and "000" not in limpio
    # A media conferencia no se toca: ahí sí sería habla.
    limpio2, tenia2 = quitar_fin_de_documento("texto\n\n—000—\n\nmás texto")
    assert not tenia2 and "000" in limpio2


def test_el_encabezado_no_se_pega_al_primer_turno(conf) -> None:
    assert "Versión estenográfica" in conf.encabezado or "estenográfica" in conf.encabezado
    assert "Presidencia de la República" in conf.encabezado
    primero = conf.turnos[0]
    assert primero.etiqueta == "PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO"
    assert primero.texto == "Buenos días."
    assert "estenográfica" not in primero.texto


def test_los_saludos_no_son_preguntas() -> None:
    assert es_ruido("Buenos días, Presidenta.")
    assert es_ruido("Bien.")
    assert es_ruido("(Inaudible)")
    assert es_ruido("Muchas gracias, Presidenta.")
    # Y lo que sí es pregunta no se filtra, aunque sea igual de corto.
    assert not es_ruido("¿No se le censura?")
    assert not es_ruido("¿Y cómo fue…?")
    assert not es_ruido("El de Tamaulipas.")


def test_la_etiqueta_se_parte_en_cargo_y_nombre() -> None:
    tipo, cargo, hablante = clasificar_etiqueta(
        "DIRECTOR GENERAL INSTITUTO MEXICANO DEL SEGURO SOCIAL (IMSS), ZOÉ ROBLEDO ABURTO"
    )
    assert tipo == "funcionario"
    assert cargo == "DIRECTOR GENERAL INSTITUTO MEXICANO DEL SEGURO SOCIAL (IMSS)"
    assert hablante == "ZOÉ ROBLEDO ABURTO"

    assert clasificar_etiqueta("PREGUNTA") == ("prensa", None, None)
    assert clasificar_etiqueta("INTERVENCIÓN") == ("anonimo", None, None)


# ===========================================================================
# Contratos de datos
# ===========================================================================


def test_los_turnos_cumplen_el_contrato(conf) -> None:
    campos = {
        "conferencia_id", "orden", "etiqueta", "cargo", "hablante",
        "tipo", "texto", "apartes",
    }
    for t in conf.turnos:
        d = t.to_dict()
        assert set(d) == campos
        assert d["conferencia_id"] == CONFERENCIA_ID
        assert d["tipo"] in ("prensa", "funcionario", "anonimo")
        assert isinstance(d["apartes"], list)
    assert [t.orden for t in conf.turnos] == list(range(len(conf.turnos)))


def test_los_hilos_cumplen_el_contrato(conf) -> None:
    for h in conf.hilos:
        d = h.to_dict()
        assert set(d) >= {
            "conferencia_id", "hilo", "periodista", "medio",
            "periodista_canonico", "metodo_identificacion", "turnos",
        }
        assert d["periodista_canonico"] is None  # se llena en la fase 7
        assert d["metodo_identificacion"] == "regex"
        for t in d["turnos"]:
            assert t["rol"] in ("pregunta", "respuesta")
            assert t["atribucion"] in ("declarada", "propagada", "incierta")
            assert isinstance(t["ruido"], bool)


# ===========================================================================
# Redacción para la codificación a ciegas (fase 9)
# ===========================================================================


def test_la_autopresentacion_se_borra_del_texto() -> None:
    """Sin esto la codificación deja de ser a ciegas.

    El 10% de las preguntas dicen el medio dentro de su propio texto, así que
    guardarlo en una columna aparte no protege nada.
    """
    from estenograficas.parser import MARCA_REDACTADA, redactar_identificacion

    original = (
        "Buenos días a todas y a todos. Carlos Navarro, de Heraldo Media Group. "
        "Presidenta, ¿qué tiene de distinto este programa?"
    )
    salida, redactado = redactar_identificacion(original)
    assert redactado
    assert "Carlos Navarro" not in salida
    assert "Heraldo Media Group" not in salida
    assert MARCA_REDACTADA in salida
    # y la pregunta sigue completa
    assert "¿qué tiene de distinto este programa?" in salida
    assert salida.startswith("Buenos días a todas y a todos.")


def test_una_pregunta_sin_presentacion_no_se_toca() -> None:
    from estenograficas.parser import redactar_identificacion

    original = "¿Y un censo interno no ha hecho para conocer cuántas personas?"
    salida, redactado = redactar_identificacion(original)
    assert not redactado
    assert salida == original


def test_no_borra_un_nombre_del_que_solo_se_habla() -> None:
    """Mismo ancla de oración que en la detección: si no es presentación, se queda."""
    from estenograficas.parser import redactar_identificacion

    original = "Se acusa a Andrés Manuel López Beltrán, de encabezar una red de huachicol."
    salida, redactado = redactar_identificacion(original)
    assert not redactado
    assert salida == original


def test_toda_pregunta_con_atribucion_declarada_queda_limpia(conf) -> None:
    """Barrido sobre la conferencia de muestra: ninguna deja el medio a la vista."""
    from estenograficas.parser import redactar_identificacion

    medios = {h.medio for h in conf.hilos}
    for h in conf.hilos:
        for t in h.turnos:
            if t.rol == "pregunta" and t.atribucion == "declarada":
                limpio, _ = redactar_identificacion(t.texto)
                for medio in medios:
                    assert medio not in limpio, f"{medio} sigue visible"
                assert h.periodista not in limpio


# ---------------------------------------------------------------------------
# Puntos 1, 2 y 3 del diagnóstico de la fase 6 (2026-08-28)
# ---------------------------------------------------------------------------


def test_pregunta_con_modalidad_es_prensa():
    """36 turnos de prensa quedaban contados como declaraciones del gobierno.

    `PREGUNTA (VIDEOLLAMADA)` no casaba con la lista de etiquetas de prensa,
    caía al final de `clasificar_etiqueta()` y salía `funcionario`. Es el mismo
    modo de falla que costó 421 turnos con `INTERLOCUTOR`.
    """
    for etiqueta in (
        "PREGUNTA (VIDEOLLAMADA)",
        "PREGUNTA(VIDEOLLAMADA)",
        "PREGUNTA (ENLACE VIDEOLLAMADA)",
        "INTERLOCUTORA (ENLACE VIDEOLLAMADA)",
    ):
        tipo, _, _ = clasificar_etiqueta(etiqueta)
        assert tipo == "prensa", etiqueta


def test_intervencion_con_sexo_es_ruido_de_sala():
    """`INTERVENCIÓN HOMBRE` es lo mismo que `INTERVENCIÓN` y va igual.

    Si se trata como hablante normal parte hilos en dos en silencio, que es el
    error que no se detecta mirando el conteo de periodistas.
    """
    for etiqueta in (
        "INTERVENCIÓN HOMBRE",
        "INTERVENCIÓN MUJER",
        "INTERVENCIÓN MUJER (ENLACE VIDEOLLAMADA)",
        "INTERVENCIONES",
    ):
        tipo, _, _ = clasificar_etiqueta(etiqueta)
        assert tipo == "anonimo", etiqueta


def test_las_siete_grafias_de_la_presidenta_son_una_sola():
    """Tres de las siete son erratas de la transcripción, no hablantes distintos."""
    grafias = [
        "PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO",
        "PRESIDENTA CLAUDIA SHEINBAUM PARDO",
        "PRESIDENTA DE MÉXICO CLAUDIA SHEINBAUM PARDO",
        "RESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO",  # sin la P
        "PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PADO",  # PADO
        "CANDIDATA A LA PRESIDENCIA DE MÉXICO, CLAUDIA SHEINBAUM PARDO",
        "CLAUDIA SHEINBAUM PARDO",
    ]
    salidas = {clasificar_etiqueta(g) for g in grafias}
    assert len(salidas) == 1, salidas
    tipo, cargo, hablante = salidas.pop()
    assert (tipo, cargo, hablante) == (
        "funcionario",
        "PRESIDENTA DE MÉXICO",
        "CLAUDIA SHEINBAUM PARDO",
    )


def test_otros_funcionarios_no_se_confunden_con_la_presidenta():
    """La regla de la presidenta es específica; no puede tragarse a nadie más."""
    tipo, cargo, hablante = clasificar_etiqueta(
        "DIRECTOR GENERAL DEL IMSS, ZOÉ ROBLEDO ABURTO"
    )
    assert (tipo, cargo, hablante) == (
        "funcionario",
        "DIRECTOR GENERAL DEL IMSS",
        "ZOÉ ROBLEDO ABURTO",
    )


def test_medio_con_varias_cabeceras_no_rompe_la_identificacion():
    """El tope de longitud del medio perdía presentaciones enteras.

    Quien representa a un grupo editorial enumera sus cabeceras y se pasa de 70
    caracteres sin esfuerzo. Lo encontró una periodista de la fuente al notar
    que Juan Hernández no aparecía en los conteos: 32 de sus 37 intervenciones
    se le estaban acreditando al periodista anterior.
    """
    casos = [
        ("Qué tal, muy buenos días a todos y a todas. Juan Hernández, de Diario "
         "Basta, Tabasco Hoy, Campeche Hoy y Quintana Roo Hoy, de Grupo Cantón. "
         "Primero, nada más precisar…", "Juan Hernández"),
        ("Buenos días. Shaila Rosagel, de Grupo Healy: El Imparcial, de Sonora; "
         "La Crónica, de Mexicali, y Frontera, de Tijuana. Presidenta, sobre…",
         "Shaila Rosagel"),
    ]
    for texto, esperado in casos:
        ident = identidad_declarada(texto)
        assert ident is not None, f"no detectó a {esperado}"
        assert ident[0] == esperado, ident


def test_el_tope_largo_no_se_traga_una_oracion_entera():
    """Subir el tope no debe volver medio a cualquier cosa que siga a una coma."""
    ident = identidad_declarada(
        "Presidenta, sobre la acusación a Andrés Manuel López Beltrán, de "
        "encabezar una red de huachicol fiscal en el sureste del país, ¿qué…")
    assert ident is None, ident


def test_una_frase_capitalizada_no_es_un_periodista() -> None:
    """`Del Operativo Enjambre, de la detención de algunos presidentes…`

    Tiene la forma exacta de una presentación: nombre capitalizado, coma, `de`,
    y algo detrás. Lo único que la delata es que empieza con preposición.
    """
    for frase in (
        "Del Operativo Enjambre, de la detención de algunos presidentes municipales.",
        "De Chiapas, de la Fiscalía de Feminicidios de Chiapas.",
        "Desde Guadalajara, del canal El Nopal Times.",
        "El Encuentro Cultural Orígenes, de Los Pinos, fue impresionante.",
    ):
        assert identidad_declarada(frase) is None
