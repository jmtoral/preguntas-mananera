# Prompt para una conversación nueva

Copia todo lo que va debajo de la línea y pégalo como primer mensaje.

---

Estoy analizando las conferencias matutinas de la Presidencia de México. El proyecto vive en `d:\PROYECTOS_PERSONALES\preguntas_matutinas`. **Lee `CLAUDE.md` y `HANDOFF.md` antes de proponer nada** — el estado del 2026-08-30 está al principio del HANDOFF.

**Lo que quiero saber:** de las ~22 mil preguntas que la prensa le hace a la presidenta, **cuántas van a favor del gobierno y cuántas en contra**. Lo neutral es lo que realmente pregunta.

**Son tres valores, no cuatro.** Hubo un cuarto, `crítica a un tercero`, y lo fusioné con `afín al gobierno` después de codificar las 150: pegarle a un rival del gobierno le sirve al gobierno, siempre. Codificándolas a mano me quedó claro. No lo vuelvas a abrir.

## Dónde va el trabajo

**Ya tengo una respuesta preliminar, salida de mi propia mano.** Codifiqué a ciegas las 150 preguntas de la muestra de oro. Sobre 135 clasificables: **51% neutral, 36% a favor, 13% en contra.** Casi tres a favor por cada una en contra, con intervalos de confianza que no se tocan.

Lo que falta es escalarlo a las 21,826 y desagregarlo por periodista y medio.

**Está hecho:** el corpus completo (460 conferencias, 21,826 preguntas útiles en `data/interim/hilos.jsonl`), la clasificación temática al 99.9%, y las 150 codificadas a mano.

**Está a medias:** el clasificador de postura. Existe en `src/estenograficas/postura.py`, corre, mide su propio costo — y **falla**: 47% de coincidencia contra mi codificación en la prueba sobre 30 preguntas.

## Tu tarea, en este orden

**1. Recodificar yo los 30 del lote 1 con las reglas finales.** Los codifiqué antes de que las reglas quedaran fijas, así que no son consistentes con el libro de códigos actual. Pídemelos y los hago: sirve además como la medición de mi consistencia conmigo mismo, que estaba pendiente.

**2. Seguir arreglando el prompt de postura.** Va en **57%** de coincidencia conmigo (60% aplicando dos correcciones mías). Ya se arregló lo grande: el modelo devolvía `no clasificable` 9 veces contra mis 2 y ahora son 3. Lo que queda son cuatro casos donde yo puse `neutral` y el modelo `afín al gobierno` — y de ésos, al menos uno el modelo lo tiene bien y yo mal.

**No sigas ajustando sin que yo recodifique primero.** Con 30 preguntas, exprimir puntos es ajustar ruido.

**Ajusta contra los 30 del lote 1 y NO toques los 120 del lote 2.** Ésa es la razón de haber partido la muestra: el prompt se ajusta con el lote 1, el alfa que voy a publicar sale del lote 2. Tocar los 120 sería entrenar contra la validación.

**3. Correr sobre las 150 y calcular el alfa de Krippendorff** contra el lote 2, partido en dos: fragmentos cortos y preguntas sustantivas. Un tercio del corpus son fragmentos de menos de 80 caracteres y no se comportan igual.

**4. Si el alfa pasa de 0.6, correr el corpus completo.** Si no pasa, **se rediseñan las categorías, no el prompt.**

**5. Reportar** en tres cubetas: **en contra** / **a favor** / **lo que realmente pregunta**.

## Cómo quiero que trabajes

- **Avísame SIEMPRE antes de gastar en la API, con el costo en dólares.** Todos los scripts tienen `--dry`, que da el conteo y el costo sin llamar a nada. Córrelo primero y enséñame el número. He estado con presupuesto muy corto y una corrida sorpresa me truena el proyecto.
- **No me propongas planes de seis frentes.** Si algo no acerca el número de los cuatro pasos de arriba, va después y lo dices en una línea.
- **Mide antes de dar algo por bueno.** Este proyecto ya encontró así un filtro que descartaba el 45% de las preguntas en silencio, un algoritmo que fusionaba temas por cadenas, y una estimación de costo equivocada por 4.6× porque no contaba los tokens de razonamiento.
- **No codifiques tú ninguna de las 150**, ni para comparar. Es la calibración y se contamina.
- No abras `data/gold/muestra_oro_LLAVE_no_abrir.csv` ni nada de `assets/`.

## Lo primero al arrancar

```bash
cd d:/PROYECTOS_PERSONALES/preguntas_matutinas
PYTHONIOENCODING=utf-8 "C:/Users/User/anaconda3/envs/votaciones_corte/python.exe" -m pytest -q
ps -W | grep -c votaciones_corte    # debe ser 0; si no, hay un proceso gastando API
```

El intérprete se llama por ruta porque conda no está en el PATH, y en Windows hay que anteponer `PYTHONIOENCODING=utf-8` o la consola destroza los acentos.

Empieza diciéndome en no más de diez líneas cómo vas a arreglar el prompt y cuánto va a costar probarlo.
