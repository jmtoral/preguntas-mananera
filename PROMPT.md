# Prompt de arranque

Copia el bloque de abajo como primer mensaje al agente. Ten en el repo `CLAUDE.md`, `HANDOFF.md` y la conferencia de muestra en `fixtures/2026-08-18.txt`.

> **Revisión del 2026-08-27.** Las fases 0 a 6 están hechas y el corpus está descargado, parseado y publicado en GitHub. **La fase 6 es parada obligatoria y está esperando decisiones del humano.** El estado real, con los seis puntos pendientes, vive en `HANDOFF.md`; este archivo es solo el plan.
>
> **Revisión del 2026-08-21.** Las fases se renumeraron. La fase 0 ya está ejecutada y el ambiente aprobado es `votaciones_corte`. Cambios respecto de la versión original: la prueba de aceptación de la fase 2 se endureció, el tema del día se extrae en la fase 6 en vez de improvisarse al final, se insertó una fase 8 de análisis descriptivo que no requiere codificación manual, la muestra de oro se recorrió a la fase 9 y la recodificación de consistencia se volvió fase propia (10). El estado real vive en `HANDOFF.md`, no aquí.

---

Vas a construir conmigo un proyecto de análisis de contenido sobre las conferencias de prensa matutinas de la Presidencia de México. Trabajamos en mi máquina local, con conda.

**Pregunta de investigación:** ¿las preguntas que la prensa hace en las conferencias son confrontativas o favorables hacia el gobierno, y cómo se distribuye eso entre medios, periodistas y temas?

Lee `CLAUDE.md` completo antes de escribir una sola línea. Contiene las reglas del proyecto, los contratos de datos, las trampas conocidas del formato y las decisiones metodológicas ya tomadas, que no debes reabrir sin consultarme. Lee también `HANDOFF.md` para saber en qué fase estamos.

## Cómo quiero que trabajes

Avanza por fases, en orden. Al terminar cada fase:

1. Corre el diagnóstico que la fase pide y muéstrame los resultados.
2. Actualiza `HANDOFF.md` con lo que hiciste, las decisiones que tomaste y por qué.
3. Detente y espérame. No encadenes fases sin que yo confirme.

Las fases 6, 9 y 10 tienen paradas obligatorias porque requieren juicio humano. No las brinques ni las simules.

**Orden crítico: el parser funciona contra archivos locales antes de que toques la red.** Ya tengo una conferencia completa en `fixtures/2026-08-18.txt`. Si descargamos 460 páginas antes de saber si el parser sirve, vamos a descargar dos veces.

## Las fases

**Fase 0. Inventario del entorno. HECHA (2026-08-21).** Ambiente aprobado: `votaciones_corte`, Python 3.11.14, en `C:\Users\User\anaconda3\envs\votaciones_corte`. Conda no está en el PATH; se invoca por ruta absoluta. Ver `HANDOFF.md` para el inventario completo.

**Fase 1. Andamiaje.** Con el ambiente ya aprobado: `git init` —el repo no está bajo control de versiones—, estructura de repositorio de `CLAUDE.md`, paquete instalado en modo editable, `.gitignore` con `data/` y `.env`, `environment.yml` exportado. Escribe el módulo de configuración de rutas y el de checkpointing, y demuestra que el checkpointing reanuda tras una interrupción real; no me digas que funciona, interrúmpelo.

**Fase 2. Parser contra una conferencia.** Sin red. Parsea `fixtures/2026-08-18.txt` en turnos y luego en hilos, según los contratos de `CLAUDE.md`. Escribe esto como prueba en `tests/`, no como celda ni como script suelto.

Pruebas de aceptación. Los cuatro periodistas identificados son Nancy Rodríguez, Javier Tovar, Dalila Escobar y Hans Salazar. Si alguno no sale, el parser está mal; no lo fuerces con un caso especial.

**Ese criterio es necesario pero no suficiente y por sí solo no prueba nada de lo difícil.** En esta conferencia hay 65 turnos `PREGUNTA:` y solo 4 autopresentaciones: 61 turnos dependen de la propagación hacia adelante, y un parser que parta los hilos mal puede seguir encontrando los 4 nombres. Aserta también:

