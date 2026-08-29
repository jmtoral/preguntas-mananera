# HANDOFF

Memoria del proyecto entre sesiones. El agente lo actualiza al terminar cada fase, antes de detenerse.

Regla de escritura: se describe lo que **pasó**, no lo que se pretendía. Un handoff optimista es peor que ninguno.

---

## Estado

**Última actualización:** 2026-08-28, tarde. **La clasificación temática terminó**: 12,135 de 12,299 preguntas (98.7%), 164 rechazadas. Los asuntos ya están consolidados y el algoritmo que los consolida se corrigió (traía un defecto de fusión por cadenas, ver abajo).

**Ambiente:** `votaciones_corte`, Python 3.11. Conda no está en el PATH; usar el intérprete por ruta:
`C:/Users/User/anaconda3/envs/votaciones_corte/python.exe`. En Windows anteponer `PYTHONIOENCODING=utf-8` o la consola destroza los acentos al imprimir (los archivos están bien, es solo la impresión).

**Repositorio:** https://github.com/jmtoral/preguntas-mananera — público, al día con `origin/main`.

**Node** está instalado en `C:\Program Files\nodejs\node.exe` pero **fuera del PATH de bash**; llamarlo por ruta. Sirve para el validador de paletas de la skill `dataviz`.

**Para matar procesos de Windows desde bash:** `taskkill` quiere el **WINPID**, que es el *cuarto* campo de `ps -W`, no el PID de bash. Con el campo equivocado dice "correcto" y no mata nada.

---

## Decisiones pendientes en detalle

```bash
cd d:/PROYECTOS_PERSONALES/preguntas_matutinas
PYTHONIOENCODING=utf-8 "C:/Users/User/anaconda3/envs/votaciones_corte/python.exe" -m pytest -q   # 136
```

**Y antes de nada, verificar que no quedó un proceso vivo de ayer:**

```bash
ps -W | grep -c votaciones_corte      # debe ser 0
```

El 2026-08-28 la sesión se reinició y el Python de Windows **no murió con ella**: hubo dos procesos escribiendo al mismo checkpoint. No rompió nada —0 truncadas, 0 duplicados— pero duplica el gasto de API.

### Las cuatro cosas pendientes, en orden

**1. Los 6 puntos de la parada de la fase 6**, más la decisión sobre presentaciones tardías. Siguen sin resolverse y **bloquean la fase 7**. Es lo único que hoy detiene el proyecto; todo lo demás es trabajo que se puede hacer en paralelo.

**2. Canonizar los nombres de medio.** Son ~620 cadenas crudas y el problema es real, no cosmético: Carlos Guzmán dice su medio de **11 formas distintas**, alternando `Quatro` y `Cuatro`. El contraste externo del 2026-08-28 confirmó que **una lectora experta tropieza con el mismo problema** —su tabla por medio es inconsistente con su propia tabla por periodista justo en ese caso—, así que no hay atajo por consulta. El eje confiable mientras tanto es el **periodista**, donde coincidimos perfecto. Ver `assets/cotejo_conteos_2026-08-28.md`.

**3. Revisar a mano los 620 grupos de consolidación.** Aplazado explícitamente por el humano el 2026-08-28. El defecto que hacía urgente esta revisión ya se corrigió en el código (ver abajo), así que lo que queda es control de calidad, no reparación. Empezar por los grupos grandes: `python scripts/consolidar_asuntos.py --minimo 6`.

**4. La muestra de oro.** Sigue sin arrancar y sigue siendo el cuello de botella metodológico: nada de la fase 9 en adelante significa algo sin ella. Necesita el instructivo de codificación con ejemplos trabajados **tomados de fuera de las 150 muestreadas**.

### El filtro de longitud que descartaba el 45% en silencio

Encontrado el 2026-08-28 al planear la fase de postura. `scripts/clasificar_temas.py` traía en su selección de preguntas un `120 < len(texto) < 1500` que **nunca se documentó ni se discutió**.

| | preguntas | |
|---|---:|---|
| ≤ 120 caracteres | 9,535 | **42%, excluidas** |
| 120–1500 | 12,299 | 55%, clasificadas |
| ≥ 1500 caracteres | 604 | **3%, excluidas** |

**Viola la regla dura 3.** Esas 10,139 preguntas no fueron a un archivo de rechazos con su razón: se filtraron antes de que el checkpoint las viera. Desaparecieron sin dejar rastro, que es exactamente el modo de falla que la regla existe para prevenir.

**Y el descarte no es inocuo, en ninguna de las dos direcciones.** Las cortas son las repreguntas:

> *«¿Tienen algún número de fallecidos?»*
> *«¿Hay algún avance sobre por qué se abrió fuego?»*
> *«Entonces, ¿el tren de Nogales sí se va a construir en este sexenio?»*

Ésas son **la cuarta dimensión del libro de códigos**, `insistencia`: "true si es repregunta tras una respuesta evasiva". Un filtro por longitud las borra casi por definición. Y las 604 largas son los turnos de tres preguntas de Manuel Pedrero y Hans Salazar, los que encabezan todos los conteos.

Para temas probablemente no mueve mucho las proporciones. **Para postura era descalificante.**

Corregido: entran todas las preguntas útiles; solo se excluyen las de menos de 12 caracteres, y ésas **sí se escriben a rechazos con su razón**. El criterio de saludos no cambia: eso lo marca el parser como `ruido` y ahí sigue.

### Cerrado el 2026-08-28: qué promete el nivel 2, medido sobre el corpus completo

La pregunta quedó respondida y la respuesta es que **el nivel 2 no mide duración de una historia**.

| | asuntos | en UNA sola conferencia |
|---|---:|---:|
| crudos, como los produjo el modelo | 9,795 | **93%** |
| consolidados con union-find (defectuoso) | 8,522 | 90% |
| **consolidados con el algoritmo corregido** | **8,862** | **89%** |

Consolidar mueve el número tres puntos. No lo cambia de naturaleza. **El asunto captura "el tema de esa tanda", no una historia que vive semanas**, y ese era el argumento con el que se eligió la opción B. La reetiquetación es la salida honesta: el nivel 2 sirve para navegar el corpus y para ver de qué habla cada periodista, no para medir cuánto dura un tema.

Lo que sí queda, y es útil: **796 asuntos que abarcan siete días o más**. Ésos sí son historias seguibles, y son el subconjunto sobre el que tiene sentido preguntar por duración.

### El defecto de `consolidar()` y su corrección

La versión original usaba **union-find**, que fusiona por cadenas: si A se parece a B y B a C, los tres quedan en el mismo grupo aunque A y C no compartan una sola palabra.

Medido sobre el corpus completo: 6 grupos encadenados de 502, pero **uno tenía 204 miembros** y pegaba *Regulación de redes sociales* con *Reclutamiento del crimen organizado* a través de la frase puente `Regulación redes sociales crimen organizado`. Jaccard entre los extremos: **0.00**. Un grupo así envenena cualquier conteo por asunto sin dar ninguna señal de que algo salió mal.

**La corrección: cada miembro se compara contra el representante del grupo, no contra un vecino cualquiera.** Se recorre de más frecuente a menos frecuente; a frecuencia igual, alfabéticamente, para que el mapa sea determinista.

| | union-find | corregido |
|---|---:|---:|
| grupos que fusionan | 502 | **620** |
| grupos encadenados | 6 | **0** |
| grupo más grande | 204 variantes | **14** |
| tiempo sobre el corpus | >120 s | **10 s** |

Fusiona **más** grupos, no menos: el encadenamiento estaba absorbiendo casos distintos en pocos grupos gigantes y por eso el total salía más bajo.

El salto de velocidad viene de un **índice invertido** palabra → representantes. Jaccard ≥ 0.5 exige al menos una palabra en común, así que solo hay que mirar a los representantes que comparten alguna. El resultado es idéntico al de la comparación exhaustiva porque los candidatos se recorren en orden de inserción.

Siete pruebas nuevas en `tests/test_temas.py`, incluida `test_no_encadena_por_una_frase_puente`, que reproduce el caso exacto, y `test_todo_miembro_se_parece_a_su_representante`, que es el invariante que la versión anterior no cumplía. `scripts/consolidar_asuntos.py` vuelve a verificar ese invariante con un `assert` en cada corrida.

---

## Hecho

### Lote 1 de la muestra de oro: codificado y revisado (2026-08-28)

**28 de 30 codificadas.** Distribución: `neutral` 14 (50%), `afín al gobierno` 7 (25%), `crítica a un tercero` 4 (14%), `crítica al gobierno` 3 (11%). Con n=28 no dice nada del corpus; sí dijo mucho del instrumento.

**Tres decisiones tomadas en la parada, todas del humano:**

1. **La regla del golpe.** Sus propios códigos ya la contenían sin nombrarla: en un caso anotó «invitación a atacar a la derecha» y codificó `afín`, en otro «critica a la gobernadora de Chihuahua» y codificó `crítica a un tercero`. La distinción que hace es **quién da el golpe**: si lo da la pregunta, `crítica a un tercero`; si la pregunta solo tiende la mano para que lo dé el gobierno, `afín al gobierno`. Escrita al instructivo.

2. **Las peticiones van a `afín al gobierno`**, salvo que traigan reproche. **Consecuencia que hay que recordar al leer resultados: `afín` queda más ancho que el elogio** — contiene halago, plataforma y petición. Las tres le sirven al gobierno, pero no son lo mismo, y si algún día importa distinguirlas hay que volver a la columna de fragmentos.

3. **Los fragmentos se codifican igual, pero el alfa se reporta partido en dos.** 13 de las 30 tienen menos de 80 caracteres; en el corpus completo son el 32%. La muestra es representativa y no se toca. Dato que motivó la decisión: **las tres `crítica al gobierno` cayeron todas en la mitad larga, ninguna en la corta.** Un solo número promediaría dos instrumentos distintos.

**Dos deslices reconocidos por el humano** (P-017, P-029): los recodifica él. **El agente no tocó ningún código de la muestra**, ni siquiera para sugerir el valor correcto; solo señaló que el contexto y el código parecían no coincidir y preguntó qué había querido decir.

**Un problema del agente, no del humano:** P-036 se codificó con información incompleta —el fragmento que escribió corresponde al turno anterior— porque la hoja vieja solo traía dos turnos previos y no traía «lo que siguió». P-013 quedó en blanco por lo mismo. Ambas hay que rehacerlas con la hoja nueva.

**El humano llenó la v1 y no la v2.** No costó nada: `muestrear_oro.py` arrastra las respuestas por código y se verificó una por una —0 diferencias, 11 fragmentos y 1 nota conservados—. Hay respaldo fechado en `data/gold/`. La hoja buena vuelve a ser `muestra_oro_hoja.xlsx`.

### El libro de códigos pasó de cuatro dimensiones a una (2026-08-28)

Decisión del humano, con el motivo explícito: **no va a escribir un artículo académico**, así que cuatro dimensiones ortogonales son un impuesto que no compra nada. `funcion` e `insistencia` no contestan la pregunta que le interesa.

Su propuesta inicial fueron las tres categorías de uso periodístico —crítica / afín / **de interés público**—, que son las mismas que usa la fuente externa. Se contrapropuso y aceptó una variante, por dos razones que conviene no volver a discutir desde cero:

1. **«De interés público» no está en el mismo eje que las otras dos.** Mide el mérito de la pregunta, no su dirección. Casi todo el buen periodismo es crítico y de interés público a la vez, así que al obligar a escoger, quien codifica resuelve ese conflicto en su cabeza, sin dejar rastro y distinto cada vez. Eso hunde la confiabilidad, y no por tener pocas categorías sino por no ser excluyentes.
2. **La etiqueta juzga.** Decir que una categoría es «de interés público» afirma que las otras no lo son. Regla 8.

Además tenía un hueco medible: **3,420 preguntas, el 15%, hablan de la oposición o de un actor externo**. Una pregunta durísima contra García Luna o contra Trump no es crítica al gobierno ni lo halaga; se habría ido al cajón de en medio revuelta con las peticiones de dato.

