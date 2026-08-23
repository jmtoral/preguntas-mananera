# Preguntas matutinas

Análisis de contenido de las versiones estenográficas de las conferencias de prensa matutinas de la Presidencia de México. La pregunta de investigación es si las preguntas que hace la prensa son confrontativas o favorables hacia el gobierno, y cómo se distribuye eso entre medios, periodistas y temas.

**Corpus: 460 conferencias, del 3 de octubre de 2024 al 20 de agosto de 2026.** 65,092 turnos de habla, 22,282 preguntas de prensa, 2,148 tandas de periodista.

> **Estado: a medio camino.** El corpus está descargado y parseado. **Las preguntas todavía no están clasificadas**, así que no hay ningún resultado sobre postura ni sobre confrontación. Lo que sí hay son los conteos descriptivos de quién recibe la palabra, y vienen con limitaciones importantes que se detallan abajo.

---

## Por qué el diseño es así

El objeto de estudio es políticamente cargado. Eso impone tres decisiones que atraviesan todo el proyecto.

**No se colapsa en un solo eje.** Una pregunta puede ser durísima contra la oposición, lo cual favorece al gobierno sin ser un halago. Cada pregunta se clasifica en cuatro dimensiones independientes; un índice único de "dureza" borraría justo esa distinción.

**Quien está en el salón y a quién le dan la palabra no es aleatorio.** La presidenta elige a dedo y lo dice en voz alta. Cualquier conclusión sobre "la prensa es blanda" tiene que discutir **selección** antes que deferencia, así que el análisis reporta composición del pleno y concesión de turnos, no solo promedios de postura.

**Las categorías tienen que ser aplicables desde cualquier posición política.** Si una categoría solo tiene sentido asumiendo una conclusión, está mal definida.

## Libro de códigos

Cuatro dimensiones, todas con `no_clasificable`.

| dimensión | valores | qué captura |
|---|---|---|
| `objetivo` | `gobierno`, `oposicion`, `actor_externo`, `medios`, `ninguno` | **A quién apunta** la pregunta, no de quién se habla |
| `postura` | `confrontativa`, `neutral`, `favorable` | Cómo se para frente a **ese objetivo**, no frente al gobierno |
| `funcion` | `pide_informacion`, `cuestiona_afirmacion`, `invita_comentario_sobre_tercero`, `plantea_demanda` | Qué hace la pregunta; independiente de la postura |
| `insistencia` | `si`, `no` | Repregunta **tras una respuesta evasiva**; requiere las dos cosas |

Toda clasificación incluye el fragmento textual que la justifica.

## Validación

El instrumento se calibra contra codificación humana, no se da por bueno porque el modelo suene convincente.

1. **150 preguntas codificadas a mano**, en dos lotes de 30 y 120, para corregir el libro de códigos donde el humano dude.
2. **A ciegas, en dos sentidos:** el humano no ve la salida del modelo, y la hoja de codificación **no lleva nombre de periodista ni medio**. Ver "Proceso" o "Televisa" mientras se codifica mete la conclusión en el dato.
3. **Consistencia intracodificador:** una semana después se recodifican 20 del primer lote. Si el humano no coincide consigo mismo, las categorías están vagas y ningún clasificador lo arregla.
4. **Alfa de Krippendorff** entre humano y modelo. Debajo de 0.6 se rediseña el libro de códigos. **No se ajusta el prompt hasta que el número suba: eso es entrenar contra la validación.**
5. **Tres corridas por pregunta, perturbadas entre sí** —orden de las categorías, orden del contexto—. A temperatura baja y prompt idéntico coincidirían por construcción y la consistencia no mediría nada. Las que no coinciden van a revisión, no se resuelven por mayoría en silencio.
6. **Segundo instrumento independiente:** embeddings **locales** más regresión logística regularizada. Locales a propósito: si los dos instrumentos salen del mismo proveedor, sus errores se correlacionan y el conjunto de discrepancias deja de ser informativo.

## El dato

Tres archivos intermedios y uno final.

### `turnos.jsonl` — un renglón por turno de habla

