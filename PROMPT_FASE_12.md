<!-- Prompt para empezar la fase 12 en una sesión nueva de Claude Code abierta en D2ScriptViewer. Pégalo tal cual, o escribe: "Lee y ejecuta PROMPT_FASE_12.md". -->

# Fase 12: interfaz en inglés, con el idioma seleccionable

La herramienta está publicada (v1.1.0) y la voy a subir a Nexus Mods, donde casi todo el público
habla inglés. Quiero que la interfaz se pueda usar en inglés o en español, a elección del usuario,
y que la elección se recuerde.

## Antes de escribir nada

Lee completos `CLAUDE.md` y `PLAN_MAESTRO.md`:

- las notas fechadas del principio;
- las secciones 5, 6, 8 y 12;
- en la sección 7, las fases 10 y 11, como modelo de criterios «Hecho cuando».

Lee también `GUIA_MODDER.md`, `README.md` y `CREDITS.md`. Esos archivos mandan: si algo de este
mensaje choca con ellos, para y pregúntame.

Comprueba el punto de partida y dímelo en dos líneas:

- `git log --oneline` empieza por el commit que añade este prompt, y justo debajo está
  `bd59bcb Plan: versión 1.1.0 publicada en GitHub`;
- `python -m unittest discover -s tests -v` da 269 tests en verde, ninguno omitido.

El `scripts.obsp` instalado está modificado (SHA `5ECCFA9E…`), y 14 tests fallan contra él porque
comparan con el SHA de Steam. Para los tests:

1. copia `media\scripts.original.obsp` del juego a una carpeta temporal fuera del repositorio;
2. comprueba que su SHA es `B46DD3DA…`;
3. apunta `D2SV_OBSP` a esa copia.

## Lo que ya se sabe (medido el 19 de noviembre de 2026)

- **Los textos no están solo en `gui/`.** Un recuento heurístico encontró al menos 533 textos
  visibles de más de una palabra, sin contar las etiquetas de una sola palabra («Abrir…»,
  «Guardar»). Por módulo:

  | Módulo | Textos | Módulo | Textos |
  |---|---|---|---|
  | `gui/app.py` | 103 | `edits.py` | 34 |
  | `saving.py` | 69 | `formats/script.py` | 26 |
  | `patches.py` | 56 | `document.py` | 24 |
  | `cli.py` | 55 | `verification.py` | 16 |
  | `formats/bod.py` | 44 | el resto | menos de 15 cada uno |

  La GUI muestra los errores, avisos y resúmenes que generan los módulos del núcleo:
  `edits`, `saving`, `validation`, `patches`, `document.PathError`…
- **`wording.py`** solo sabe los plurales del español.
- **Los nombres de presentación de los scripts forman parte de las rutas:** `Funciones`,
  `Estados`, `Miembros`, `Valores iniciales`, `Parámetros`, `Hash de ruta`, `Clase base` y
  `Símbolos` (`formats/script.py`). Por eso salen en:
  - Ctrl+G;
  - «Copiar ruta de la propiedad» y «Copiar ruta completa»;
  - la tabla de `GUIA_MODDER.md`;
  - los parches: `apply_patch` compara la `etiqueta` guardada con `bod.path_label`
    (`patches.py:469`). Si se traducen sin más, un parche hecho en un idioma no se aplica en el
    otro.
- **Los diálogos nativos de Windows** siguen el idioma del sistema, no el de la aplicación: los
  de abrir y guardar archivo, y los botones Sí/No de `messagebox`.

## Invariantes de esta fase

- **El idioma nunca cambia un byte** de lo que se guarda, se exporta o se escribe en un parche.
- `.d2svpatch.json` y la exportación JSON conservan su formato y sus claves (`formato`, `valor`,
  `etiqueta`…). Un parche creado en un idioma se aplica en el otro.
- **Los datos del juego no se traducen nunca:** nombres de objetos, campos, clases y cadenas.
- Solo biblioteca estándar.
- Comentarios, identificadores y documentación interna siguen como ahora.

## Decisiones que debes proponerme (con una recomendación en cada una)

1. **Mecanismo.** Te sugiero estudiar esta opción:
   - funciones `_()` y `ngettext()`, al estilo gettext, en un módulo `i18n.py`, con la clave en
     el texto en español que ya está en el código;
   - el catálogo inglés en un módulo Python, sin `.po`, `.mo` ni archivos de datos, así que ni
     `D2ScriptViewer.spec` ni los archivos incluidos de la autoprueba cambian (sí `MODULES` de
     `selftest.py`).

   Compárala con lo que veas mejor.