**El esquema que quedó:** una columna, cuatro valores — `crítica al gobierno`, `afín al gobierno`, `crítica a un tercero`, `neutral`, más `no clasificable`.

**La regla operativa, que es lo que hace codificable el esquema: la carga está en la premisa, no en el tema.** «¿Hay algún dato de avance?» es neutral; «hay avances importantes, ¿cuál es su mensaje?» es afín. Mismo tema, signo distinto, y la diferencia está entera en lo que la pregunta da por sentado. Y cuando habla de un tercero pero le reclama al gobierno, es crítica al gobierno: la prueba es **quién queda mal si la pregunta tiene razón**.

`objetivo`, `funcion` e `insistencia` **se dejan de codificar, no se borran**. La muestra es la misma; si algún día hace falta el artículo, se codifican entonces sobre estas mismas 150.

### La muestra de oro y su instructivo, listos

`scripts/muestrear_oro.py` produce hoja y llave por separado, con semilla fija (`20260828`), así que la muestra es reproducible y **no cambió** al rehacer las columnas.

- **Hoja:** `data/gold/muestra_oro_hoja.xlsx`, dos pestañas de 30 y 120, menú desplegable en la única columna a codificar.
- **Llave:** `data/gold/muestra_oro_LLAVE_no_abrir.csv`. Periodista, medio e `id_pregunta` viven aquí. La hoja **no lleva el id** porque trae la fecha y el número de hilo y con eso se puede buscar de quién es.

**La ceguera se verifica, no se promete.** Se midió primero la fuga por contexto: **108 respuestas de la presidenta nombran al periodista de esa tanda** («Gracias, Hans»). El script tapa nombre, apellidos y vocativos, y después revisa fila por fila que ningún término de la llave sobreviva. Sobre la hoja generada: **0 fugas**.

Un error propio, corregido: la primera versión del detector descartaba por palabras genéricas del nombre del medio —`México`, `Grupo`, `programa`—, lo que habría excluido toda pregunta de tema nacional. Sesgo grande y en una sola dirección. Con la lista de genéricas los descartes bajaron de 12 a 5, todos legítimos.

**Composición de las 150:** 10 de 2024, 89 de 2025, 51 de 2026 —proporcional al corpus—; 13 abren tanda y 137 son seguimiento; mediana de 177 caracteres.

**`INSTRUCTIVO_CODIFICACION.md`**, con 10 ejemplos trabajados verificados por cotejo como fuera de las 150. Deja escrito que los ejemplos son lectura del agente y que eso infla el acuerdo, para que se reporte junto al número. El humano eligió esa opción a sabiendas, sobre la alternativa de codificar 10 en frío primero.

### Conteo de palabras: hallazgo con su confusor medido (2026-08-28)

Se puede contar cuánto habla cada quien sin clasificar nada. Sobre el corpus completo:

| | palabras |
|---|---:|
| pregunta la prensa | 1,220,267 |
| responde la presidenta | 2,072,415 |
| otros funcionarios | 532,244 |

Razón global **1.70** (solo la presidenta), 2.13 contando a todo el gobierno.

**El primer resultado, sobre 40 periodistas con 8 conferencias o más, parecía un hallazgo de trato diferencial:** la razón va de 0.71 (Demian Duarte) a 3.23 (Carlos Navarro), 4.5 a 1. **Está mal leído así.**

| correlación con la razón | r |
|---|---:|
| largo de la **pregunta** | **−0.68** |
| largo de la **respuesta** | +0.34 |

La razón la gobierna el **denominador**. Y el denominador se mueve más: las preguntas van de 30 a 114 palabras (factor 3.8), las respuestas de 61 a 140 (factor 2.3). **Ordenar por razón es en buena medida ordenar por quién habla más al preguntar.** Demian Duarte aparece último porque hace las preguntas más largas de los 40, no porque lo traten mal.

**La medida que sí aguanta es palabras por respuesta**, que no depende del estilo de quien pregunta y aun así varía 2.3 veces: de 61 (Judith Sánchez Reyes) a 140 (Manuel Pedrero), mediana 93.

**Y aun ésa no mide trato preferente.** Faltan tres controles, anotados para que nadie salte el paso: el **tema** (una pregunta técnica de salud obliga a respuesta larga sin que sea deferencia), el **número de preguntas por tanda** (quien acumula cinco recibe una sola respuesta para las cinco y su promedio por turno sube), y **a quién le dan la palabra**, que no es aleatorio. Una respuesta larga puede ser atención, evasión o clase magistral, y sin `postura` clasificada el largo no distingue entre las tres.

Datos en `data/outputs/razon_palabras.json`.

### Artefacto de exploración

`data/outputs/quien_pregunta.html`, publicado. Cuatro secciones: quién pregunta y cada cuándo, de qué pregunta cada quien (40 periodistas, categorías y asuntos consolidados), cuánto contesta la presidenta (bruto, por turno y la dispersión del confusor), y el cruce con publicidad oficial.

**Es exploración, no producto final.** Ninguna pregunta está clasificada por postura, así que el artefacto solo cruza dinero y palabras contra **frecuencia**, nunca contra dureza. Cada sección lleva su advertencia escrita.

Los generadores viven en el scratchpad de la sesión, no en `scripts/`: dependen de material que no debe entrar al repo y de números de una sola corrida. Si el artefacto se vuelve producto, hay que reescribirlos en `src/`.

### Clasificación temática — TERMINADA el 2026-08-28

**12,135 preguntas clasificadas de 12,299 (98.7%). 164 rechazadas (1.3%). Reconstruido y consolidado.**

Corrió en dos tramos, con una pausa a la mitad por presupuesto de API. El segundo tramo hizo 9,070
preguntas en 2,793 s, o sea **3.2 preguntas por segundo**.

Las 164 rechazadas no se descartaron en silencio: viven en
`data/checkpoints/temas_dos_niveles.rechazos.jsonl` con su razón. Queda pendiente decidir si se
reintentan; son el 1.3% y no cambian ninguna proporción, pero la regla dura 3 dice que nada se tira.

**Los tres comandos, en este orden:**

```bash
python scripts/clasificar_temas.py     # retoma desde el checkpoint, no repaga nada
python scripts/reconstruir_temas.py    # SIEMPRE al terminar: el checkpoint es la verdad
python scripts/consolidar_asuntos.py   # DESPUÉS de reconstruir, nunca antes
```

**Ya es concurrente.** Se midió que agrandar el lote no servía —10 preguntas tardan 15 s y 25 tardan 33 s, o sea ~1.4 s por pregunta pase lo que pase— porque el cuello es la **salida**, que el modelo escribe token por token. Solapar peticiones sí sirve: `clasificar_paralelo()` con 6 trabajadores pasó de **0.45 a 2.5 preguntas por segundo, 5.5 veces más rápido.** Lo que falta debería tomar ~1 hora, no 7.

**El costo de paralelizar, asumido a sabiendas:** el vocabulario de asuntos es estado compartido y cada trabajador ve una foto con segundos de retraso, así que va a inventar nombres nuevos para casos que otro acaba de nombrar. Se aceptó porque la reutilización ya rendía poco (30%) y `consolidar()` existe para fusionar casi-duplicados.

**Un susto que salió bien.** Al reiniciarse la sesión el Python de Windows no murió con ella, y por unos minutos hubo **dos procesos escribiendo al mismo checkpoint**. Resultado: 0 líneas truncadas y 0 ids duplicados. El registro append-only con `fsync` por renglón aguantó escritores concurrentes. (Nota operativa: `taskkill` quiere el WINPID, cuarto campo de `ps -W`, no el PID de bash.)

**El orden importa.** `reconstruir_temas.py` reescribe `temas_dos_niveles.jsonl` desde el checkpoint, así que borra cualquier campo que se le haya agregado después. Por eso la consolidación **no toca ese archivo**: deja su mapa aparte, en `data/interim/mapa_consolidacion.json`. El asunto crudo que produjo el modelo se conserva siempre y la consolidación se puede rehacer con otro umbral sin volver a pagar clasificación.

### Clasificación temática en dos niveles — el diseño

Trabajo del 2026-08-27. **Hay una corrida larga en curso**; si esta sesión murió, retomarla es un comando.

**Diseño, ya decidido y probado.**

- **Nivel 1 `categoria`:** una de 18, lista cerrada, en `data/interim/taxonomia_temas_candidata.json`. Es lo que se tabula. Probado dos veces: 190/190 y 400/400 clasificadas sin una sola categoría fuera de lista.
- **Nivel 2 `asunto`:** el caso concreto con nombres (`"Diálogo con Trump sobre acusaciones Rocha Moya"`). Es lo que permite seguir una historia en el tiempo.
- **La consolidación de asuntos es sobre TODO el corpus, no por mes.** Decisión del humano. Un caso vive semanas y cruza de mes a mes; consolidar por mes lo partiría y volvería invisible cuánto dura un tema, que es de lo más interesante que este dataset puede medir.

**Cómo se llegó ahí, para no repetir los callejones sin salida:**

1. Etiqueta libre por pregunta: **funciona** (17/20 a la primera; las 3 que fallaron eran repreguntas que no se sostienen solas, y con su contexto salieron). Pero da ~22 mil cadenas únicas: sirve para navegar, no para tabular.
2. **Agrupar con embeddings locales: FALLÓ.** Con las etiquetas, el grupo mayor se tragó el 23%; con las preguntas completas, el 59%. Todas estas frases son "asunto gubernamental en español" y la distancia coseno no distingue seguridad de infraestructura dentro de un mismo campo semántico. **No reintentar esto para temas.** Ojo: eso también matiza la fase 7 —los embeddings ahí probablemente sí sirvan porque `Diario 24 Horas` / `24 Horas` son paráfrasis, que es lo que estos modelos hacen bien— pero ya no darlo por sentado sin medir.
3. **Inducir la taxonomía con el modelo: FUNCIONÓ.** 18 categorías, cero "otros", 47 segundos con flash. Abstraer temas es lo que un LLM hace bien y la distancia coseno no.
4. **Convergencia de asuntos:** en muestra dispersa en 23 meses solo el 9% cae en un asunto repetido; **en un mes completo sube a 38%, y a 42% fusionando casi-duplicados.** La prueba dispersa estaba mal diseñada: preguntas de años distintos no pueden compartir caso.

**Dónde está todo:**

| ruta | qué es |
|---|---|
| `src/estenograficas/temas_dos_niveles.py` | el módulo: clasificar, consolidar, reconstruir |
| `src/estenograficas/temas.py` | etiqueta libre (el primer intento, sigue sirviendo) |
| `scripts/clasificar_temas.py` | corre el corpus. **Reanudable** |
| `scripts/reconstruir_temas.py` | rearma el jsonl desde el checkpoint, sin API |
| `data/interim/taxonomia_temas_candidata.json` | las 18 categorías con nombre humano y de máquina |
| `data/interim/temas_dos_niveles.jsonl` | la salida |
| `data/interim/vocab_asuntos.json` | memoria de asuntos entre corridas |
| `data/interim/temas_muestra_200.jsonl` | las 190 etiquetas libres de la prueba |
| `data/checkpoints/temas_dos_niveles.*` | **la fuente de verdad** |

**Para retomar:**

```bash
python scripts/clasificar_temas.py     # retoma desde el checkpoint, no repaga lo hecho
python scripts/reconstruir_temas.py    # SIEMPRE al terminar
```

**Por qué existe la reconstrucción.** El checkpoint hace `fsync` por renglón; el `.jsonl` se vacía cada 50. Medido: 12 renglones de desfase. Al reanudar se saltarían por estar en `procesados()` y **faltarían para siempre**. El checkpoint guarda `categoria` y `asunto` —lo que cuesta dinero— y el fragmento se recupera de `hilos.jsonl` gratis.

**Universo que se está clasificando: 12,299 preguntas, no 22,282.** El filtro toma solo las de 120 a 1,500 caracteres. **Esa decisión se heredó de una prueba y no está pensada:** hay preguntas reales de menos de 120 caracteres. Hay que decidir si se clasifica esa cola o se declara fuera del universo de análisis, y decirlo en la metodología. Costo estimado con el filtro actual: ~$2.50 USD y algo más de una hora.