```json
{"conferencia_id": "2026-08-18", "orden": 4,
 "etiqueta": "PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO",
 "cargo": "PRESIDENTA DE MÉXICO", "hablante": "CLAUDIA SHEINBAUM PARDO",
 "tipo": "funcionario",
 "texto": "Martes 18 de agosto, ya merito viene el Informe.\n\nBueno, hoy vamos a hablar de salud…",
 "apartes": ["Bueno, vamos con Eduardo"]}
```

`apartes` recoge el habla fuera de micrófono, que contaminaría cualquier conteo de palabras por hablante.

### `hilos.jsonl` — un renglón por tanda de periodista

```json
{"conferencia_id": "2026-08-18", "hilo": 1,
 "periodista": "Javier Tovar", "medio": "Agencia France-Presse",
 "periodista_canonico": null, "metodo_identificacion": "regex",
 "turnos": [
   {"rol": "pregunta",  "quien": "Javier Tovar", "atribucion": "declarada",
    "ruido": false, "orden": 39,
    "texto": "Presidenta, buenos días. Javier Tovar, de la Agencia France-Presse…"},
   {"rol": "respuesta", "quien": "CLAUDIA SHEINBAUM PARDO", "atribucion": "declarada",
    "ruido": false, "orden": 40,
    "texto": "A nosotros no nos dan información de la Embajada…"},
   {"rol": "pregunta",  "quien": "Javier Tovar", "atribucion": "propagada",
    "ruido": false, "orden": 41,
    "texto": "¿Y un censo interno no ha hecho para conocer cuántas personas…?"}
 ]}
```

`atribucion` es el corazón del parser. **`declarada`** cuando el periodista dice su nombre; **`propagada`** cuando la identidad se arrastra hacia adelante dentro de la tanda; **`incierta`** cuando no se puede sostener, y entonces `quien` va nulo. **Nulo antes que inventado.**

### `preguntas.jsonl` — la unidad de análisis final

**Todavía no existe.** Se produce en la fase de clasificación. Esta es su forma:

```json
{"id_pregunta": "2026-08-18-h1-t41",
 "conferencia_id": "2026-08-18", "fecha": "2026-08-18",
 "periodista_canonico": null, "medio_canonico": null,
 "texto": "¿Y un censo interno no ha hecho para conocer cuántas personas…?",
 "tema": "Censo de mexicanos con visa revocada",
 "objetivo":    {"valor": "gobierno",       "fragmento": "¿Y un censo interno no ha hecho…?"},
 "postura":     {"valor": "neutral",        "fragmento": "¿…para conocer más o menos cuántas personas…?"},
 "funcion":     {"valor": "pide_informacion","fragmento": "¿Y un censo interno no ha hecho…?"},
 "insistencia": {"valor": "no",             "fragmento": null},
 "procedencia": {"metodo": "llm", "modelo": "gemini-2.5-flash",
                 "corridas": 3, "acuerdo_entre_corridas": 3,
                 "confianza": 1.0, "revision_humana": false}}
```

Los valores de clasificación de ese ejemplo son **ilustrativos del formato**, no una clasificación real: el corpus todavía no se ha clasificado.

## Hallazgos preliminares: quién recibe la palabra

> ### ⚠️ Léase con estas cuatro limitaciones
>
> 1. **La canonicalización de medios no está hecha.** El corpus tiene **560 cadenas distintas** de nombre de medio; las tablas de abajo usan una normalización burda que las reduce a 465. `Grupo Imagen` y `Diario Imagen` pueden ser el mismo medio o no; esa decisión todavía no se toma.
> 2. **Solo cuentan los periodistas que se autopresentaron.** Contra un conteo manual externo del mismo periodo, **nos falta alrededor del 31%** de las intervenciones. Ese faltante **no es aleatorio**.
> 3. **Un periodista puede representar dos medios a la vez** (`El Chapucero y Efecto Colateral`) y puede cambiar de medio en el tiempo. Aplanar eso borra información real.
> 4. **Esto mide concesión de turnos, no postura.** No dice nada sobre si esas preguntas son duras o blandas.
>
> Es decir: **estos números describen el pipeline tanto como describen la realidad.** Se publican para que el método sea auditable, no como resultado.