2. **Idioma inicial:** si el primer arranque lo decide el idioma de Windows (español si es `es-*`,
   inglés si no) y después manda lo guardado en `config.json` (añadir la clave a `KNOWN_KEYS`).
3. **Cambio de idioma:**
   - dónde va el menú; su etiqueta debería entenderse en los dos idiomas, p. ej. «Idioma /
     Language»;
   - si se aplica en caliente o al reiniciar, con oferta de reiniciar. Mide qué cuesta cada
     opción antes de recomendar.
4. **Rutas:** te sugiero estudiar esta opción:
   - la etiqueta interna (la que guardan los parches) es canónica, la de hoy;
   - el árbol muestra los nombres traducidos;
   - Ctrl+G acepta los dos vocabularios;
   - «Copiar ruta» copia en el idioma de la interfaz.

   Dime qué pasa con `GUIA_MODDER.md`.
5. **Alcance:**
   - la GUI, junto con todo mensaje del núcleo que llegue a ella;
   - la CLI: si se queda en español (subcomandos, opciones y salida) o qué parte se traduce;
   - la autoprueba del `.exe`.
6. **Documentación en inglés:** README (sección o archivo aparte) y una versión inglesa de
   `GUIA_MODDER.md`. Dime si va en esta fase o después.
7. **Detalles de presentación:**
   - los nombres de la columna Tipo, que la barra de búsqueda del objeto compara tal como se ven;
   - los separadores de miles en contadores («7 862» frente a «7,862»);
   - el título de la ventana y «Acerca de».

Propón también los criterios «Hecho cuando». Como mínimo:

- un test que recorra con `ast` todas las llamadas a `_()` y `ngettext()`, compruebe que cada
  texto tiene su traducción con los mismos marcadores de formato y que no sobran entradas;
- un test de la GUI en inglés que recorra menús y widgets buscando restos en español (tildes,
  «ñ», «¿», «¡», «»»);
- un test de persistencia del idioma;
- un parche creado en español se aplica en inglés, y al revés;
- guardar la misma edición en los dos idiomas da el mismo SHA;
- Ctrl+G funciona con los dos vocabularios;
- el `.exe` construido pasa la autoprueba;
- quedan actualizados:
  - el plan: la fase 12 en la sección 7 y una nota fechada;
  - `CLAUDE.md`: la regla «La interfaz… van en español» y el mapa del código;
  - `CHANGELOG.md` en `[Unreleased]`, el README y `GUIA_MODDER.md` (el menú nuevo).

No hace falta prueba en el juego: no cambia el formato ni el guardado.

## Cómo trabajar (lo aprendido hasta ahora)

- **Archivo real:** usa la copia de `D2SV_OBSP`. Nunca escribas en la carpeta del juego.
- **Tests antes de afirmar.** Comprueba el código de salida de `unittest`; no lo pases por una
  tubería que lo oculte. `PYTHONIOENCODING=utf-8` en la consola.
- **Commits:** solo si los tests pasan; locales, sin push ni etiquetas.
- **Sin capturas de pantalla del escritorio.** Para la GUI, usa tests y mediciones. La revisión
  visual del inglés la hago yo.
- **Interfaz:**
  - la GUI no puede congelarse;
  - confirmaciones y avisos por `app.ask`, `app.ask_save`, `app.inform` y `app.alert`;
  - los atajos se prueban con `invoke_binding`.
- **El inglés lo redactas tú y lo reviso yo.** Antes de traducir en masa, dame un glosario de los
  términos de la herramienta y una muestra:
  - objeto, propiedad, referencia, hueco, tramo, copia rotativa, parche, pista, pendiente,
    revertir…;
  - unos 30 textos traducidos, con menús, avisos de guardado y errores.
- **Versión:** esto sería la 1.2.0, pero el número y la release los decido yo.

## Puntos de control: para y espérame

1. Al proponer las decisiones y los criterios «Hecho cuando».
2. Con el glosario y la muestra de traducciones.
3. Antes de cerrar la fase: dime cómo arrancar la GUI en inglés y en español para revisarla.
4. Si algo choca con los invariantes, con el apéndice A o con una decisión del plan.