**Pendientes de esta línea:**

- Correr la consolidación (`consolidar()`) cuando termine, y **mostrarle al humano los grupos grandes para que los apruebe**.
- Decidir la cola de preguntas cortas.
- Un asunto salió con una palabra en inglés (`Impunity Alejandro Moreno Cárdenas`). Vigilar si se repite.
- Los porcentajes estimados de la taxonomía **no sirven**: el modelo estimó 6% para relaciones internacionales y en mayo de 2026 fueron 16.5%. No es defecto de la taxonomía, es que la agenda cambia mes a mes — que es justo lo que hay que medir.



### Resumen temático por pregunta (`temas.py`)

Pedido por el humano el 2026-08-23. `src/estenograficas/temas.py` le pide a Gemini una etiqueta de 5 a 10 palabras por pregunta. Uso acotado según la regla dura 4: el modelo ve una pregunta, nunca el documento. Cada resumen lleva `metodo`, `modelo` y el fragmento exacto que se le mandó.

**El prompt prohíbe explícitamente calificar la pregunta** —nada de "cuestiona", "critica", "insiste", "dura", "blanda"— y exige frase nominal. La razón no es estética: si el resumen califica y algún día aparece junto a la pregunta en una hoja de codificación, ancla al humano en el campo que más importa.

**Probado sobre las 20 de la hoja de ejemplo.** 17 de 20 salieron a la primera. Las 3 que devolvieron `SIN TEMA` no estaban rotas: **no se sostienen solas**. Son repreguntas que dependen del turno anterior (`"…por eso le preguntaba"`, `"¿Y habría este reconocimiento?"`), y dos de las tres el humano las había marcado `insistencia = sí`. Mandándolas **con su contexto inmediato** —que la regla dura 4 también permite— las 3 salieron bien.

**Implicación para la fase 11, que vale más que el resumen mismo:** si una fracción de las preguntas no es autocontenida, el clasificador tampoco puede verlas solas. El plan ya decía "una pregunta con su contexto inmediato"; ahora hay una razón medida para que así sea.

**Un error real en 3 de 3 revisadas a mano:** el resumen de `2025-05-15-h5-t96` dice "información solicitada a Biden" cuando el texto dice que **Biden se la pidió a ella**. Dirección invertida. **Estas etiquetas sirven para navegar, no son dato analizable**, y quien las use tiene que saberlo.

**Volumen si se corre sobre todo el corpus:** 22,282 preguntas, ~1.98 M tokens de entrada y ~267 K de salida. Es mucho menos que la clasificación de la fase 11, que son las mismas preguntas por 3 corridas con un prompt largo.

**Decidido:** se corre **después** de que el humano codifique las 150, para que ninguna versión de la hoja de codificación lo lleve.

### Material de terceros en `assets/`

El humano compartió el 2026-08-23 un archivo externo, `assets/Ranking_medios_mananeras_ene-jun_2026.xlsx`, con la instrucción de que **nunca se publique ni se comparta**. No se identifica aquí a su autoría, a propósito: nombrarla en un archivo versionado sería exactamente la fuga que se está evitando.

**Estaba dentro del repo y NO estaba en `.gitignore`.** Nunca llegó a commitearse —se verificó con `git log --all -- assets/`—, pero estaba a un `git add -A` de distancia, y esta sesión corrió `git add -A` muchas veces. **Ya se ignoró el directorio `assets/` completo**, que también contiene `Línea de tiempo sucesos.xlsx`. Verificado con `git check-ignore`.

Regla permanente, escrita también en `README.md`: se lee localmente para contrastar, no entra a ningún commit ni a ningún archivo derivado que se publique.

### Contraste con un conteo manual externo

Su archivo está bien documentado: fuente, unidad de conteo, unificaciones de marca aplicadas, y qué medios decidió **no** unificar. Cubre enero–junio de 2026, canonicalizado a mano, agrupando por reportero.

| | ella | nosotros |
|---|---|---|
| intervenciones (ene–jun 2026) | **752** | **521** |
| medios | 188 (canonicalizados) | 192 cadenas crudas |
| periodistas | — | 164 |

**Nos faltan 231 intervenciones, el 31%.** Ese hueco es el mejor dato que hay del proyecto ahora mismo, porque es una **medición externa de nuestra cobertura de identificación**: nuestro regex solo levanta al periodista que se autopresenta de forma reconocible, y ella los identificó a mano. Es exactamente lo que la fase 7 tiene que cerrar con el modelo sobre los turnos que el regex no resuelve.

Ojo al interpretar el 31%: **no se puede atribuir todo a falta de recall todavía.** Su unidad es "una intervención por fecha y turno de pregunta de cada medio" y la nuestra es el hilo; si dos periodistas del mismo medio hablan el mismo día, puede que cuenten distinto. Descomponer ese hueco —cuánto es recall y cuánto es definición de unidad— es tarea de la fase 7.

En el top la forma coincide razonablemente: Heraldo Media Group y Noticiero en Redes empatados arriba, luego Contralínea y Revista Fortuna. Revista Fortuna cuadra exacto (20 y 20). Las diferencias grandes (`Diario Basta`, `Grupo Imagen (Excélsior)`) son en parte de mi agrupación burda, no necesariamente datos faltantes.

**Cómo se usa, decidido:** como **validación posterior**, nunca como insumo. Si construimos nuestra canonicalización copiando la suya, coincidir deja de ser evidencia de nada. Es la misma lógica que la codificación a ciegas y que los embeddings locales de la fase 12.

### Segundo contraste externo (2026-08-28): las tandas coinciden 10 de 10

La misma fuente compartió un segundo conteo, ahora sobre **todo el periodo**, por medio y por periodista. Está en `assets/orientacion_externa_2026-08-28.csv` y el cotejo completo en `assets/cotejo_conteos_2026-08-28.md`. **Ambos están en `.gitignore` y no se citan con atribución en ningún lado.**

**El resultado fuerte: las tandas coinciden exactamente en los 10 periodistas.** Nancy Flores 64 y 64, Hans Salazar 64 y 64, Yareth Arciniega 57 y 57, Carlos Navarro 54 y 54, Arturo Pavón 51 y 51, Carlos Guzmán 48 y 48, Yusbel Carolina 44 y 44, Karina Aguilar 36 y 36, Liliana Noble 35 y 35, Zeltzin Juárez 34 y 34. Diez de diez, sin una diferencia.

Es la mejor validación externa que tiene el parser. Confirma tres cosas caras: que los hilos se cortan donde deben, que la identidad se propaga bien dentro del hilo, y que la canonización de **nombres de persona** no está partiendo a nadie en dos.

**Las preguntas no coinciden, pero el hueco está acotado.** Sobre esos mismos 10: nosotros 4,751 limpias, ella 5,071, nosotros 5,383 si contamos los turnos marcados `ruido`. **Su número cae dentro de nuestro rango, casi al centro.** La diferencia no es de segmentación —las tandas son idénticas— sino de qué cuenta como pregunta: filtramos saludos, interjecciones del pleno e `INTERVENCIÓN:`. No hay nada que arreglar; sí hay que **declarar el criterio en el README**, porque cualquiera que cuente va a llegar a otro número por esta razón y no por un error. Ya se declaró.

**Las dos discrepancias por medio son de canonización, en los dos lados.** Sus 41 tandas de `Heraldo Media Group` son la cadena literal; el corpus además trae `El Heraldo Media Group` (18) y `El Heraldo de México` (4), que nosotros sí juntamos: ahí nuestro número está mejor. Y su tabla reporta 32 tandas para Quatro Media pero 48 para Carlos Guzmán, cuyo medio más frecuente es ése: **su propia tabla es inconsistente consigo misma**, por las 11 grafías del medio. Conclusión práctica: la canonización de medios no se resuelve consultando a alguien que conoce la fuente, porque tropieza con lo mismo.

### El segundo archivo trae además valoraciones: qué se puede y qué no

Además de conteos, ese archivo contiene **valoraciones sobre personas identificadas por su nombre**. Qué son exactamente está escrito en el encabezado del propio archivo, en `assets/`, que es donde tiene que quedarse. **No se describen aquí**: este archivo sí se publica.

**Reglas, no negociables:**

1. **No sale del repo local.** Ni al README, ni a un artefacto, ni a un commit, ni a una figura, ni parafraseado. `assets/` está ignorado y ahí se queda. Los conteos de ese archivo sí se pueden usar para cotejar; las valoraciones no salen.
2. **No es la muestra de oro y no la sustituye.** La muestra de oro se codifica pregunta por pregunta, a ciegas y **sin ver medio ni periodista** (regla metodológica 2). Esto es lo contrario: un juicio sobre la persona, hecho sabiendo quién es. Son instrumentos distintos midiendo unidades distintas.
3. **No se usa para entrenar, ni para ajustar el prompt, ni para elegir umbrales.** Eso sería entrenar contra la validación (regla 4).
4. **No se hereda hacia las preguntas.** Una valoración sobre una persona no se le aplica a cada una de sus preguntas; medir esa distribución **es** el objeto del proyecto, y etiquetar por herencia asumiría la conclusión.
5. **No se reporta alfa de Krippendorff contra esto.** Su unidad es la persona; la nuestra, la pregunta.

**Para qué sí sirve, y es valioso:** como **comparación externa registrada de antemano**. Se guardó el 2026-08-28, antes de que exista una sola clasificación de `postura`, para poder contrastarla al final sin haberla mirado en el camino. **Lo interesante será el desacuerdo**, no la coincidencia: los casos donde la medida pregunta por pregunta se aleje de la reputación son el hallazgo, igual que el conjunto de discrepancias de la fase 10.

Y la advertencia de siempre: el proyecto **mide y describe, no adjetiva** (regla 8). Publicar una valoración de tercero sobre periodistas con nombre y apellido sería justo lo contrario.

### Codificación a ciegas: redacción aprobada e implementada

El humano aprobó el 2026-08-23 la **opción 1**: tachar la autopresentación dentro del texto de la pregunta y dejar `[identificación removida]`, en vez de excluir del muestreo las preguntas que abren hilo.

Implementado en `parser.redactar_identificacion()`, con 4 pruebas, incluida una que barre todas las preguntas `declarada` de la conferencia de muestra y verifica que ni el nombre ni el medio queden a la vista. Reemplaza solo la oración de presentación, no el turno, así que la pregunta se conserva y no se pierde la categoría de preguntas de apertura.

Alcance del problema: **2,149 preguntas, el 10% del total**, dicen el medio dentro de su propio texto.

**Falta:** la hoja real de la fase 9 todavía no existe. Hay una de ejemplo, con seis preguntas reales, en `data/gold/EJEMPLO_hoja_de_codificacion.xlsx`, con las cuatro columnas del libro de códigos como menú desplegable. **Esas seis preguntas quedan excluidas de la muestra de oro** porque el humano ya las vio; sus ids están en el commit correspondiente.

### La etiqueta de hablante se rompía de TRES formas, ya arregladas

Lo encontró el humano codificando la hoja de ejemplo: dos de seis preguntas venían "mal cortadas". No era un problema de presentación sino de segmentación.

`_ETIQUETA` exigía dos puntos seguidos de espacio, y el corpus trae tres variantes que rompen eso, las tres silenciosas:

1. `PREGUNTA:\xa0Bien.` — espacio duro. Ya estaba resuelto normalizando antes de segmentar.
2. **`...CLAUDIA SHEINBAUM PARDO:Ah, ok.`** sin espacio tras los dos puntos, y `...PARDO :—` con espacio antes. **271 turnos afectados, 253 de ellos de prensa: la respuesta del gobierno quedaba metida dentro de la pregunta del periodista.** No corrompe la lectura, corrompe la unidad de análisis.
3. `SECRETARIO DE SALUD, DAVID KERSHENOBICH (enlace videollamada):` — paréntesis en minúsculas, fuera del juego de caracteres. 35 turnos.

