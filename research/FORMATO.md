# Notas de formato

Hallazgos sobre `scripts.obsp` que complementan el apéndice A de `PLAN_MAESTRO.md`. Todo se
midió sobre la copia de Steam (SHA-256 `B46DD3DA…`), sin incorporar datos del juego al
repositorio.

## 2026-10-03 — Fase 1

### Verificado con el núcleo del proyecto

Lo mismo que el prototipo, ahora reproducido por `python -m d2scriptviewer verify` y por
`tests/test_golden.py`:

- La reconstrucción del contenedor da el SHA original, también recodificando los 4 172 BOD.
- Los 4 172 BOD salen idénticos; sus contadores de cabecera (número de nombres y longitud
  máxima en bytes) coinciden con los recalculados.
- Las 3 690 cabeceras de script son coherentes (versión 1, longitud máxima de símbolo real,
  hash de ruta y grupo iguales a los del índice).
- 70 182 pares hash↔cadena sin conflictos en ningún sentido; ninguna cadena no ASCII,
  incluidas las `05`.
- Las tablas de tipos (A.1) y de tags (A.2) coinciden exactamente. El recuento de `07`
  (146 328) no incluye los 4 172 objetos raíz, que no llevan tag.
- Los 3 406 `FC` apuntan a objetos que existen en el propio archivo.
- Bools: 27 062 valen 1 y 7 935 valen 0; ninguno tiene otro byte.
- Profundidad máxima del árbol BOD: 11 niveles.
- Las listas `09` usan el modo 0 (37 039) y el 1 (7); los mapas `0A`, solo el 1 (39). El
  decodificador rechaza cualquier otro modo en lugar de suponer su significado.

### Hipótesis: `idObjeto` = hash del nombre en minúsculas

**Confirmada en los 7 862 objetos el 2026-10-04** con la función de hash (ver abajo).

En 4 835 de los 7 862 objetos, `idObjeto` es exactamente el hash de `nombre.lower()` (por
ejemplo, `death/death`, nombre `Death`, tiene id `8C882C7C958E9802` = hash de `death`). En los
3 027 restantes la cadena en minúsculas no aparece en el archivo, así que no se puede
comprobar, pero ninguno la contradice. Consecuencia: renombrar un objeto exigiría la función
de hash (fase 6); hasta entonces el nombre y la identidad no se editan.

## 2026-10-04 — Fase 6: la función de hash

Es un **CRC-64 reflejado** con polinomio `0x0060034000F0D50B` (forma reflejada
`0xD0AB0F0002C00600`) y valor inicial y XOR final `0xFFFFFFFFFFFFFFFF`. Se dedujo solo con los
70 182 pares hash↔cadena del archivo, sin código ajeno ni análisis del ejecutable:

1. **Las cadenas de un carácter** delatan una estructura lineal sobre GF(2): el XOR de los hashes
   de `'0'` y `'1'`, `'0'` y `'2'`, `'0'` y `'3'`… se combina como el XOR de los caracteres. Cambiar
   el bit k del carácter hace siempre XOR con `0x01A1561E0005800C << k`.
2. **El prefijo no importa**: en todas las cadenas, cambiar el bit k del último carácter produce
   ese mismo XOR (por ejemplo, `'10'` frente a `'11'`). Es lo que hace un CRC por tablas: el
   último byte entra como `T[byte]`, y `T` es lineal.
3. **El penúltimo carácter** se propaga como en un CRC reflejado:
   `crc = (crc >> 8) ^ T[(crc ^ byte) & 0xFF]`. Con `T[0x80]` = polinomio reflejado sale
   `0xD0AB0F0002C00600`, y `T[1] = 0x01A1561E0005800C` cuadra con el paso 1.
4. **El resto depende solo de la longitud**: para cada longitud (89 distintas), el XOR del hash
   con el CRC «en bruto» (valor inicial 0, sin XOR final) es constante. Esas 89 constantes cuadran
   con valor inicial y XOR final `~0`. La cadena vacía da 0, como en el archivo.

Comprobado: los 70 182 pares, y `hashRuta`, `hashNombre`, `hashCarpeta`, `hashClase` e `idObjeto`
de los 7 862 objetos. El polinomio no es ninguno de los CRC-64 habituales (ECMA-182, ISO, Jones),
y por eso no apareció en las pruebas anteriores (sección 2.4 del plan). Lo comprueban
`python -m d2scriptviewer verify` y `tests/test_golden.py`; los tests sintéticos contrastan la
implementación por tablas con una bit a bit en forma normal.

### Lo que no explica: enteros de 32 bits con aspecto de hash

De los 18 660 enteros `02` distintos del archivo, 15 467 tienen pinta de hash (|valor| ≥ 1 000 000)
y aparecen 67 453 veces (`OnStateOne = 0x4DFA84A3`, `MeshID`…). Comparados con las mitades alta y
baja del CRC-64, y con el CRC-32 de zlib, de las 70 182 cadenas conocidas y sus minúsculas, solo
coinciden 3, 1 y 0 valores, lo que cabe esperar del azar. Usan otra función, o hashean textos que
no están en el archivo; no se ha investigado más.