- Los 3 bloques de video quedan eliminados y con ellos las 18 apariciones de `VOZ MUJER`, `VOZ HOMBRE`, `DERECHOHABIENTE` y `MADRE DEL PACIENTE`. Ninguna de esas etiquetas sobrevive a la segmentación.
- Las 5 ocurrencias de `INTERVENCIÓN:` quedan marcadas `ruido: true` y **ninguna parte un hilo en dos**.
- Número de hilos y turnos por hilo, cuadrados a mano contra el texto.
- Cuántos `PREGUNTA:` quedan con `atribucion: "incierta"`, y que ninguno de esos tenga periodista asignado.
- El encabezado del artículo no quedó pegado al primer turno de la presidenta.

Diagnóstico adicional: todas las etiquetas de hablante encontradas, con frecuencia.

**Fase 3. Parser contra varios años.** Descarga a mano tres o cuatro conferencias sueltas, una de finales de 2024, una de 2025 y una de 2026, guárdalas en `fixtures/` y corre el parser. El formato cambia con el tiempo. Diagnóstico: qué etiquetas aparecen en unas y no en otras.

**Fase 4. Descubrimiento.** Ahora sí, recorre el archivo paginado de artículos de Presidencia en gob.mx y arma la lista de URLs de versiones estenográficas de conferencias de prensa. No construyas los slugs por fecha, tienen erratas e inconsistencias. Salida: `data/interim/urls.jsonl`. Diagnóstico: conteo por mes y meses con huecos sospechosos.

**Fase 5. Descarga.** HTML crudo, User-Agent de navegador, un request por segundo, reintentos con backoff, checkpoint conforme avanza. El HTML crudo es inmutable. Salida: `data/raw/{fecha}.html`. Si el sitio empieza a bloquear, la Wayback Machine puede servir de respaldo para las URLs que fallen; no asumas que su cobertura es completa. Al terminar, recuérdame respaldar `data/raw/` fuera del repo. Diagnóstico: tasa de éxito y lista de fallos.

**Fase 6. Parseo masivo y tema del día. PARADA OBLIGATORIA.** Corre el parser sobre todo el corpus y escribe también `data/interim/conferencias.jsonl` con el tema del día de cada una, con su método y el fragmento que lo justifica. El tema se extrae aquí, no en la fase de análisis: la presidenta lo anuncia en la apertura ("hoy vamos a hablar de salud") y ese texto está en el corpus, pero si el campo no existe desde ahora, la fase 13 no lo va a poder improvisar.

Diagnóstico obligatorio: el conjunto completo de etiquetas de hablante únicas ordenadas por frecuencia, más 10 turnos al azar con su etiqueta y sus primeros 200 caracteres, más la distribución de temas del día y cuántas conferencias quedaron sin tema.

**Detente.** Tengo que revisar esa lista antes de que sigas. Una etiqueta que aparece tres veces en 460 conferencias casi siempre es un error de parseo, no un hablante real, y los errores de segmentación son silenciosos.

**Fase 7. Identidad.** Extrae nombre y medio del periodista que abre cada hilo. Regex primero sobre los primeros 300 caracteres; el modelo solo sobre lo que el regex no resolvió, mandándole ese fragmento y nada más. Después canonicaliza con embeddings más clustering: el mismo periodista aparece escrito distinto entre conferencias. Muéstrame los clusters dudosos para que yo los apruebe. Diagnóstico: hilos sin identificar y periodistas únicos tras canonicalizar.

**Fase 8. Análisis descriptivo, sin clasificación.** Esta fase no necesita ni una sola pregunta codificada y produce la mitad del hallazgo. Panel por medio y por periodista: composición del pleno, con qué frecuencia recibe la palabra cada quien, cuántos turnos le tocan, cómo evoluciona en el tiempo, cruce con el tema del día. Es lo que pide la regla metodológica 7 de `CLAUDE.md`: quién está en el salón y a quién le dan la palabra no es aleatorio, y cualquier conclusión sobre deferencia tiene que discutir selección primero.

Efecto secundario deliberado: al ver el corpus real, con sus preguntas y sus medios, la fase 9 va a dejar de ser abstracta.

