# CLAUDE.md

Reglas permanentes del proyecto. Se leen al inicio de cada sesión y no se negocian sin consultar.

## Qué es esto

Análisis de contenido de las versiones estenográficas de las conferencias de prensa de la Presidencia de México (gob.mx/presidencia), desde octubre de 2024. El objetivo es medir si las preguntas de la prensa son confrontativas o favorables hacia el gobierno, y describir cómo se distribuye eso entre medios, periodistas y temas.

El producto final es un dataset defendible y un análisis, no un pipeline bonito. Si hay que elegir entre elegancia del código y trazabilidad del dato, gana la trazabilidad.

Escala real, medida sobre el corpus completo: **460 conferencias, 65,092 turnos de habla, 27,278 turnos de prensa y 22,282 preguntas útiles** (sin saludos ni inaudibles). La estimación original de "10 mil turnos de pregunta" se quedó corta por casi el triple.

## Entorno

Máquina local, control total. Conda para el ambiente.

**No crear un ambiente nuevo sin consultar.** Es muy probable que ya exista uno reutilizable. El procedimiento es inventariar lo que hay, proponer el mejor candidato con su justificación, y esperar aprobación.

**Estructura:**

```
estenograficas/
  src/estenograficas/   # toda la lógica, paquete importable
  tests/                # pruebas contra conferencias de muestra
  notebooks/            # exploración y figuras, sin lógica
  fixtures/             # conferencias de muestra, versionadas
  data/                 # en .gitignore, ver abajo
  CLAUDE.md
  HANDOFF.md
  .env                  # en .gitignore
  environment.yml
```

```
data/
  raw/          # HTML crudo, inmutable, nunca se sobreescribe
  interim/      # turnos.jsonl, hilos.jsonl
  gold/         # muestra codificada a mano por el humano
  outputs/      # dataset final, tablas, figuras
  checkpoints/  # estado de procesos largos
```

**El código va en `src/`, no en celdas.** Los notebooks son para mirar datos y hacer figuras. Nada de lógica reutilizable ahí. Rutas resueltas por una función de configuración, ninguna ruta absoluta hardcodeada.

**Secretos:** la API key de Gemini vive en `.env` (en `.gitignore`), se lee con `python-dotenv`. Nunca hardcodeada, nunca impresa.

**Respaldo:** `data/raw/` es el activo caro del proyecto. Debe estar respaldado fuera del repo antes de que empiece cualquier etapa que lo consuma.

## Reglas duras

1. **El HTML crudo no se vuelve a descargar.** Se baja una vez y se conserva. El parser se va a reescribir muchas veces; el corpus no.
2. **Toda etapa es idempotente y reanudable.** Correrla dos veces produce el mismo resultado y no rehace trabajo hecho. La descarga en particular escribe checkpoint conforme avanza.
3. **Nada se descarta en silencio.** Si un registro no se pudo procesar, se escribe a un archivo de rechazos con la razón. Un pipeline que "funciona" porque tira lo que no entiende está roto.
4. **El modelo nunca ve el documento completo.** Recibe fragmentos acotados: los primeros 300 caracteres de un turno para identificar autoría, o una pregunta con su contexto inmediato para clasificar. Mandar la conferencia entera es caro y produce paráfrasis en lugar de extracción.
5. **Todo campo derivado del modelo lleva su procedencia:** `metodo` (regex, llm, manual), `confianza`, y el fragmento textual exacto que lo justifica.
6. **Nulo antes que inventado.** Si no se sabe quién preguntó, el campo va nulo y se marca.

## Trampas conocidas del formato

Estas ya costaron trabajo descubrirlas. No las vuelvas a descubrir.