### Medios con más tandas

| medio | tandas | preguntas | preguntas por tanda |
|---|---|---|---|
| revista Contralínea | 65 | 562 | 8.6 |
| Noticiero en Redes | 65 | 775 | 11.9 |
| Revista Fortuna | 59 | 702 | 11.9 |
| Código Libre | 44 | 453 | 10.3 |
| Heraldo Media Group | 41 | 407 | 9.9 |
| Diario 24 Horas | 39 | 436 | 11.2 |
| Grupo Imagen | 38 | 407 | 10.7 |
| Grupo Milenio | 38 | 408 | 10.7 |
| Canal Once | 37 | 347 | 9.4 |
| Pulso Saludable | 35 | 254 | 7.3 |
| **Proceso** | 33 | 640 | **19.4** |
| NoticiasDeFrente | 33 | 358 | 10.8 |
| Grupo Fórmula | 33 | 421 | 12.8 |
| Quatro Media (Veracruz) | 32 | 440 | 13.8 |

**La columna que importa es la tercera.** Proceso hace 19.4 preguntas por tanda contra 7.3 de Pulso Saludable: más del doble. *Cuántas veces te dan la palabra* y *cuánto preguntas cuando te la dan* son dos cosas distintas, y un ranking por tandas las confunde.

### Periodistas con más tandas

| periodista | medio más frecuente | tandas | preguntas |
|---|---|---|---|
| Nancy Flores | revista Contralínea | 64 | 550 |
| Hans Salazar | Noticiero en Redes | 64 | 766 |
| Yareth Arciniega | Revista Fortuna | 57 | 689 |
| Carlos Navarro | Heraldo Media Group | 54 | 512 |
| Arturo Pavón | El Chapucero y Efecto Colateral | 51 | 472 |
| Carlos Guzmán | Quatro Media (Veracruz) | 48 | 575 |
| Yusbel Carolina | Código Libre | 44 | 454 |
| Karina Aguilar | Diario 24 Horas | 36 | 403 |
| Liliana Noble | Pulso Saludable | 35 | 254 |
| Zeltzin Juárez | NoticiasDeFrente | 34 | 396 |

**Lo que se puede decir hoy:** en las primeras posiciones hay más medios digitales y de nicho que grandes cadenas nacionales. **Lo que NO se puede decir todavía:** nada sobre por qué, ni sobre si preguntan distinto. Eso requiere clasificación y análisis de selección.

## Cómo se construyó

```bash
python -m estenograficas.descubrimiento   # → data/interim/urls.jsonl
python -m estenograficas.descarga         # → data/raw/{fecha}.html
python -m estenograficas.parseo           # → turnos, hilos, conferencias
```

Cada etapa es idempotente y reanudable, con checkpoint y archivo de rechazos. **Nada se descarta en silencio:** lo que no se puede procesar se escribe con su razón. Un pipeline que "funciona" porque tira lo que no entiende está roto.

**El HTML crudo no se vuelve a descargar.** Se baja una vez y se conserva; el parser se reescribe muchas veces, el corpus no.

**gob.mx responde un reto anti-bot** a cualquier cliente que no ejecute JavaScript. La descarga usa un navegador real; el modo headless no lo pasa. La Wayback Machine queda como respaldo: cubre el 61% del periodo, pero se desploma al 22% de febrero de 2026 en adelante por el rezago normal de archivado.

**Cobertura:** 460 de 491 días hábiles del periodo, 93.7%. Los 31 restantes son festivos: Navidad, Año Nuevo, Semana Santa, 15 y 16 de septiembre, 5 de febrero, 18 de marzo, 20 de noviembre.

## Trampas del formato

El valor de este repositorio está tanto en esta lista como en el código. Cada una costó trabajo encontrarla y **ninguna daba síntomas**: el pipeline corría, los archivos salían bien formados, y el dato estaba mal.

