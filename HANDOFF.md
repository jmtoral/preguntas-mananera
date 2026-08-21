# HANDOFF

Memoria del proyecto entre sesiones. El agente lo actualiza al terminar cada fase, antes de detenerse.

Regla de escritura: se describe lo que **pasó**, no lo que se pretendía. Un handoff optimista es peor que ninguno.

---

## Estado

**Fase actual:** 1 (andamiaje) terminada. Fase 2 (parser contra una conferencia) no iniciada.
**Última actualización:** 2026-08-21.
**Ambiente conda:** **`votaciones_corte`**, Python 3.11.14, en `C:\Users\User\anaconda3\envs\votaciones_corte`. Aprobado por el humano el 2026-08-21 para usarse directo, sin clonar.
**Bloqueado esperando:** confirmación para arrancar la fase 2. Además, **no se ha hecho ningún commit**: el repo está inicializado y todo el andamiaje existe en el disco, pero sin historial. Falta el visto bueno del humano para commitear.

## Hecho

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

## Siguiente paso concreto

Dos cosas, en este orden:

1. **Commitear el andamiaje.** El repo no tiene ni un commit. `git add -A` mete 15 archivos y ya se verificó que ni `.env` ni `data/` entran.
2. **Fase 2: parser contra una conferencia.** Escribir `src/estenograficas/parser.py` y `tests/test_parser.py` contra `fixtures/2026-08-18.txt`, sin red. Los criterios de aceptación endurecidos están en `PROMPT.md`, fase 2: no basta con encontrar a los cuatro periodistas —hay 65 turnos `PREGUNTA:` y solo 4 autopresentaciones—, hay que asertar también que los 3 bloques de video desaparecen con sus 18 etiquetas contaminantes, que las 5 `INTERVENCIÓN:` quedan `ruido: true` sin partir hilos, el número de hilos y turnos por hilo cuadrados a mano, y que ningún `PREGUNTA:` con `atribucion: "incierta"` tenga periodista asignado.

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

## Problemas abiertos

1. **El repo está inicializado pero sin ningún commit.** Todo el andamiaje vive solo en el disco. Un `rm -rf` accidental se lo lleva completo, incluidas las correcciones a `CLAUDE.md` y `PROMPT.md`. Pendiente el visto bueno para commitear.
2. **No se verificó que el otro proyecto que usa `votaciones_corte` siga funcionando** después de la instalación. El dry-run no mostró downgrades, que es evidencia buena pero no es haberlo corrido. Si `votaciones_corte` empieza a fallar en su proyecto original, empezar por aquí.
3. **`environment.yml` lista de más.** Como `votaciones_corte` es compartido, el export trae paquetes del otro proyecto. Reconstruirlo en otra máquina da un ambiente que funciona pero más gordo que el mínimo, y con torch CPU. Si algún día importa, se recorta a mano.
4. **Sin estimación de costo para la fase 11.** ~10 mil preguntas × 3 corridas ≈ 30 mil llamadas. Se estima antes de la fase 9, no al llegar a la 11.
5. **La compensación del instructivo de codificación no está resuelta.** Ejemplos trabajados por el agente hacen la tarea posible pero anclan al humano a la lectura del agente. La alternativa es que el humano codifique 10 en frío primero y de ahí salga el instructivo. Se decide al llegar a la fase 9.
6. **pandas 3.0.1** es muy reciente. Se probó logística con validación cruzada sobre un `DataFrame` de pandas 3.0.1 y pasó, pero no se ha corrido nada que combine pandas 3.0 con `sentence-transformers`. Si algo truena raro en las fases 8 o 12, sospechar de aquí.
7. **`LogisticRegression(penalty=...)` está deprecado** en scikit-learn 1.9 y desaparece en 1.10. La fase 12 tiene que escribirse con `l1_ratio` y `C`. Anotado ahora porque en la fase 12 se va a ver como un warning ignorable y no lo es.
8. **La cobertura del fixture es de una sola conferencia y de 2026.** Todo lo verificado hasta ahora —incluida la trampa de los videos y `INTERVENCIÓN:`— vale para ese archivo. La fase 3 existe para ver qué se rompe en 2024 y 2025.

## Cómo retomar

```bash
cd d:/PROYECTOS_PERSONALES/preguntas_matutinas
conda activate votaciones_corte   # conda no está en el PATH; usar C:\Users\User\anaconda3\Scripts\conda.exe
pytest -q
```

Luego leer `CLAUDE.md`, leer este archivo, y continuar desde "siguiente paso concreto".

---

## Plantilla para actualizar

**Estado:** fase, fecha, ambiente en uso, y qué está bloqueando si algo lo está.

**Hecho:** qué se produjo, dónde quedó, cuántos registros. Con números. "Se parsearon 431 de 447 conferencias; 16 rechazadas, razones en `data/interim/rechazos.jsonl`" sirve. "Parseo completado" no sirve.

**Siguiente paso concreto:** una acción, no una fase. Lo bastante específico para ejecutarla sin releer todo.

**Decisiones tomadas:** cada fila con su razón. Especialmente las que parecieron menores en el momento; son las que después nadie recuerda por qué se tomaron.

**Problemas abiertos:** cosas que fallaron y se dejaron pasar, supuestos sin verificar, casos raros pospuestos. Incluir los feos. Un problema documentado cuesta una hora; uno descubierto en la fase 11 cuesta el proyecto.
