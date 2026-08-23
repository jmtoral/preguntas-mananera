# Preguntas matutinas

Análisis de contenido de las versiones estenográficas de las conferencias de prensa de la Presidencia de México. Mide si las preguntas de la prensa son confrontativas o favorables hacia el gobierno, y cómo se distribuye eso entre medios, periodistas y temas.

**Corpus actual: 460 conferencias, del 3 de octubre de 2024 al 20 de agosto de 2026.**

Las reglas del proyecto están en [CLAUDE.md](CLAUDE.md), el estado real en [HANDOFF.md](HANDOFF.md) y el plan por fases en [PROMPT.md](PROMPT.md). Este archivo es el mapa.

---

## Empezar

```bash
cd d:/PROYECTOS_PERSONALES/preguntas_matutinas
conda activate votaciones_corte     # conda no está en el PATH:
                                    # C:\Users\User\anaconda3\Scripts\conda.exe
pytest -q
```

El ambiente es `votaciones_corte`, Python 3.11. La API key de Gemini va en `.env` (copiar de `.env.example`); está en `.gitignore` y nunca se imprime.

## Las etapas

Cada una es idempotente y reanudable, y ninguna descarta un registro en silencio.

| comando | qué hace | salida |
|---|---|---|
| `python -m estenograficas.descubrimiento` | recorre el archivo de gob.mx y la Wayback Machine | `data/interim/urls.jsonl` |
| `python -m estenograficas.descarga` | baja el HTML crudo | `data/raw/{fecha}.html` |
| `python -m estenograficas.parseo` | parsea todo a turnos, hilos y conferencias | tres `.jsonl` en `data/interim/` |

**La descarga abre un navegador visible.** gob.mx responde un reto anti-bot a cualquier cliente que no ejecute JavaScript, y headless no lo pasa. La ventana se manda fuera de pantalla, pero el proceso necesita un escritorio: no corre en un servidor.

## Estructura

```
src/estenograficas/   toda la lógica, paquete importable
  config.py           rutas y secretos
  checkpoint.py       reanudación y archivo de rechazos
  parser.py           texto → turnos → hilos
  descubrimiento.py   fase 4
  descarga.py         fase 5
  parseo.py           fase 6
tests/                116 pruebas
fixtures/             5 conferencias de muestra, versionadas
notebooks/            exploración y figuras, sin lógica
data/                 en .gitignore
```

`data/raw/` es el activo caro: 460 archivos, 75 MB, fuera de git. **Respaldarlo aparte.**

## Cómo se codifica a mano

El proyecto se apoya en 150 preguntas codificadas por el humano. No son el dataset: son la calibración que permite medir si las ~22 mil que clasificará el modelo son confiables.

**La hoja de trabajo es un Excel.** Hay un ejemplo funcional en:

```
data/gold/EJEMPLO_hoja_de_codificacion.xlsx
```

Ocho columnas. Las tres primeras las llena el pipeline; las cuatro con menú desplegable las llena el humano; la última es para anotar dudas.

| columna | quién |
|---|---|
| `id_pregunta` | pipeline — es la llave, no se toca |
| `contexto (2 turnos previos)` | pipeline |
| `PREGUNTA A CODIFICAR` | pipeline |
| `objetivo` | **humano** |
| `postura` | **humano** |
| `funcion` | **humano** |
| `insistencia` | **humano** |
| `notas / dudas` | **humano** |

Reglas que no se negocian:

- **La hoja no lleva nombre de periodista ni medio.** Viven aparte con la llave de unión.
- **La autopresentación se borra del texto de la pregunta.** El 10% de las preguntas dicen el medio dentro de su propio texto (`"Carlos Navarro, de Heraldo Media Group. Presidenta, ¿qué…"`); ahí se sustituye por `[identificación removida]`. Guardar el medio en otra columna no protege nada si sigue estando a la vista.
- **El agente no codifica ninguna**, ni para comparar.
- Dos lotes: 30 → se corrige el libro de códigos con las dudas → 120. Una semana después se recodifican 20 de las primeras 30 para medir consistencia consigo mismo.

El libro de códigos está en [CLAUDE.md](CLAUDE.md).

## Estado

Fases 0 a 6 hechas. La 6 es parada obligatoria y está esperando revisión humana de la lista de etiquetas. Ver [HANDOFF.md](HANDOFF.md).
