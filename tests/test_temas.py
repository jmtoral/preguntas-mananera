"""Pruebas de la consolidación de asuntos de nivel 2."""

from estenograficas.temas_dos_niveles import _bolsa, consolidar


def test_bolsa_ignora_acentos_y_palabras_cortas():
    assert _bolsa("Reforma Judicial en México") == {"reforma", "judicial", "mexico"}


def test_fusiona_parafrasis_con_el_mismo_vocabulario():
    mapa = consolidar(
        ["Acuerdo comercial México Unión Europea"] * 3
        + ["Acuerdo comercial con Unión Europea"]
    )
    assert len(set(mapa.values())) == 1
    # el representante es el más frecuente
    assert mapa["Acuerdo comercial con Unión Europea"] == (
        "Acuerdo comercial México Unión Europea"
    )


def test_no_fusiona_asuntos_distintos():
    mapa = consolidar(["Reforma judicial elección jueces", "Precio gasolina Pemex"])
    assert len(set(mapa.values())) == 2


def test_no_encadena_por_una_frase_puente():
    """El defecto que traía la versión con union-find.

    `Regulación redes sociales crimen organizado` se parece lo suficiente a los
    dos lados, y con fusión por cadenas arrastraba a un mismo grupo cosas que no
    comparten una sola palabra. Cada miembro tiene que parecerse al
    representante, no a un vecino cualquiera.
    """
    a = "Regulación redes sociales algoritmos"
    puente = "Regulación redes sociales crimen organizado"
    b = "Reclutamiento forzado crimen organizado"
    mapa = consolidar([a, puente, b])
    assert not (_bolsa(a) & _bolsa(b)), "los extremos no comparten palabras"
    assert mapa[a] != mapa[b], "quedaron encadenados a través del puente"


def test_todo_miembro_se_parece_a_su_representante():
    """Invariante que la versión anterior no garantizaba."""
    asuntos = [
        "Deuda Pemex pago proveedores",
        "Adeudos Pemex proveedores 2025",
        "Autosuficiencia financiera Pemex",
        "Regulación redes sociales algoritmos",
        "Regulación redes sociales crimen organizado",
        "Reclutamiento forzado crimen organizado",
        "Reclutamiento forzado jóvenes crimen organizado",
    ]
    mapa = consolidar(asuntos)
    for miembro, rep in mapa.items():
        if miembro == rep:
            continue
        A, B = _bolsa(miembro), _bolsa(rep)
        assert len(A & B) / len(A | B) >= 0.5, f"{miembro!r} no se parece a {rep!r}"


def test_es_determinista():
    asuntos = ["Precio gasolina Pemex", "Precio de la gasolina", "Reforma judicial"] * 2
    assert consolidar(asuntos) == consolidar(list(reversed(asuntos)))


def test_asunto_sin_palabras_significativas_queda_solo():
    mapa = consolidar(["De la ley", "Reforma judicial elección"])
    assert mapa["De la ley"] == "De la ley"