Arreglado con un solo regex que admite espacio opcional antes y después de los dos puntos y un paréntesis final de cualquier caja, con `(?!//)` para no tragarse un `HTTPS://`.

**Efecto medido sobre las 460:** turnos 64,726 → 65,092; turnos con etiqueta pegada adentro **271 → 0**; hilos 2,149 → 2,148. **Los turnos de prensa siguen siendo 27,278**, que es justo lo que debía pasar: no aparecieron preguntas nuevas, lo que se fue es la respuesta del gobierno que traían pegada.

### Parseo masivo (fase 6) — CORRIDO. **ESPERANDO REVISIÓN DEL HUMANO.**

`src/estenograficas/parseo.py`. Se corre con `python -m estenograficas.parseo`. **460 conferencias parseadas, 0 rechazadas.**

| archivo | renglones |
|---|---|
| `data/interim/turnos.jsonl` | 64,726 |
| `data/interim/hilos.jsonl` | 2,149 |
| `data/interim/conferencias.jsonl` | 460 |

Turnos de prensa: 27,278. **Preguntas útiles, sin ruido: 22,307.** Ese es el tamaño real del universo a clasificar.

Nota sobre idempotencia: esta etapa **reescribe los tres archivos en cada corrida** en vez de ir agregando. Parsear las 460 toma un minuto, así que reanudar no ahorra nada, y agregar sobre un archivo viejo dejaría renglones de una versión anterior del parser mezclados con los nuevos. Correrla dos veces da el mismo resultado, que es lo que pide la regla dura 2.

#### El arreglo de videos que hubo que revertir

Al ver 86 `VOZ MUJER` sobrevivientes conté los marcadores reales del corpus: 431 `(INICIA VIDEO)` contra 475 cierres, más ~160 `(PROYECCIÓN DE VIDEO …)`. Parecía obvio que `PROYECCIÓN DE VIDEO` era una apertura y la agregué.

**Lo medí antes de darlo por bueno y estaba mal: borraba 787 turnos, 239 de ellos de prensa.** `(PROYECCIÓN DE VIDEO)` suele ser una marca suelta sin cierre propio, así que el bloque se comía todo hasta el siguiente `(FINALIZA VIDEO)`, que puede estar mucho más adelante. Revertido, con el porqué escrito en el código para que nadie lo reintente.

Lo que sí quedó: los cierres ahora reconocen `FINALIZA`, `FINALIZAN`, `CONCLUYE` y `TERMINA`, y `AUDIO` además de `VIDEO`. 438 bloques quitados contra 431 antes, con un costo de 2 turnos de prensa que estaban dentro de bloques de video.

#### Diagnóstico obligatorio: lo que tienes que revisar

**986 etiquetas de hablante únicas. 433 aparecen una sola vez.** La mayoría son funcionarios y beneficiarios reales con el cargo escrito distinto cada día, pero ahí adentro hay errores.

**1. `PREGUNTA (VIDEOLLAMADA)`, 36 turnos.** Es prensa preguntando por videollamada y el parser la cuenta como **funcionario**, porque no está en la lista de etiquetas de prensa. Es el mismo tipo de error que `INTERLOCUTOR` y hay que arreglarlo. Recomendación: tratar cualquier etiqueta que empiece con `PREGUNTA` como prensa.

**2. Variantes de la etiqueta de la presidenta, siete formas para la misma persona:**

| turnos | etiqueta |
|---|---|
| 27,687 | `PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO` |
| 815 | `PRESIDENTA CLAUDIA SHEINBAUM PARDO` |
| 12 | `PRESIDENTA DE MÉXICO CLAUDIA SHEINBAUM PARDO` |
| 3 | `RESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO` (sin la P) |
| 1 | `PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PADO` (PADO) |
| 1 | `CANDIDATA A LA PRESIDENCIA DE MÉXICO, CLAUDIA SHEINBAUM PARDO` |
| 1 | `CLAUDIA SHEINBAUM PARDO` |

Las tres últimas son erratas de la transcripción, no hablantes distintos.

**3. Variantes del ruido de sala que no están cubiertas:** `INTERVENCIÓN HOMBRE` (12), `INTERVENCIÓN MUJER` (7), `INTERVENCIÓN MUJER (ENLACE VIDEOLLAMADA)` (8). Son la misma cosa que `INTERVENCIÓN`, que sí está cubierta.

**4. Contaminación de video que sobrevive: 269 turnos en 62 conferencias.** `VOZ MUJER` (68), `VOZ HOMBRE` (61), `VOZ DE MUJER` (10), `VOCES A CORO` (6), `NIÑA` (12), `NIÑO JULIÁN` (7), más los `BENEFICIARIA DEL PROGRAMA…`. Todas caen como `anonimo`, así que **no ensucian el conteo de prensa**, pero sí están en el flujo de turnos. Vienen de los bloques que abren con `PROYECCIÓN DE VIDEO` y no se pueden quitar sin el destrozo descrito arriba. **Decisión tuya:** filtrarlos por etiqueta en vez de por bloque, o dejarlos como `anonimo` y excluirlos en el análisis.

**5. `(ENLACE VIDEOLLAMADA)` aparece 818 veces y NO lo trato como video.** Es gente participando a distancia —gobernadoras, beneficiarios— que sí habla en la conferencia. Confírmame que es la lectura correcta.

**6. Tema del día: 49% (224 de 460).** Y la calidad de lo que extrae el regex es despareja. Bien: `salud`, `seguridad`, `el informe quinquenal de salud`. Mal: `casa llena`, `tres temas`, `estos cuatro temas y luego pasamos a las preguntas`. **El campo sirve para agrupar a grandes rasgos pero no está listo para cruzarlo en el análisis final**; probablemente necesite el modelo sobre el fragmento de apertura, que es un uso acotado y legítimo según la regla dura 4.

**7. Siete conferencias sin ningún hilo**, ahora con detalle:

| fecha | turnos | de prensa |
|---|---|---|
| 2025-10-03 | 18 | **0** |
| 2026-05-29 | 31 | 2 |
| 2025-05-21 | 94 | 4 |
| 2024-12-18 | 88 | 12 |
| 2026-05-20 | 76 | 19 |
| 2025-04-02 | 69 | 29 |
| 2025-04-07 | 94 | 32 |

La de 2025-10-03 con 0 turnos de prensa probablemente no es una mañanera. Las de abajo sí tienen prensa y ningún periodista se autopresentó de forma reconocible: ahí hay hilos que se están perdiendo.

**Los 10 turnos al azar del diagnóstico salieron limpios**, con etiqueta y tipo correctos, incluido un `VOZ HOMBRE` marcado `anonimo`. La salida completa del diagnóstico se regenera corriendo la etapa.

### Descarga del corpus (fase 5) — TERMINADA

**460 conferencias en `data/raw/`, 75 MB, del 2024-10-03 al 2026-08-20. Tasa de éxito 99.6%** (460 de 462 procesadas). Las **460 salieron de gob.mx**; Wayback no tuvo que entrar como respaldo ni una vez.

**Los 2 "rechazos" no son fallos.** Los dos dicen `ya existe X.html; el crudo no se sobreescribe`, o sea que la regla de inmutabilidad hizo su trabajo:

- El slug con el año truncado (`-del-30-de-marzo-de-202`) resultó ser un duplicado de `2026-03-30`, que ya se había bajado por su URL buena.
- **La conferencia de Culiacán resultó ser la misma del 2025-07-11**, publicada bajo dos URLs. Corrijo lo que dije antes: no era una conferencia distinta que faltara, era una entrada duplicada. Se descubrió justo porque la fecha se saca del contenido.

**Sacar la fecha del contenido en vez del slug recuperó dos conferencias.** Dos slugs mienten sobre su propia fecha, y el contenido dice `2024-10-28` y `2026-03-18`. **Las dos estaban en la lista de días sin conferencia de la fase 4**, o sea que se habrían dado por perdidas. Es exactamente lo que `CLAUDE.md` advertía al prohibir construir slugs por fecha.

**Cobertura final: 93.7%** de los días hábiles entre el 2024-10-03 y el 2026-08-20 (460 de 491). Los 31 restantes son los festivos ya identificados en la fase 4.

**Verificación de punta a punta.** El parser corre contra las 460 sin una sola excepción:

| | |
|---|---|
| turnos totales | 64,975 |
| turnos de prensa | **27,280** |
| hilos | 2,140 |
| promedio por conferencia | 141 turnos, 59 de prensa, 4.7 hilos |

**Ese 27,280 corrige una estimación del plan.** `CLAUDE.md` dice "del orden de 10 mil turnos de pregunta"; son casi el triple. Buena parte serán ruido y repreguntas cortas, pero **la estimación de costo de la fase 11 hay que rehacerla sobre este número**, no sobre 10 mil.

**7 conferencias quedan sin ningún hilo** y hay que mirarlas en la fase 6: `2024-12-18`, `2025-04-02`, `2025-04-07`, `2025-05-21`, `2025-10-03`, `2026-05-20`, `2026-05-29`. Ninguna truena; simplemente ningún periodista se autopresentó de forma reconocible. La más chica del corpus es `2026-05-29` con 92 KB.

**El checkpoint pasó su prueba en producción.** A mitad de la descarga maté el proceso a propósito (por una falsa alarma de encoding). Al relanzarlo retomó sin rehacer nada y sin una sola línea truncada. Eso ya no es un test, es el caso real.

### Dos cambios de formato de 2024, encontrados al mirar lo descargado

No son de la descarga sino del parser, y son los más caros hallados hasta ahora. Salieron de correr el parser contra las primeras 90 conferencias bajadas, no de leer código.

**1. `INTERLOCUTOR` e `INTERLOCUTORA` son etiquetas de PRENSA.** Es la forma que se usó antes de estandarizar `PREGUNTA`: **421 turnos en 18 conferencias, todas entre el 3 y el 29 de octubre de 2024**. El parser las tomaba como funcionario, es decir que **convertía preguntas de periodistas en declaraciones de gobierno**. Es el peor error posible en un proyecto que mide qué pregunta la prensa, y no habría dado ningún síntoma: el pipeline corría, los archivos salían bien formados, y octubre de 2024 simplemente parecía un mes en que la prensa casi no preguntaba.

Efecto de la corrección: 2024-10-03 pasa de 11 a **33** turnos de prensa; 2024-10-08 de 16 a **52**.

**2. El orden de la etiqueta se invierte según el año.** En 2026 es `CARGO, NOMBRE`; en octubre de 2024 es `NOMBRE, CARGO` (`CITLALLI HERNÁNDEZ MORA, SECRETARIA DE LAS MUJERES`). Sobre las primeras 90 conferencias: **116 al derecho contra 60 al revés**, más 31 ambiguas. Un `rsplit(",", 1)` a ciegas intercambia cargo y nombre en un tercio de los funcionarios. Ahora se orienta por **cuál de los dos lados nombra un cargo**, no por la posición; ante la duda se respeta el orden dominante.

También: `ASISTENTES` pasa a ruido de sala, es el pleno coreando.

**Falsa alarma que conviene dejar registrada.** Creí ver mojibake en los archivos descargados y detuve la descarga a medias para investigarlo. No lo hay: los acentos vienen como entidades HTML (`&Oacute;`), BeautifulSoup los resuelve bien, y lo que se veía mal era la consola de Windows al imprimir. Los 464 archivos están en UTF-8 limpio. El susto sirvió para una cosa: **el checkpoint sobrevivió a que matara el proceso a mitad de la descarga**, que es exactamente la prueba que la fase 1 montó y esta vez pasó en producción, no en un test.

**Pendiente relacionado, para la fase 6:** hay tres formas distintas de la etiqueta de la presidenta —`PRESIDENTA CLAUDIA SHEINBAUM PARDO` (742 turnos), `PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO` y `PRESIDENTA DE MÉXICO CLAUDIA SHEINBAUM PARDO` sin coma—. Son la misma persona y hay que unificarlas.

