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

En 4 835 de los 7 862 objetos, `idObjeto` es exactamente el hash de `nombre.lower()` (por
ejemplo, `death/death`, nombre `Death`, tiene id `8C882C7C958E9802` = hash de `death`). En los
3 027 restantes la cadena en minúsculas no aparece en el archivo, así que no se puede
comprobar, pero ninguno la contradice. Consecuencia: renombrar un objeto exigiría la función
de hash (fase 6); hasta entonces el nombre y la identidad no se editan.
