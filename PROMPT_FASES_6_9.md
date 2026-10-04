<!-- Prompt para continuar el plan en una sesión nueva de Claude Code abierta en D2ScriptViewer. Pégalo tal cual, o escribe: "Lee y ejecuta PROMPT_FASES_6_9.md". -->

# Ejecutar PLAN_MAESTRO.md: fases 6 a 9

Vamos a seguir con `PLAN_MAESTRO.md` desde la fase 6 hasta la 9. El primer hito (fases 0 a 4) y
la fase 5 están cerrados y validados en el juego.

## Antes de escribir nada

Lee completos `CLAUDE.md` y `PLAN_MAESTRO.md`:

- las notas fechadas del principio;
- las secciones 2.4, 7, 8, 9 y 14;
- el apéndice A, incluidas las hipótesis de A.3 sobre el bytecode.

Lee también `research/FORMATO.md`, `research/PRUEBAS_EN_JUEGO.md` y `CREDITS.md`. Esos archivos
mandan: si algo de este mensaje choca con ellos, para y pregúntame.

Comprueba el punto de partida y dímelo en dos líneas:

- `git log --oneline` debe empezar por `7462fe8 Fase 5 cerrada…`;
- `python -m unittest discover -s tests -v` debe dar 155 tests en verde;
- `python -m d2scriptviewer verify` debe dar «Todo correcto» con
  `D2SV_OBSP=C:\Users\vicen\Documents\Extractions\Darksiders\scripts.obsp`.

## Orden y alcance

- Fases en el orden del plan: 6 (función de hash), 7 (scripts compilados), 8 (exportación y
  parches) y 9 (distribución). Si al empezar te pido otro orden, sigue el mío.
- Las fases 6 a 9 **no tienen criterios «Hecho cuando» en el plan**. Al empezar cada fase:
  1. analiza los datos reales;
  2. propón los criterios de cierre y las decisiones abiertas, con una recomendación en cada
     una, y pregúntamelos (como en la fase 5);
  3. regístralos en el plan con una nota fechada;
  4. solo entonces implementa.
- Las fases 6 y 7 son investigación con resultado incierto. Antes de empezarlas acuerda conmigo
  hasta dónde llegar y cuándo parar. Si las vías acordadas no dan resultado, para, documenta lo
  descartado en `research/` y en la sección 2.4 del plan, y pregúntame. No abras vías nuevas sin
  permiso: por ejemplo, analizar `Darksiders2.exe` con Ghidra o x64dbg, o tocar el repositorio de
  Darksiders2DLL.

## Puntos de partida por fase

- **Fase 6 (hash de 64 bits):**
  - El banco de pruebas son los 70 182 pares hash↔cadena del archivo.
  - Antes de proponer candidatos, comprueba la lista de lo ya descartado (sección 2.4).
  - Hay un dato nuevo en `research/FORMATO.md`: en 4 835 objetos, `idObjeto` es el hash del
    nombre en minúsculas.
  - Toda implementación ajena (CityHash, MurmurHash, xxHash, SpookyHash, FarmHash, lookup3…) se
    registra en `CREDITS.md` en el mismo cambio, con licencia comprobada. Nada con copyleft sin
    preguntarme.
  - Si aparece la función: tests con los 70 182 pares; levantar la prohibición de crear cadenas
    con hash (`CLAUDE.md` y `edits.parse_known_name`) solo con mi visto bueno; y una prueba en el
    juego de una cadena nueva.
- **Fase 7 (scripts, tipo 0):**
  - Siguen siendo de solo lectura hasta que formalices su estructura.
  - Primero el desensamblador de solo lectura; después, los parches de literales del mismo tamaño.
  - El único patrón confirmado es `NumSlots\0`, `0x23` + int32 y luego `0x29 0x32` en
    `death/death`.
  - Cualquier parche se prueba en el juego conmigo antes de cerrar la fase.
- **Fase 8 (exportar y parches):**
  - JSON por objeto con las referencias resueltas, `manifest.json`, CSV para `FloatTable` y el
    archivo de parche `.d2svpatch.json`.
  - Decide conmigo el formato del parche: cómo identifica objetos y propiedades para sobrevivir a
    una restauración de Steam, y si incluye cambios estructurales.
  - Reaplicar un parche sobre el original debe dar exactamente el mismo archivo que el guardado
    a mano (mismo SHA). Prueba en el juego: restaurar, reaplicar y jugar.
- **Fase 9 (distribución):**
  - PyInstaller y un workflow de release como el de Darkstractor.
  - Antes de nada lee la entrada de PyInstaller en `..\Darkstractor\CREDITS.md` (su licencia y la
    nota sobre publicar binarios) y pregúntame.
  - La sección 12 tiene abierto «Repositorio público». No hay remoto, así que el release, la CI
    en GitHub y el número de versión los decido yo: pregúntame.

## Cómo trabajar (lo aprendido hasta ahora)

- **Archivo real:** usa siempre la copia de `D2SV_OBSP`. Nunca escribas en la carpeta del juego:
  allí solo guardo yo con la herramienta. Los ensayos van a carpetas temporales o a `build\`.
- **Tests antes de afirmar:** la reconstrucción con el SHA `B46DD3DA…`, los 4 172 BOD y los
  3 690 scripts deben seguir pasando. Los tests nuevos de la CI son sintéticos, sin datos del juego.
- **Commits:** solo si los tests pasan. Comprueba el código de salida de `unittest`; no lo pases
  por una tubería que lo oculte. Un commit local por fase, sin push.
- **Pruebas en el juego:**
  1. ensaya la edición sobre una copia y dame qué editar, qué esperar y cómo restaurar;
  2. espera mi resultado;
  3. antes de registrarlo, lee el estado del archivo instalado (SHA, tamaño, `.d2sv_backups`) y
     compáralo con lo que digo; si no cuadra, pregúntame.
- **Sin capturas de pantalla del escritorio:** pueden recoger cosas mías. Para la GUI, usa tests
  y mediciones.
- **Interfaz:** la GUI no puede congelarse; el trabajo pesado va en hilos con `queue`.
  Confirmaciones y avisos por `app.ask`, `app.ask_save`, `app.inform` y `app.alert`.
- **Al cerrar cada fase:**
  1. tests completos y `verify`;
  2. criterios comprobados uno por uno;
  3. nota fechada al principio del plan;
  4. `CLAUDE.md` (estado, mapa del código y comandos);
  5. `CHANGELOG.md` en `[Unreleased]`;
  6. commit;
  7. resumen breve: qué funciona, tests, desviaciones y siguiente paso. Di en una línea qué
     entrada de `CREDITS.md` añadiste o cambiaste.

## Puntos de control: para y espérame

1. Al proponer los criterios y decisiones de cada fase.
2. En cada prueba en el juego.
3. Si en la fase 6 o la 7 se agotan las vías acordadas.
4. Si algo contradice el apéndice A o una decisión del plan, o tendrías que suponer qué significa
   un campo.