### Descubrimiento de URLs (fase 4) — TERMINADA

`src/estenograficas/descubrimiento.py` completo, con `tests/test_descubrimiento.py` (20 pruebas). **98 pruebas en total, 98 pasan.**

Se corre con `python -m estenograficas.descubrimiento`. Reanudable: el recorrido del archivo usa el módulo `checkpoint`, una entrada por página, así que si se interrumpe no vuelve a pedir lo ya hecho.

**Salida: `data/interim/urls.jsonl`, 464 URLs.**

| | |
|---|---|
| de gob.mx | 462 |
| de Wayback | 2 |
| sin fecha en el slug | 4 |
| días hábiles del sexenio | 494 |
| días cubiertos | 459 |
| **cobertura** | **92.9%** |

El recorrido tomó 110 páginas y no dio ni un error. Wayback aportó exactamente 2 fechas que gob.mx no tenía: ese es el papel de respaldo funcionando, y justifica haber conservado la estrategia mixta aunque gob.mx resultara casi completo.

**Conteo por mes:** entre 17 y 23 conferencias mensuales, sin ningún mes anómalo. Los extremos bajos son diciembre de 2025 (17) y noviembre de 2024 y 2025 (18); el alto es julio de 2025 y 2026 (23). Agosto de 2026 va en 14 porque el mes no ha terminado.

**Los 35 días hábiles sin URL son casi todos festivos identificables**, no conferencias perdidas: 24, 25 y 31 de diciembre y 1 de enero de los dos años; Semana Santa (17-18 de abril de 2025, 2-3 de abril de 2026); 15 y 16 de septiembre; 5 de febrero; 18 de marzo; 20 de noviembre; 5 de mayo; 1 y 2 de octubre de 2024, que son anteriores a la primera conferencia (3 de octubre); y el 21 de agosto de 2026, que es hoy.

Quedan **como una docena sin explicación obvia** y hay que mirarlos en la fase 6: 2024-10-28, 2024-11-18, 2024-11-19, 2024-12-12, 2025-06-16, 2025-06-17, 2025-09-01 (día del Informe), 2025-11-10, 2025-12-05, 2025-12-12 y 2026-04-17. Pueden ser giras, puede ser que la conferencia exista bajo otro slug.

**Las 4 URLs sin fecha en el slug:**

- Tres son el mismo `-del-30-de-marzo-de-202`, con el año truncado, y vienen de Wayback con statuscode 301. Esa fecha ya está cubierta por otra URL, así que son redirecciones duplicadas.
- Una es real y distinta: **`...-de-la-presidenta-de-mexico-claudia-sheinbaum-pardo-en-culiacan-sinaloa`**. Una conferencia fuera de Palacio Nacional, con un patrón de slug sin fecha. Su `conferencia_id` tiene que salir del contenido en la fase 5. Confirma que no se podían construir slugs por fecha.

**497 versiones estenográficas descartadas** por no ser conferencia matutina —derecho de réplica, giras, eventos—. No se tiraron en silencio: quedaron listadas en `data/interim/otras_estenograficas.txt` por si alguna resulta relevante.

### Playwright contra gob.mx: reconocimiento

Aprobado e instalado el 2026-08-21: `playwright` más Chromium (114.5 MB). **Funciona, pero con una condición que cambia el plan.**

**Headless NO pasa el reto anti-bot. Headful sí, en 1.7 segundos.**

| intento | resultado |
|---|---|
| curl con cabeceras de navegador completas | 1,838 bytes de `Challenge Validation` |
| Playwright `headless=True`, espera 6 s | reto |
| Playwright `headless=True`, espera 50 s + parches anti-detección (`navigator.webdriver`, `plugins`, `languages`, `window.chrome`) | reto |
| **Playwright `headless=False`** | **174 KB, `article-body` presente, 65 `PREGUNTA`, sin reto, 1.7 s** |

Consecuencia práctica: la descarga abre un navegador de verdad. **Se puede mandar fuera de pantalla** con `--window-position=-2400,-2400 --window-size=1280,900`, probado y funciona, pero el proceso no puede correr en un servidor sin escritorio. Si algún día se mueve a uno, esto se rompe.

**La sesión aguanta.** Cinco conferencias seguidas en un mismo contexto, una por segundo: 200 en todas, entre 0.7 s y 1.7 s cada una, sin que el reto vuelva a aparecer. No hace falta reabrir el navegador por página.

**El archivo paginado es mucho más chico de lo que se temía.** `https://www.gob.mx/presidencia/archivo/articulos?order=DESC&page=N`, 9 artículos por página y 4 o 5 conferencias por página. Se hizo búsqueda binaria del final:

- página 1 → 17-20 de agosto de 2026
- página 60 → 13-18 de agosto de 2025
- página 90 → 7-10 de febrero de 2025
- página 105 → 21-25 de octubre de 2024
- **página 108 → 3-4 de octubre de 2024, y es la última con contenido** (109 en adelante vienen vacías)

La página 108 cae justo en el inicio del sexenio. **El archivo completo se recorre en 108 páginas, unos dos minutos a un request por segundo**, y contiene del orden de 440 conferencias.

**Esto invierte la estrategia.** El plan mixto se decidió cuando parecía que gob.mx era caro de recorrer. No lo es: gob.mx conviene como fuente **principal** de descubrimiento —da la URL canónica, cubre todo el sexenio y es rápido— y Wayback pasa a ser el **respaldo** para lo que gob.mx no dé o para cuando bloquee. Sigue siendo mixto, pero con los papeles al revés. La medición de Wayback no se desperdicia: es exactamente el respaldo que hace falta y ya está cuantificada.

### Medición de la cobertura de Wayback (previa a la fase 4)

Pedida por el humano el 2026-08-21 para decidir cómo bajar el corpus. **Ojo al leer esta sección: sigue siendo válida como medición, pero el reparto que propone quedó invertido** por lo que se descubrió después con Playwright (sección de arriba). Wayback es el respaldo, no la base.

**1,221 capturas** de la API CDX bajo el prefijo `version-estenografica-conferencia-de-prensa-de-la-presidenta-claudia-sheinbaum-pardo-del-`, entre octubre de 2024 y agosto de 2026. De ahí: 352 fechas con alguna captura, **50 fechas donde Wayback SOLO tiene capturas 4xx/5xx**, y **302 fechas utilizables**.

**Cobertura global: 61.1%** (302 de 494 días hábiles). Pero el promedio esconde lo único que importa, que es *cuándo* falta:

| tramo | días hábiles | en Wayback | falta | cobertura |
|---|---|---|---|---|
| 2024-10 a 2026-01 | 336 | 267 | 69 | **~80%** |
| 2026-02 a 2026-08 | 158 | 35 | 123 | **~22%** |

Mes a mes, de octubre de 2024 a enero de 2026 la cobertura va entre 65% y 95%. **A partir de febrero de 2026 se desploma:** 35%, 14%, 9%, 19%, 14%, 4%, 13%. Es el rezago normal de rastreo del archivo: lo reciente todavía no está archivado.

Consecuencia para el plan: **de gob.mx hay que bajar como máximo 192 conferencias**, de las cuales 123 son de los últimos siete meses. No 460. Wayback carga con el 61% y con casi todo lo viejo.

**Dos errores míos de medición, corregidos, porque el número cambió con cada uno:**

1. Filtrar `statuscode:200` en la consulta CDX tira las capturas *revisit* (`-`), que sí tienen contenido.
2. `collapse=urlkey` devuelve **una** captura por URL, y a veces devuelve un 404 aunque exista un 200 de la misma página.

Los dos subestimaban, de formas distintas. La medición buena no colapsa: trae todas las capturas y cuenta una fecha como cubierta si tiene al menos una captura que no sea 4xx ni 5xx.

**Advertencias sobre este número:**

- **192 es cota superior de lo que falta.** Parte de esos días hábiles simplemente no tuvieron conferencia: días festivos, giras, Semana Santa. Cuántos exactamente no se sabe hasta poder listar el propio archivo de gob.mx.
- Las fechas salen del **slug**, y `CLAUDE.md` advierte que traen erratas. Se confirmó: hay slugs con año truncado (`-de-202`), con backslash pegado (`%5C`) y con sufijo numérico (`-421610`). Uno de ~500 quedó ilegible. La fecha canónica tiene que salir del contenido, no del slug.
- Se buscó bajo un solo patrón de slug. Existen otros (`conferencia-de-prensa-matutina`, `del-presidente-andres-manuel-lopez-obrador`), pero corresponden a otras cosas o al sexenio anterior.

### Parser contra varios años (fase 3)

Cuatro conferencias nuevas en `fixtures/`, más la que ya estaba: **2024-11-11, 2025-07-02, 2026-02-03, 2026-08-04 y 2026-08-18**. Dos de 2026 a petición del humano, separadas medio año, porque el formato también puede cambiar dentro del mismo año. **78 pruebas, 78 pasan.**

**gob.mx no se deja descargar.** Responde HTTP 200 con una página de `Challenge Validation` de 1.8 KB —JavaScript anti-bot— en vez del contenido. Se probó con cabeceras de navegador completas (User-Agent de Chrome, `Accept-Language`, `Sec-Ch-Ua`, `Sec-Fetch-*`, `--compressed`) y responde lo mismo. **Los cinco fixtures vienen de la Wayback Machine**, que sí funciona y tiene capturas de las tres temporadas. Esto no era un supuesto del plan y cambia las fases 4 y 5.

**Cuatro defectos reales encontrados, ninguno parchado con caso especial:**

1. **La estructura del HTML cambió en 2025.** En 2024 los `<p>` cuelgan directo de `div.article-body`; desde 2025 el CMS los envuelve en `<div>`. Mi extractor miraba solo hijos directos, así que **tres de las cuatro conferencias se parseaban como UN turno y cero hilos, sin lanzar ningún error**. Es el modo de falla más peligroso del proyecto: silencioso y con salida bien formada. Corregido con búsqueda recursiva.
2. **Espacio duro tras la etiqueta.** En 2025-07-02 hay un `PREGUNTA:` seguido de `\xa0`. La etiqueta no casa y **el turno de prensa se funde con el de la presidenta**, quedando atribuido a ella. Uno en cinco conferencias; extrapolado, decenas en el corpus. Se normalizan los espacios Unicode antes de segmentar.
3. **Muletillas de presentación.** `Soy Aissa García, de Telesur` producía el nombre "Soy Aissa García". Peor: `Su servidor, Carlos Pozos, de LM Noticias` no se detectaba en absoluto porque el nombre no arranca la oración, y **se perdía el hilo entero de ese periodista**. Con las muletillas contempladas, 2026-02-03 pasó de 4 a 5 hilos.
4. **Descarga en gzip.** Una de las cuatro capturas venía comprimida y curl la guardó cruda; 49 KB de binario que el parser habría rechazado. Trivial de arreglar aquí, pero la fase 5 tiene que manejarlo.

**Resultado tras las correcciones:**

| conferencia | turnos | hilos | prensa | video | apartes |
|---|---|---|---|---|---|
| 2024-11-11 | 73 | 5 | 30 | 0 | 6 |
| 2025-07-02 | 182 | 5 | 71 | 0 | 22 |
| 2026-02-03 | 195 | 5 | 79 | 0 | 23 |
| 2026-08-04 | 167 | 4 | 75 | 2 | 27 |
| 2026-08-18 | 159 | 4 | 65 | 3 | 32 |

**Diagnóstico que pedía la fase 3, qué etiquetas aparecen en unas y no en otras:**

- Compartidas por las cinco: solo dos, `PREGUNTA` (320 en total) y `PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO` (356).
- **`INTERVENCIÓN` aparece en 2025 y 2026 pero NO en la conferencia de 2024.** 10 ocurrencias en cuatro conferencias. Puede ser que la práctica de transcripción cambiara, o simple azar de la muestra; con una sola conferencia de 2024 no se puede afirmar. Vale la pena mirarlo en la fase 6.
- Las otras 40 etiquetas son `CARGO, NOMBRE` de funcionarios y cambian con quién acompaña a la presidenta ese día. No son cambio de formato.
- Una etiqueta **sin coma** y que no es ruido conocido: `GOBERNADORA INTERINA DE SINALOA YERALDINE BONILLA VALVERDE` (2026-08-04). Cargo y nombre sin coma de por medio, así que `rsplit(",", 1)` no los separa. Un caso en cinco conferencias; el diagnóstico de la fase 6 dirá si es sistemático.
- Cero contaminación de video en las cinco. El cierre `—000—` está en las cinco.

