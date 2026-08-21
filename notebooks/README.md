# notebooks

Exploración y figuras. **Sin lógica reutilizable**: eso vive en `src/estenograficas/`
y se importa. Si una celda hace algo que valga la pena correr dos veces, se muda al paquete.

Regla práctica: un notebook puede tener `from estenograficas import ...` y `df.plot(...)`.
No puede tener la función que parsea.