| trampa | efecto si no se atiende |
|---|---|
| Los testimonios en video traen hablantes etiquetados (`VOZ MUJER`, `DERECHOHABIENTE`) | Gente que no está en la conferencia entra al corpus |
| `INTERLOCUTOR` / `INTERLOCUTORA` fue la etiqueta de prensa hasta octubre de 2024 | **421 turnos de periodistas contados como declaraciones de gobierno** |
| El orden de la etiqueta se invierte: `CARGO, NOMBRE` en 2026, `NOMBRE, CARGO` en 2024 | Cargo y nombre intercambiados en un tercio de los funcionarios |
| Etiqueta seguida de espacio duro, o sin espacio, o con paréntesis en minúsculas | **271 turnos fundidos con el anterior; 253 preguntas de prensa traían adentro la respuesta del gobierno** |
| Desde 2025 el CMS envuelve los párrafos en `<div>` | La conferencia entera se lee como un párrafo: un turno, cero hilos, cero errores |
| El periodista se identifica una sola vez y luego solo dice `PREGUNTA:` | Sin propagar la identidad, se pierde el 90% de la autoría |
| Turnos `PREGUNTA:` consecutivos y cortos son gente distinta gritando desde el salón | Se le atribuyen a un periodista frases que no dijo |
| `Nombre, de Medio` sin anclar a inicio y fin de oración | Encuentra 6 periodistas en una conferencia que tiene 4: se traga `…a X, de encabezar una red de huachicol` |
| Muletillas: `Soy…`, `Su servidor, …` | El nombre sale con el verbo pegado, o el hilo entero se pierde |
| `—000—` cierra el boletín y tiene la forma exacta de un aparte fuera de micrófono | Se le atribuye a la presidenta |
| Los slugs traen erratas: año truncado, backslash, sufijos numéricos | Construir URLs por fecha pierde conferencias que existen |

**Y una que se intentó arreglar y hubo que revertir:** tratar `(PROYECCIÓN DE VIDEO)` como apertura de bloque parecía obvio, pero es una marca suelta sin cierre propio, así que el bloque se comía todo hasta el siguiente `(FINALIZA VIDEO)`. Medido antes de darlo por bueno: **borraba 787 turnos, 239 de prensa.** Está documentado en el código para que nadie lo reintente.

## Estructura

```
src/estenograficas/
  config.py           rutas y secretos; ninguna ruta absoluta escrita a mano
  checkpoint.py       reanudación con fsync por item y archivo de rechazos
  parser.py           texto → turnos → hilos
  descubrimiento.py   descubrimiento de URLs
  descarga.py         descarga del HTML crudo
  parseo.py           parseo masivo del corpus
  temas.py            resumen temático por pregunta
tests/                120 pruebas
fixtures/             5 conferencias de muestra, versionadas
data/                 en .gitignore
```

## Reproducir

```bash
conda env create -f environment.yml
conda activate votaciones_corte
pip install -e .
cp .env.example .env        # y poner la API key de Gemini
pytest -q
```

La descarga tarda unos 15 minutos y abre una ventana de navegador. `data/raw/` pesa 75 MB.

## Costo

Medido contando tokens con la API sobre una muestra real, no estimado:

| etapa | tokens | costo (batch) |
|---|---|---|
| clasificación, 3 corridas | 47 M entrada, 8.7 M salida | ~$18 USD |
| resúmenes temáticos | 2 M entrada | ~$1 USD |

Más de la mitad del costo de entrada es el libro de códigos repetido en cada llamada.

## Licencia y fuentes

Las versiones estenográficas son documentos públicos de la Presidencia de la República, publicados en gob.mx. Este repositorio contiene el código y cinco conferencias de muestra; el corpus completo no se redistribuye y se reconstruye corriendo el pipeline.

## Advertencia

Este trabajo **mide y describe, no adjetiva**. Los conteos publicados arriba son preliminares y están sujetos a las limitaciones enunciadas. Ningún resultado sobre postura, confrontación o deferencia ha sido producido todavía, y cualquier afirmación en ese sentido atribuida a este proyecto sería prematura.