**Periodistas identificados:** 5, 5, 5, 4 y 4 respectivamente. Nancy Flores (Contralínea) aparece en febrero y en agosto de 2026 escrita igual en las dos, pero eso es suerte del muestreo y no evidencia contra la necesidad de la fase 7.


### Parser contra una conferencia (fase 2)

`src/estenograficas/parser.py` y `tests/test_parser.py`, sin red. **43 pruebas en total, 43 pasan** (24 nuevas del parser).

**La prueba de aceptación pasa:** los cuatro periodistas salen y son exactamente Nancy Rodríguez (Oro Sólido y de Empuje Migrante), Javier Tovar (Agencia France-Presse), Dalila Escobar (Proceso) y Hans Salazar (Noticiero en Redes). Cuatro hilos, ni uno más.

**Lo que costó: un regex ingenuo de `Nombre, de Medio` encuentra SEIS periodistas en esta conferencia.** Los dos de más son `Andrés Manuel López Beltrán, de encabezar una red de huachicol` —donde el `de` introduce un verbo, no un medio— y `Estados Unidos, de Cambridge Analytica`. No se arreglaron con una lista negra. La diferencia real es estructural: **la autopresentación es su propia oración**, empieza tras punto y termina en punto. Anclando el regex a límites de oración, y solo en los primeros 300 caracteres, quedan cuatro. Ya está documentado como trampa en `CLAUDE.md`.

**Trampa nueva encontrada: `—000—`.** Último párrafo del archivo, entero entre rayas, indistinguible en forma de un aparte fuera de micrófono. Es el cierre de boletín de Presidencia. Se colaba como aparte del último turno de la presidenta. Se quita antes de segmentar y solo si está al final. Documentada en `CLAUDE.md`.

**Segmentación, verificada por fuera del parser.** Los números de la prueba no salen del parser: se contaron con un `awk` independiente sobre el texto crudo, excluyendo bloques de video y partiendo por las líneas de las cuatro autopresentaciones (368, 508, 676, 940). Cuadra exacto.

| | turnos |
|---|---|
| exposición previa a la primera pregunta | 17 |
| hilo 0, Nancy Rodríguez | 22 |
| hilo 1, Javier Tovar | 12 |
| hilo 2, Dalila Escobar | 62 |
| hilo 3, Hans Salazar | 46 |
| **total** | **159** |

Preguntas no-ruido por hilo: 9, 6, 31 y 12.

**Trampas verificadas contra el fixture:**

- **Videos:** 3 bloques quitados, 0 aperturas sin cerrar, y **las 18 etiquetas contaminantes** (`VOZ MUJER`, `VOZ HOMBRE`, `DERECHOHABIENTE`, `MADRE DEL PACIENTE`) desaparecieron. Hay prueba aparte de que un video **sin cerrar** se reporta en vez de tragarse el resto del archivo.
- **`INTERVENCIÓN:`** 5 ocurrencias, 4 dentro del hilo de Hans Salazar, **ninguna partió un hilo**. Van con `atribucion: "incierta"` y `quien: null`.
- **Interjecciones del pleno:** una sola racha en toda la conferencia, de 3 turnos `PREGUNTA` consecutivos y cortos (31, 9 y 12 caracteres): "A lo mejor no la han informado" / "¿Quiénes?" / "¿De quiénes?". Los tres quedan inciertos y sin periodista. Hay prueba de que dos preguntas **largas** seguidas NO se marcan como interjección, que es el falso positivo que importa.
- **Apartes:** 32 extraídos a su campo y sacados del texto. Un inciso dentro de una oración (`—si me dan la siguiente—`) **no** se toca: la diferencia es ocupar el párrafo entero, y hay prueba de las dos caras.
- **Encabezado:** los 4 renglones de título y caption quedan aparte; el primer turno es la presidenta diciendo exactamente `Buenos días.`
- **Saludos:** filtrados por patrón de cortesía completa, no por longitud. `¿No se le censura?` es igual de corto y no se filtra.

**Atribución final de los 67 turnos de prensa en hilos:** 4 declarada, 56 propagada, 7 incierta. Ningún turno incierto trae periodista.


### Andamiaje (fase 1)

**Git.** `git init` con rama `main`. `.gitignore` se escribió **antes** que cualquier otra cosa, precisamente para que `.env` no pudiera colarse: `git check-ignore` confirma que está ignorado, y `git add -A --dry-run` lista 15 archivos entre los que **no** están `.env` ni `data/`. Hay una prueba automatizada (`test_el_env_esta_ignorado_por_git`) que falla si alguien lo saca del ignore.

**Estructura**, la de `CLAUDE.md`: `src/estenograficas/`, `tests/`, `notebooks/`, `fixtures/`, y `data/{raw,interim,gold,outputs,checkpoints}`. Los directorios de `data/` no viajan en git (están ignorados); los crea `paths().ensure_dirs()` en cada clon. Se agregó `.env.example` (vacío, versionado) y un `notebooks/README.md` que repite la regla de que ahí no va lógica.

**Paquete** `estenograficas` 0.1.0 instalado en editable (`pip install -e .`) contra `pyproject.toml` con layout `src`. Las dependencias **no** se declaran en `pyproject.toml` a propósito: la fuente de verdad del ambiente es `environment.yml`, y declararlas en los dos lados garantiza que se desincronicen.

`environment.yml` exportado con `--no-builds`. Se le quitó la línea `prefix:`, que filtraba la ruta absoluta de esta máquina y no sirve para reproducir nada. Lleva encabezado advirtiendo que el ambiente es compartido y que el archivo lista de más.

**`src/estenograficas/config.py`.** La raíz se descubre subiendo hasta encontrar `pyproject.toml`, así que funciona igual desde pytest, desde un notebook o con el paquete instalado; `ESTENOGRAFICAS_ROOT` la sobreescribe y es lo que usan las pruebas para trabajar en un directorio temporal. Todas las rutas cuelgan de `paths()`, incluidos los nombres fijos de archivo (`turnos.jsonl`, `hilos.jsonl`, `conferencias.jsonl`, `preguntas.jsonl`). Hay una prueba que barre el paquete con regex buscando rutas absolutas escritas a mano y falla si aparece alguna. `gemini_api_key()` falla ruidosamente si no hay key y **su mensaje de error no incluye el valor ni truncado**, porque una key en un traceback termina en un log; hay prueba de eso también.

**`src/estenograficas/checkpoint.py`.** Registro append-only de items hechos y rechazados por etapa. Cada registro se escribe con `flush` más `os.fsync` antes de devolver el control: eso es lo que lo hace sobrevivir a una muerte súbita del proceso. El costo es abrir el archivo una vez por item, que frente a un request con espera de un segundo es ruido. Un item rechazado **cuenta como procesado y no se reintenta solo**; para reintentarlo hay que borrar su renglón a mano, que es la fricción que se quería. La función `ejecutar()` centraliza el manejo de fallas para que ninguna etapa reinvente el tirar registros en silencio (regla dura 3). La lectura tolera una **última** línea truncada —escritura interrumpida a media línea, ese item se reprocesa— y la reporta en `lineas_truncadas`; una línea rota **en medio** levanta `CheckpointCorrupto`, porque eso no es una interrupción y no se adivina.

**Demostración de reanudación, con interrupción real.** No se simuló: se lanzó un subproceso, se dejó avanzar y se mató con `Popen.kill()` (TerminateProcess en Windows: sin `finally`, sin cerrar archivos, sin vaciar buffers).

- Corrida 1: reportó `item-00`..`item-05` y murió con `returncode=1`. El checkpoint en disco tenía exactamente esos 6 renglones, `lineas_truncadas: 0`, y `pendientes()` devolvió los 14 restantes.
- Corrida 2, relanzada sin borrar nada: procesó 13 items, **cero rehechos** (intersección vacía contra lo que había antes de relanzar). `item-07`, que falla a propósito, quedó en el archivo de rechazos con `ValueError: fallo deliberado...`. Estado final: 19 hechos, 1 rechazado, 20 procesados.
- Corrida 3: 0 items procesados, resumen idéntico. Idempotencia.

Esto está congelado como prueba en `tests/test_checkpoint.py::test_reanuda_tras_matar_el_proceso`, que lanza y mata el proceso de verdad en cada corrida de la suite, no como un script suelto.

**Suite:** 19 pruebas, 19 pasan, 4.6 s. `pytest -q` desde la raíz.

### Inventario del entorno (fase 0)

### Inventario del entorno (fase 0)

- `conda` no está en el PATH de la shell. Vive en `C:\Users\User\anaconda3\Scripts\conda.exe`; hay además un directorio `C:\Users\User\Anaconda3` que conda lista como ambiente sin nombre. Todo se invoca por ruta absoluta. El intérprete del proyecto es `C:\Users\User\anaconda3\envs\votaciones_corte\python.exe`.
- 13 ambientes, 10 inspeccionados. Ninguno cubría el stack completo. Se propusieron dos opciones (clonar `votaciones_corte` o instalar encima); el humano eligió instalar encima.
- Segundo candidato descartado: `mlops` (Python 3.13.7), tenía scikit-learn pero no google-genai, y 3.13 es terreno más frágil para torch.
- **Disco:** `D:` (repo) 685.5 GB libres, sobra para `data/raw/`. `C:` (ambientes) 59 GB libres antes de instalar.
- **El repo no está bajo git.** Sigue sin estarlo. La fase 1 empieza con `git init`.

### Instalación en `votaciones_corte` (aprobada)

Se corrió primero `pip install --dry-run --report` para ver qué iba a tocar. **El plan no incluía ningún downgrade:** `numpy` 2.4.2, `pandas` 3.0.1, `requests`, `google-genai` 1.66.0, `python-dotenv`, `tenacity` y `tqdm` no aparecieron en el plan de instalación, es decir que pip los dio por satisfechos y no los modificó. El otro proyecto que usa este ambiente no debería haberse roto, pero eso no se verificó corriéndolo.

Agregados: `scikit-learn` 1.9.0, `pytest` 9.1.1, `openpyxl` 3.1.5, `krippendorff` 0.8.2, `sentence-transformers` 6.0.0, más sus dependencias (`torch` 2.13.0 —122 MB de wheel—, `transformers` 5.15.1, `tokenizers`, `huggingface_hub`, `scipy` 1.17.1, `safetensors`, `sympy`, `networkx`, `joblib`, `threadpoolctl`, `filelock`, `fsspec`, `regex`, `jinja2`, `rich`, `typer` y demás).

Avisos benignos de pip: varios ejecutables (`isympy.exe`, `pygmentize.exe`, `typer.exe`) quedaron en `envs\votaciones_corte\Scripts`, que no está en el PATH. No importa; nada del proyecto los invoca por nombre.

**Verificación posterior a la instalación.** Los 15 paquetes del stack importan. Las versiones de lo que ya estaba salieron **idénticas al inventario previo**: requests 2.32.5, beautifulsoup4 4.14.3, lxml 6.0.2, pandas 3.0.1, numpy 2.4.2, google-genai 1.66.0, tqdm 4.67.3. Eso es la evidencia de que la instalación no movió nada. Además se corrió una prueba de interoperabilidad real, no solo imports: una regresión logística con validación cruzada de 5 pliegues sobre un `DataFrame` de pandas 3.0.1 (cv media 0.850, sin error) y un alfa de Krippendorff sobre dos codificadores idénticos (dio 1.000, como debe). El script de verificación vive en el scratchpad, no en el repo.

Dos cosas que salieron de ahí y afectan fases futuras:

