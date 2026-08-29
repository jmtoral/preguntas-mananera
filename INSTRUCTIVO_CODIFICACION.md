# Instructivo de codificación

Para codificar `data/gold/muestra_oro_hoja.xlsx`. Se lee completo una vez antes de empezar y después se consulta.

---

## Qué estás haciendo y por qué

Vas a codificar 150 preguntas a mano. **Esas 150 no son el dataset.** El dataset son las ~22 mil que va a clasificar el modelo. Las 150 son la **calibración**: sirven para medir si las otras 22 mil son confiables. Es el mismo procedimiento que se usaba con asistentes de investigación humanos mucho antes de que hubiera modelos de lenguaje.

Por eso importa el orden. Codificas **antes** de que el modelo corra sobre el corpus y **sin ver** su salida. Si se clasifican las 22 mil primero, dejas de codificar a ciegas y el número final acaba midiendo otra cosa.

La hoja no trae nombre de periodista ni medio, ni siquiera el identificador de la pregunta —que lleva la fecha y permitiría buscar de quién es—. Solo un código, `P-001`. La llave existe, está en `data/gold/muestra_oro_LLAVE_no_abrir.csv`, y **no hay que abrirla mientras codificas**. Ver «Proceso» o «Contralínea» mientras decides mete la conclusión dentro del dato.

**En dos lotes.** Primero los 30 del lote 1. Ahí paramos, revisamos dónde dudaste y corregimos las definiciones. Después los 120 del lote 2. Una semana después vas a recodificar 20 del lote 1 sin ver lo que pusiste: eso mide tu consistencia contigo mismo, y si no coincides contigo, las categorías están mal definidas y ningún clasificador lo arregla.

**Una advertencia sobre este documento.** Los ejemplos trabajados son mi lectura, no la tuya. Elegiste esta versión sabiendo el costo: tu codificación se va a parecer a la mía por construcción, y eso infla el acuerdo. Cuando reportemos el número hay que decirlo. Donde no estés de acuerdo con un ejemplo, **anótalo**: eso es información, no un error tuyo.

Todas las preguntas de este instructivo están **fuera** de las 150. Ninguna es de las que vas a codificar.

---

## Una sola columna, cuatro valores

| valor | qué es |
|---|---|
| `crítica al gobierno` | pone en aprieto al gobierno federal: señala contradicción, fracaso, omisión, opacidad |
| `afín al gobierno` | lo halaga, da por buena su versión, o le ofrece plataforma para lucirse |
| `crítica a un tercero` | le pega a la oposición, a un actor externo, a un empresario, a la prensa |
| `neutral` | pide un dato o una explicación sin carga en ninguna dirección |

Y `no clasificable` cuando de verdad no se puede, que es una respuesta y no un hueco.

**Por qué existe `crítica a un tercero`.** El 15% de las preguntas habla de la oposición o de un actor externo. Una pregunta durísima contra García Luna, contra Salinas Pliego o contra Trump no es crítica al gobierno ni lo halaga, pero tampoco es neutral: favorece al gobierno sin ser un halago. Sin esta categoría acabaría revuelta con las peticiones de dato, y es de las cosas más interesantes que tiene el corpus.

**Por qué no hay «de interés público».** Porque no está en el mismo eje que las demás: mide el mérito de la pregunta, no su dirección, y casi todo el buen periodismo es crítico *y* de interés público a la vez. Además, ponerle ese nombre a una categoría afirma que las otras no lo son, y este trabajo mide y describe, no adjetiva.

---

## La regla que resuelve casi todo: **la carga está en la premisa, no en el tema**

Antes de clasificar, lee **lo que la pregunta da por sentado**. Ahí está el signo, no en el asunto del que habla.

Dos preguntas sobre lo mismo:

> *«Sobre este mismo tema de salud, Presidenta, preguntar si ¿hay algún dato de avance sobre la credencialización universal?»*

`neutral`. La premisa no afirma nada. Quiere el dato.

> *«Han pasado algunos meses, hay avances importantes, sabemos y hemos seguido de cerca estos o los mismos. ¿Cuál es el mensaje que envía en estos momentos? Sabemos que hay detenciones también importantes en varios estados.»*

`afín al gobierno`. La premisa ya afirma que hay avances importantes y la pregunta es una invitación a mandar un mensaje. **Mismo tema, signo distinto, y la diferencia está entera en la premisa.**