- **Los videos contaminan.** Entre `(INICIA VIDEO)` y `(FINALIZA VIDEO)` hay hablantes etiquetados (`VOZ MUJER:`, `DERECHOHABIENTE, NOMBRE:`) que no son parte del diálogo de la conferencia. Se eliminan antes de segmentar.
- **La etiqueta de hablante es todo mayúsculas y termina en dos puntos.** Trae cargo y nombre separados por coma: `DIRECTOR GENERAL DEL IMSS, ZOÉ ROBLEDO ABURTO`. Un `rsplit(",", 1)` separa los campos.
- **El periodista se identifica una sola vez.** Su primer turno dice "Nancy Rodríguez, de Oro Sólido"; sus siguientes cinco turnos dicen solo `PREGUNTA:`. La identidad se propaga hacia adelante dentro del hilo.
- **El forward-fill se rompe con las interjecciones del pleno.** Turnos `PREGUNTA:` consecutivos, cortos, sin respuesta de por medio, suelen ser gente distinta gritando desde el salón. Se marcan `atribucion: "incierta"` y no se les asigna periodista.
- **Los apartes entre rayas** (`—A ver, acá—`) son habla fuera de micrófono. Van en campo aparte, porque contaminan cualquier conteo de palabras por hablante.
- **El encabezado del artículo** (título, subtítulo, caption duplicado) precede al primer turno y no debe quedar pegado a la primera intervención.
- **Los saludos no son preguntas.** `PREGUNTA: Buenos días, Presidenta.` y `PREGUNTA: Bien.` son ruido y se filtran.
- **La etiqueta puede venir seguida de espacio duro.** Visto en 2025-07-02: `PREGUNTA:` con `\xa0` en vez de espacio. La etiqueta no casa, el turno se funde con el anterior y queda atribuido a la presidenta. **No hay excepción ni aviso: solo un turno de menos.** Los espacios Unicode se normalizan antes de segmentar. Uno en cinco conferencias de muestra; en 460 son decenas.
- **La estructura del HTML cambió en 2025.** En 2024 los `<p>` cuelgan directo de `div.article-body`; desde 2025 el CMS los envuelve en uno o más `<div>`. Buscar solo hijos directos devuelve la conferencia entera como un párrafo: un turno, cero hilos, cero errores. La búsqueda va recursiva.
- **El periodista se presenta con muletilla.** `Soy Aissa García, de Telesur`, `Su servidor, Carlos Pozos, de LM Noticias`, `Mi nombre es…`. Sin quitarlas, `Soy` queda dentro del nombre y `Su servidor` impide detectar la presentación entera, perdiendo el hilo completo de ese periodista.
- **`—000—` cierra el documento, no es un aparte.** Último párrafo del archivo, entero entre rayas, idéntico en forma a un aparte fuera de micrófono. Es el cierre de boletín de Presidencia. Se quita antes de segmentar y solo si está al final.
- **La autopresentación del periodista es su propia oración.** `Gracias, Presidenta. Dalila Escobar, de Proceso.` Un regex de `Nombre, de Medio` sin anclar a inicio y fin de oración encuentra seis periodistas en la conferencia del 2026-08-18, que tiene cuatro: se traga `...a Andrés Manuel López Beltrán, de encabezar una red de huachicol`, donde el `de` introduce un verbo y no un medio.
- **`INTERVENCIÓN:` no es un hablante.** Verificado en `fixtures/2026-08-18.txt`: 5 ocurrencias, ninguna dentro de un bloque de video, contenido siempre `(Inaudible)` o un fragmento fuera de micrófono entre rayas (`—25—`). Es ruido de sala. Se marca `ruido: true` y **no interrumpe la propagación de identidad dentro del hilo**: si se trata como turno normal, parte hilos en dos en silencio, que es exactamente el error que no se detecta mirando el conteo de periodistas.

## Contratos de datos

`data/interim/turnos.jsonl`, un renglón por turno de habla:
```json
{"conferencia_id": "2026-08-18", "orden": 42, "etiqueta": "...", "cargo": null,
 "hablante": "...", "tipo": "prensa|funcionario|anonimo", "texto": "...",
 "apartes": ["..."]}
```

`data/interim/hilos.jsonl`, un renglón por hilo (un periodista y su tanda):
```json
{"conferencia_id": "2026-08-18", "hilo": 3, "periodista": null, "medio": null,
 "periodista_canonico": null, "metodo_identificacion": "regex|llm|sin_identificar",
 "turnos": [{"rol": "pregunta|respuesta", "quien": null, "texto": "...",
             "atribucion": "declarada|propagada|incierta", "ruido": false}]}
```

`data/interim/conferencias.jsonl`, un renglón por conferencia. Existe porque el análisis de la fase 11 cruza postura contra el tema del día, y ese campo no se puede improvisar al final:
```json
{"conferencia_id": "2026-08-18", "fecha": "2026-08-18", "tema_dia": "salud",
 "metodo_tema": "regex|llm|manual", "fragmento_tema": "hoy vamos a hablar de salud",
 "n_turnos": 0, "n_hilos": 0}
```

`data/outputs/preguntas.jsonl`: la unidad de análisis final, una pregunta con sus clasificaciones y su procedencia.

## Libro de códigos

Cada pregunta se clasifica en cuatro dimensiones. **No colapsar en un solo eje.** Una pregunta puede ser durísima contra la oposición, lo cual favorece al gobierno sin ser un halago.

| Campo | Valores |
|---|---|
| `objetivo` | gobierno, oposicion, actor_externo, medios, ninguno |
| `postura` | confrontativa, neutral, favorable |
| `funcion` | pide_informacion, cuestiona_afirmacion, invita_comentario_sobre_tercero, plantea_demanda |
| `insistencia` | true si es repregunta tras una respuesta evasiva |

Todo valor admite `no_clasificable`. Toda clasificación incluye el fragmento textual que la justifica.

## Reglas metodológicas

