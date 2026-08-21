# HANDOFF

Memoria del proyecto entre sesiones. El agente lo actualiza al terminar cada fase, antes de detenerse.

Regla de escritura: se describe lo que **pasó**, no lo que se pretendía. Un handoff optimista es peor que ninguno.

---

## Estado

**Fase actual:** 4 (descubrimiento de URLs) terminada. Fase 5 (descarga) no iniciada.
**Última actualización:** 2026-08-21, cerrando la sesión.
**Ambiente conda:** **`votaciones_corte`**, Python 3.11.14, en `C:\Users\User\anaconda3\envs\votaciones_corte`. Aprobado por el humano el 2026-08-21 para usarse directo, sin clonar.
**Bloqueado esperando:** nada. Se puede continuar directo.


## Hecho

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

## Siguiente paso concreto

**Fase 5: descarga.** Escribir `src/estenograficas/descarga.py` que consuma `data/interim/urls.jsonl` y baje el HTML crudo a `data/raw/{conferencia_id}.html`.

Requisitos que ya están decididos y no hay que volver a discutir:

- **Playwright headful** para gob.mx, ventana fuera de pantalla, reutilizando **un solo contexto** para todas las descargas: ya se probaron cinco seguidas a un request por segundo sin que el reto reapareciera. Abrir un navegador por página sería absurdo.
- **Un request por segundo**, reintentos con backoff, **checkpoint conforme avanza** con el módulo `checkpoint`.
- **El HTML crudo es inmutable**: si `data/raw/{id}.html` ya existe, no se vuelve a bajar ni se sobreescribe.
- **Manejar gzip.** Ya mordió una vez en la fase 3: una captura vino comprimida y se guardó binario.
- **Wayback como respaldo** para las URLs de gob.mx que fallen, no como fuente por defecto.
- Las 4 URLs sin `conferencia_id` necesitan que la fecha salga del **contenido**, no del slug. La de Culiacán es una conferencia real.
- Al terminar, **recordarle al humano respaldar `data/raw/` fuera del repo** antes de que nada lo consuma.
- Diagnóstico que pide la fase: tasa de éxito y lista de fallos.

Fragmento de Playwright que ya funciona, para no volver a descubrirlo:

```python
nav = p.chromium.launch(
    headless=False,                       # headless NO pasa el reto
    args=["--window-position=-2400,-2400", "--window-size=1280,900"],
)
ctx = nav.new_context(locale="es-MX", user_agent=UA,
                      viewport={"width": 1280, "height": 900})
```


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

## Problemas abiertos

1. **gob.mx solo se deja leer con navegador VISIBLE.** Headless no pasa el reto anti-bot ni con espera de 50 s ni con parches anti-detección; headful pasa en 1.7 s. La ventana se puede mandar fuera de pantalla, pero **el pipeline no puede correr en un servidor sin escritorio**. Si algún día se mueve a uno, esto se rompe y hay que volver a Wayback.
2. **Hay una atribución que sabemos que está mal y no se parchó.** El turno `PREGUNTA: No lo interrumpas cuando…` quedó atribuido a Hans Salazar como `propagada`. Es alguien del salón regañando a otro, no Hans. La heurística de interjecciones no lo agarra porque es un solo turno con respuesta antes y después, no una racha. **No se metió un caso especial a propósito** (`CLAUDE.md`: no parchar para que un caso raro deje de fallar). Es la clase de error que la parada obligatoria de la fase 6 existe para encontrar, y es evidencia de que la propagación hacia adelante tiene un piso de error irreducible sin juicio humano.
3. **El hilo de Dalila Escobar tiene 62 turnos y 31 preguntas, muy por encima de los otros tres.** Puede ser real —ella misma dice "el último, tercer tema"— o puede ser que otro periodista habló sin presentarse y quedó absorbido en su hilo. No se puede distinguir sin leer. Revisar en la fase 6.
4. **Tres turnos `INTERVENCIÓN` quedan con `texto` vacío** porque todo su contenido era un aparte (`—25—`, `—36 [por ciento] del '24 al…—`). Es correcto según el contrato, pero un texto vacío es fácil de confundir con un error de parseo cuando se vean 460 conferencias.
5. **El fixture empieza con `ersión estenográfica`**, sin la V inicial. Es un defecto del texto de origen, no del parser. Si aparece en más archivos, la extracción del título en la fase 6 tiene que tolerarlo.
6. **No se verificó que el otro proyecto que usa `votaciones_corte` siga funcionando** después de la instalación. El dry-run no mostró downgrades, que es evidencia buena pero no es haberlo corrido. Si `votaciones_corte` empieza a fallar en su proyecto original, empezar por aquí.
7. **`environment.yml` lista de más.** Como `votaciones_corte` es compartido, el export trae paquetes del otro proyecto. Reconstruirlo en otra máquina da un ambiente que funciona pero más gordo que el mínimo, y con torch CPU. Si algún día importa, se recorta a mano.
8. **Sin estimación de costo para la fase 11.** ~10 mil preguntas × 3 corridas ≈ 30 mil llamadas. Se estima antes de la fase 9, no al llegar a la 11.
9. **La compensación del instructivo de codificación no está resuelta.** Ejemplos trabajados por el agente hacen la tarea posible pero anclan al humano a la lectura del agente. La alternativa es que el humano codifique 10 en frío primero y de ahí salga el instructivo. Se decide al llegar a la fase 9.
10. **pandas 3.0.1** es muy reciente. Se probó logística con validación cruzada sobre un `DataFrame` de pandas 3.0.1 y pasó, pero no se ha corrido nada que combine pandas 3.0 con `sentence-transformers`. Si algo truena raro en las fases 8 o 12, sospechar de aquí.
11. **`LogisticRegression(penalty=...)` está deprecado** en scikit-learn 1.9 y desaparece en 1.10. La fase 12 tiene que escribirse con `l1_ratio` y `C`. Anotado ahora porque en la fase 12 se va a ver como un warning ignorable y no lo es.
12. **La cobertura sigue siendo de cinco conferencias.** Una de 2024, una de 2025 y tres de 2026. Suficiente para haber encontrado cuatro defectos reales, insuficiente para afirmar que el parser aguanta 460. La parada obligatoria de la fase 6 sigue siendo el filtro de verdad.
13. **Una docena de días hábiles sin conferencia que no son festivos obvios:** 2024-10-28, 2024-11-18, 2024-11-19, 2024-12-12, 2025-06-16, 2025-06-17, 2025-09-01, 2025-11-10, 2025-12-05, 2025-12-12 y 2026-04-17. Pueden ser giras o pueden existir bajo otro slug. Revisar en la fase 6.
14. **La conferencia de Culiacán no tiene fecha en el slug.** `...-en-culiacan-sinaloa`. Es real y está en `urls.jsonl` con `conferencia_id: null`. La fase 5 tiene que sacarle la fecha del contenido, y de paso confirmar si hay más conferencias fuera de Palacio Nacional con este patrón.

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