Lo mismo del otro lado:

> *«El PAN envió una solicitud a la Corte Internacional de Justicia y a la ONU para revocar a Rubén Rocha, del gobierno de Sinaloa. Me gustaría saber su opinión al respecto.»*

`neutral`. Habla de la oposición, pero la premisa es un hecho verificable dicho sin carga. Que ella pueda aprovecharlo para pegarle al PAN no es asunto de la pregunta: **se codifica lo que hace la pregunta, no lo que podría hacer la respuesta.**

> *«¿Qué tanto daño ha hecho en la Ciudad de México este cártel inmobiliario encabezado por el nuevo dirigente del PAN?»*

`crítica a un tercero`. Aquí la premisa ya dio por probado que hay un cártel inmobiliario y que lo encabeza el dirigente del PAN. La pregunta no es si existe, es cuánto daño hizo.

---

## La pregunta clave cuando hay un tercero de por medio: **¿quién da el golpe?**

Salió del lote 1 y resuelve la confusión más frecuente.

- Si lo da **la pregunta** —la premisa ya da por culpable al tercero— es `crítica a un tercero`.
- Si la pregunta solo **tiende la mano** para que lo dé el gobierno, es `afín al gobierno`.

> *«Hace unos días la gobernadora de Chihuahua, María Eugenia Campos…»* seguido del reclamo.

`crítica a un tercero`. El golpe lo da la pregunta.

> *«Me gustaría preguntarle su opinión acerca de si el feminismo es compatible con la ideología y el pensamiento de derecha.»*

`afín al gobierno`. La pregunta no ataca a nadie: le entrega el micrófono para que ataque ella. Y en efecto lo hizo, largo.

**Y el error que hay que evitar: `crítica a un tercero` no es «la pregunta menciona a un tercero».** Es contra quién va el reclamo. Si la pregunta habla de un alcalde, de un empresario o de Estados Unidos **pero le reclama al gobierno**, es `crítica al gobierno`. La prueba sigue siendo la misma: **¿quién queda mal si la pregunta tiene razón?**

## Las peticiones van a `afín al gobierno`

Decidido en el lote 1. Una pregunta que pide algo —*«¿podría incluirse la educación en empatía hacia los animales?»*, *«¿nos podría apoyar con este tema?»*— trata al gobierno como interlocutor benévolo y le da la ocasión de conceder. No es elogio, pero es del lado amable.

**Consecuencia que hay que tener presente al leer los resultados:** `afín al gobierno` es entonces **más ancho que el elogio**. Contiene tres cosas — halago, plataforma para lucirse o para pegarle a un rival, y petición— y las tres tienen en común que le sirven al gobierno.

**Excepción:** si la petición viene con reproche —*«llevamos tres años pidiéndolo y nada»*— es `crítica al gobierno`. El reproche manda sobre la petición.

## Más ejemplos trabajados

> *«Oiga, y aprovechando el viaje, hablando de las reformas constitucionales hay quien piensa, percibe que hay cierta prisa en implementarlas… ¿Por qué la prisa? ¿Por qué no tomarse el tiempo de analizar estas reformas que afectan a todo el país?»*

`crítica al gobierno`. No insulta ni acusa: incorpora una crítica ajena («hay quien percibe») y pide cuentas por ella. **Crítica no quiere decir grosera.**

> *«Entonces: ¿no hay problema en estos centros de acopio, Presidenta?, porque se han acercado a nosotros, los productores.»*

`crítica al gobierno`. Ella acaba de describir el Plan Frijol; él contrapone el testimonio de los productores. Contradecir la versión oficial con otra es criticar, aunque el tono sea amable.

> *«¿Cuántos elementos se enviaron para reforzar y hasta cuándo estarían?»*

`neutral`. Quiere el número.

> *«¿Cuál es su opinión de que a Fox y Calderón se nombrara persona non grata?»*

`crítica a un tercero`. El objeto son dos expresidentes de oposición y la pregunta se apoya en una sanción ya impuesta.

> *«Insistir en el tema de García Luna: ¿Cree que esta sentencia da un poco de justicia a todas las víctimas que dejó la guerra contra el narco desde 2006 hasta 2012?»*

`crítica a un tercero`. La premisa atribuye las víctimas a la guerra de gobiernos anteriores.

