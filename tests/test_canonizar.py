"""Canonización de nombres de persona y de cabecera.

Las dos decisiones que estas pruebas fijan, porque son las que se pueden
deshacer sin querer:

1. **La fusión automática es tímida.** Une erratas, no une personas. Cuando
   las dos grafías son frecuentes se reportan y decide un humano.
2. **Comparar y mostrar son cosas distintas.** `El Imparcial` y `Imparcial`
   son la misma cabecera al comparar; lo que se muestra conserva el artículo.
"""

from __future__ import annotations

from collections import Counter

import pytest

from estenograficas.canonizar import (
    canonizar_medios,
    canonizar_nombres,
    clave,
    partir_medios,
)


def test_una_errata_se_absorbe_en_la_forma_frecuente() -> None:
    frec = Counter({"Hans Salazar": 66, "Han Salazar": 1})
    mapa, dudosos = canonizar_nombres(frec)
    assert mapa["Han Salazar"] == "Hans Salazar"
    assert dudosos == []


def test_dos_formas_frecuentes_no_se_fusionan_solas() -> None:
    """`Sandra Aguilar` y `Sandra Aguilera` son dos personas, de dos medios.

    Fusionarlas por parecido borraría a una. Se reportan y decide un humano.
    """
    frec = Counter({"Sandra Aguilar": 24, "Sandra Aguilera": 11})
    mapa, dudosos = canonizar_nombres(frec)
    assert mapa["Sandra Aguilera"] == "Sandra Aguilera"
    assert [(a, b) for a, _, b, _ in dudosos] == [("Sandra Aguilar", "Sandra Aguilera")]


def test_la_correccion_humana_manda_sobre_la_frecuencia() -> None:
    """La estenográfica escribe `Yareth` sus 59 veces y el nombre es `Yaneth`.

    Ningún algoritmo puede deducirlo: no hay una grafía mayoritaria correcta
    contra la cual comparar.
    """
    frec = Counter({"Yareth Arciniega": 59, "Yarteh Arciniega": 1})
    mapa, _ = canonizar_nombres(frec, {"Yareth Arciniega": "Yaneth Arciniega",
                                       "Yarteh Arciniega": "Yaneth Arciniega"})
    assert set(mapa.values()) == {"Yaneth Arciniega"}


def test_un_par_declarado_aparte_deja_de_reportarse() -> None:
    """Escribir `variante == canonico` es cómo se dice «ya lo revisé, son dos»."""
    frec = Counter({"Sandra Aguilar": 24, "Sandra Aguilera": 11})
    _, dudosos = canonizar_nombres(
        frec, {"Sandra Aguilar": "Sandra Aguilar", "Sandra Aguilera": "Sandra Aguilera"}
    )
    assert dudosos == []


# ---------------------------------------------------------------------------
# Medios
# ---------------------------------------------------------------------------


def test_quien_representa_a_un_grupo_suma_a_cada_cabecera() -> None:
    """Decisión del proyecto: `medio patito, menganito y sultanito` son tres.

    Contar la cadena entera como una sola entidad vuelve invisibles a las
    cuatro cabeceras de Grupo Cantón, que es como Juan Hernández desapareció.
    """
    assert partir_medios(
        "Diario Basta, Tabasco Hoy, Campeche Hoy y Quintana Roo Hoy, de Grupo Cantón"
    ) == ["Diario Basta", "Tabasco Hoy", "Campeche Hoy", "Quintana Roo Hoy",
          "Grupo Cantón"]


def test_los_dos_puntos_tambien_separan() -> None:
    assert partir_medios("Grupo Healy: El Imparcial, La Crónica y Frontera") == [
        "Grupo Healy", "El Imparcial", "La Crónica", "Frontera"
    ]


def test_la_conjuncion_rezagada_no_se_queda_pegada() -> None:
    """Partir por coma deja fragmentos como `y Frontera`, que no es un medio."""
    assert "Frontera" in partir_medios("La Crónica, de Mexicali, y Frontera, de Tijuana")


def test_un_estado_no_es_un_medio() -> None:
    assert partir_medios("Quatro Media Telecomunicaciones, Veracruz") == [
        "Quatro Media Telecomunicaciones"
    ]


@pytest.mark.parametrize(
    "a, b",
    [
        ("El Imparcial", "Imparcial"),
        ("revista Contralínea", "Contralínea"),
        ("La Crónica", "la Cronica"),
    ],
)
def test_articulo_y_soporte_se_ignoran_al_comparar(a: str, b: str) -> None:
    assert clave(a) == clave(b)


def test_diario_y_grupo_son_parte_del_nombre_no_un_soporte() -> None:
    """Quitarlos fusionaría `Diario Basta` con cualquier cosa llamada `Basta`."""
    assert clave("Diario Basta") != clave("Basta")
    assert clave("Grupo Cantón") != clave("Cantón")


def test_la_grafia_que_se_muestra_es_la_mejor_capitalizada() -> None:
    """`El imparcial` aparece 22 veces y `El Imparcial` 21: gana la correcta."""
    mapa = canonizar_medios(["El imparcial"] * 22 + ["El Imparcial"] * 21)
    assert set(mapa.values()) == {"El Imparcial"}


def test_si_no_hay_grafia_buena_se_arregla_la_primera_letra() -> None:
    """`revista Contralínea` es la única forma que existe para ese medio."""
    mapa = canonizar_medios(["revista Contralínea"] * 66)
    assert set(mapa.values()) == {"Revista Contralínea"}
