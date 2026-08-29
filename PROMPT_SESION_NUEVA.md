# Prompt para una conversación nueva

Copia todo lo que va debajo de la línea y pégalo como primer mensaje.

---

Estoy analizando las conferencias matutinas de la Presidencia de México. El proyecto vive en `d:\PROYECTOS_PERSONALES\preguntas_matutinas`. **Lee `CLAUDE.md` y `HANDOFF.md` antes de proponer nada** — sobre todo la sección «Plan al 2026-08-28 (segunda versión)», que está al principio del HANDOFF.

**Lo que quiero saber, y es lo único que quiero saber por ahora:** de las ~22 mil preguntas que la prensa le hace a la presidenta, **cuántas van a favor del gobierno y cuántas en contra**. Las críticas a terceros cuentan como a favor. Lo neutral es lo que realmente pregunta.

**Dónde está el trabajo.** El corpus está construido y no hay que tocarlo: 460 conferencias, 65,092 turnos, 22,466 preguntas útiles, todo en `data/interim/hilos.jsonl`. El tema de cada pregunta ya está clasificado en un 75%. **Lo que falta es la postura, y eso es el proyecto.**

**Estado exacto al empezar:**

- Estoy codificando a mano 150 preguntas en `data/gold/muestra_oro_hoja.xlsx`. Van 28 del lote 1; faltan 5 arreglos y los 120 del lote 2.
- Los créditos de la API de Gemini **están agotados**. Sin recargar en ai.studio no corre nada. Recargar es mi tarea, no la tuya.
- Faltan 5,560 preguntas por clasificar por tema; 3,237 de ellas solo porque se acabaron los créditos.

**Los tres pasos que quiero, en orden, y nada más:**

1. Yo termino las 150.
2. Tú escribes el prompt de postura y lo corres sobre el corpus. Cuatro valores al codificar (`crítica al gobierno`, `afín al gobierno`, `crítica a un tercero`, `neutral`), tres pasadas con perturbación entre ellas.
3. Reportas en mis tres cubetas: **en contra** / **a favor** (afín + crítica a tercero) / **lo que realmente pregunta**, con el alfa de Krippendorff contra mis 150 al lado.

**Cómo quiero que trabajes:**

- **No me propongas planes de seis frentes.** Si algo no acerca el número de los tres pasos de arriba, va después y lo dices en una línea.
- Antes de dar algo por bueno, **mídelo**. Este proyecto ya encontró así un filtro que descartaba el 45% de las preguntas en silencio y un algoritmo que fusionaba temas por cadenas.
- Dime los costos en dólares antes de gastar.
- **No codifiques tú ninguna de las 150**, ni para comparar. Es la calibración y se contamina.
- No abras `data/gold/muestra_oro_LLAVE_no_abrir.csv` ni nada de `assets/`.

**Lo primero que tienes que hacer al arrancar:**

```bash
cd d:/PROYECTOS_PERSONALES/preguntas_matutinas
PYTHONIOENCODING=utf-8 "C:/Users/User/anaconda3/envs/votaciones_corte/python.exe" -m pytest -q   # deben pasar 140
ps -W | grep -c votaciones_corte    # debe ser 0; si no, hay un proceso zombi gastando API
```

El intérprete se llama por ruta porque conda no está en el PATH. En Windows hay que anteponer `PYTHONIOENCODING=utf-8` o la consola destroza los acentos al imprimir.

Empieza diciéndome, en no más de diez líneas, qué vas a hacer para el paso 2 y cuánto va a costar.