---

## El caso que más se equivoca

Cuando la pregunta habla de un tercero **pero le reclama al gobierno**, es `crítica al gobierno`. El tema es el tercero; el reclamo es para quien está en el estrado.

> **contexto** — R: *Hemos hablado de que, terminando la aplicación de la reforma al Poder Judicial, hay otros temas que se tienen que discutir…*
> **pregunta** — *«Usted mencionaba ahí dos casos de García Luna que están en proceso, pero cuánto tiene que salió García Luna y esos casos están estancados.»*

`crítica al gobierno`. Habla de García Luna, pero lo que señala es que **el gobierno actual** tiene los casos parados. Compárala con la de arriba, que es del mismo personaje y va a la categoría contraria.

**La prueba rápida:** ¿quién queda mal si la pregunta tiene razón? Si es el gobierno, es `crítica al gobierno`, sin importar de quién hable.

---

## Las columnas de contexto, y las preguntas cortadas

La hoja trae **dos** columnas de contexto, una de cada lado:

- **`lo que se dijo antes`** — hasta cuatro turnos previos.
- **`lo que siguió`** — lo que vino después.

Las dos son contexto, no el objeto: **se codifica la pregunta, no la respuesta.** Existe la de la derecha porque hay preguntas que la estenográfica corta a media frase —la presidenta interrumpe— y sin ver cómo siguió el intercambio, el fragmento es ilegible. **Son 16 de las 150**, y llevan la marca `⟨la pregunta queda cortada aquí en la versión estenográfica⟩`.

Ejemplo real de la muestra:

> **pregunta** — *«El cambio de nombre de "Solidaridad" por "Playa del Carmen", que representa lo más oscuro de ese…»*
> **lo que siguió** — PRESIDENTA: *Hay que preguntarle a la ciudadanía.* / PRENSA: *Ya se realizó.* / PRESIDENTA: *Ah, ¿sí?* / PRENSA: *Sí. Fue un éxito. La gente no quería saber nada de lo que era el gobierno de Carlos Salinas de Gortari…*

Sola es incodificable. Con lo que siguió se ve que el objeto es Salinas, y entonces sí se puede decidir.

**Si aun con las dos columnas no se entiende, `no clasificable` y una nota.** No adivines: el corte está en la fuente, no es culpa tuya, y una decisión inventada contamina la calibración más que un hueco declarado.

**Y si el turno no es una pregunta, también va `no clasificable`.** Hay turnos de prensa que son conversación pura —*«Estuve 12 años.»*, *«Van a hacer el Día de Muertos.»*—. Son turnos reales del corpus y por eso están en la muestra, pero no tienen postura que medir. Márcalos y sigue; **`no clasificable` es una respuesta, no un hueco**, y dejarlos en blanco sí es un hueco.

**Un tercio de las preguntas del corpus tienen menos de 80 caracteres**, así que la muestra trae muchas. No es un defecto del muestreo: la conferencia es así. Al final la confiabilidad se va a reportar **partida en dos** —fragmentos y preguntas sustantivas— para saber si el instrumento sirve igual en las dos, en vez de un promedio que esconde la diferencia. Tú no tienes que hacer nada distinto: codifica las dos igual.

## Cuando dudes

- **Si caben dos, elige la que carga más peso y escribe la duda.** La columna `notas / dudas` vale tanto como la otra: el lote de 30 existe para encontrar dónde las definiciones fallan, y eso solo se ve en tus dudas.
- **Si la pregunta no se sostiene sola** —hay fragmentos como *«La hizo a un lado.»*—, mira el contexto. Si con él se entiende, códificala; si no, `no clasificable` y una nota. **No adivines.**
- **Si es una crítica al gobierno y a un tercero a la vez**, gana el gobierno: es el eje que interesa medir.
- La columna `fragmento que te hizo decidir` es la frase exacta que te hizo elegir. Con cinco o seis palabras basta. Sirve para que después se pueda auditar la decisión sin volver a leer todo.

## Antes de empezar

- No abras la llave.
- No busques la conferencia por su fecha para ver quién preguntó.
- La mayoría son rápidas y obvias. Las difíciles son pocas y son las que importan.
- Un «no sé» documentado vale más que un acierto adivinado.

**Cuando termines los 30, avisa y paramos ahí.**