**Fase 9. Muestra de oro. PARADA OBLIGATORIA.** Muestra estratificada de 150 preguntas (por año, tipo de medio y longitud). Expórtala a hoja de cálculo con las cuatro columnas del libro de códigos vacías, el texto de la pregunta y dos turnos de contexto.

Antes de la hoja, entrégame un **instructivo de codificación**: cómo decidir entre los valores de cada dimensión frente a una pregunta real, con ejemplos trabajados **tomados de fuera de las 150 muestreadas**. El libro de códigos dice qué valores existen; no dice cómo elegir. Sin eso no puedo codificar de manera consistente y el alfa va a salir bajo por mi culpa, no por la del modelo.

**El nombre del periodista y el medio NO van en esa hoja.** Guárdalos aparte con la llave de unión. Si veo "Proceso" mientras codifico, voy a codificar por expectativa y no por el texto, y después el análisis va a "descubrir" algo que metí yo.

Entrégame primero un lote de 30. Las codifico, veo dónde dudé y corregimos el libro de códigos antes de que me des las 120 restantes. **Tú no codificas ninguna, ni siquiera para comparar.**

**Fase 10. Consistencia intracodificador. PARADA OBLIGATORIA, con espera de una semana.** Una semana después del primer lote, me devuelves 20 de esas 30 sin mis códigos y las recodifico a ciegas. Si no coincido conmigo mismo, las categorías están vagas y hay que rediseñarlas antes de gastar una sola llamada a la API. Esta fase existe porque estaba enterrada como nota al pie en `CLAUDE.md` y lo que no está agendado no ocurre. Diagnóstico: acuerdo intracodificador por dimensión.

**Fase 11. Clasificación.** Con mi muestra codificada de vuelta, clasifica todo el corpus con la API de Gemini: salida JSON estricta, temperatura baja, batch mode, tres corridas independientes por pregunta. **Las tres corridas se perturban entre sí** —orden de las categorías en el prompt, orden de los turnos de contexto—; a temperatura baja y prompt idéntico las tres van a coincidir por construcción y la consistencia no mediría nada. Antes de lanzar, estímame el costo: son del orden de 30 mil llamadas y no quiero enterarme a la mitad.

Calcula alfa de Krippendorff contra mi codificación y consistencia entre corridas. **Si el alfa sale abajo de 0.6, detente y dímelo.** El problema es el libro de códigos, no el modelo. No ajustes el prompt hasta que el número suba.

**Fase 12. Segundo instrumento.** Embeddings locales más regresión logística regularizada entrenada sobre mi muestra de oro, con validación cruzada. Los embeddings son locales y no de Gemini a propósito: si los dos instrumentos salen del mismo proveedor, sus errores se correlacionan y las discrepancias dejan de decir nada. No un fine-tune: con 150 ejemplos sobreajusta.

Su exactitud se reporta por validación cruzada y **no se compara de frente contra el alfa de Gemini**: se entrenó con las mismas 150 que calibran a Gemini, así que no es un instrumento independiente en ese sentido. Lo que sí quiero es la comparación sobre todo el corpus y las preguntas donde los dos instrumentos discrepan; son las interesantes. Reporta también qué features pesan más, que para eso elegimos un modelo interpretable.

**Fase 13. Análisis.** Cierra lo que abrió la fase 8, ahora con postura encima: distribución de postura por medio y por periodista, evolución en el tiempo, cruce con el tema del día. Reporta composición del pleno y concesión de turnos junto a los promedios de postura, nunca los promedios solos.

## Reglas de conducta

- Nunca me digas que algo funcionó sin enseñarme la evidencia.
- Si un supuesto tuyo se rompe contra los datos reales, dímelo de inmediato en vez de parchar el código para que deje de fallar.
- Si una decisión metodológica te parece equivocada, discútela antes de implementarla.
- No inventes atribuciones. Si no se sabe quién preguntó, el campo va nulo.
- No toques mis ambientes conda sin aprobación explícita.

**No empieces por la fase 1: las fases 0 a 6 ya están hechas.** Lee `HANDOFF.md` y arranca desde "Lo primero al retomar".