- **`torch` quedó en versión CPU** (`2.13.0+cpu`). Para embeddings de ~10 mil preguntas cortas alcanza de sobra, pero las fases 7 y 12 van a tardar más de lo que tardarían con GPU. Si molesta, el ambiente `laluzqueopaca` tiene torch con CUDA 12.1 y sirve de referencia de que la máquina lo soporta.
- **`scikit-learn` 1.9 deprecó el argumento `penalty`** de `LogisticRegression`; se elimina en 1.10. La fase 12 usa regresión logística *regularizada*, así que esto le pega directo: hay que escribirla con `l1_ratio` y `C` desde el principio, no con `penalty="l2"`.

### Key de Gemini

El humano creó `.env` en la raíz del repo. Verificado con `python-dotenv` desde el ambiente: el archivo existe, `GEMINI_API_KEY` **no** estaba en el entorno antes de `load_dotenv` (o sea que sí viene del archivo y no de una variable de sistema), carga correctamente, mide 39 caracteres y empieza con `AIza`, que es el formato de las keys de Google. **El valor no se imprimió en ningún punto**; el script de verificación reporta longitud, prefijo y un sha256 truncado como huella. El script vive en el scratchpad, no en el repo.

Pendiente: `.env` tiene que entrar a `.gitignore` en la fase 1, antes del primer commit.

### Verificación del fixture `fixtures/2026-08-18.txt`

1,201 líneas, 97 KB. Hecha con grep/awk, sin escribir parser.

- Etiquetas y frecuencia: `PRESIDENTA DE MÉXICO, CLAUDIA SHEINBAUM PARDO` 77, `PREGUNTA` 65, `VOZ MUJER` 10, `DIRECTOR GENERAL DEL IMSS BIENESTAR, ALEJANDRO SVARCH PÉREZ` 6, `INTERVENCIÓN` 5, `DIRECTOR GENERAL DEL ISSSTE, MARTÍ BATRES GUADARRAMA` 3, `DERECHOHABIENTE, REBECA MAIRA GUTIÉRREZ CERÓN` 3, `VOZ HOMBRE` 2, `DIRECTOR GENERAL DEL IMSS, ZOÉ ROBLEDO ABURTO` 2, y una cada una de `SUBSECRETARIO ... EDUARDO CLARK DOBARGANES`, `MADRE DEL PACIENTE, LILIANA POOT`, `DERECHOHABIENTE, BÁRBARA BECERRA`, `DERECHOHABIENTE, BERTHA VILLAMIL`.
- **La trampa de los videos se confirma tal como estaba documentada:** 3 bloques (líneas 164–192, 252–276, 298–308) y las **18** apariciones de `VOZ MUJER` / `VOZ HOMBRE` / `DERECHOHABIENTE` / `MADRE DEL PACIENTE` caen dentro de ellos. Cero falsos positivos si se recortan antes de segmentar.
- Los cuatro periodistas de la prueba de aceptación existen y se autopresentan una sola vez: Nancy Rodríguez (Oro Sólido / Empuje Migrante, línea 368), Javier Tovar (AFP, 508), Dalila Escobar (Proceso, 676), Hans Salazar (Noticiero en Redes, 940).
- **Hallazgo nuevo:** `INTERVENCIÓN:`, 5 ocurrencias (líneas 346, 946, 994, 1026, 1168), ninguna dentro de video, siempre `(Inaudible)` o fragmento fuera de micrófono entre rayas. No es un hablante. Ya documentado en `CLAUDE.md`.

### Correcciones a la documentación (aprobadas el 2026-08-21)

`CLAUDE.md`:

1. Trampa nueva: `INTERVENCIÓN:` no es hablante, va `ruido: true` y **no debe interrumpir la propagación de identidad**. Si se trata como turno normal parte hilos en dos en silencio.
2. Contrato nuevo `data/interim/conferencias.jsonl` con `tema_dia`, su método y el fragmento que lo justifica. El cruce por tema del análisis final no tenía de dónde salir.
3. Regla metodológica 5: las tres corridas de Gemini se **perturban entre sí** (orden de categorías, orden de contexto). A temperatura baja y prompt idéntico coincidirían por construcción y la consistencia no mediría nada.
4. Regla metodológica 6: los embeddings del segundo instrumento son **locales, no de Gemini**, para que los errores de los dos instrumentos no se correlacionen; eso es lo que justifica la dependencia pesada. Y la logística **no se compara de frente contra el alfa**: se entrenó con las mismas 150, su exactitud solo se lee por validación cruzada.
5. Regla metodológica 2: se anotó el aplazamiento de la codificación manual y el entregable que lo desbloquea (ver abajo).
6. Regla metodológica 3: la recodificación intracodificador pasa a ser fase con número propio.

`PROMPT.md`: fases renumeradas, ver abajo.

### Aplazamiento de la codificación manual

El humano dijo el 2026-08-21 que todavía no le queda claro en qué consiste su trabajo de codificación y pidió moverlo a una etapa posterior.

**Se movió, pero no se reordenó.** La muestra de oro sigue teniendo que estar codificada antes de que Gemini corra sobre el corpus; si no, la calibración deja de ser a ciegas y el alfa mide otra cosa. Lo que se hizo fue meter trabajo real entre medio y agregar el entregable que faltaba:

- **Fase 8 nueva, análisis descriptivo sin clasificación.** Composición del pleno, concesión de turnos, frecuencia por medio y periodista, evolución temporal, cruce con tema. No requiere una sola pregunta codificada y produce la mitad del hallazgo, que es justo lo que exige la regla metodológica 7. Efecto secundario buscado: ver el corpus real vuelve concreta la tarea de codificar.
- **Instructivo de codificación** como entregable previo a la hoja, con ejemplos trabajados tomados **de fuera de las 150 muestreadas**. El libro de códigos dice qué valores existen, no cómo elegir entre ellos.

### Renumeración de fases

| Nueva | Antes | Qué cambió |
|---|---|---|
| 0 | 0 | Hecha |
| 1–5 | 1–5 | Igual, salvo que la 1 arranca con `git init` |
| 6 | 6 | Ahora también extrae el tema del día a `conferencias.jsonl` |
| 7 | 7 | Igual |
| **8** | — | **Nueva.** Análisis descriptivo sin clasificación |
| 9 | 8 | Muestra de oro, ahora con instructivo de codificación previo |
| **10** | — | **Nueva.** Recodificación intracodificador, con espera de una semana |
| 11 | 9 | Clasificación Gemini, con corridas perturbadas y estimación de costo previa |
| 12 | 10 | Segundo instrumento, con embeddings locales y sin comparación directa contra el alfa |
| 13 | 11 | Análisis de postura, encima de lo que dejó la 8 |

## Decisiones tomadas

| Decisión | Razón | Fase |
|---|---|---|
| Unidad de análisis es el hilo, no el par pregunta-respuesta | Un periodista hace 5 o 6 turnos seguidos con una sola autopresentación | previa |
| Clasificación en 4 dimensiones, no en un eje | Preguntas duras contra la oposición favorecen al gobierno sin ser halago | previa |
| El parser se valida contra fixtures locales antes de tocar la red | Evita descargar 460 páginas dos veces | previa |
| Segundo instrumento es logística sobre embeddings, no fine-tune | 150 ejemplos etiquetados; un transformer afinado sobreajusta | previa |
| Local en vez de Colab | El proyecto es I/O, no cómputo; el runtime efímero solo estorba a la descarga larga | previa |
| Usar `votaciones_corte` directo en vez de clonarlo | Decisión del humano. Ya traía google-genai más el stack de scraping, y Python 3.11 es el terreno más seguro para torch. El dry-run confirmó que no había downgrades | 0 |
| `INTERVENCIÓN:` es ruido y no rompe hilo | Verificado en el fixture: 5 casos, todos inaudibles o fuera de micrófono, ninguno dentro de video | 0 |
| El tema del día se extrae en la fase 6, no en la 13 | Está en la apertura de cada conferencia; si el campo no existe desde el parseo, el análisis final no lo puede improvisar | 0 |
| Las 3 corridas de Gemini se perturban entre sí | A temperatura baja y prompt idéntico coinciden por construcción; la consistencia saldría alta sin medir nada | 0 |
| Embeddings locales, no de Gemini, para el segundo instrumento | Si los dos instrumentos comparten proveedor, sus errores se correlacionan y las discrepancias dejan de ser informativas | 0 |
| La codificación manual se aplaza en calendario pero no en orden | Sigue teniendo que preceder a la corrida sobre el corpus, o la calibración deja de ser a ciegas | 0 |
| Se inserta una fase de análisis descriptivo antes de la muestra de oro | Es trabajo real que no depende de la codificación y vuelve concreta la tarea de codificar | 0 |
| `.gitignore` se escribió antes que cualquier otro archivo | La key ya estaba en el disco cuando se corrió `git init`; cualquier otro orden la ponía a un `git add -A` de distancia | 1 |
| Las dependencias no se declaran en `pyproject.toml` | La fuente de verdad del ambiente es `environment.yml`; declararlas dos veces garantiza que se desincronicen | 1 |
| El checkpoint hace `fsync` por item en vez de mantener el archivo abierto | Frente a un request con espera de 1 s el costo es ruido, y a cambio no hay estado en memoria que perder cuando el proceso muere | 1 |
| Un item rechazado cuenta como procesado y no se reintenta solo | Reintentar debe ser un acto deliberado —borrar el renglón—, no algo que pase por inercia en cada corrida | 1 |
| Última línea truncada se tolera; una rota en medio es error | Al final es una escritura interrumpida y es esperable; en medio es corrupción y no se adivina qué decía | 1 |
| Se le quitó `prefix:` a `environment.yml` | Filtraba la ruta absoluta de esta máquina y no aporta nada a la reproducción | 1 |
| La autopresentación se ancla a límites de oración | Sin eso el regex encuentra 6 periodistas donde hay 4. No se usó lista negra: la diferencia es estructural, no de nombres | 2 |
| Un hilo abre solo con autopresentación explícita | Lo demás sería inventar. Un periodista que nunca se presenta queda absorbido por el hilo anterior y se reporta como problema abierto, no se adivina | 2 |
| `INTERVENCIÓN` va con rol `pregunta` y atribución `incierta` | Viene del pleno, no de los funcionarios; el contrato solo admite dos roles y `respuesta` sería mentira | 2 |
| El aparte se define por párrafo entero entre rayas | Es lo que separa el habla fuera de micrófono del inciso hablado dentro de una oración | 2 |
| El ruido se filtra por patrón de cortesía, no por longitud | `¿No se le censura?` tiene 18 caracteres y es una pregunta real | 2 |
| Se marcan como ruido los agradecimientos, no solo los saludos | `CLAUDE.md` dice "saludos"; un "Muchas gracias, Presidenta" es la misma cortesía y tampoco es una pregunta. Extensión menor, anotada por si se quiere revertir | 2 |
| Solo raya y semirraya delimitan apartes, no el guion ASCII | El guion se usa en rangos y compuestos y generaba falsos apartes | 2 |
| Los fixtures de otros años se guardan como HTML crudo, no como .txt | Es lo que la fase 5 va a producir; guardar texto ya extraído oculta los cambios de estructura del CMS, que fue justo lo que se encontró | 3 |
| La extracción de HTML busca los <p> recursivamente | En 2024 cuelgan de .article-body y desde 2025 van dentro de <div>; mirar solo el primer nivel da un turno y cero hilos sin error | 3 |
| Los espacios Unicode se normalizan antes de segmentar | Un espacio duro tras la etiqueta funde el turno con el anterior en silencio | 3 |
| Se contemplan muletillas de presentación (Soy, Su servidor, Mi nombre es) | Sin ellas se pierde el hilo completo de quien se presenta así, y el nombre sale con el verbo pegado | 3 |
| Las pruebas multianio afirman invariantes, no conteos | Los conteos de esas cuatro no se cuadraron a mano; una prueba que afirme un número salido del propio parser no prueba nada | 3 |
| Estrategia de descarga mixta: Wayback + gob.mx con navegador | Decisión del humano. Wayback cubre 80% hasta enero de 2026 pero solo 22% de febrero en adelante; ninguna fuente sola alcanza | previa a 4 |
| La cobertura se mide sin `collapse` y sin filtro de statuscode | Las dos opciones subestiman: `statuscode:200` tira las capturas revisit, y `collapse=urlkey` puede devolver un 404 existiendo un 200 | previa a 4 |
| La fecha canónica saldrá del contenido, no del slug | Confirmado que los slugs traen año truncado, backslash pegado y sufijos numéricos | previa a 4 |
| Playwright corre headful con la ventana fuera de pantalla | Headless no pasa el reto de gob.mx en ninguna variante probada; fuera de pantalla es el compromiso que no estorba al usuario | 4 |
| gob.mx pasa a ser la fuente principal y Wayback el respaldo | El archivo entero son 108 páginas, ~2 minutos. La estrategia mixta se decidió creyendo que era caro; no lo es. Da además la URL canónica | 4 |
| Las estenográficas que no son conferencia matutina se listan aparte | Regla dura 3: nada se descarta en silencio. Son 497 y quedaron en otras_estenograficas.txt por si alguna resulta relevante | 4 |
| El recorrido del archivo lleva checkpoint por página | Son 110 páginas con navegador; si se corta a la mitad no tiene sentido volver a empezar | 4 |
| Se pasa el reto una vez y luego se usa `context.request` | Comparte la cookie del navegador pero devuelve el cuerpo crudo; `page.content()` daría el DOM serializado por Chromium, no los bytes del servidor | 5 |
| La fecha del contenido manda sobre la del slug | Recuperó dos conferencias que estaban listadas bajo una fecha equivocada y que se habrían dado por perdidas | 5 |
| `INTERLOCUTOR` e `INTERLOCUTORA` son prensa | 421 turnos en octubre de 2024. Contarlos como funcionarios convierte preguntas de periodistas en declaraciones de gobierno | 5 |
| La etiqueta se orienta por dónde está el cargo, no por la posición | El orden se invierte según el año: 116 `CARGO, NOMBRE` contra 60 `NOMBRE, CARGO` en las primeras 90 conferencias | 5 |
| `get_text("")` sin separador al extraer párrafos | Con separador, `el periódico <em>La Jornada</em>,` salía `La Jornada , donde`. 616 espacios espurios en 5,844 turnos, pegados justo al nombre del medio | 6 |
| `PROYECCIÓN DE VIDEO` NO se trata como apertura de bloque | Se probó y borraba 787 turnos, 239 de prensa: es una marca suelta sin cierre, y el bloque se comía todo hasta el siguiente `(FINALIZA VIDEO)` | 6 |
| Los cierres de video aceptan FINALIZA, FINALIZAN, CONCLUYE, TERMINA y AUDIO | 475 cierres contra 431 aperturas canónicas; faltaban formas | 6 |
| La fase 6 reescribe los tres JSONL en cada corrida | Parsear las 460 toma un minuto; agregar dejaría renglones de una versión vieja del parser mezclados con los nuevos | 6 |
| El tema del día va nulo cuando no se anuncia | 51% de las conferencias no anuncian tema. Nulo antes que inventado | 6 |
| `assets/` completo va a `.gitignore` | Material de terceros compartido en confianza; estaba a un `git add -A` de entrar al historial | 6 |
| La autopresentación se tacha del texto, no se excluye la pregunta | Decisión del humano. Conserva la categoría de preguntas de apertura, que es el 10% y no es como el resto | 9 |
| La etiqueta admite espacio opcional antes y después de los dos puntos | Tres variantes reales rompían la segmentación en silencio; 253 turnos de prensa traían la respuesta del gobierno adentro | 6 |
| Las preguntas de ejemplo se filtran para excluir las que traen otra etiqueta adentro | Aunque el bug esté arreglado, el filtro protege contra la siguiente variante que aparezca | 9 |
| El conteo externo se usa como validación posterior, no como insumo | Si la canonicalización se construye copiando la suya, coincidir deja de ser evidencia. Misma lógica que la codificación a ciegas | 7 |

