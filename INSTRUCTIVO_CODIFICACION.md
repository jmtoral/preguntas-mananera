# Instructivo de codificación

Para codificar `data/gold/muestra_oro_hoja.xlsx`. Se lee una vez completo antes de empezar y después se consulta.

---

## Qué estás haciendo y por qué

Vas a codificar 150 preguntas a mano. **Esas 150 no son el dataset.** El dataset son las ~22 mil que va a clasificar el modelo. Las 150 son la **calibración**: sirven para medir si las otras 22 mil son confiables. Es el mismo procedimiento que se usaba con asistentes de investigación humanos mucho antes de que hubiera modelos de lenguaje.

Por eso importa el orden. Codificas **antes** de que el modelo corra sobre el corpus y **sin ver** su salida. Si se clasifican las 22 mil primero, dejas de codificar a ciegas y el alfa de Krippendorff acaba midiendo otra cosa.

La hoja tampoco trae nombre de periodista ni medio, ni siquiera el identificador de la pregunta —que lleva la fecha y permitiría buscar de quién es—. Solo un código, `P-001`. La llave de unión existe, está en `data/gold/muestra_oro_LLAVE_no_abrir.csv`, y **no hay que abrirla mientras codificas**. Ver «Proceso» o «Contralínea» mientras decides mete la conclusión dentro del dato.

**En dos lotes.** Primero los 30 del lote 1. Ahí paramos, revisamos dónde dudaste y corregimos el libro de códigos. Después los 120 del lote 2. Una semana después vas a recodificar 20 del lote 1 sin ver lo que pusiste: eso mide tu consistencia contigo mismo, y si no coincides contigo, las categorías están mal definidas y ningún clasificador lo arregla.

**Una advertencia sobre este documento.** Los ejemplos trabajados de abajo son mi lectura, no la tuya. Elegiste esta versión sabiendo el costo: tu codificación se va a parecer a la mía por construcción, y eso infla el alfa. Cuando reportemos el número hay que decirlo. Donde no estés de acuerdo con un ejemplo, **anótalo**: eso es información, no un error tuyo.

Todas las preguntas de este instructivo están **fuera** de las 150. Ninguna es de las que vas a codificar.

---

## Las cuatro dimensiones no se colapsan

La regla que más se rompe: **`postura` se mide hacia el `objetivo`, no hacia el gobierno.**

Una pregunta durísima contra la oposición es `confrontativa` — hacia la oposición. Eso favorece al gobierno sin ser un halago, y por eso hacen falta dos columnas y no una. Si colapsas los ejes, esa pregunta se vuelve invisible o se codifica al revés.

Cada pregunta lleva las cuatro. Ninguna se deja en blanco: si de verdad no se puede, va `no_clasificable`, que es una respuesta, no un hueco.

---

## 1 · `objetivo` — sobre quién cae el peso

**No es a quién se le pregunta.** Todo se le pregunta al gobierno, así que si `objetivo` significara eso, las 22 mil serían `gobierno` y la columna no diría nada.

`objetivo` es **de quién trata la pregunta**, quién queda expuesto por ella.

| valor | qué cae aquí |
|---|---|
| `gobierno` | el gobierno federal actual: sus programas, funcionarios, decisiones, cifras, omisiones |
| `oposicion` | partidos y figuras de oposición, gobiernos estatales opositores, expresidentes panistas y priistas |
| `actor_externo` | Estados Unidos, Trump, otros países, empresas, crimen organizado, organismos internacionales |
| `medios` | la prensa misma: publicidad oficial, libertad de expresión, quién recibe la palabra |
| `ninguno` | no hay objeto identificable: trámite, dato general, pregunta sobre un hecho sin responsable |

**Ejemplo trabajado.**

> *«El embajador, ok. ¿Y cuál es su opinión de que a Fox y Calderón se nombrara persona non grata?»*

`objetivo = oposicion`. Trata de dos expresidentes de oposición. Se le pregunta a ella, pero ella no es el objeto: son ellos.

> *«¿Cuál es su opinión de que el día de ayer, Estados Unidos anunció que va a frenar visas de inmigrantes a 75 países?, que aquí no está México, desde luego.»*

`objetivo = actor_externo`. La decisión es de otro gobierno.

---

## 2 · `postura` — hacia el objetivo

| valor | señal |
|---|---|
| `confrontativa` | pone al objetivo en aprieto: señala contradicción, fracaso, omisión, opacidad; contrapone su versión con otra |
| `neutral` | pide un dato o una explicación sin carga en ninguna dirección |
| `favorable` | celebra, felicita, da por buena la versión del objetivo, o le ofrece plataforma para lucirse |

**Tres ejemplos trabajados, en orden de dureza.**

> *«Oiga, y aprovechando el viaje, hablando de las reformas constitucionales hay quien piensa, percibe que hay cierta prisa en implementarlas… ¿Por qué la prisa? ¿Por qué no tomarse el tiempo de analizar estas reformas que afectan a todo el país?»*

`objetivo = gobierno`, `postura = confrontativa`. No insulta ni acusa: incorpora una crítica ajena («hay quien percibe») y pide cuentas por ella. Eso basta. **Confrontativa no quiere decir grosera.**

> *«Sobre este mismo tema de salud, Presidenta, preguntar si ¿hay algún dato de avance sobre la credencialización universal?»*

