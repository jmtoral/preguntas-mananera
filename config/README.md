# config/

Conocimiento editorial versionado. **No son datos derivados: son decisiones humanas**, y por eso
viven en el repo y no en `data/`, que está en `.gitignore`.

## `puente_medios.csv`

Une el medio **como el periodista lo dice en la conferencia** con el **beneficiario de la
publicidad oficial federal**. Sin esta tabla no hay cruce posible.

**Por qué no puede ser automática.** El nombre hablado casi nunca es la razón social:

| lo que dice el periodista | quién cobra en realidad |
|---|---|
| Contralínea | Difusión de Información, S.A. de C.V. |
| Revista Fortuna | V&L Global Services Consulting & Advisors Busines, S.C. |

Ningún pareo por parecido de cadenas encuentra esos dos. Se probó y falló: dio "solo 4 de 20
medios reciben dinero", que resultó falso. **Un `confianza: pendiente` significa "no se ha
investigado", nunca "no cobra".**

| columna | qué es |
|---|---|
| `medio_hablado` | como lo dice el periodista, sin tocar |
| `clave_normalizada` | la llave de unión con `hilos.jsonl` |
| `intervenciones` | veces que ese medio recibió la palabra |
| `rfc_beneficiario` | la llave estable del lado de publicidad oficial |
| `beneficiario_canonico` | nombre canónico en el dataset de gasto |
| `monto_2024_2026` | pesos recibidos en la ventana que traslapa con el corpus |
| `confianza` | `alta` = verificado por una persona · `media` = pareo automático, **revisar** · `pendiente` = sin investigar |
| `nota` | por qué se decidió así |

### Lo que falta

43 de 60 medios están `pendiente`, incluidos varios de los que más preguntan: Noticiero en
Redes (65 intervenciones), Código Libre (44), Diario 24 Horas (39), Proceso (33).

Tres explicaciones posibles para cada uno, y hay que distinguirlas antes de concluir nada:

1. Cobra bajo una razón social que no se parece al nombre hablado, como Contralínea.
2. Cobra de gobiernos **estatales o municipales**. El dataset de publicidad oficial es **solo
   federal**, así que ese dinero no aparecería aquí.
3. De verdad no cobra.

### Advertencia de lectura

Este cruce va a invitar la lectura *"a quien le pagan pregunta más suave"*. **El dato no la
sostiene todavía**, por tres razones:

- Es una **asociación descriptiva**, no una relación causal.
- El tamaño de audiencia empuja a la vez el gasto publicitario y la probabilidad de recibir la
  palabra. Es un confusor obvio y no está controlado.
- **Ninguna pregunta está clasificada por postura.** Hoy solo se puede cruzar dinero contra
  *frecuencia*, no contra *dureza*.