1. **Por qué existe la codificación manual.** El humano codifica 150 preguntas de unas 10 mil. Esas 150 no son el dataset, son la calibración: sirven para medir si las 9,850 que clasificó el modelo son confiables. Es el mismo procedimiento que se usaba con asistentes de investigación humanos mucho antes de los LLMs.

2. **Se codifica a mano ANTES de correr el modelo sobre el corpus, y a ciegas.** El agente no codifica ninguna, ni siquiera para comparar. "A ciegas" son dos cosas: el humano no ve la salida del modelo, y la hoja de codificación **no incluye nombre de periodista ni medio**. Esos campos viven aparte con la llave de unión. Ver "Proceso" o "Televisa" mientras se codifica mete la conclusión en el dato.

   **La codificación manual se puede posponer en el calendario; no se puede reordenar.** Acordado el 2026-08-21: la muestra de oro se construye más tarde, después de la fase 7, porque el humano todavía no tiene claro en qué consiste su trabajo de codificación. Eso está bien: las fases 1 a 7 no la necesitan. Lo que **no** se mueve es que quede codificada antes de que el modelo corra sobre el corpus. Si se clasifican las 10 mil primero y se codifican las 150 después, la calibración deja de ser a ciegas, el humano codifica sabiendo que hay una salida del modelo esperando, y el alfa mide otra cosa.

   **Entregable que hace falta para desbloquearla: un instructivo de codificación.** El libro de códigos dice qué valores existe, no cómo decidir entre ellos frente a una pregunta real. El instructivo lo escribe el agente con ejemplos trabajados **tomados de fuera de las 150 muestreadas**, nunca de dentro. Compensación a discutir cuando lleguemos: los ejemplos hacen el trabajo posible pero anclan al humano a la lectura del agente. La alternativa es que el humano codifique 10 en frío y de ahí salga el instructivo.

3. **En dos lotes.** 30 primero, se corrige el libro de códigos donde el humano dudó, luego las 120 restantes. El humano recodifica 20 del primer lote una semana después para medir su propia consistencia; si no coincide consigo mismo, las categorías están vagas y ningún clasificador lo arregla. **Esa recodificación es una fase con su propio número, no una nota al pie**, porque impone una espera de una semana y lo que no está agendado no ocurre.

4. **Se reporta alfa de Krippendorff** entre la codificación humana y la del modelo. Debajo de 0.6 el libro de códigos está mal definido y se rediseña. **No se ajusta el prompt hasta que el número suba: eso es entrenar contra la validación.**

5. **Tres corridas por pregunta, temperatura baja, con perturbación entre corridas.** Las que no coinciden entre corridas son ambiguas y van a revisión, no se resuelven por mayoría en silencio. **La temperatura baja sola no mide nada:** tres corridas idénticas coinciden por construcción y la "consistencia" sale alta sin significar nada. Las corridas se diferencian por algo sustantivo —orden de las categorías en el prompt, orden de los turnos de contexto— para que el desacuerdo signifique fragilidad real de la clasificación y no ruido de muestreo.

6. **El segundo clasificador es embeddings más regresión logística regularizada, no un fine-tune.** Con 150 ejemplos etiquetados un transformer afinado sobreajusta. La regresión además es interpretable. Si algún día hay 2000 ejemplos codificados, se reconsidera.

   **Los embeddings son locales, no de la API de Gemini.** Si el segundo instrumento se construye sobre embeddings del mismo proveedor que el primero, sus errores se correlacionan y el conjunto de discrepancias —que es el producto interesante de la fase 10— deja de ser informativo. Esa independencia es lo que justifica la dependencia pesada de `sentence-transformers`.

   **La logística no se compara de frente contra el alfa de Gemini.** Se entrena con las mismas 150 que calibran a Gemini, así que no es un instrumento independiente en el mismo sentido: su exactitud solo es interpretable por validación cruzada sobre la muestra de oro, y ese número no es comparable con el alfa. Lo que sí es válido, y es para lo que existe la fase 10, es el conjunto de preguntas donde los dos instrumentos discrepan.

7. **Quien está en el salón y a quién le dan la palabra no es aleatorio.** La presidenta elige a dedo y lo dice en voz alta. Cualquier conclusión sobre "la prensa es blanda" tiene que discutir selección antes que deferencia. El análisis reporta composición del pleno y concesión de turnos, no solo promedios de postura.

8. **Tema políticamente cargado.** El trabajo mide y describe, no adjetiva. Las categorías se definen de modo que alguien con la posición política contraria las aplicaría igual. Si una categoría solo tiene sentido asumiendo una conclusión, está mal definida.

## Cosas que no hacer

- No crear ni modificar ambientes conda sin aprobación explícita.
- No parchar el código para que un caso raro deje de fallar. Investigar por qué falla.
- No reportar "listo" sin el diagnóstico que lo respalde.
- No optimizar nada antes de que el pipeline corra de punta a punta.
- No agregar dependencias pesadas sin justificarlas.
