# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

D2ScriptViewer es un visor/editor de escritorio para `media\scripts.obsp` de Darksiders II
Deathinitive Edition (PC). El usuario fijó este orden de prioridades:

1. Visualizar.
2. Modificar.
3. Guardar en el mismo formato `.obsp`, creando antes una copia intacta del original.

Exportar a JSON es secundario.

`PLAN_MAESTRO.md` es la fuente de verdad: fases, decisiones, pruebas y riesgos. Su
**apéndice A** contiene la especificación verificada del formato. Léelo antes de implementar.
Cuando se cierre una fase o cambie una decisión, actualízalo con una nota fechada al
principio, como hace el plan de Darksiders2DLL.

Estado al 4 de octubre de 2026: **primer hito cerrado** (fases 0 a 4): visor, edición de
valores y guardado en `.obsp` con copia del original, validados en el juego. El juego carga un
archivo guardado por la herramienta, también con otro tamaño y los offsets recalculados, y
restaurar devuelve el SHA de Steam (`research/PRUEBAS_EN_JUEGO.md`). Fase 5 (edición
estructural) cerrada y validada en el juego: el juego tolera que se renumeren los objetos `07`
de un BOD. Sus decisiones (tuplas fijas, nulos solo en huecos de objeto, qué bloquea y qué avisa
al guardar) están al principio del plan. Fase 6 cerrada y validada en el juego: la función de hash
es un CRC-64 reflejado (deducido de los datos), los valores `0F` admiten cadenas nuevas con
aviso, y el juego usa una cadena nueva para encontrar una animación del `.upak`. Fase 7
(scripts compilados) cerrada y validada en el juego: estructura completa, desensamblador y
parches de literales del mismo tamaño; el juego ejecuta un literal parcheado. Fase 8 (exportación
JSON/CSV y parches `.d2svpatch.json`) cerrada y validada en el juego: un parche reaplicado tras
restaurar reproduce byte a byte el archivo guardado a mano. Fase 9 (distribución) cerrada:
versión 1.0.0, ejecutable de Windows con PyInstaller 6.22.3 y workflow de release, preparados en
local; el push, la visibilidad del repositorio y la etiqueta los decide el usuario. Las fases 0
a 9 están cerradas. Fase 10 (búsqueda dentro del objeto) cerrada el 8 de octubre de 2026: una
barra en el panel de propiedades con un campo por columna, Ctrl+F para el objeto y Ctrl+Mayús+F
para la búsqueda global; sus dos tests con el archivo real (`RealTreeSearchTests`) pasan. Fase 11
(ir a una ruta) cerrada el 9 de octubre de 2026: Ctrl+G abre una barra «Ir a» que lee la ruta de
«Copiar ruta de la propiedad» o `objeto · propiedad` y salta a esa fila. Las decisiones de la sección 12 del plan están confirmadas: Python ≥ 3.10
con tkinter/ttk, copia llamada `scripts.original.obsp` junto al archivo, copias rotativas (las
últimas 5, en `.d2sv_backups\`) y licencia MIT a nombre de BOTProT800.

El usuario escribe en español. La interfaz, los comentarios y la documentación van en
español; los identificadores, en inglés (estilo de Darkstractor).

## Comandos

Ya existen:

```powershell
python -m d2scriptviewer                                    # GUI (o doble clic en D2ScriptViewer.pyw)
python -m d2scriptviewer --version
python -m d2scriptviewer info                               # huella, estado y objetos por tipo
python -m d2scriptviewer list --tipo Desc --clase Death --filtro death
python -m d2scriptviewer show death/death_desc --profundidad 3
python -m d2scriptviewer roundtrip --salida build\roundtrip.obsp
python -m d2scriptviewer verify                             # comprobaciones del apéndice A
python -m d2scriptviewer hash Death death/death_desc        # hash e idObjeto, sin archivo
python -m d2scriptviewer disasm death/death                 # miembros y código de un script
python -m d2scriptviewer export --salida build\export        # JSON por objeto, manifest y CSV
python -m d2scriptviewer patch crear --salida build\x.d2svpatch.json   # base: *.original.obsp o --base
python -m d2scriptviewer patch aplicar build\x.d2svpatch.json --salida build\y.obsp
python -m unittest discover -s tests -v                     # todos los tests
python -m unittest tests.<modulo>.<Clase>.<test>            # un solo test
$env:D2SV_OBSP = 'C:\ruta\a\scripts.obsp'                   # archivo real para CLI y tests
build\venv-pyinstaller\Scripts\python -m PyInstaller --noconfirm --workpath build\pyinstaller D2ScriptViewer.spec
dist\D2ScriptViewer.exe --autoprueba informe.txt            # autoprueba del .exe (sale con 0 si va bien)
```

El entorno `build\venv-pyinstaller` tiene PyInstaller 6.22.3, la versión que fija
`release.yml` y cuya licencia está verificada en `CREDITS.md`. Cambiarla exige volver a leer su
`COPYING.txt` y actualizar la entrada.

Los subcomandos (salvo `hash`) leen `--archivo`, o `D2SV_OBSP`, o la ruta del juego. `roundtrip --salida` se
niega a escribir encima de la entrada, de un archivo existente o de un `*.original.obsp`.

La GUI abre, por orden, el último archivo usado, `D2SV_OBSP` o el del juego.

## Mapa del código

- `d2scriptviewer/formats/`: `obsp.py` (contenedor y escritor), `bod.py` (árbol, codificador
  canónico, recorrido y presentación; `Note` es una fila de solo lectura; `child` da un hijo sin
  construir la lista entera; `parse_path_label` y `find_path`, la inversa de `path_label` de la
  fase 11: tramo a tramo, nombre exacto y si no sin mayúsculas ni tildes y único, `0x…` por valor,
  y el nodo válido más profundo con el motivo si falla), `script.py` (script
  completo: cabecera, miembros, valores iniciales, funciones y estados; `parse`, `encode`,
  `only_literals_changed` y `present`, el árbol de presentación enlazado al script),
  `bytecode.py` (tabla de 57 opcodes, `disassemble`/`assemble`, número de argumentos), `hashes.py`
  (`name_hash`, el CRC-64 del juego; `object_id`; diccionario global con variantes de
  mayúsculas y descuadres).
- `document.py`: archivo abierto con decodificación bajo demanda y caché (`bod()` es seguro
  entre hilos: todos reciben el mismo árbol). En los scripts, `bod()` da el árbol de
  presentación (`script.ScriptTree`) y `blob()` recodifica su `script`; solo se editan las hojas
  `Int32`/`Float32`/`Bool`, y las operaciones estructurales se rechazan.
- `edits.py`: validación del texto del usuario por tipo (`parse_name` admite cadenas nuevas con
  su hash calculado), avisos de identificador y de cadena nueva, y operaciones
  reversibles (`ValueEdit`, `InsertItem`, `RemoveItem`, `MoveItem`, `ReplaceValue`,
  `ReplaceTree`, agrupadas en `EditGroup`). Las rutas valen porque deshacer y rehacer son LIFO.
- `document.py` (fase 11): `parse_location` analiza `propiedad`, `objeto · propiedad`,
  `objeto::propiedad` o el objeto solo, sin resolver la propiedad (necesita el árbol, que puede
  estar decodificándose); `full_label` da `objeto · propiedad`; `looks_like_location` decide si el
  portapapeles parece una ruta. Los errores son `PathError`, con el tramo culpable (`start`, `end`).
- `document.py`: un objeto está **modificado si sus bytes difieren** de los de partida; nada de
  originales por ruta (las rutas se desplazan al insertar o quitar). `changes()` compara el árbol
  actual con `baseline_tree()` mediante `diffing.py` (alineamiento por huellas y LCS).
- `validation.py`: claves repetidas y `FC` sin destino bloquean `prepare_save`; los `*ID`
  repetidos nuevos avisan (listas alineadas con el diff, no por ruta).
- `saving.py`: `prepare_save` (en el hilo de Tk) y `execute_save` (en un hilo): autoverificar
  (también que los hashes de la tabla de cadenas y de los objetos modificados cuadran, y que en
  un script solo cambiaron literales),
  comprobar que se puede escribir, copia del original, copia rotativa, `.tmp` + `fsync` +
  `os.replace` y relectura con SHA. `restore_original`, `file_status`, `cleanup_orphan_tmp`.
  `fail_at` permite a los tests simular fallos en cada paso.
- `references.py` (índice `FC`, diccionario y `SlotIndex` de huecos en una pasada).
- `search.py`: `search`, la búsqueda global en un hilo, y `find_in_tree` (fase 10), la del
  objeto abierto. `find_in_tree` compara Nombre, Tipo y Valor tal como se ven (`row_value_text`)
  y devuelve las rutas en el orden de las filas, que es el lexicográfico. Corre en el hilo de
  Tk: el objeto mayor tarda decenas de milisegundos.
- `export.py` (fase 8): JSON por objeto con referencias resueltas, `manifest.json` y CSV de las
  `FloatTable`; nunca dentro de la carpeta del juego ni en una carpeta ocupada por otra cosa.
- `patches.py` (fase 8): `create_patch` deriva, comparando la base con el documento, operaciones
  que solo copian contenido del original (`valor`, `quitar`, `mover`, `insertar`, `nulo`,
  `copiar`, `referencia`) y se autoverifica reaplicándose; `apply_patch` comprueba objeto (ruta,
  identidad, SHA), etiqueta, valor anterior y huellas, y aplica todo como un paso de deshacer
  con `Document.run_operations` (si algo falla, no queda nada aplicado).
- `diffing.align`: alineamiento de listas por huellas, compartido por el comparador y los parches.
- `wording.py`: plurales («1 objeto», «2 objetos»).
- `verification.py`: las comprobaciones completas que usa `verify`.
- `selftest.py`: la autoprueba del ejecutable (`MODULES` debe listar todos los módulos; un test lo
  comprueba). `run_d2scriptviewer.py` es la entrada del `.exe` (siempre GUI, salvo
  `--autoprueba`), `D2ScriptViewer.spec` la receta de PyInstaller (copia a `build\licencias` los
  textos de licencia de terceros y `VERSIONES.txt`) y `THIRD_PARTY_NOTICES.md` los explica.
  `.github/workflows/release.yml` publica la release con una etiqueta `v*`.
- `gui/`: `app.py` (ventana, hilos, navegación, edición; `go_to_location` resuelve Ctrl+G, también
  tras decodificar en un hilo, con `_pending_location`), `object_tree.py`, `property_view.py`
  (árbol perezoso con tramos de 500, y la barra de búsqueda del objeto: recalcula en `show_bod` y
  `set_edited` sin mover la selección y navega con `reveal`; la barra «Ir a» y la pista retenida,
  `set_hint(..., hold=True)`, que la selección encolada de un salto no pisa),
  `editors.py` (editor en la celda, selector de referencias y `FillNullDialog`), `pending_view.py`, `details.py`,
  `script_view.py`, `search_view.py`, `theme.py`. Los hilos solo encolan mensajes;
  `_poll_messages` los atiende en el hilo de Tk. Las confirmaciones y avisos pasan por `app.ask`,
  `app.ask_save`, `app.inform` y `app.alert`, y el portapapeles por `app.read_clipboard`: los
  tests los sustituyen.
- `tests/fixtures.py`: OBSP sintético con los 11 tags y hashes reales; `tests/support.py`: archivo real;
  `tests/test_gui.py`: humo de la GUI (se omite sin Tk). Las ventanas van ocultas y Tk descarta
  ahí las teclas sintéticas, así que los atajos se prueban con `invoke_binding`, que llama al
  callback del enlace. `<<TreeviewSelect>>` llega por la cola de eventos: un test de la pista
  llama antes a `update()`.
- `research/FORMATO.md`: hallazgos de formato fuera del apéndice A.
- `GUIA_MODDER.md`: atajos de teclado y qué se suele modificar. Si cambias un atajo, un menú o
  una prueba en el juego, actualízala en el mismo cambio.

Solo biblioteca estándar, sin dependencias externas. La CI (Windows, Python 3.10–3.13)
lo comprueba importando los módulos sin instalar nada. Los tests que necesitan el
archivo real buscan `D2SV_OBSP` o la ruta por defecto del juego, y se omiten si no lo
encuentran.

## Arquitectura

### Formato (detalle en el apéndice A del plan)

- **Contenedor OBSP**, en este orden:
  1. Cabecera de 29 bytes.
  2. Tabla de cadenas `{u64 hash, u32 len, chars}`: sin repetidos, en orden de primera
     aparición de (ruta, nombre, carpeta, clase) al recorrer el índice.
  3. Índice de 51 bytes por objeto (`<QQIIHBQQQ`): hashRuta, idObjeto, offset, tamaño,
     grupo, tipo, hashNombre, hashCarpeta, hashClase.
  4. Blobs contiguos y sin relleno hasta el EOF.

  Al escribir se regeneran la tabla, los offsets y la cabecera.
- **Identidad de un objeto**: el par (grupo, idObjeto). Las referencias entre objetos
  (tag `FC`) usan ese par, nunca offsets.
- **Blobs BOD** (todos los tipos salvo el 0): un árbol que se describe a sí mismo, con una
  tabla de nombres internada propia de cada blob:
  - `01` = nombre nuevo con su hash; `00` = índice a un nombre ya definido.
  - Comparten esa tabla los nombres de campo, los de clase y las cadenas `0F`.

  Tags: `02` int32 · `03` float32 · `04` bool · `05` cadena sin hash · `07` objeto ·
  `09` lista (modo 0) o pares (modo 1) · `0A` mapa · `0B` tupla · `0F` cadena con hash ·
  `FC` referencia externa · `FE` nulo.
- **Codificador canónico**, que reproduce byte a byte los 4 172 blobs:
  - interna por (hash, texto) en un recorrido en profundidad: la clase antes que los
    campos y el nombre antes que el valor;
  - numera los objetos `07` en ese mismo orden;
  - recalcula los dos contadores de la cabecera.
- **Scripts compilados (tipo 0)**, apéndice A.3: tabla de símbolos propia, hash de ruta y grupo;
  después, hashes del nombre y de la clase base, miembros (con valor por defecto si las banderas
  llevan `0x08`), valores iniciales, funciones (hash, tamaño, código) y estados. Los valores usan
  la codificación de los BOD con los nombres como índices a los símbolos. El código empieza por
  el número de parámetros y sigue con instrucciones de 57 opcodes; los nombres en línea llevan su
  hash. Los 3 690 se reserializan idénticos.
- **Hash de 64 bits** (apéndice A.4 del plan): CRC-64 reflejado con polinomio
  `0x0060034000F0D50B` (reflejado `0xD0AB0F0002C00600`) y valor inicial y XOR final `~0`, sobre
  los bytes de la cadena. Distingue mayúsculas, da 0 para la cadena vacía y es la misma en el
  contenedor, los BOD y los scripts. `idObjeto` es el hash del nombre en minúsculas. Los enteros
  de 32 bits con aspecto de hash no son hashes: en su mayoría son marcas de tiempo Unix
  (2010–2012) que el editor asignaba como ID, p. ej. `SoundDesc.ID`, al que apunta
  `SoundTrigger.SoundID` (`research/FORMATO.md`, 2026-10-09).
- **Audio** (`research/FORMATO.md`, 2026-10-09): cada `SoundDesc` nombra su `Bank` y su `Event`
  (cadenas `0F`), pero el obsp no tiene ninguna lista de bancos ni los carga. Un banco
  modificado con los mismos nombres no exige tocarlo; uno nuevo se puede nombrar, pero falta
  probar en el juego si se carga.

### Flujo de la aplicación (sección 5 del plan)

- **Abrir** solo lee cabecera, cadenas e índice. Cada objeto se decodifica al seleccionarlo
  y se guarda en caché.
- **Editar**: cada edición es un comando reversible sobre el árbol y marca su objeto como modificado.
- **Guardar**:
  1. Construir en memoria: los blobs intactos se copian tal cual y los modificados se recodifican.
  2. Volver a parsear el resultado y verificarlo.
  3. Crear la copia del original.
  4. Escribir un `.tmp`, hacer `fsync` y sustituir con `os.replace`.
  5. Releer el archivo y comparar su SHA-256 con el de memoria.

## Invariantes que no se pueden romper

- **Sin pérdidas.** Un objeto no editado conserva sus bytes exactos, y editar y revertir
  devuelve el archivo idéntico. El original mide 18 334 463 bytes y su SHA-256 es
  `B46DD3DA7F17A0ED016E30AF523BFBA86D358C9920DFFA866C69D4A0F4F67C7C`; reconstruirlo sin
  cambios debe dar ese mismo SHA.
- Los int32 y float32 guardan sus 4 bytes crudos. Un float solo se reempaqueta si se edita.
- **Copia del original.** Al guardar encima de `X.obsp` se crea `X.original.obsp` una sola vez:
  es la copia del archivo tal como estaba, verificada por SHA-256 y en solo lectura. Nunca se
  sobrescribe ni se borra, y no se permite guardar encima de un `*.original.obsp`.
- **Scripts: solo parches del mismo tamaño.** Se editan los literales int, float y bool del
  código que no son número de argumentos (el `int n` antes de `0x38`/`0x39`/`0x36`) y los int,
  float y bool de los valores por defecto e iniciales. Nada que cambie tamaños o saltos.
- **Todo hash es el de su texto** (`hashes.name_hash`): guardar se bloquea si no cuadra. Las
  cadenas con hash nuevas solo entran en valores `0F`, con confirmación del usuario. Los nombres
  de campo y de clase, y las rutas, nombres e identidades de los objetos, no se editan (las
  identidades nuevas quedaron fuera de la fase 6).
- Las cadenas son solo ASCII (el original no tiene ninguna que no lo sea) y su longitud cabe en u16.
- No se escribe en la instalación del juego fuera del guardado explícito. Los experimentos
  se hacen sobre copias.
- **Ningún dato del juego entra en el repositorio** (`*.obsp`, volcados, extractos). Los tests
  usan fixtures sintéticos generados con el propio codificador.

## Convenciones heredadas de Darkstractor

- Todo `.py` y `.pyw` empieza con estas dos líneas, antes de `from __future__ import annotations`:

  ```python
  # SPDX-FileCopyrightText: 2026 BOTProT800
  # SPDX-License-Identifier: MIT
  ```

- **Licencia MIT y créditos.** Todo material de procedencia externa se registra en
  `CREDITS.md` **en el mismo cambio** en que entra. Cuenta como externo: código, herramientas,
  formatos documentados por terceros y notas de ingeniería inversa ajenas.
  - El formato de cada entrada y las secciones son los de `..\Darkstractor\AGENTS.md`.
  - Las entradas nunca se borran: se mueven a `## History`.
  - Si falta el autor o la licencia, pregunta antes de cerrar la entrada.
  - Nada con copyleft (GPL, LGPL, AGPL, MPL) sin consultar antes.
  - Al terminar, informa en una línea qué entrada añadiste o cambiaste.
- La versión vive solo en `d2scriptviewer/__init__.py`.
- La GUI usa tkinter/ttk con el tema oscuro de `..\Darkstractor\darkstractor\gui.py`. El
  trabajo pesado va en hilos que se comunican con la GUI mediante `queue`. Los ajustes se
  guardan en `%APPDATA%\D2ScriptViewer\config.json`.
- Los hallazgos de investigación y los resultados de las pruebas en el juego van en `research/*.md`.

## Entorno y proyectos relacionados

- **Juego**: `C:\Program Files (x86)\Steam\steamapps\common\Darksiders II Deathinitive Edition`.
  `media\scripts.obsp` está suelto, no dentro de los `.upak`. El SHA-256 de
  `Darksiders2.exe` es `5580738EF70BC5BBCC72D7DC4A9C319956CD14DBFEF6F9DBEC54C1B5D97799FB`.
- **Copia para experimentos**: `C:\Users\vicen\Documents\Extractions\Darksiders\scripts.obsp`,
  idéntica al original.
- **`..\Darksiders2DLL`** (C++, proxy `dinput8.dll`):
  - No lee, fija ni redirige `scripts.obsp`: su mod de inventario (`scripts=inventory`) se
    abandonó y eliminó el 4 de octubre de 2026. No propongas avisos ni trabajo sobre ese modo.
  - El juego abre `scripts.obsp` con `FILE_SHARE_READ`; con el juego abierto, guardar fallará.
  - `research/INVENTORY_SCRIPT.md` (conservado como investigación) documenta el único patrón de
    bytecode confirmado: `NumSlots\0`, `0x23` + int32 y luego `0x29 0x32`, con offsets en `death/death`.
- **`..\Darkstractor`** (Python stdlib + tkinter): referencia de estilo, estructura del
  repositorio, CI y tests.
- **Para la fase 7**: `Darksiders2.exe` contiene el compilador del lenguaje de scripts, con
  las cadenas flex/bison de sus tokens y reglas de gramática.