## Problemas abiertos

Los seis puntos de la parada de la fase 6 **no están aquí**: viven arriba, en "Lo primero al retomar", porque son decisiones pendientes y no problemas latentes.

### Bloquean trabajo

1. **`data/raw/` no está respaldado.** 460 archivos, 75 MB, fuera de git. Reconstruirlos son 15 minutos de navegador y depende de que gob.mx siga sirviendo. `CLAUDE.md` exige el respaldo antes de que cualquier etapa los consuma.
2. **La hoja real de codificación no existe.** Solo las dos de ejemplo. Sale en la fase 9, y antes hay que decidir la compensación del punto 3.
3. **La compensación del instructivo de codificación sigue sin resolverse.** El agente ya trabajó cuatro ejemplos a petición del humano, así que **el anclaje ya ocurrió parcialmente**. Falta decidir si se escribe el instructivo completo con ejemplos del agente (rápido, ancla más) o si el humano codifica 10 en frío primero (más lento, criterio propio). Las preguntas ya mostradas al humano quedan **excluidas de la muestra de oro**; sus ids están en los commits correspondientes.

### Riesgos conocidos del dato

4. **Una atribución que sabemos mal y NO se parchó.** El turno `PREGUNTA: No lo interrumpas cuando…` quedó atribuido a Hans Salazar; es alguien del salón regañando a otro. La heurística de interjecciones no lo agarra porque es un solo turno con respuesta antes y después. Es el piso de error irreducible de la propagación hacia adelante sin juicio humano.
5. **El hilo de Dalila Escobar del 2026-08-18 tiene 62 turnos y 31 preguntas**, muy por encima de los otros. Puede ser real —ella dice "el último, tercer tema"— o puede que otro periodista hablara sin presentarse y quedara absorbido. No se distingue sin leer.
6. **Nos faltan 231 intervenciones (31%)** contra el conteo manual externo en enero–junio de 2026. Parte es recall de identificación, parte puede ser diferencia en la unidad de conteo. Es la meta medible de la fase 7. **Matizado el 2026-08-28:** el segundo contraste, sobre todo el periodo y agrupando por periodista, dio coincidencia **exacta en 10 de 10**. El hueco del 31% es entonces de los turnos **sin periodista identificado**, no de los que sí identificamos, y no afecta a los periodistas frecuentes.
6b. **La canonización de nombres de medio no está hecha:** ~620 cadenas crudas. Carlos Guzmán dice su medio de 11 formas, alternando `Quatro` y `Cuatro`. Cualquier conteo por medio publicado hoy es un piso. El eje confiable es el periodista.
7. **El `tema_dia` solo cubre el 49% y su calidad es despareja.** Bien: `salud`, `seguridad`. Mal: `casa llena`, `tres temas`. **No está listo para cruzarlo en el análisis final**; probablemente necesite el modelo sobre el fragmento de apertura.
8. **Una docena de días hábiles sin conferencia que no son festivos obvios:** 2024-10-28, 2024-11-18, 2024-11-19, 2024-12-12, 2025-06-16, 2025-06-17, 2025-09-01 (día del Informe), 2025-11-10, 2025-12-05, 2025-12-12, 2026-04-17. Pueden ser giras o existir bajo otro slug.
9. **Tres turnos `INTERVENCIÓN` quedan con `texto` vacío** porque todo su contenido era un aparte. Es correcto según el contrato, pero un texto vacío se confunde fácil con un error de parseo.
10. **`CLAUDE.md` dice "del orden de 10 mil turnos de pregunta"** y el corpus tiene **27,278**. Corregir esa línea.
11. **164 preguntas rechazadas por el clasificador temático** (1.3%), con su razón, en `data/checkpoints/temas_dos_niveles.rechazos.jsonl`. No cambian ninguna proporción, pero la regla dura 3 dice que nada se descarta en silencio: falta decidir si se reintentan.
12. **Los 620 grupos de consolidación no se han revisado a mano.** Aplazado por el humano el 2026-08-28. El defecto de encadenamiento ya está corregido en el código y el invariante se verifica con `assert` en cada corrida, así que lo que falta es control de calidad, no reparación.

### Del entorno

13. **gob.mx solo se deja leer con navegador VISIBLE.** Headless no pasa el reto anti-bot ni con espera de 50 s ni con parches anti-detección. La ventana se manda fuera de pantalla, pero **el pipeline no puede correr en un servidor sin escritorio.**
14. **No se verificó que el otro proyecto que usa `votaciones_corte` siga funcionando** después de instalarle scikit-learn, sentence-transformers, torch y playwright. El dry-run no mostró downgrades y las versiones previas salieron idénticas, pero eso no es haberlo corrido.
15. **`environment.yml` lista de más**, porque el ambiente es compartido. Reconstruirlo da algo que funciona pero más gordo que el mínimo, y con torch en versión CPU.
16. **`LogisticRegression(penalty=...)` está deprecado** en scikit-learn 1.9 y desaparece en 1.10. La fase 12 tiene que escribirse con `l1_ratio` y `C`.
17. **pandas 3.0.1** es muy reciente. Se probó logística con validación cruzada sobre un DataFrame y pasó, pero no se ha combinado con `sentence-transformers`.
18. **La cobertura de fixtures sigue siendo de cinco conferencias.** Suficiente para haber encontrado once modos de falla, insuficiente para afirmar que el parser aguanta 460 sin sorpresas.

### Resueltos en esta sesión, anotados para no repetirlos

- **Costo de la fase 11: medido.** ~$18 USD con `gemini-2.5-flash` en batch, tres corridas sobre 22,282 preguntas. Más de la mitad del costo de entrada es el libro de códigos repetido en cada llamada; si algún día importa, ahí está el ahorro (context caching), no en bajar de modelo.
- **La conferencia de Culiacán resultó ser un duplicado** del 2025-07-11 publicado bajo dos URLs, no una conferencia faltante.
- **La hoja de ejemplo v1 se generó antes de implementar la redacción**, así que mostraba el medio y el humano codificó viéndolo. La v2 ya sale redactada; ninguna de esas preguntas entra a la muestra de oro.
- **`consolidar()` fusionaba por cadenas.** Union-find metía en un grupo de 204 miembros cosas con Jaccard 0.00 entre sí. Corregido: cada miembro se compara contra el representante. 7 pruebas nuevas, 0 grupos encadenados, y 12 veces más rápido con un índice invertido.
- **Un `<h2>` de más en el artefacto se llevó el CSS de otra sección.** Al reemplazar un bloque de estilos por posición, el corte se comió las reglas de la sección de dinero, que quedó sin estilo aunque su HTML seguía completo. Detectado contando selectores, no mirando la página.

## Cómo retomar

Todo lo necesario está en "Estado" y "Lo primero al retomar", arriba. En corto:

```bash
cd d:/PROYECTOS_PERSONALES/preguntas_matutinas
PYTHONIOENCODING=utf-8 "C:/Users/User/anaconda3/envs/votaciones_corte/python.exe" -m pytest -q
```

Leer `CLAUDE.md` (reglas del proyecto), luego este archivo desde arriba. **No avanzar a la fase 7 sin que el humano resuelva los 6 puntos de la parada.**

---

## Plantilla para actualizar

**Estado:** fase, fecha, ambiente en uso, y qué está bloqueando si algo lo está.

**Hecho:** qué se produjo, dónde quedó, cuántos registros. Con números. "Se parsearon 431 de 447 conferencias; 16 rechazadas, razones en `data/interim/rechazos.jsonl`" sirve. "Parseo completado" no sirve.

**Siguiente paso concreto:** una acción, no una fase. Lo bastante específico para ejecutarla sin releer todo.

**Decisiones tomadas:** cada fila con su razón. Especialmente las que parecieron menores en el momento; son las que después nadie recuerda por qué se tomaron.

**Problemas abiertos:** cosas que fallaron y se dejaron pasar, supuestos sin verificar, casos raros pospuestos. Incluir los feos. Un problema documentado cuesta una hora; uno descubierto en la fase 11 cuesta el proyecto.