`objetivo = gobierno`, `postura = neutral`. Pide un dato. Preguntar por «avances» no la vuelve favorable: no celebra nada, solo quiere el número.

> *«Han pasado algunos meses, hay avances importantes, sabemos y hemos seguido de cerca estos o los mismos. ¿Cuál es el mensaje que envía en estos momentos? Sabemos que hay detenciones también importantes en varios estados.»*

`objetivo = gobierno`, `postura = favorable`. Aquí sí. La premisa ya afirma que hay avances importantes y la pregunta es una invitación a mandar un mensaje. **La diferencia con la anterior está en la premisa, no en el tema.**

---

## 3 · `funcion` — qué está haciendo la pregunta

| valor | qué es |
|---|---|
| `pide_informacion` | quiere un dato que no tiene: cuántos, cuándo, dónde, cómo va |
| `cuestiona_afirmacion` | pone en duda algo que el gobierno dijo o sostiene |
| `invita_comentario_sobre_tercero` | pide su opinión sobre alguien más |
| `plantea_demanda` | pide una acción, una gestión, una solución; a veces a nombre de terceros |

**Cuando caben dos, gana la dominante.** Casi toda pregunta pide información de alguna forma; eso no la vuelve `pide_informacion`. Pregúntate qué pasa si el gobierno solo entrega el dato: si con eso la pregunta queda satisfecha, es `pide_informacion`; si el periodista seguiría inconforme, es otra cosa.

> *«¿Cuántos elementos se enviaron para reforzar y hasta cuándo estarían?»*

`pide_informacion`. Con el número queda satisfecha.

> *«Entonces: ¿no hay problema en estos centros de acopio, Presidenta?, porque se han acercado a nosotros, los productores.»*

`cuestiona_afirmacion`. Ella acaba de describir el Plan Frijol; él contrapone el testimonio de los productores. Trae también una demanda implícita, pero lo dominante es la contradicción.

> *«Conversando con algunos de los padres de familia, ellos mismos acusan que nunca fueron consultados por la Comisión… ¿Tiene algún acercamiento con ellos?»*

`plantea_demanda`. Habla a nombre de terceros y lo que pide es una acción, no un dato.

---

## 4 · `insistencia` — es la única que necesita el contexto

`sí` cuando la pregunta **vuelve sobre un punto que la respuesta anterior no resolvió**. Para eso está la columna de contexto con los dos turnos previos.

No es «hizo otra pregunta del mismo tema». Es: hubo respuesta, la respuesta esquivó o quedó corta, y el periodista regresa.

> **contexto** — R: *Perdón, no te escucho.*
> **pregunta** — *«¿Tampoco le ha solicitado el gobierno de Estados Unidos permiso para venir a detener a integrantes de cárteles en este…?»*

`insistencia = sí`. El «tampoco» delata que es la segunda vuelta.

> **contexto** — R: *Ellos dicen que tiene que ver con la decisión que tomó el Gobierno de México con enviar… Son cuatro puntos los que establece el Departamento…*
> **pregunta** — *«¿Ya le están pidiendo a Estados Unidos una explicación? ¿Le han enviado algún escrito o solicitud?»*

`insistencia = sí`. La respuesta explicó lo que dice el otro gobierno y no lo que hizo el nuestro; la pregunta regresa a eso.

**Ojo:** el 91% de las preguntas de la muestra son turnos de seguimiento dentro de una tanda, pero eso **no** las vuelve insistencia. Un periodista que pasa a su segundo tema distinto no está insistiendo.

---

## Casos difíciles: qué hacer

**No los resuelvas a la fuerza. Anótalos.** La columna `notas / dudas` es tan importante como las otras: el lote 1 existe para encontrar dónde el libro de códigos está mal, y eso solo se ve en tus dudas. Tres que ya sé que vas a encontrar:

**1. El objetivo son «los partidos», incluido el del gobierno.**

> *«El Consejo General del INE sancionó a partidos políticos con multas por 50 millones de pesos porque incumplieron con la obligación de destinar 3 por ciento para los liderazgos femeninos. ¿Qué llamado le haría a los partidos?»*

No es `oposicion` —Morena está adentro— ni `gobierno`. Hoy la tabla no tiene dónde ponerlo. Pon lo que te parezca y **escribe la duda**; si sale varias veces, el libro de códigos necesita un valor nuevo.

**2. La invita a pronunciarse sobre sí misma.** `funcion` tiene `invita_comentario_sobre_tercero` pero no su equivalente cuando el comentario es sobre el propio gobierno («¿cuál es el mensaje que envía?»). Es un hueco real de la tabla. Anótalo.

**3. Preguntas que no se sostienen solas.** Algunas son fragmentos («La hizo a un lado.»). Si con el contexto se entiende, códificala; si no, `no_clasificable` en las cuatro y una nota. **No adivines.**

---

## Antes de empezar

- No abras la llave.
- No busques la conferencia por su fecha para ver quién preguntó.
- Si una pregunta te resulta obvia y rápida, está bien: la mayoría lo son. Las difíciles son pocas y son las que importan.
- Cuando dudes entre dos valores, elige uno y escribe por qué dudaste. **Un «no sé» documentado vale más que un acierto adivinado.**
- La columna `fragmento que te hizo decidir la postura` es la frase exacta del texto que te hizo elegir. Con copiar cinco o seis palabras basta.

Cuando termines los 30, avisa y paramos ahí.
