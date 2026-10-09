# Plan maestro: D2ScriptViewer — visor y editor de `scripts.obsp` (Darksiders II Deathinitive Edition, PC)

> **Fase 11 cerrada (2026-10-09): ir a una ruta.** Ctrl+G abre la barra «Ir a», que lee la ruta de
> «Copiar ruta de la propiedad», `objeto · propiedad` (o `objeto::propiedad`) o el objeto solo, y
> salta a esa fila. No cambia el formato ni el guardado, así que no necesita prueba en el juego.
>
> Criterios de «Hecho cuando», uno por uno:
>
> 1. **Barra, teclas, relleno y pista:** sí. Además de los tests, se probaron con teclas generadas
>    en la ventana visible (Xvfb) y el archivo real:
>    - Ctrl+G, escribir `MoveStates[44].JumpImpulse` e Intro: fila con 350 y foco en el árbol;
>    - `ui_core/pausemenu::Funciones.onInit.0x004E`: salto de objeto a la fila con `true`;
>    - `Funciones.onInit.0x004F`: se queda en la función y dice que la instrucción anterior es
>      `0x004E`;
>    - Ctrl+Z en el campo no cambia nada; Escape cierra la barra y Alt+← vuelve al objeto
>      anterior.
>
>    El teclado de Xvfb no tiene la tecla «·», así que el separador « · » solo lo cubren los tests.
> 2. **Tests unitarios con los fixtures** (`PathLabelInverseTests`, `LocationTests`): sí.
>    - Ida y vuelta en todas las filas de los 4 objetos, también con el objeto delante.
>    - Pares, la lista de 1 200 elementos y el script: `0x…` por valor, tildes y etiquetas con
>      espacios.
>    - Mayúsculas y su ambigüedad, y un campo repetido.
>    - Fallos a mitad (nombre, índice y tipo) y errores de sintaxis.
>    - Los formatos con objeto, el objeto solo y cuándo el portapapeles parece una ruta.
> 3. **Tests de la GUI** (`GotoPathGuiTests`, y el aviso de clave repetida en
>    `StructureGuiTests`): sí.
>    - Ctrl+G y el menú, también con una celda en edición, sin archivo y desde la búsqueda global.
>    - Una fila del mismo objeto y otra dentro de un tramo de otro objeto, con el historial.
>    - Decodificación en un hilo: el salto, una ruta pedida mientras se decodifica y un cambio de
>      objeto antes de que termine.
>    - El error en la pista, comprobado tras `update()`, y Escape.
>    - Ctrl+Z, Ctrl+Y y Ctrl+P en el campo, el portapapeles y «Copiar ruta completa».
>    - La pista de estructura con las teclas en mayúscula.
>
>    Los tests de los dos errores previos fallan con el código anterior (comprobado con
>    mutaciones).
> 4. **Tests con el archivo real** (`RealPathLabelTests`): sí.
>    - Ida y vuelta en las 1 145 518 filas de los 7 862 objetos: unos 19 s aquí (16 µs por fila;
>      el test admite hasta 120 s). La única excepción es la prevista: la segunda fila de
>      `wailing_host` va a la primera, con aviso.
>    - Las tres rutas de la guía dan 350, `true` y `'flag_quest_debug_question_asked'` en las
>      cuatro formas (sola, con « · », con `::` y entre acentos graves), cada una en menos de 50 ms.
>    - `activate` y `Activate` en `base/simpleinteractive`.
> 5. **Prueba en el juego:** no hace falta.
> 6. **Documentación** (plan con las secciones 6 y 8, `CLAUDE.md`, `CHANGELOG.md`, README y
>    `GUIA_MODDER.md`): sí.
>
> Detalles decididos al implementar:
>
> - `bod.child` da un hijo sin construir la lista entera de hijos. Lo usan `path_label`,
>   `resolve` y `get_slot`, con la misma salida, comprobada en las 1 145 518 filas. `path_label`
>   en todas las filas pasa de 17,1 s a 2,4 s.
> - Un nombre se corta en `.`, `[`, `]`, `·`, `:` y en los caracteres de control. Así, un segundo
>   `::` da un error de sintaxis claro en lugar de acabar dentro de un nombre.
> - Cada mensaje de fallo empieza por el tramo que falló, que es el que la barra selecciona.
> - Escape también retira un error retenido, para que vuelva la pista de la fila.
> - `Document.parse_location` no necesita el árbol: la propiedad se resuelve cuando está
>   decodificado, también tras hacerlo en un hilo.
> - El menú del clic derecho se construye en `context_menu(iid)`, para poder probarlo, y el
>   portapapeles se lee con `app.read_clipboard`, que los tests sustituyen.
>
> **Revisión adversarial**, tras el primer commit de cierre. Cuatro revisores (núcleo, GUI,
> regresiones y tests) y un verificador por hallazgo. Se corrigió:
>
> - **Pista:**
>   - un salto correcto a la fila donde se quedó un fallo anterior dejaba el error en rojo; ahora
>     lo retira;
>   - Escape retiraba también avisos que no eran de la barra (la clave repetida tras Ctrl+D);
>     ahora solo retira los suyos.
> - **Decodificación en un hilo:**
>   - Escape no anulaba el salto que esperaba a la decodificación. Los verificadores lo vieron
>     como algo que el plan no especifica («Escape cierra la barra»); se adopta porque la
>     propuesta del usuario dice «Intro va y Escape cancela»;
>   - un intento nuevo que fallaba no anulaba el anterior;
>   - una ruta pedida con Ctrl+G perdía frente a la de la navegación (búsqueda global,
>     referencias);
>   - el fallo de un objeto ya abandonado sustituía al que se estaba viendo (error anterior a la
>     fase, que el salto hacía alcanzable).
> - **Texto:**
>   - el espacio duro (U+00A0) y el tabulador cuentan como espacios;
>   - un carácter invisible (U+200B, U+FEFF…) se señala con su código;
>   - un salto de línea se señala donde está;
>   - un índice de más de 18 cifras da un error claro, no una excepción;
>   - con un carácter fuera del plano básico (un emoji), la barra marca el tramo correcto en
>     Tk 8.6.
> - **Tests:**
>   - el caso «cambio de objeto antes de que termine» espera a la decodificación y mira qué se
>     muestra;
>   - nuevos: la nota de dos campos iguales en la GUI, la búsqueda pendiente antes del salto,
>     Ctrl+G con la barra abierta, el Intro del teclado numérico, el foco ocupado por el usuario,
>     un objeto que no decodifica y que `child` nunca recurre a `children`;
>   - el del portapapeles ya no toca el del sistema.
>
> Cada test nuevo se comprobó con el código de antes o con una mutación: falla sin el arreglo.
> Queda fuera, porque es anterior y afecta también a la barra de la fase 10: hacer clic en una
> barra con una celda en edición devuelve el foco al árbol 150 ms después.
>
> **Desviación:** como en la fase 10, todo se ejecutó en Linux (contenedor en la nube, Python
> 3.12.3 y Tk 8.6.14 bajo Xvfb), no en Windows. No entra material externo: `CREDITS.md` no cambia.
>
> 269 tests: 2 omitidos (el bloqueo de Windows y, como root, el de solo lectura) y código de salida 0.

> **Fase 11 abierta (2026-10-09): ir a una ruta.** El usuario pidió pegar una ruta como
> `MoveStates[44].JumpImpulse` y que el panel de propiedades salte a esa fila. Decisiones del
> usuario:
>
> - **Acceso:** Ctrl+G y el menú Ir → «Ir a la ruta…», desde cualquier panel de la ventana
>   principal (no desde la búsqueda global ni desde los diálogos). Cancelan una celda en edición,
>   como Ctrl+F. El campo es una barra «Ir a» dentro del panel de propiedades, entre la barra de
>   búsqueda y el árbol:
>   - aparece con Ctrl+G y se oculta con Escape o al llegar;
>   - si la ruta falla, sigue abierta con el tramo que falló seleccionado;
>   - se rellena con el portapapeles si parece una ruta y, si no, con el último texto usado.
> - **Formato:** el de «Copiar ruta de la propiedad» (`bod.path_label`), también en los scripts
>   (`Funciones.onInit.0x004E`), relativo al objeto abierto.
>   - Con el objeto delante, `objeto · propiedad`, con o sin espacios. También vale `::`, para
>     teclados sin «·».
>   - Un texto sin separador cuyo primer tramo lleva «/» abre ese objeto.
>   - Nueva entrada «Copiar ruta completa» en el clic derecho, con « · ».
> - **Mayúsculas:** por tramo, primero el nombre exacto; si no lo hay, sin distinguir
>   mayúsculas y solo si la coincidencia es única.
>   - Si son varias, se queda en el padre y la pista las nombra.
>   - Ante dos campos exactamente iguales, va al primero y lo avisa.
> - **Fallos:** va al nodo válido más profundo, o al objeto si falla el primer tramo. La pista
>   dice qué tramo falló y por qué: hasta 3 nombres parecidos, el rango válido de un índice o lo
>   que se esperaba. Si el objeto no existe o el texto no es una ruta, no se navega.
> - **Alcance:** entran dos errores previos de la pista:
>   - tras Ctrl+D sobre una entrada de mapa, el aviso de clave repetida desaparece en cuanto Tk
>     procesa los eventos (el test actual no los procesa);
>   - un `.capitalize()` deja en minúsculas las teclas de la pista de estructura («Ctrl+d
>     duplica, supr elimina…»).
>
>   Quedan fuera los índices por `Name` (`MoveStates[Jump]`), el autocompletado de rutas y una
>   opción en la CLI.
>
> Medido sobre la copia de `D2SV_OBSP` (7 862 objetos, 1 145 518 filas):
>
> - **Etiquetas de campo:**
>   - las de los BOD solo tienen letras y cifras;
>   - las de los árboles de los scripts añaden `_`, tildes (`Versión`, `Símbolos`,
>     `Parámetros`) y espacios en tres etiquetas fijas (`Hash de ruta`, `Clase base`,
>     `Valores iniciales`);
>   - ninguna contiene `.`, `[`, `]`, `·`, `:` ni `/`, ni se llama `clave`, `valor` o `(raíz)`;
>   - las 5 898 que empiezan por cifra son desplazamientos `0xNNNN`.
> - **Nombres repetidos:**
>   - solo un objeto `07` repite un nombre de campo: `wailing_host/wailing_host ·
>     Miembros.StageThreeHealthPct` (miembros 6 y 7);
>   - solo `base/simpleinteractive · Funciones` tiene dos que difieren en mayúsculas
>     (`activate` y `Activate`).
> - **Rutas de objeto:**
>   - son únicas y están en minúsculas;
>   - solo usan `a-z`, `0-9`, `_`, `/` y un espacio, en una sola ruta (`base/volcanic rumbles`);
>     ninguna lleva `·` ni `::`;
>   - 792 objetos comparten nombre con otro, así que el objeto se identifica por su ruta.
> - **Prototipo:**
>   - la ida y vuelta `path_label` → ruta acierta en 1 145 517 filas; solo falla la segunda de
>     `wailing_host`;
>   - resolver cuesta unos 10 µs por ruta;
>   - sugerir con `difflib` cuesta 1,6 ms en el `07` con más campos y 44 ms sobre las 7 862
>     rutas de objeto.
> - `path_label` en todas las filas tarda 17–22 s, porque `bod.children` construye la lista
>   entera de hijos en cada paso.
> - `<<TreeviewSelect>>` llega por la cola de eventos: tras `reveal`, la pista de la fila pisa
>   cualquier mensaje puesto antes. Es lo que borra el aviso de clave repetida.
> - 16 objetos superan los 48 KB y se decodifican en un hilo; entre ellos está el del ejemplo,
>   `death/playercommon_movestates` (50 374 bytes).
>
> Detalles decididos al planificar, dentro de lo acordado:
>
> - **Pista retenida:** un mensaje puesto al saltar no lo pisa la selección que provoca el salto;
>   la pista normal vuelve al elegir otra fila.
> - **Intento flexible:** además de las mayúsculas, ignora las tildes (`Parametros` llega a
>   `Parámetros`). No crea coincidencias nuevas entre hermanos.
> - **Desplazamientos:** un tramo `0x…` sin coincidencia de texto se compara por valor (`0x4e`
>   es `0x004E`). Uno que cae dentro de una instrucción se queda en la función y dice en cuál está.
> - **Texto tolerado:** espacios entre tramos, `[ 44 ]`, ceros a la izquierda, `\` por `/` en el
>   objeto y comillas, `«»` o acentos graves que envuelvan el texto (al copiar del `.md`).
> - `[texto]` es un error de sintaxis que dice que los índices por `Name` no están disponibles.
> - **«Parece una ruta»:**
>   - una sola línea de hasta 256 caracteres, con la sintaxis válida y alguno de `.`, `[`, `·`,
>     `::` o `/`;
>   - además, el objeto existe o el primer tramo es un campo de la raíz del objeto abierto;
>   - el texto entra seleccionado.
>
> Criterios en la fase 11 de la sección 7.

> **Fase 10 cerrada (2026-10-08): búsqueda dentro del objeto.** Los dos tests con el archivo
> real (`RealTreeSearchTests`) pasan con una copia idéntica a la de Steam (18 334 463 bytes,
> SHA-256 `B46DD3DA…` comprobado antes de ejecutarlos):
>
> - en `death/death`, `op_3A` + `NumSlots` da las 7 rutas de `Funciones.onInit`, de `0x0770`
>   a `0x0A4A`, y el `int32` siguiente vale 21, 21, 21, 22, 22, 22 y 21;
> - el objeto mayor (`base/itemfoleytable`) se busca en 18–27 ms con los cuatro criterios del
>   test, lejos del límite de 200 ms.
>
> **Desviación:** se ejecutaron en Linux (contenedor en la nube, Python 3.12.3 y Tk 8.6.14), no
> en Windows. El usuario subió el archivo a la sesión y pidió cerrar la fase si pasaban. Ningún
> dato del juego entró en el repositorio.
>
> Root escribe en archivos de solo lectura, así que dos tests de `test_saving` fallaban al
> ejecutar la suite como root (nota de la fase 10). Decisión del usuario: omitirlos como root.
> `test_read_only_target` se omite entero. En `test_first_save_creates_verified_read_only_copy`
> solo se omite `os.access`: como root se comprueba el bit de solo lectura y el resto del test se
> ejecuta. En Windows y como usuario normal no cambia nada.

> **Fase 10 implementada (2026-10-07): búsqueda dentro del objeto.** Falta pasar sus dos tests
> con el archivo real: se escribieron en un contenedor Linux sin `scripts.obsp` y quedaron
> omitidos. Se cierra cuando pasen en Windows con `D2SV_OBSP`.
>
> - `search.find_in_tree` devuelve las rutas en el orden de las filas, que es el orden
>   lexicográfico de las rutas. Comparte con el panel el texto de la columna Valor
>   (`row_value_text`, con `→` y el destino en las referencias). `tree_types` da los tipos del
>   objeto.
> - El panel de propiedades lleva la barra bajo el título. Siguiente y anterior se buscan con
>   `bisect` desde la fila seleccionada, y un tramo cuenta como su primer elemento. Ir a un
>   resultado usa `reveal`, y `show_bod` y `set_edited` recalculan sin mover la selección.
> - Ctrl+F lleva el foco a la barra, y Ctrl+Mayús+F (`<Control-F>`) abre la búsqueda global. El
>   menú Buscar tiene las dos entradas.
> - Medido aquí con un árbol sintético de 31 901 filas: entre 25 y 65 ms por búsqueda, y 42 ms
>   para listar sus tipos.
>
> Detalles decididos al implementar, dentro de lo acordado el 2026-10-06:
>
> - Al escribir, si la fila seleccionada sigue siendo un resultado, no se mueve. Si no lo es, se
>   va al siguiente resultado desde ella.
> - El contador dice «3 de 7» sobre un resultado, «7 resultados» si la fila seleccionada no es
>   uno, «Sin resultados» si no hay ninguno, y nada si los campos están vacíos.
> - Ctrl+F vuelve al último campo usado, con su texto seleccionado, y cancela un editor abierto.
>   En otra ventana (la búsqueda global o un diálogo) no salta a la principal.
> - F2 en la barra edita la fila seleccionada, como F2 en el árbol.
> - Los tipos del desplegable se calculan al abrirlo. Los botones ‹ › usan un estilo compacto
>   (`Small.TButton`) para que los campos quepan en el ancho por defecto del panel.
>
> Criterios de «Hecho cuando»:
>
> 1. La barra, las teclas y el recálculo funcionan como se describe: sí. Además de los tests, se
>    probaron con teclas reales y la ventana visible en Xvfb: Ctrl+F, escribir, Intro, Mayús+Intro,
>    F3, Escape, Mayús+F3 en el árbol, Ctrl+Z en la barra y en el árbol, y Ctrl+Mayús+F.
> 2. Tests unitarios con los fixtures (`TreeSearchTests`): sí. Cubren cada campo, las
>    combinaciones, las mayúsculas, las referencias por su destino, el orden, una lista de 1 200
>    elementos, los criterios vacíos y la búsqueda sin resultados, más los tipos y un script.
> 3. Tests de la GUI (`ObjectSearchGuiTests`): sí. Cubren el contador, anterior y siguiente con
>    vuelta al principio, un resultado dentro de un tramo, el recálculo tras editar, deshacer y
>    cambiar la estructura y al cambiar de objeto, F2 sobre un resultado, Ctrl+Z en los tres
>    campos y Ctrl+Mayús+F. Con la ventana oculta, Tk descarta las teclas sintéticas, así que
>    los tests invocan el callback de cada enlace (`invoke_binding`).
> 4. Tests con el archivo real (`RealTreeSearchTests`): escritos, sin ejecutar. Comprueban que
>    `death/death` da las 7 rutas de `0x0770` a `0x0A4A`, con 21, 21, 21, 22, 22, 22 y 21 en la
>    fila siguiente, y que `base/itemfoleytable` se busca en menos de 200 ms.
> 5. Prueba en el juego: no hace falta.
> 6. Plan (sección 6 incluida), `CLAUDE.md`, `CHANGELOG.md`, README y `GUIA_MODDER.md` (atajos,
>    y el inventario como ejemplo no probado en el juego): sí.
>
> 234 tests. Se ejecutaron en Linux con Python 3.12.3 y Tk 8.6.14 bajo Xvfb, como usuario no root:
> 30 omitidos (los del archivo real) y código de salida 0. Como root fallan dos tests de
> `test_saving` porque root escribe en archivos de solo lectura; no afecta a Windows.
>
> **Fase 10 abierta (2026-10-06): búsqueda dentro del objeto.** El usuario pidió buscar por tipo
> y por valor en el panel de propiedades. Así se llega a filas como los siete `op_3A NumSlots`
> de `death/death` sin desplegar el árbol a mano. Decisiones del usuario:
>
> - **Columnas:** un campo por columna (Nombre, Tipo y Valor), todos opcionales y combinados
>   con «y».
> - **Atajos:** Ctrl+F pasa a ser la búsqueda en el objeto, y Ctrl+Mayús+F la búsqueda global. La
>   1.0.0 no está publicada, así que el cambio no rompe costumbres.
> - **Resultados:** de uno en uno, con siguiente, anterior y contador. El árbol es la única vista.
> - **Alcance:** solo el objeto abierto. Ampliar la búsqueda global al código de los scripts
>   queda para otra fase.
>
> Medido sobre la copia de `D2SV_OBSP`:
>
> - el objeto mayor (`base/itemfoleytable`, 26 040 filas) se recorre y compara en 36–57 ms, así
>   que se busca en el hilo de Tk, sin índices ni hilos;
> - `death/death` tiene 7 592 filas, y `op_3A` + `NumSlots` da exactamente 7;
> - hay 13 tipos en los BOD y 71 en los scripts;
> - 12 nodos tienen más de 500 hijos y se muestran en tramos.
>
> Criterios en la fase 10 de la sección 7.
>
> **Fase 9 cerrada (2026-10-04): versión 1.0.0 preparada para publicar.** Con ella se completan
> las fases 0 a 9.
>
> - PyInstaller 6.22.3 se instaló en `build\venv-pyinstaller`. Su `COPYING.txt` confirma la
>   GPL-2.0-or-later con la *Bootloader Exception*, y que los *run-time hooks* que se incrustan
>   son Apache-2.0. Así queda resuelto el punto que Darkstractor dejó pendiente.
> - `D2ScriptViewer.spec` construye `dist\D2ScriptViewer.exe` (11,7 MB), que lleva dentro
>   `LICENSE`, `CREDITS.md`, `CHANGELOG.md`, `THIRD_PARTY_NOTICES.md` y `licencias\`:
>   - `LICENSE-Python.txt`, que incluye OpenSSL, libffi, bzip2, zlib y el runtime de Microsoft;
>   - `LICENSE-PyInstaller.txt` y `LICENSE-TclTk.txt`;
>   - `VERSIONES.txt`: Python 3.12.5, PyInstaller 6.22.3, Tcl/Tk 8.6.13, OpenSSL 3.0.13 y
>     zlib 1.3.1.
> - `--autoprueba` del `.exe` congelado: 29 módulos, hash, OBSP sintético con `verify`, los 8
>   archivos incluidos y la ventana principal sin mostrarla: todo correcto, código de salida 0.
> - La rueda `d2scriptviewer-1.0.0` se construye con su `LICENSE`.
> - `release.yml` reproduce todo esto en GitHub con una etiqueta `v*` y adjunta los avisos a la
>   release. `tests.yml` comprueba todos los módulos y ejecuta la autoprueba.
>
> Criterios de «Hecho cuando»: receta y entrada (sí); autoprueba (sí); workflows (sí, sin
> ejecutar en GitHub porque el push lo hace el usuario); avisos de terceros, `CREDITS.md` y
> README (sí); versión 1.0.0 (sí); `.exe` construido en local y con la autoprueba superada (sí).
> 214 tests.
>
> **Desviación:** la CI de GitHub nunca se ha ejecutado; se reproduce en local con Python
> 3.12.5. El usuario decide el push, si el repositorio es público y la etiqueta `v1.0.0`.
>
> **Decisiones de la fase 9 (2026-10-04)**, confirmadas por el usuario tras leer la entrada de
> PyInstaller del `CREDITS.md` de Darkstractor.
>
> Esa entrada da la licencia de PyInstaller como GPL-2.0-or-later con una excepción para el
> bootloader, por verificar en el `COPYING.txt` de la versión usada. Además, publicar el `.exe`
> redistribuye binarios de terceros: el bootloader, CPython y, en este proyecto, también Tcl/Tk,
> OpenSSL y libffi. Hay un remoto (`origin`, GitHub) que el usuario añadió; `origin/main` estaba
> en `1d8a7bd`.
>
> - **Publicación:** solo en local. El usuario hace el push, decide si el repositorio es público
>   y crea la etiqueta del release.
> - **Versión del primer release:** 1.0.0.
> - **PyInstaller en local:** en un entorno virtual dentro de `build\` (ignorado por git), con
>   versión fija. La licencia se verifica en su `COPYING.txt` y el `.exe` se prueba con una
>   autoprueba.
> - **Ejecutables:** solo la GUI, un único `D2ScriptViewer.exe` sin consola. La CLI sigue
>   disponible con Python.
>
> **Hecho cuando:**
>
> - `D2ScriptViewer.spec` (un archivo, sin consola, con `LICENSE`, `CREDITS.md`,
>   `CHANGELOG.md`, `THIRD_PARTY_NOTICES.md` y los textos de licencia de terceros dentro) y un
>   script de entrada que abre la GUI;
> - una autoprueba oculta (`--autoprueba archivo`) que importa los módulos, comprueba el hash,
>   construye un OBSP en memoria, pasa `verify` y crea una ventana Tk;
> - `release.yml` como el de Darkstractor: con una etiqueta `v*`, tests, rueda, sdist y `.exe`,
>   comprobación de tamaño, autoprueba y release con el `.exe` y los avisos. `tests.yml` comprueba
>   también los módulos nuevos;
> - `THIRD_PARTY_NOTICES.md`, la entrada de PyInstaller en `CREDITS.md` con la licencia
>   comprobada, y el README con la guía de uso y las advertencias;
> - la versión 1.0.0 en `__init__.py` y en `CHANGELOG.md`;
> - el `.exe` se construye en local y pasa la autoprueba. Sin push, etiqueta ni release.
>
> **Fase 8 cerrada (2026-10-04)** con la prueba en el juego (detalle en
> `research/PRUEBAS_EN_JUEGO.md`). El usuario editó a mano, guardó, exportó el parche, restauró,
> lo reaplicó, guardó y jugó.
>
> - La versión hecha a mano y la reaplicada son idénticas (SHA `BC3F812B…`, 18 334 632 bytes), y
>   el juego refleja el salto alto. Al terminar quedó restaurado `B46DD3DA…`.
> - El muñeco del menú no hizo el combo porque la edición se hizo en `Animations[435].Name` y no
>   en `AnimationName`, la fila prevista. Es la misma en las dos versiones, así que no afecta al
>   parche. Con el usuario se decidió cerrar con este resultado.
>
> Criterios de «Hecho cuando»:
>
> 1. Exportar JSON por objeto, `manifest.json` y CSV de las `FloatTable`, en un hilo y nunca
>    dentro de la carpeta del juego: sí.
> 2. Crear el parche con valores y estructura sin datos del juego, autoverificado: sí.
> 3. Aplicarlo como cambios pendientes que se deshacen (o a un archivo nuevo en la CLI), con
>    rechazo claro si algo no coincide: sí.
> 4. Tests sintéticos de cada operación y de los rechazos, más los del archivo real: sí.
> 5. En el juego: guardar a mano, exportar, restaurar, reaplicar, mismo SHA y jugar: sí.
> 6. Plan, `CLAUDE.md`, `CHANGELOG.md` y README: sí.
>
> 211 tests. Siguiente paso: la fase 9 (distribución), empezando por la entrada de PyInstaller
> de Darkstractor y las decisiones del usuario (repositorio, CI, release y versión).
>
> **Fase 8 implementada (2026-10-04)**, antes de la prueba en el juego (punto de control):
>
> - `export.py`: JSON por objeto, `manifest.json` y CSV de las `FloatTable`. Con el archivo
>   real, 7 862 JSON y 65 CSV, unos 120 MB, en 17 s; la GUI exporta una instantánea en un hilo.
> - `patches.py`: `create_patch` alinea las listas (`diffing.align`, extraído del comparador
>   sin cambiar su comportamiento) y deriva operaciones.
>   - Cada emparejamiento y cada origen de copia se prueba antes de usarse, y las inserciones se
>     hacen antes de quitar, así que cualquier elemento original sirve de origen.
>   - Si no hay un origen en la misma lista, se busca en todo el original un objeto igual o de la
>     misma clase y campos, que pasa a la lista de fuentes.
>   - El parche se reaplica sobre la base antes de escribirse.
> - `apply_patch` usa `Document.run_operations`: si algo falla, deshace lo aplicado.
> - Medido: el parche de las ediciones de las fases 5 a 7 (3 objetos, 4 operaciones) se crea en
>   0,5 s y reaplicado da el mismo SHA. Un fuzz de 230 secuencias de operaciones al azar (200
>   sintéticas y 30 sobre objetos reales) da siempre un parche que reproduce el archivo.
> - 211 tests. **Desviación:** en el JSON del parche las etiquetas legibles incluyen nombres de
>   campo (p. ej. `Slots[2].SlotID`); son rutas, no contenido copiado del juego.
>
> **Decisiones de la fase 8 (2026-10-04)**, confirmadas por el usuario a partir del análisis de
> los datos:
>
> - Las 7 862 rutas son únicas y válidas como nombres de archivo en Windows (sin choques al
>   ignorar mayúsculas, un solo nivel de carpeta, 74 caracteres como máximo).
> - El JSON de todos los BOD ocupa unos 62 MB y tarda unos 5 s: va en un hilo.
> - Los 65 `FloatTable` son rectangulares: `Data` (filas `Row` de floats), `ColumnNames` y
>   `RowNames`.
>
> Decisiones:
>
> - **El parche incluye cambios estructurales sin datos del juego:** operaciones que solo copian
>   contenido del original (duplicar, quitar, mover, poner a nulo, rellenar con una copia de otro
>   lugar del original o con una referencia). Si un cambio no se puede expresar así, se avisa y no
>   se exporta.
> - **Identificación por objeto:**
>   - cada objeto lleva su ruta, (grupo, id) y el SHA-256 de su blob original y del resultado;
>   - cada propiedad lleva su ruta de índices, su etiqueta legible y su valor anterior, y al
>     aplicar se comprueban las tres;
>   - se aplica sobre el original de Steam y sobre archivos donde solo difieren otros objetos,
>     así que los parches se pueden combinar. Los objetos de los que se copia también se
>     comprueban.
> - **Sin importación:** JSON y CSV son solo de exportación; lo único que se reaplica son los
>   parches.
> - **Prueba en el juego:** con las ediciones ya probadas (duplicar `MoveStates[0]` y
>   `JumpImpulse` 700 de la fase 5, y `PaperDoll_Idle` → `D_WScy_Combo04` de la fase 6). Se
>   guarda a mano, se exporta el parche, se restaura, se reaplica y debe dar el mismo SHA.
> - **Menores:**
>   - nunca se exporta dentro de la carpeta del juego, y el destino debe estar vacío o ser una
>     exportación anterior;
>   - floats con el decimal más corto que da el mismo float32 (hexadecimal para NaN e infinitos);
>   - nombres como texto, todo en UTF-8 y CSV con coma y punto decimal;
>   - la versión no cambia (la decide el usuario en la fase 9).
>
> Criterios de «Hecho cuando» en la sección 7.
>
> **Fase 7 cerrada (2026-10-04)** con la prueba en el juego (detalle en
> `research/PRUEBAS_EN_JUEGO.md`). El usuario cambió en `ui_core/pausemenu` el literal de
> `Game.setPaused(true)` (`Funciones.onInit.0x004E`) a `false`. Informó de que, con el menú de
> pausa abierto, el juego sigue en tiempo real, y de que las flechas mueven al personaje en vez de
> la selección del menú. La versión jugada (SHA `69A486B6…`, un solo byte cambiado) coincide con
> el ensayo, y el usuario restauró `B46DD3DA…`.
>
> Criterios de «Hecho cuando»:
>
> 1. Los 3 690 scripts se interpretan enteros y se reserializan idénticos: sí.
> 2. Las 9 721 funciones se desensamblan justo hasta su tamaño, sin opcodes desconocidos, y los
>    111 603 nombres en línea llevan su hash; la tabla de 57 opcodes con sus recuentos está en
>    el apéndice A.3: sí.
> 3. El panel central muestra miembros y funciones desensambladas, y existe `disasm`. Los
>    scripts de más de 48 KB se decodifican en un hilo. Medido: los 3 690 se muestran uno a uno
>    con una media de 2,3 ms y 0,27 s el peor: sí.
> 4. Parches del mismo tamaño de literales y valores, con deshacer y cambios pendientes; al
>    guardar se comprueba que solo cambiaron esos valores: sí.
> 5. Tests sintéticos (script generado por el serializador) y con el archivo real: sí.
> 6. El juego carga el parche y refleja su efecto; restaurar devuelve `B46DD3DA…`: sí.
> 7. Apéndice A.3, `research/FORMATO.md`, `CLAUDE.md` y `CHANGELOG.md`: sí.
>
> 188 tests. Siguiente paso: la fase 8 (exportación y parches), empezando por analizar los
> datos y acordar con el usuario el formato del parche.
>
> **Decisiones de la fase 7 (2026-10-04)**, confirmadas por el usuario a partir de un primer
> análisis de los 3 690 scripts. Detrás de la cabecera, el cuerpo empieza por el hash del nombre
> corto (= símbolo 1) y el de la clase base (= símbolo 2) en los 3 690. Le siguen una tabla de
> miembros con valores por defecto codificados como en los BOD y una tabla de funciones (hash,
> tamaño y bytecode con líneas, literales y nombres en línea). 3 422 cuerpos acaban en un u32 a 0.
>
> - **Alcance:** estructura completa del cuerpo, desensamblador de solo lectura y parches del
>   mismo tamaño (literales de tamaño fijo y valores por defecto de los miembros). El
>   descompilador a pseudocódigo queda fuera de la fase, para el futuro.
> - **Vías:** solo análisis estadístico de los 3 690 scripts, con la función de hash para validar
>   los nombres en línea. Nada del ejecutable: ni volcado de cadenas ni Ghidra.
> - **Parada:** los parches solo se habilitan si los 3 690 scripts se interpretan y desensamblan
>   al 100 %. Si las vías se agotan sin llegar, se para, se documenta lo descartado en
>   `research/` y en la sección 2.4, y se pregunta al usuario.
> - **Prueba en el juego:** un literal o valor por defecto con efecto visible que no se guarde en
>   la partida, elegido con el desensamblador y ensayado sobre una copia. `NumSlots` se descarta:
>   nunca se probó en el juego y puede afectar a las partidas guardadas.
> - **Menores:** el desensamblado solo da nombre a los opcodes con significado comprobado (el
>   resto, `op_XX`), y nada que cambie tamaños o saltos.
>
> Criterios de «Hecho cuando» en la sección 7.
>
> **Fase 6 cerrada (2026-10-04)** con la prueba en el juego (detalle en
> `research/PRUEBAS_EN_JUEGO.md`). El usuario cambió tres `AnimationName` de
> `death/death_animations` (`Jump`, `JumpF` y `PaperDoll_Idle`) a la cadena nueva
> `D_WScy_Combo04`: un combo de guadaña que está en el paquete de Death del `.upak` pero que no
> aparecía en `scripts.obsp`. Informó de que el salto y el muñeco del menú reproducen el combo,
> sin cierres ni congelaciones del juego. El muñeco se queda en el último fotograma al terminar,
> porque el combo no está en bucle (hipótesis). La versión jugada (SHA `D976CDED…`) coincide con
> el ensayo. El archivo no se había restaurado; con autorización del usuario, Claude ejecutó
> `saving.restore_original`, que devolvió `B46DD3DA…`.
>
> Criterios de «Hecho cuando»:
>
> 1. Función en `hashes.py` con sus parámetros en el apéndice A.4; tests con los 70 182 pares y
>    los 7 862 objetos, y tests sintéticos (valor de control, cadena vacía, mayúsculas,
>    referencia bit a bit, estructura lineal) con fixtures de hashes reales: sí.
> 2. `verify` comprueba la función y las identidades, y guardar se bloquea con un hash que no
>    cuadra: sí.
> 3. Cadenas nuevas en `0F` con aviso y confirmación; editar y deshacer devuelve `B46DD3DA…` y el
>    archivo guardado pasa `verify`: sí, por tests, también con el archivo real.
> 4. `python -m d2scriptviewer hash` y la pista del hash en el editor: sí.
> 5. Sección 2.4, apéndice A, `research/FORMATO.md`, `CLAUDE.md` y `CHANGELOG.md`: sí.
> 6. El juego carga la cadena nueva y refleja su efecto; restaurar devuelve `B46DD3DA…`: sí.
>
> 171 tests. Siguiente paso: la fase 7 (scripts compilados), empezando por analizar los datos y
> acordar con el usuario los criterios y hasta dónde investigar.
>
> **Fase 6: función de hash identificada (2026-10-04)** solo con los datos del archivo, en el
> paso de análisis y sin vías externas (ni código ajeno, ni Ghidra, ni la DLL):
>
> - Es un **CRC-64 reflejado** con polinomio `0x0060034000F0D50B` (`0xD0AB0F0002C00600` en forma
>   reflejada) y valor inicial y XOR final `0xFFFFFFFFFFFFFFFF`, sobre los bytes de la cadena.
>   Valor de control: `"123456789"` → `9AFB180E4C211BB4`. No es ninguno de los CRC-64 habituales
>   (ECMA, ISO, Jones), y por eso no apareció entre lo descartado en 2.4.
> - **Cómo se dedujo:** cambiar el bit k del último carácter hace siempre XOR con
>   `0x01A1561E0005800C << k`, sea cual sea el resto de la cadena. Los cambios del penúltimo
>   carácter se propagan como en un CRC reflejado, y de ahí sale el polinomio. Con él, el resto
>   depende solo de la longitud, y de eso salen el valor inicial y el XOR final.
> - **Comprobado:** acierta los 70 182 pares y `hashRuta` en los 7 862 objetos. `idObjeto` es el
>   hash del nombre en minúsculas en **los 7 862** (antes solo se podían comprobar 4 835).
> - **No explica** los enteros de 32 bits con aspecto de hash (`OnStateOne`, `MeshID`…): ni sus
>   mitades ni el CRC-32 coinciden más de lo que daría el azar. Queda abierto (sección 2.4).
>
> Decisiones de la fase 6, confirmadas por el usuario:
>
> - **Cadenas nuevas en valores `0F`:** se admiten, con aviso. Vale cualquier texto ASCII sin
>   NUL de hasta 65 535 caracteres, y su hash se calcula. Si el texto no aparece en el archivo, se
>   avisa y se pide confirmación, con un aviso específico si solo difiere en mayúsculas de una
>   cadena conocida. Una colisión con otra cadena conocida da error. El autocompletado sigue
>   ofreciendo las conocidas.
> - **Identidades nuevas en el índice OBSP** (renombrar o duplicar objetos): fuera de la fase 6.
>   Si se abordan, será en una fase aparte con su propia prueba en el juego.
> - **Un hash que no cuadra con su texto** impide guardar. Lo comprueba la autoverificación del
>   guardado en la tabla de cadenas y en los objetos modificados, que son los únicos que puede
>   cambiar la herramienta: los demás son idénticos byte a byte al archivo abierto. `verify` lo
>   comprueba en todo el archivo.
> - **Prueba en el juego:** cambiar un `0F` que nombra un recurso de fuera de `scripts.obsp`
>   (p. ej. un `AnimationName`) por un nombre que esté en los `.upak` pero no en `scripts.obsp`,
>   buscado en solo lectura con Darkstractor.
> - **Decisiones menores**, aceptadas sin cambios: los nombres de campo y de clase siguen sin
>   editarse; se añade `python -m d2scriptviewer hash <texto>`, y el editor de `0F` muestra como
>   pista el hash de lo que se escribe; no se añade entrada en `CREDITS.md`, porque el CRC es un
>   algoritmo de manual implementado aquí con parámetros deducidos de los datos.
>
> Criterios de «Hecho cuando» en la sección 7.
>
> **Fase 5 cerrada (2026-10-04)** con la prueba en el juego (detalle en
> `research/PRUEBAS_EN_JUEGO.md`). El usuario duplicó `MoveStates[0]` de
> `death/playercommon_movestates` (+3 objetos `07`; el estado «Jump» pasa del índice interno 585 al
> 588) y puso `JumpImpulse` 700. Informó de que el juego carga el archivo y refleja el cambio. La
> versión jugada (SHA `FE50F6A4…`) coincide con el ensayo, y restaurar devolvió `B46DD3DA…`.
> **Conclusión:** el juego tolera la renumeración de los objetos `07`, así que la edición
> estructural es viable.
>
> Criterios de «Hecho cuando»:
>
> 1. Duplicar, eliminar, subir y bajar en listas y mapas; poner a nulo un `07` o `FC`; rellenar
>    nulos según las decisiones: sí.
> 2. Todo se deshace y se revierte; editar y deshacer deja el blob idéntico: sí, por tests y fuzz.
> 3. «Cambios pendientes» muestra la estructura: sí.
> 4. Validación (bloquear claves repetidas y `FC` sin destino; avisar de `*ID` nuevos): sí.
> 5. El fuzz sobre los BOD reales es canónico y deshacer da el original: sí.
> 6. El juego carga la edición estructural: sí.
>
> 155 tests. Las fases 6 a 9 quedan a elección del usuario.
>
> Fase 5 implementada (2026-10-04), antes de la prueba en el juego (punto de control):
>
> - **Operaciones** (`edits.py`): `InsertItem`, `RemoveItem`, `MoveItem`, `ReplaceValue` y
>   `ReplaceTree`, todas reversibles y con la misma forma que `ValueEdit`. El documento ofrece
>   `duplicate_item`, `remove_item`, `move_item`, `set_null`, `fill_null`, `copy_example` y
>   `revert_object`; revertir sustituye el árbol entero y también se puede deshacer.
> - **Modelo de cambios nuevo** (`document.py`): un objeto está modificado si sus bytes actuales
>   difieren de los de partida. Los cambios pendientes salen de comparar el árbol actual con el de
>   partida (`diffing.py`), así que distinguen valor, reemplazado, añadido, eliminado y movido. El
>   modelo anterior guardaba los originales por ruta y no servía cuando las rutas se desplazan.
> - **Índice de huecos** (`references.SlotIndex`, en la misma pasada de fondo): qué clases y si
>   hay referencias en cada (clase dueña, campo, papel). Ofrece ejemplos para rellenar un nulo,
>   que se copian del árbol de partida.
> - **Validación** (`validation.py`, aplicada en `prepare_save`): claves repetidas y `FC` sin
>   destino bloquean; los `*ID` repetidos nuevos avisan. Las listas se comparan con su pareja
>   según el alineamiento del diff, no por ruta. Un primer intento por ruta daba 39 avisos falsos
>   al duplicar un estado de movimiento; hay un test de regresión.
> - **GUI:** menú contextual, Editar → Estructura y atajos Ctrl+D, Supr y Alt+↑/↓. El panel se
>   repinta conservando los nodos abiertos. Diálogo para rellenar nulos. Los avisos piden
>   confirmación al guardar y los errores lo impiden.
>
> Medido: duplicar, mover o quitar en el objeto más grande (350 KB) cuesta 0,16 s como máximo.
> El fuzz de 400 operaciones al azar sobre 73 BOD reales recodifica siempre de forma canónica,
> `verify` da correcto y deshacerlo todo devuelve `B46DD3DA…`. 155 tests. La edición candidata
> para el juego está en `research/PRUEBAS_EN_JUEGO.md` y ensayada sobre una copia.
>
> Decisiones de la fase 5 (2026-10-04), confirmadas por el usuario a partir del análisis de los
> 4 172 BOD:
>
> - **Tuplas `0B`:** sin cambios de forma; solo se editan sus valores. En el juego son de tamaño
>   fijo por campo (35 campos, siempre 2, 3 o 4 elementos). Corrige la tabla de la sección 6.
> - **Nulos:** «poner a nulo» solo donde hay un objeto `07` o una referencia `FC`; es donde
>   aparecen los 220 nulos del juego (`AnimController`, `InterruptHandler`, `AmbientBehavior*`…).
>   Un nulo se rellena copiando un objeto de una clase que ya aparece en ese mismo hueco (clase
>   del objeto dueño + campo) en algún lugar del archivo, o con una referencia si en ese hueco
>   también las hay.
> - **«Duplicar objetos»** se refiere a objetos `07` dentro del árbol. Crear objetos nuevos en el
>   índice OBSP exige una identidad nueva (hash del nombre): fase 6.
> - **Validación al guardar:** impiden guardar una clave repetida en un mapa `0A` o en una lista
>   de pares (no hay ninguna entre las 1 322 del juego) y un `FC` sin destino. Solo avisa un
>   campo `*ID` que pasa a repetirse en una lista de objetos donde antes era único (solo el 72 %
>   de esas listas tiene los `*ID` únicos en el juego, así que no es una regla general).
> - **Cierre:** tests más un punto de control con una edición estructural que hace el usuario
>   en el juego. El riesgo que se comprueba: insertar o borrar objetos `07` renumera sus
>   índices internos, y no se sabe si el juego los usa.
>
> **Primer hito cerrado (2026-10-04): fases 0 a 4.** Fase 4 cerrada con la prueba en el juego
> (detalle en `research/PRUEBAS_EN_JUEGO.md`):
>
> - El usuario guardó con la herramienta, sobre el `scripts.obsp` instalado, `JumpImpulse` del
>   estado «Jump» 350 → 700 (mismo tamaño) y después un `FlagID` de `base/quest_test_dialog`
>   alargado 5 bytes, que desplaza los offsets de 7 813 objetos.
> - Informó de que el juego carga los dos archivos y refleja el cambio.
> - La prueba de restaurar no había quedado aplicada en el archivo instalado. Con autorización
>   del usuario, Claude ejecutó `saving.restore_original` (el código de Archivo → Restaurar
>   original). El resultado: SHA `B46DD3DA…`, 18 334 463 bytes y `verify` correcto.
> - `scripts.original.obsp` (SHA `B46DD3DA…`) no cambió desde que se creó en el primer guardado.
>
> Criterios de la sección 10:
>
> 1. Abre el archivo del juego o una copia y navega los 7 862 objetos: sí (fase 2; mostrados
>    uno a uno, el peor en 0,22 s).
> 2. Propiedades BOD, metadatos y símbolos de los scripts: sí.
> 3. Edita int, float, bool, cadenas sin hash, cadenas conocidas y referencias, con deshacer: sí
>    (fase 3).
> 4. Guarda en `.obsp`; el primer guardado crea `scripts.original.obsp` idéntico al previo (SHA
>    verificado) y los siguientes no lo tocan: sí, por test y en la instalación (copia de
>    las 03:42:21 intacta tras los guardados de las 03:49 y 03:55).
> 5. Objetos no editados idénticos byte a byte; editar y revertir da el archivo idéntico: sí (tests
>    de oro, de edición y de guardado, también con el archivo real).
> 6. El juego carga el archivo guardado y refleja un cambio comprobable; restaurar devuelve
>    `B46DD3DA…`: sí.
>
> Medido al cierre: 127 tests sin omisiones y `verify` en 2,9 s. **Corrección al cerrar:** un
> test falló una vez de cada cinco ejecuciones y destapó un fallo real. Dos copias rotativas
> creadas en el mismo intervalo del reloj de Windows recibían el mismo nombre y la segunda pisaba
> a la primera. Ahora el nombre siempre es posterior a la última copia y se crea en modo
> exclusivo: hay un test nuevo y 20 ejecuciones seguidas sin fallos. Las copias de la prueba en
> el juego se crearon con minutos de diferencia y no se vieron afectadas.
> **Desviación:** la CI sigue sin ejecutarse en GitHub (no hay remoto); se reproduce en local con
> Python 3.12. Siguiente paso, según la sección 11: fases 5 a 9, según interés.
>
> Cambio de decisión (2026-10-04): se abandonó el mod de inventario de Darksiders2DLL
> (`scripts=inventory`) y su código se eliminó de la DLL. La DLL ya no lee, fija ni redirige
> `scripts.obsp`, así que editar el archivo instalado no entra en conflicto con ella. Se quitaron
> el aviso del diálogo de guardado, el caso especial de la sección 4.3 y su riesgo en la sección 9;
> se actualizaron las secciones 2.1 y 13 y el apéndice B. `research/INVENTORY_SCRIPT.md` de la DLL
> se conserva como investigación del formato (patrón `NumSlots` y offsets de `death/death`).
>
> Fase 4 implementada (2026-10-04), antes de la prueba en el juego (punto de control 2):
> `saving.py` sigue la sección 4. Construye en `prepare_save` y autoverifica en `verify_plan`
> (mismos objetos e identidades, blobs sin editar idénticos y editados iguales al árbol).
> Comprueba que el destino se puede escribir con `CreateFileW` vía `ctypes`, que distingue
> «en uso» (32/33) de «sin permiso» (5) porque `open()` los confunde. Crea la copia del original
> una sola vez (`X.original.obsp`, SHA verificado, solo lectura, etiquetada como original de
> Steam o como previa modificada), hace la copia rotativa en `.d2sv_backups\X.<AAAAMMDD-hhmmss-µs>.obsp`
> (las últimas 5) y escribe en `X.obsp.tmp` con `fsync` + `os.replace`. Después relee y compara
> el SHA; si no coincide ofrece restaurar. También restaura el original, informa del estado del
> archivo y limpia un `.tmp` huérfano al abrir. En la GUI: Guardar (Ctrl+S), Guardar como
> (Ctrl+Mayús+S), Restaurar original, conmutador de copias rotativas, confirmación al guardar
> dentro de la instalación del juego y Guardar/No/Cancelar al salir o abrir otro archivo. Tras
> guardar, `Document.mark_saved` toma el archivo escrito como nueva base sin perder el
> historial de deshacer. Tests (126 en total): la copia se crea una sola vez y nunca se toca;
> un fallo simulado en cada paso previo a la sustitución deja el destino intacto y sin `.tmp`;
> un handle con `FILE_SHARE_READ` (como lo abre el juego) da «Cierra Darksiders II…» sin
> crear nada; se rechaza `*.original.obsp`; 7 guardados dejan 5 copias rotativas; y el ciclo
> guardar → reabrir → restaurar sobre una copia real devuelve `B46DD3DA…`. Protocolo y ediciones
> candidatas en `research/PRUEBAS_EN_JUEGO.md`, ensayados sobre una copia: `JumpImpulse` del
> estado «Jump» 350 → 700 (mismo tamaño) y un `FlagID` de `base/quest_test_dialog` alargado
> 5 bytes (desplaza los offsets de 7 813 objetos). **Desviaciones:** la copia rotativa lleva
> microsegundos en el nombre para que dos guardados en el mismo segundo no choquen; `wording.py`
> corrige los plurales y los floats se muestran en notación decimal.
>
> Fase 3 cerrada (2026-10-04): edición de valores. Núcleo en `edits.py` (validación y comandos)
> y `document.py` (seguimiento de cambios, deshacer/rehacer, revertir propiedad u objeto,
> cambios pendientes y `current_data()`, el archivo tal como se guardaría). Editores: `02`
> (decimal o `0x…` como patrón de 32 bits, rango int32, pista con hexadecimal), `03` (admite
> coma decimal; rechaza NaN, infinitos y desbordamientos; la pista muestra el valor redondeado a
> float32), `04` (true/false), `05` (ASCII, sin NUL, ≤ 65 535), `0F` (solo cadenas ya presentes,
> con autocompletado entre las 70 182 y distinción de mayúsculas) y `FC` (selector de objetos;
> el destino debe existir). Edición en la celda con doble clic, F2 o Intro; menú contextual;
> Ctrl+Z / Ctrl+Y; Ctrl+P abre «Cambios pendientes» (antes → después por objeto); marcas en el
> árbol, en las propiedades, en el título y en la barra de estado; confirmación al salir o abrir
> otro archivo con cambios. Los campos con aspecto de identificador (`ID`, `*ID`, `*Id`,
> `*Hash*` o enteros con |valor| ≥ 1 000 000) muestran un aviso y piden confirmación. Un objeto
> está modificado mientras alguna propiedad difiera de su original: volver al valor de partida,
> a mano o deshaciendo, devuelve sus bytes originales. Criterios comprobados por test, también
> con el archivo real: cada edición cambia solo su blob (el float de `PanicHitTime` en
> `death/death_desc`: un blob distinto, mismo tamaño; una cadena `05` alargada 5 bytes: solo
> ese blob cambia y los offsets posteriores se desplazan 5), editar un `0F` y un `FC` y deshacer
> devuelve el SHA `B46DD3DA…`, y el resto de floats conserva sus bytes crudos (incluido un NaN
> con carga útil propia). 103 tests. **Desviaciones:** el `FC` se edita con un diálogo (F2), no
> en la celda, porque el doble clic sobre una referencia sigue navegando a su destino; el
> umbral de «parece un hash» (1 000 000) es una heurística propia.
>
> Fase 2 cerrada (2026-10-03), con visto bueno del usuario el 2026-10-04 (punto de control 1):
> visor de solo lectura en `gui/` (`app.py`, `object_tree.py`, `property_view.py`, `details.py`,
> `script_view.py`, más `search_view.py` y `theme.py`) sobre el núcleo nuevo `references.py`
> (índice "apunta a" / "usado por" y diccionario de hashes en una sola pasada) y `search.py`
> (búsqueda por ruta, nombre, carpeta, clase, valores, símbolos de script y, opcionalmente,
> nombres de campo, con prefiltro sobre los bytes crudos). Se abre con `python -m
> d2scriptviewer` o `D2ScriptViewer.pyw`. Abrir lee el archivo entero y lo cierra; indexar,
> buscar y decodificar objetos de más de 48 KB van en hilos con `queue`; los grupos del árbol
> de objetos y los hijos de las propiedades se cargan al abrirlos (listas de más de 500
> elementos, en tramos). Medido con el archivo real: abrir 0,38 s, índice listo en 1,8 s
> (3 406 referencias, 70 182 cadenas), **los 7 862 objetos mostrados uno a uno en 7,2 s: el peor
> 0,22 s y la media 0,9 ms**; búsqueda de metadatos 0,02 s y de valores 0,2–0,7 s. Ni el
> archivo ni su carpeta cambian (tamaño, fecha, SHA y listado comprobados por test). 74 tests.
> **Desviaciones:** los objetos se agrupan por carpeta del editor (o tipo) **y después por el
> directorio de la ruta**, porque 2 358 objetos no tienen carpeta y 4 075 cuelgan de `oc`;
> la hoja muestra el último tramo de la ruta. Las preferencias (archivo, geometría,
> agrupación) se guardan al cerrar en `%APPDATA%\D2ScriptViewer\config.json`, nunca junto al
> `.obsp`. Doble clic sobre un `FC` navega a su destino; Alt+←/→ recorre el historial.
>
> Fase 1 cerrada (2026-10-03): núcleo en `binary.py`, `formats/obsp.py` (lector y escritor que
> regenera tabla, índice y cabecera), `formats/bod.py` (árbol tipado, decodificador y codificador
> canónico), `formats/script.py` (cabecera y símbolos), `formats/hashes.py` (diccionario global),
> `document.py` (abrir y decodificar bajo demanda) y `verification.py`. CLI: `info`, `list`
> (`--tipo --clase --filtro`), `show <ruta|nombre>` (`--profundidad`), `roundtrip` (`--salida`) y
> `verify`; todas aceptan `--archivo`. Con el archivo real: reconstrucción con SHA `B46DD3DA…`
> (también recodificando los 4 172 BOD), 4 172 / 4 172 BOD idénticos, 3 690 / 3 690 cabeceras de
> script coherentes, 70 182 pares hash↔cadena sin conflictos, tablas de tipos y tags del apéndice
> exactas y 3 406 `FC` con destino. Tiempos (Python 3.12): leer y parsear el índice 30 ms,
> decodificar todos los BOD 1,75 s, codificarlos 0,55 s, `verify` completo 2,8 s. 53 tests
> (9 de oro con el archivo real; los sintéticos cubren los 11 tags, los modos 0/1 de lista, el
> modo 1 de mapa, clases nativas y de script, nombres nuevos y por referencia, nulos y `FC`).
> **Desviaciones:** los `idObjeto` se muestran en hexadecimal (`grupo:ID`); el módulo de
> comprobaciones se llama `verification.py` (no estaba en la sección 5); el decodificador
> rechaza modos de lista o mapa que no aparecen en el juego en lugar de suponer su significado.
> Hipótesis nueva, en `research/FORMATO.md`: `idObjeto` = hash del nombre en minúsculas
> (4 835 casos comprobables, ninguno en contra).
>
> Fase 0 cerrada (2026-10-03): repositorio git (rama `main`), paquete `d2scriptviewer` con
> `python -m d2scriptviewer --version` (0.1.0), `pyproject.toml` sin dependencias, LICENSE MIT,
> cabeceras SPDX, `CREDITS.md`, `README.md`, `CHANGELOG.md`, `.gitignore` con `*.obsp`,
> `build/` y `dist/`, CI en `.github/workflows/tests.yml` y apoyo para el archivo real en
> `tests/support.py` (`D2SV_OBSP` o ruta del juego; si falta, se omite). 5 tests en verde.
> **Desviación:** la CI no se ha ejecutado en GitHub porque no hay remoto ni push. Se reprodujo
> en local con Python 3.12.5 (el único instalado) y un test que parsea todo el código con
> `feature_version=(3, 10)` y comprueba que solo se importa la biblioteca estándar.
> Decisiones de la sección 12 confirmadas por el usuario el mismo día.
>
> Estado verificado localmente: 3 de octubre de 2026. Todavía no hay código en el
> proyecto. Los hallazgos de formato salen de un prototipo desechable ejecutado
> fuera del repositorio; todo lo que no está demostrado va marcado como
> **hipótesis**.

## 1. Objetivo

Construir una herramienta de escritorio que abra `scripts.obsp`, muestre su
contenido de forma legible, permita modificarlo y lo guarde en el mismo formato
`.obsp`, listo para que el juego lo cargue.

Prioridades, en este orden:

1. **Visualizar**: navegar los 7 862 objetos del archivo y ver sus datos.
2. **Modificar**: editar valores con validación, deshacer y lista de cambios pendientes.
3. **Guardar como `.obsp`**: reescribir el archivo con el formato original.
4. **Copia del original**: al guardar encima de `scripts.obsp`, crear antes una copia
   sin cambios del archivo original, verificada y que nunca se sobrescribe.

Objetivos secundarios, después del primer hito:

- Exportar a JSON (y CSV para las tablas).
- Desensamblar, y más adelante descompilar, los scripts compilados.

### Fuera del alcance del primer hito

- Editar bytecode de scripts (más adelante: solo parches de literales del mismo tamaño).
- Crear cadenas nuevas que necesiten hash, hasta identificar la función (fase 6).
- Recompilar scripts desde código fuente.
- Cargar el archivo como mod a través de Darksiders2DLL (ver apéndice B).
- Modificar `.upak`, `worlds.bin` u otros archivos del juego.

## 2. Estado local confirmado

### 2.1 Rutas

- Proyecto: `C:\Users\vicen\Documents\Proyectos\Software\D2ScriptViewer` (solo este plan y `CLAUDE.md`).
- Juego: `C:\Program Files (x86)\Steam\steamapps\common\Darksiders II Deathinitive Edition`.
- Archivo instalado: `media\scripts.obsp`, suelto (no está dentro de los `.upak`).
- Copias extraídas, idénticas al instalado (MD5 `063C0AE1D9696F2E13098569D441F460`):
  `C:\Users\vicen\Documents\Extractions\Darksiders\scripts.obsp`, `misc\scripts.obsp` y
  `misc\scripts_1.obsp`.
- Darksiders2DLL (`...\Software\Darksiders2DLL`): proxy `dinput8.dll` en C++. No lee ni redirige
  `scripts.obsp` (el modo `scripts=inventory` se retiró el 2026-10-04).
- Darkstractor (`...\Software\Darkstractor`): extractor en Python (solo biblioteca estándar)
  con tkinter. Trata `scripts.obsp` como copia exacta, sin interpretarlo.

### 2.2 Huellas

- `scripts.obsp`: 18 334 463 bytes, SHA-256
  `B46DD3DA7F17A0ED016E30AF523BFBA86D358C9920DFFA866C69D4A0F4F67C7C`
  (coincide con el registrado en Darksiders2DLL).
- `Darksiders2.exe`: SHA-256 `5580738EF70BC5BBCC72D7DC4A9C319956CD14DBFEF6F9DBEC54C1B5D97799FB`.

### 2.3 Lo que el prototipo ya demostró

| Prueba | Resultado |
|---|---|
| Reconstruir el `.obsp` completo desde sus partes (cabecera, cadenas, índice, datos) | Idéntico byte a byte, mismo SHA-256 |
| Decodificar los 4 172 objetos BOD a árbol y recodificarlos con un codificador canónico | 4 172 / 4 172 idénticos |
| Recalcular los contadores de la cabecera BOD (nº de nombres, longitud máxima) | 4 172 / 4 172 coinciden |
| Cabecera de los 3 690 scripts compilados (versión, símbolos, hash de ruta, grupo) | 3 690 / 3 690 coherentes |
| Misma cadena → mismo hash en contenedor, BOD y scripts | 70 182 pares, 0 conflictos |
| Cadenas no ASCII en todo el archivo | Ninguna |
| Rendimiento en Python 3.12 | Índice 15 ms · decodificar todo BOD 1,5 s · codificar 0,6 s |

Consecuencia: guardar en `.obsp` con ediciones de valores, e incluso con cambios
estructurales en BOD, es viable desde el principio. Lo único bloqueado es crear
cadenas **nuevas** (falta la función de hash).

### 2.4 Lo que todavía no se conoce

- ~~**Función de hash de 64 bits.**~~ **Resuelta el 2026-10-04 (fase 6):** CRC-64 reflejado con
  polinomio `0x0060034000F0D50B`, apéndice A.4. Se descartaron antes:
  - FNV-1 y FNV-1a 64, también en minúsculas, con NUL y en UTF-16.
  - CRC-64 ECMA, ISO y Jones (reflejados o no, con init/xorout 0 o ~0). La estructura de CRC era
    correcta, pero el polinomio no es ninguno de los habituales.
  - Multiplicativos comunes (31, 33, 65599…).
  - Mitades de 32 bits con CRC32, FNV-32, djb2 o sdbm.

  El FNV-1 64 que contiene el ejecutable pasa la cadena a minúsculas antes de hashear, así que no es este.
- **Los enteros de 32 bits con aspecto de hash** (p. ej. `OnStateOne = 0x4DFA84A3`, `MeshID`): no
  son ninguna de las dos mitades del CRC-64 ni el CRC-32 de las cadenas conocidas (ni sus
  minúsculas); solo hay coincidencias al azar. **Resuelto en su mayoría (2026-10-09):** no son
  hashes, sino marcas de tiempo Unix que el editor asignaba como ID (el 71,5 % de los 15 467
  valores distintos cae entre 2010 y 2012, casi todos en horario laboral de Austin, y solo 6 son
  negativos). Tampoco son ShortID de Wwise. Quedan excepciones sin estudiar (`research/FORMATO.md`).
- El campo de la cabecera OBSP que vale `1` y el `u16 = 1` de la cabecera BOD.
- La semántica de muchos enteros: algunos son IDs o hashes de 32 bits (p. ej. `OnStateOne = 0x4DFA84A3`).
- ~~El juego de opcodes completo del bytecode.~~ Formato resuelto en la fase 7 (apéndice A.3):
  se conocen los 57 opcodes y sus operandos, pero de la mayoría no se sabe qué hacen.

### 2.5 Pista importante para los scripts

El ejecutable incluye el compilador del lenguaje de scripts, un parser flex/bison:

- Tokens: `WHILE`, `BREAK`, `CONTINUE`, `RETURN`, `FUNCTION`, `NULLOBJECT`, `RAND_RANGE`,
  `CONTAINS`, `REMOVE`, `INT_CAST`, `ADD_ASSIGN`…
- Reglas: `if_statement`, `while_statement`, `iterator_statement`, `method_chain`,
  `property_chain`…
- Mensajes de error en tiempo de ejecución.

Con eso se puede reconstruir la gramática del lenguaje para un descompilador futuro.
Además, Darksiders2DLL ya documentó un patrón real del bytecode: `NumSlots\0`, `0x23`
+ int32 y luego `0x29 0x32` (`research/INVENTORY_SCRIPT.md`).

## 3. Decisiones de diseño

### 3.1 Tecnología: Python ≥ 3.10, solo biblioteca estándar, tkinter/ttk

Mismo stack y convenciones que Darkstractor:

- Cabeceras SPDX MIT y `CREDITS.md`. Las reglas para agentes que Darkstractor tiene en
  `AGENTS.md` aquí viven en `CLAUDE.md`.
- Tests con `unittest` y CI en Windows con Python 3.10–3.13.
- Ejecutable con PyInstaller.
- Interfaz en español con el mismo tema oscuro.

El rendimiento medido basta si se decodifica bajo demanda. Si se prefiere otro stack
(p. ej. C#/WPF), hay que decidirlo antes de la fase 0.

### 3.2 Principios

1. **Sin pérdidas.** Cada objeto conserva sus bytes originales y solo se recodifican los
   modificados. Guardar sin cambios produce exactamente el mismo archivo.
2. **Decodificar bajo demanda.** Abrir el archivo solo lee cabecera, cadenas e índice. Cada
   objeto se decodifica al seleccionarlo y queda en caché.
3. **Ediciones como comandos reversibles** (deshacer/rehacer). El documento sabe qué objetos
   están modificados.
4. **Validar antes de escribir.** Tipos, rangos (int32, float32), ASCII, longitudes (u16 en BOD)
   y existencia de las referencias.
5. **Verificar después de escribir.** El resultado se vuelve a parsear y comparar antes de darlo por bueno.
6. **Nunca tocar la copia del original.** Nunca se escribe en disco sin una acción explícita de guardar.
7. **Sin datos del juego en el repositorio.** Los tests usan fixtures sintéticos. Las pruebas con
   el archivo real solo se ejecutan si está presente.

## 4. Guardado y copia del original

### 4.1 Política de la copia

- Al guardar encima de `X.obsp`, si no existe `X.original.obsp` en la misma carpeta, se crea
  primero, copiando el archivo **tal como está en disco antes de guardar**.
- La copia se verifica (su SHA-256 debe ser igual al del archivo copiado) y se marca como solo lectura.
- Si ya existe, **no se toca nunca**: ni en guardados posteriores ni al restaurar.
- Si el SHA del archivo copiado es `B46DD3DA…`, la copia se etiqueta como "original de Steam".
  Si no, se avisa de que el archivo ya venía modificado, pero la copia se hace igualmente.
- La herramienta se niega a guardar encima de un `*.original.obsp`; para eso solo ofrece "Guardar como…".
- Opción activada por defecto: copia rotativa de la versión anterior en
  `.d2sv_backups\X.<fecha>.obsp`, conservando las últimas 5.

### 4.2 Secuencia de guardado

1. **Construir en memoria.** Los blobs sin cambios se copian tal cual y los modificados se
   recodifican. Se recalculan los offsets y tamaños del índice y se regeneran la tabla de cadenas y la cabecera.
2. **Autoverificar.** Se vuelve a parsear el resultado y se comprueba:
   - el mismo número de objetos e identidades (ruta, nombre, grupo, id, tipo);
   - que los blobs no modificados son idénticos;
   - que los modificados decodifican al árbol editado.
3. **Copia del original**, según la sección 4.1.
4. **Escribir.** Se escribe en `X.obsp.tmp` (misma carpeta), con `flush` + `fsync`, y se sustituye
   con `os.replace`, que es atómico en el mismo volumen. Un `.tmp` huérfano se limpia en el siguiente arranque.
5. **Comprobar.** Se relee el archivo final y su SHA-256 se compara con el de memoria.
6. **Fallos.** Si algo falla antes del paso 4, el archivo queda intacto. Si falla el paso 5, se
   informa y se ofrece restaurar desde la copia.

### 4.3 Casos especiales

- **Juego abierto.** El juego abre el archivo con `FILE_SHARE_READ`; mientras lo tenga abierto, la
  escritura fallará. Mensaje: "Cierra Darksiders II y vuelve a intentarlo".
- **Steam.** "Verificar integridad" o una actualización restauran el original. Al abrir, la
  herramienta muestra el estado del archivo: original de Steam, modificado o desconocido.
- **Restaurar original.** Copia `X.original.obsp` encima de `X.obsp`, con verificación. La copia se conserva.

## 5. Arquitectura

```text
D2ScriptViewer/
├─ d2scriptviewer/
│  ├─ __init__.py          # __version__ (fuente única)
│  ├─ __main__.py          # python -m d2scriptviewer
│  ├─ binary.py            # lectura/escritura binaria little-endian
│  ├─ errors.py
│  ├─ formats/
│  │  ├─ obsp.py           # contenedor: cabecera, cadenas, índice, blobs; escritor
│  │  ├─ bod.py            # árbol BOD tipado; decodificador y codificador canónico
│  │  ├─ script.py         # tipo 0: cabecera y símbolos; luego desensamblador
│  │  └─ hashes.py         # diccionario hash↔cadena; función de hash (fase 6)
│  ├─ document.py          # archivo abierto: objetos, caché, modificados, undo/redo
│  ├─ edits.py             # comandos de edición y validación
│  ├─ references.py        # índice inverso de referencias FC ("usado por")
│  ├─ search.py            # búsqueda global en segundo plano y dentro del objeto (fase 10)
│  ├─ saving.py            # pipeline de guardado, copia del original, restaurar
│  ├─ settings.py          # %APPDATA%\D2ScriptViewer\config.json
│  ├─ cli.py               # info, list, show, roundtrip, verify (export más adelante)
│  └─ gui/
│     ├─ app.py            # ventana, tema, menús, atajos, barra de estado
│     ├─ object_tree.py    # panel de objetos
│     ├─ property_view.py  # árbol de propiedades, editores y barra de búsqueda
│     ├─ details.py        # metadatos, hex, referencias
│     └─ script_view.py    # símbolos y (más adelante) desensamblado
├─ tests/
├─ research/               # notas de formato y resultados de pruebas en el juego
├─ CLAUDE.md  CREDITS.md  LICENSE  README.md  CHANGELOG.md  pyproject.toml
└─ PLAN_MAESTRO.md
```

### 5.1 Modelo BOD

Nodos:

| Nodo | Tag |
|---|---|
| `Object(index, clase, campos)` | 07 |
| `Int32` | 02 |
| `Float32` | 03 |
| `Bool` | 04 |
| `RawString` | 05 |
| `Name` | 0F |
| `List` / `Pairs` | 09, modo 0 / 1 |
| `Map` | 0A |
| `Tuple` | 0B |
| `ExternalRef(grupo, id)` | FC |
| `Null` | FE |

Los números guardan sus 4 bytes originales. Un float solo se reempaqueta si se edita, así
que ningún valor sin tocar cambia por redondeo. El codificador:

- interna los nombres por (hash, texto) en orden de primera aparición;
- numera los objetos en orden de aparición;
- recalcula la cabecera.

Esas tres reglas reproducen los 4 172 blobs originales.

## 6. Interfaz

Tres zonas, con el estilo visual de Darkstractor:

- **Objetos (izquierda).** Árbol por carpeta del editor (`oc\Body\slayer`, `data\quests\Z1`…) o
  por ruta. Filtros por tipo (Desc, AnimationList, SoundList, script, FloatTable…) y por clase,
  y buscador. Los objetos modificados llevan una marca.
- **Propiedades (centro).** `ttk.Treeview` con columnas Nombre | Tipo | Valor, carga perezosa de
  hijos y edición en línea con doble clic. Encima, una barra de búsqueda con un campo por columna
  (fase 10): recorre los resultados de uno en uno, con contador. Debajo de ella, la barra «Ir a»
  (fase 11), oculta hasta Ctrl+G: lee una ruta (`MoveStates[44].JumpImpulse` u
  `objeto · propiedad`) y salta a esa fila. El clic derecho copia la ruta de la propiedad o la
  ruta completa.
- **Detalles (derecha/abajo).** Ruta, nombre, clase, carpeta, grupo, id, tipo, offset y tamaño.
  Pestañas: Hex | Referencias ("apunta a" / "usado por") | Script.
- **Barra de estado.** Estado del archivo (original / modificado), número de cambios pendientes y ruta.
- **Acciones.** Abrir (Ctrl+O), Guardar (Ctrl+S), Guardar como, Deshacer/Rehacer (Ctrl+Z / Ctrl+Y),
  Revertir objeto, Cambios pendientes, Restaurar original, Buscar en el objeto (Ctrl+F; F3 y
  Mayús+F3 recorren los resultados), Buscar en todo el archivo (Ctrl+Mayús+F), Ir a la ruta
  (Ctrl+G) e Ir a referencia (doble clic).

Editores por tipo de valor:

| Tag | Editor | Fase |
|---|---|---|
| 02 int32 | Entrada con validación de rango y vista hexadecimal | 3 |
| 03 float32 | Entrada; muestra el valor ya redondeado a float32 | 3 |
| 04 bool | Casilla | 3 |
| 05 cadena sin hash | Texto libre ASCII (≤ 65 535) | 3 |
| 0F cadena con hash | Autocompletado entre las 70 182 cadenas conocidas; texto libre con el hash calculado y confirmación (fase 6) | 3 / 6 |
| FC referencia | Selector de objetos del índice; navegable | 3 |
| 09 / 0A contenedores | Duplicar, eliminar y reordenar elementos | 5 |
| 0B tupla | Solo sus valores: es de tamaño fijo (decisión del 2026-10-04) | 3 |
| FE nulo / 07 objeto / FC | Poner a nulo un 07 o FC; rellenar un nulo con la copia de un objeto de una clase vista en ese hueco | 5 |
| Scripts (tipo 0) | Solo lectura; luego parches de literales del mismo tamaño | 7 |

## 7. Fases

### Fase 0 — Base del repositorio

- `git init`, estructura del árbol, `pyproject.toml` sin dependencias, LICENSE MIT, cabeceras SPDX.
- `CLAUDE.md` (ya creado) con las reglas de Darkstractor (créditos, SPDX, licencias), `CREDITS.md`,
  `README.md` y `CHANGELOG.md`.
- `.gitignore` que excluya `*.obsp`, `build/` y `dist/`.
- CI de tests en Windows (3.10–3.13) que compruebe que no hacen falta dependencias externas.
- Apoyo para tests con el archivo real: variable `D2SV_OBSP` o ruta por defecto del juego. Si no existe, el test se omite.

**Hecho cuando** `python -m d2scriptviewer --version` funciona y la CI pasa.

### Fase 1 — Núcleo de formato (sin GUI)

- `obsp.py`: cabecera, tabla de cadenas, índice y acceso a blobs; escritor que regenera tabla, índice y cabecera.
- `bod.py`: decodificador a árbol y codificador canónico (11 tags).
- `script.py`: cabecera y tabla de símbolos de los scripts.
- `hashes.py`: diccionario global hash↔cadena.
- CLI: `info`, `list [--tipo --clase --filtro]`, `show <ruta|nombre>` (árbol en texto), `roundtrip` y `verify`.

**Hecho cuando**, con el archivo real:

- la reconstrucción da el SHA `B46DD3DA…`;
- los 4 172 BOD salen idénticos;
- las 3 690 cabeceras de script son coherentes;
- los tests sintéticos cubren todos los tags.

### Fase 2 — Visor (solo lectura)

- Ventana, árbol de objetos, filtros, propiedades, detalles con hex y símbolos de scripts.
- Índice de referencias FC con navegación "ir a" / "usado por".
- Búsqueda global en segundo plano: rutas, nombres, clases y valores.
- Abre el archivo leyéndolo entero y cerrándolo: no lo bloquea ni escribe nada.

**Hecho cuando** se navega todo el archivo, cualquier objeto se muestra en menos de 1 s y no
se escribe nada en disco.

### Fase 3 — Edición de valores

- Editores de la sección 6 para 02, 03, 04, 05, 0F (con cadenas conocidas) y FC.
- Deshacer/rehacer, revertir objeto, marca de modificado y panel "Cambios pendientes"
  (antes → después, por objeto).
- Aviso al editar campos con aspecto de identificador (`ID`, `*ID`, enteros que parecen hashes).

**Hecho cuando** editar y deshacer deja el blob idéntico y cada edición cambia solo su blob.

### Fase 4 — Guardado `.obsp` y copia del original (cierra el primer hito)

- Todo lo de la sección 4: Guardar, Guardar como, Restaurar original, copias rotativas, estado del
  archivo y mensajes para archivo bloqueado o sin permisos.
- Protocolo en el juego, con resultados en `research/PRUEBAS_EN_JUEGO.md`:
  1. Cambiar un valor de efecto evidente sin alterar el tamaño del blob y comprobar el efecto en
     el juego. Candidatos, a confirmar con el visor de la fase 2: una fila de `tables\Char_Death`
     o un float del `Desc` de Death.
  2. Hacer un cambio que altere el tamaño de un blob (p. ej. una cadena 05 más larga) para validar
     que el juego acepta los offsets recalculados.
  3. Restaurar el original y verificar el SHA `B46DD3DA…`.

**Hecho cuando** el juego carga un `scripts.obsp` guardado por la herramienta y refleja la
edición, y la copia del original es idéntica al archivo previo.

### Fase 5 — Edición estructural de BOD

- Duplicar, eliminar y reordenar elementos de listas y pares de mapas; poner a nulo; duplicar objetos.
- La renumeración de objetos y los contadores ya los resuelve el codificador.
- Validaciones: IDs únicos donde existan y referencias FC válidas.

**Hecho cuando** (fijado el 2026-10-04 con el usuario):

- se pueden duplicar, eliminar, subir y bajar elementos de listas `09` (modo 0 y 1) y entradas
  de mapas `0A`; poner a nulo un `07` o un `FC`; y rellenar un nulo según las decisiones de arriba;
- todo se puede deshacer y revertir, y editar y deshacer deja el blob idéntico;
- «Cambios pendientes» muestra también los cambios de estructura;
- guardar se bloquea con claves repetidas o `FC` sin destino, y avisa de `*ID` nuevos repetidos;
- un fuzz de operaciones aleatorias sobre los BOD reales recodifica de forma canónica y deshacerlo
  todo devuelve el original;
- el juego carga un archivo con una edición estructural (punto de control con el usuario).

### Fase 6 — Investigación: función de hash

- Banco de pruebas: los 70 182 pares conocidos sirven como vectores.
- Vías posibles:
  - **Offline:** más candidatos (CityHash, MurmurHash64A/3, xxHash64, SpookyHash, FarmHash, lookup3…).
    Cualquier implementación ajena se registra en `CREDITS.md`.
  - **Análisis estático** de `Darksiders2.exe` (Ghidra / x64dbg), partiendo del lector del OBSP
    (la cadena `scripts.obsp` está en el ejecutable) o del intérprete.
  - **Instrumentación** con Darksiders2DLL, registrando pares cadena → hash en tiempo de ejecución.
- Resultado: `hashes.py` con la función y sus tests. Habilita cadenas nuevas y renombrados.

**Hecho cuando** (fijado el 2026-10-04 con el usuario, tras identificar la función):

- `formats/hashes.py` calcula el hash, con sus parámetros documentados en el apéndice A. Con el
  archivo real, los tests comprueban los 70 182 pares y `idObjeto` y `hashRuta` de los 7 862
  objetos. Los tests sintéticos de la CI cubren el valor de control, la cadena vacía = 0 y que
  distingue mayúsculas, y los fixtures se generan con hashes reales;
- `verify` comprueba la función en todos los pares y que `idObjeto` es el hash del nombre en
  minúsculas, y guardar se bloquea si un hash no cuadra con su texto;
- los valores `0F` admiten cadenas nuevas con aviso y confirmación (decisiones de arriba);
  editar y deshacer devuelve `B46DD3DA…`, y el archivo guardado pasa `verify`;
- `python -m d2scriptviewer hash <texto>` y la pista del hash en el editor;
- están actualizados la sección 2.4, el apéndice A, `research/FORMATO.md`, `CLAUDE.md` (la
  regla de no crear cadenas con hash se levanta) y `CHANGELOG.md`;
- el juego carga un archivo con una cadena nueva y refleja su efecto (punto de control con el
  usuario); restaurar devuelve `B46DD3DA…`.

### Fase 7 — Scripts compilados

1. Formalizar la estructura del cuerpo: tablas de miembros y funciones, rangos de código.
2. Desensamblador de solo lectura. La tabla de opcodes se deduce estadísticamente sobre los 3 690
   scripts y se contrasta con el intérprete del ejecutable. Vista por función con líneas y nombres.
3. Parches de literales del mismo tamaño, generalizando el parche `NumSlots` de Darksiders2DLL:
   editar operandos `0x23` (int) y equivalentes sin cambiar tamaños.
4. A largo plazo: descompilador a pseudocódigo usando la gramática del compilador incluido en el
   ejecutable. Las ediciones que cambien el tamaño solo serán posibles cuando se entiendan los saltos.

**Hecho cuando** (fijado el 2026-10-04 con el usuario; puntos 1 a 4 de arriba, sin el 4.º):

- `formats/script.py` interpreta el cuerpo entero de los 3 690 scripts (miembros con sus valores
  por defecto, funciones y tablas finales) hasta el último byte, y volver a serializarlos da los
  mismos bytes en los 3 690;
- el desensamblador decodifica de forma lineal todas las funciones justo hasta su tamaño
  declarado, sin opcodes desconocidos, y todos los hashes en línea son los de sus nombres. La
  tabla de opcodes, con sus recuentos, sustituye a las hipótesis del apéndice A.3;
- la pestaña Script muestra los miembros y las funciones desensambladas, con líneas y nombres,
  y existe `python -m d2scriptviewer disasm <objeto>`; el trabajo pesado va en un hilo;
- se pueden parchear, sin cambiar tamaños, los literales de tamaño fijo y los valores por
  defecto de los miembros, con validación, deshacer y cambios pendientes. Al guardar se vuelve a
  desensamblar y se comprueba que solo cambiaron operandos;
- hay tests sintéticos (un script generado por el propio serializador) y con el archivo real
  (los 3 690 de ida y vuelta y desensamblados);
- el juego carga un parche con efecto visible que no se guarda en la partida (punto de control
  con el usuario), y restaurar devuelve `B46DD3DA…`;
- están actualizados el apéndice A.3, `research/`, `CLAUDE.md` y `CHANGELOG.md`.

Si no se llega al 100 % con la vía estadística, se para y se pregunta (decisión de arriba).

### Fase 8 — Exportación y parches (secundaria)

- **JSON por objeto**: árbol con tipos y valores, con las referencias resueltas a `"ruta/nombre"`
  además de grupo/id. Las carpetas reflejan la ruta, y un `manifest.json` recoge el índice.
- **CSV** para `FloatTable` y tablas similares.
- **Archivo de parche** (`.d2svpatch.json`) con la lista de ediciones (objeto + ruta de propiedad
  + valor). Sirve para reaplicar los cambios tras una restauración de Steam y para compartirlos
  sin distribuir el archivo del juego.
- Opcional: importar desde JSON, en un formato reversible.

**Hecho cuando** (fijado el 2026-10-04 con el usuario; sin importación):

- Archivo → Exportar… y `export --salida DIR` escriben:
  - un JSON por objeto con el árbol tipado y las referencias resueltas (ruta y nombre, además de
    grupo e id), con los scripts como miembros, valores iniciales y funciones desensambladas;
  - un `manifest.json` con la huella del archivo y el índice;
  - un CSV por cada `FloatTable`, con nombres de fila y de columna;

  todo en un hilo con progreso, nunca dentro de la carpeta del juego;
- Archivo → Exportar parche… y `patch crear` escriben un `.d2svpatch.json` relativo al original:
  valores (también cadenas nuevas, referencias y literales de scripts) y cambios estructurales
  sin datos del juego. Antes de escribirlo se reaplica sobre la base y debe dar el mismo SHA;
- Archivo → Aplicar parche… lo aplica como ediciones pendientes que se pueden deshacer, y
  `patch aplicar` lo aplica a un archivo nuevo. Se rechaza con un mensaje claro si un objeto,
  una propiedad o un valor anterior no coinciden;
- hay tests sintéticos de ida y vuelta para cada operación y con bases que no coinciden, y tests
  con el archivo real: exportar todo y reaplicar ediciones de las fases 5 a 7 con el SHA exacto;
- en el juego: guardar a mano, exportar el parche, restaurar, reaplicar, obtener el mismo SHA y
  jugar (punto de control con el usuario);
- están actualizados el plan, `CLAUDE.md`, `CHANGELOG.md` y el README.

### Fase 9 — Distribución

- Ejecutable con PyInstaller y workflow de release como el de Darkstractor.
- README con guía de uso y advertencias (copia del original, juego cerrado, Steam).

### Fase 10 — Búsqueda dentro del objeto

Decisiones del 2026-10-06 en la nota del principio.

- **Barra** bajo el título del objeto, en el panel de propiedades: campos `Nombre`, `Tipo` y
  `Valor`, botones de anterior y siguiente (‹ ›) y un contador («3 de 7»).
  - Nombre y Valor: texto contenido, sin distinguir mayúsculas, tal como se ve en la columna.
    En una referencia, `→` y el destino.
  - Tipo: desplegable con los tipos del objeto abierto y «(cualquiera)». Se puede escribir.
    Coincidencia exacta, sin distinguir mayúsculas.
  - Un campo vacío no filtra. Con los tres vacíos no hay resultados.
- **Teclas:**
  - Ctrl+F lleva el foco a la barra; Ctrl+Mayús+F abre la búsqueda global.
  - En la barra, Intro o F3 va al siguiente y Mayús+Intro o Mayús+F3 al anterior. Al llegar al
    final vuelve al principio.
  - Escape devuelve el foco al árbol. F3 y Mayús+F3 también funcionan desde el árbol.
- **Ir a un resultado** abre los nodos y tramos necesarios, selecciona la fila y la deja a la
  vista. La pista y la edición (F2) siguen igual.
- **Recalcular:**
  - al escribir, tras 200 ms sin teclear;
  - al cambiar de objeto: los criterios se conservan y la selección no se mueve;
  - tras editar, deshacer, rehacer o cambiar la estructura.
- **Núcleo sin Tk:** `search.find_in_tree` devuelve las rutas en el orden de las filas. La GUI
  solo la llama y navega con `reveal`.

**Hecho cuando:**

- la barra, las teclas y el recálculo funcionan como se describe arriba;
- hay tests unitarios con los fixtures:
  - cada campo por separado y combinados;
  - mayúsculas y referencias buscadas por su destino;
  - el orden de las filas;
  - una lista de más de 500 elementos;
  - criterios vacíos y sin resultados;
- hay tests de la GUI:
  - contador, y anterior/siguiente con vuelta al principio;
  - un resultado dentro de un tramo;
  - recálculo tras editar y al cambiar de objeto;
  - F2 sobre un resultado;
  - Ctrl+Z en un campo de la barra no deshace el archivo;
  - Ctrl+Mayús+F abre la búsqueda global;
- hay tests con el archivo real:
  - en `death/death`, `op_3A` + `NumSlots` da las 7 rutas de `Funciones.onInit` (`0x0770` a
    `0x0A4A`), y el `int32` siguiente vale 21, 21, 21, 22, 22, 22 y 21;
  - el objeto mayor se busca en menos de 200 ms;
- no hace falta prueba en el juego: no cambia el formato ni el guardado;
- están actualizados:
  - el plan, sección 6 incluida;
  - `CLAUDE.md`, `CHANGELOG.md` (`[Unreleased]`) y el README;
  - `GUIA_MODDER.md`: atajos, y el ejemplo del inventario marcado como no probado en el juego.

### Fase 11 — Ir a una ruta

Decisiones del 2026-10-09 en la nota del principio.

- **Barra «Ir a»** en el panel de propiedades, entre la barra de búsqueda y el árbol, oculta
  hasta que se pulsa Ctrl+G o Ir → «Ir a la ruta…».
  - Al abrirse, se rellena con el portapapeles si parece una ruta y, si no, con el último texto
    usado, seleccionado. Ctrl+G con la barra abierta solo vuelve al campo y selecciona su texto.
  - **Intro** va. Si llega, la barra se cierra y el foco pasa al árbol con la fila
    seleccionada, que F2 edita. Si falla, sigue abierta con el tramo que falló seleccionado.
  - **Escape** cierra la barra y devuelve el foco al árbol.
  - Ctrl+Z, Ctrl+Y y Ctrl+P en el campo no tocan el archivo.
  - Ctrl+G solo actúa en la ventana principal y cancela una celda en edición.
- **Formatos:**
  - `propiedad`: la etiqueta de `bod.path_label`, en el objeto abierto.
  - `objeto · propiedad` u `objeto::propiedad`, con espacios opcionales: cambia de objeto, y
    el cambio queda en el historial (Alt+←).
  - `objeto` solo, con «/» en el primer tramo: abre el objeto.
  - «Copiar ruta completa» (clic derecho) copia `objeto · propiedad`.
- **Resolución, tramo a tramo:**
  - un nombre: exacto; si no, sin mayúsculas ni tildes y único; en `0x…`, por valor;
  - un par: `clave` o `valor`;
  - un índice: `[n]` dentro del rango.
- **Pista**, retenida (no la pisa la selección que provoca el salto):
  - en un fallo: el tramo, el motivo y hasta 3 nombres parecidos, el rango válido o lo que se
    esperaba;
  - con dos campos iguales: va al primero y lo avisa;
  - con un objeto inexistente: no navega y sugiere rutas parecidas.
- **Objetos que se decodifican en un hilo:** la ruta se resuelve al terminar, sin congelar la
  ventana. Si mientras tanto se cambia de objeto, no se salta.
- **Errores previos de la pista:** el aviso de clave repetida usa la pista retenida, y la pista
  de estructura conserva las mayúsculas de las teclas.
- **Núcleo sin Tk:**
  - en `bod.py`, la inversa de `path_label` (texto → pasos, con errores de sintaxis claros) y
    su resolución sobre un árbol, que da el nodo válido más profundo y el motivo del fallo;
  - en `Document`, la resolución del objeto y `full_label`, lo que hoy hace `_label`.

  La GUI solo la llama y navega con `navigate` y `reveal`.

**Hecho cuando:**

- la barra, las teclas, el relleno y la pista funcionan como se describe arriba;
- hay tests unitarios con los fixtures:
  - ida y vuelta `path_label` → ruta en todas las filas de los 4 objetos;
  - pares (`clave` y `valor`), una lista de más de 500 elementos (`big_list_document`) y un
    script;
  - mayúsculas y su ambigüedad;
  - rutas que fallan a mitad (nombre, índice y tipo);
  - texto vacío o sin sentido;
  - el formato con objeto, el objeto solo y cuándo «parece una ruta»;
- hay tests de la GUI, con `invoke_binding`:
  - Ctrl+G y el menú;
  - ir a una fila dentro de un tramo;
  - saltar de objeto, también cuando se decodifica en un hilo;
  - el error en la pista, comprobado después de procesar los eventos;
  - Ctrl+Z en el campo no deshace el archivo;
  - el relleno desde el portapapeles;
  - «Copiar ruta completa»;
  - el aviso de clave repetida sigue en la pista después de procesar los eventos, y la pista de
    estructura conserva las mayúsculas;
- hay tests con el archivo real:
  - ida y vuelta en todas las filas de los 7 862 objetos, con su tiempo medido; la segunda fila
    de `wailing_host` va a la primera, con aviso;
  - `MoveStates[44].JumpImpulse` en `death/playercommon_movestates` (float 350),
    `Funciones.onInit.0x004E` en `ui_core/pausemenu` (bool true) y
    `Dialogs[0].Actions[1].FlagID` en `base/quest_test_dialog`;
- no hace falta prueba en el juego: no cambia el formato ni el guardado;
- están actualizados:
  - el plan, sección 6 incluida;
  - `CLAUDE.md`, `CHANGELOG.md` (`[Unreleased]`) y el README;
  - `GUIA_MODDER.md`: el atajo, el menú, y que las rutas de la tabla «Lo que ya está probado»
    se pueden pegar en Ctrl+G.

## 8. Estrategia de pruebas

### Unitarias (sin el juego, en CI)

- **Fixtures sintéticos** construidos con el propio codificador: un OBSP mínimo con varios tipos de
  objeto que cubra los 11 tags, listas en modo 0 y 1, clases nativas y de script, nombres nuevos y
  por referencia, nulos y referencias externas.
- **Invariantes**: decodificar y volver a codificar da lo mismo; la cabecera se recalcula; los
  offsets son contiguos; la tabla de cadenas queda en orden de primera aparición.
- **Ediciones**: cada tipo de valor y sus límites (int32, float32 NaN/inf, ASCII, longitud), deshacer/rehacer.
- **Guardado**:
  - la copia se crea una sola vez, verificada, y nunca se sobrescribe;
  - un fallo simulado a mitad deja el original intacto;
  - un archivo bloqueado (handle abierto sin compartir escritura) produce un error claro;
  - se rechaza guardar encima de `*.original.obsp`.

### Con el archivo real (se omiten si no está)

- Reconstrucción idéntica (SHA `B46DD3DA…`), 4 172 BOD idénticos y 3 690 scripts coherentes.
- Editar un valor cambia solo ese blob y los offsets posteriores del índice (diff estructural).
- Editar y revertir deja el archivo idéntico.

### GUI

- Prueba de humo: crear la ventana, cargar un fixture, seleccionar un objeto, editar un valor y cerrar.
- Las ventanas se prueban ocultas. Como Tk descarta las teclas sintéticas sin foco, los atajos se
  prueban invocando el callback de su enlace (`invoke_binding` en `tests/test_gui.py`).
- `<<TreeviewSelect>>` llega por la cola de eventos: lo que un test compruebe en la pista después
  de seleccionar una fila exige procesar antes los eventos (`update()`), o pasaría sin comprobar
  nada (fase 11).

### En el juego (manual)

- El protocolo de la fase 4, con resultados en `research/`.

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Función de hash desconocida | Resuelto en la fase 6 (CRC-64, apéndice A.4). Una cadena nueva pide confirmación porque el juego solo la reconoce si existe algo con ese nombre |
| Semántica desconocida de algunos valores (IDs, hashes, enums) | Mostrar el dato crudo, avisar en campos tipo ID, hacer cambios pequeños y probarlos en el juego |
| El juego valida algo que no vemos | No hay checksum aparente en la cabecera; pasos 1 y 2 del protocolo de la fase 4 |
| Otro archivo depende de offsets del `.obsp` (improbable) | Paso 2 del protocolo (cambio de tamaño) |
| Corromper el archivo instalado | Copia del original, escritura atómica, verificación posterior y Restaurar original |
| Juego abierto con el archivo en uso | Detectar el error y pedir que se cierre el juego |
| Steam restaura el archivo | Mostrar el estado al abrir; reaplicar con el archivo de parche (fase 8) |
| Redondeo de floats | Conservar los bytes crudos y reempaquetar solo los valores editados |
| Objetos grandes en tkinter (hasta 350 KB, `base/itemfoleytable`) | Hijos perezosos en el árbol y búsqueda en un hilo aparte |
| Contenido del juego en el repositorio | `.gitignore` con `*.obsp` y fixtures sintéticos |

## 10. Criterios de finalización del primer hito

- Abre el `scripts.obsp` del juego o una copia y permite navegar los 7 862 objetos.
- Muestra las propiedades de los objetos BOD y los metadatos y símbolos de los scripts.
- Edita int, float, bool, cadenas sin hash, cadenas conocidas y referencias, con deshacer.
- Guarda en `.obsp`. El primer guardado crea `scripts.original.obsp` idéntico al archivo previo
  (SHA verificado) y los siguientes no lo tocan.
- Los objetos no editados quedan idénticos byte a byte, y editar y revertir devuelve el archivo idéntico.
- El juego carga el archivo guardado y refleja un cambio comprobable. Restaurar original devuelve el SHA `B46DD3DA…`.

## 11. Orden inmediato recomendado

1. Confirmar las decisiones abiertas (sección 12).
2. Fases 0 y 1, portando el prototipo con sus tests.
3. Fase 2 (visor), luego fases 3 y 4 (edición y guardado).
4. Prueba en el juego.
5. Fases 5 a 9 según interés.

## 12. Decisiones

Confirmadas por el usuario el 3 de octubre de 2026:

| Decisión | Estado |
|---|---|
| Stack | **Decidido:** Python ≥ 3.10, solo biblioteca estándar, tkinter/ttk (el usuario tiene Python 3.12.5 con Tk 8.6) |
| Nombre de la copia | **Decidido:** `scripts.original.obsp`, junto al archivo que se guarda |
| Copias rotativas de la versión anterior | **Decidido:** activadas, las últimas 5, en `.d2sv_backups\` |
| Licencia y autoría | **Decidido:** MIT, BOTProT800 |
| Repositorio público | Abierta; el archivo del juego nunca se versiona |

## 13. Prompt de contexto para retomar el proyecto

> D2ScriptViewer es un visor/editor en Python (solo stdlib, tkinter) para
> `media\scripts.obsp` de Darksiders II Deathinitive Edition (18 334 463 bytes,
> SHA-256 `B46DD3DA…`). Prioridad: visualizar → editar → guardar al mismo
> formato `.obsp`, creando antes `scripts.original.obsp` (una sola vez,
> verificada, nunca sobrescrita). Exportar a JSON es secundario. El formato
> está en el apéndice A de `PLAN_MAESTRO.md`: el contenedor y los 4 172 objetos
> BOD se reconstruyen byte a byte; la función de hash de 64 bits es un CRC-64 con
> polinomio propio (apéndice A.4). Proyectos relacionados: Darksiders2DLL (C++, proxy `dinput8.dll`;
> no toca `scripts.obsp`) y Darkstractor (Python, mismo estilo).
> Consulta la sección 7 para saber en qué fase está el proyecto.

## 14. Créditos y procedencia

El conocimiento del formato procede del análisis local del 3 de octubre de 2026 y de
`Darksiders2DLL/research/INVENTORY_SCRIPT.md` (trabajo propio: offsets y patrón de `NumSlots`).
No se ha usado código ni documentación de terceros. Si se incorpora cualquier implementación
externa (p. ej. de funciones de hash en la fase 6), se registrará en `CREDITS.md` según las reglas
de `CLAUDE.md`.

---

## Apéndice A — Especificación verificada

Todos los enteros son little-endian. Los "hash" son u64 de la función del apéndice A.4;
la cadena vacía tiene hash 0.

### A.1 Contenedor OBSP

| Offset | Tamaño | Campo | Valor en el original |
|---|---|---|---|
| 0x00 | 4 | Firma `OBSP` | |
| 0x04 | 1 | Byte `0x00` | 0 |
| 0x05 | 4 | Versión | 10 |
| 0x09 | 4 | Desconocido | 1 |
| 0x0D | 4 | Número de objetos | 7 862 |
| 0x11 | 4 | Fin de la tabla de cadenas (= inicio del índice) | 0x9C0E6 |
| 0x15 | 4 | Número de cadenas | 15 520 |
| 0x19 | 4 | Longitud máxima de cadena | 74 |
| 0x1D | … | Tabla de cadenas: `{ u64 hash; u32 len; char[len] }`, ASCII sin NUL | |
| 0x9C0E6 | 51 × n | Índice | |
| 0xFDF28 | … | Datos: blobs contiguos en el orden del índice, sin relleno; el último acaba en EOF | |

- La tabla de cadenas contiene, sin repetir y en orden de primera aparición, las cadenas
  (ruta, nombre, carpeta, clase) al recorrer el índice. Incluye la cadena vacía.
- Entrada del índice, 51 bytes, empaquetada (`<QQIIHBQQQ`):

```text
u64 hashRuta     ruta del objeto, p. ej. "sh_plinth/plinth_desc"
u64 idObjeto     identidad; junto con el grupo es lo que usan las referencias FC
u32 offset       absoluto en el archivo
u32 tamaño
u16 grupo        626 valores distintos (10000–11818)
u8  tipo         categoría del blob (tabla siguiente)
u64 hashNombre   p. ej. "Plinth_Desc"
u64 hashCarpeta  carpeta del editor, p. ej. "oc\Body\slayer" (160 distintas; 0 = ninguna)
u64 hashClase    clase nativa o ruta de clase de script; 0 en los tipos 0, 9 y 15
```

| Tipo | Contenido | Objetos | Bytes |
|---|---|---|---|
| 0 | Script compilado | 3 690 | 5 795 617 |
| 1 | Instancias de clases de script, `ItemGeneratorTable`, `Quest`, `DialogSet`… | 757 | 1 525 649 |
| 2 | `CharacterMoveStateList` | 275 | 1 945 850 |
| 3 | `SoundList` | 275 | 830 826 |
| 4 | `AnimationList` | 1 071 | 3 603 893 |
| 5 | `CharacterConditionalList` | 7 | 64 591 |
| 6 | `InputWindowList` | 5 | 53 506 |
| 7 | `HitInfoList` | 3 | 64 617 |
| 8 | `*Desc` (actores, personajes, proyectiles, ítems…) | 1 668 | 2 686 596 |
| 9 | `ModuleSystem` (grafos de módulos) | 4 | 47 565 |
| 14 | `TerrainMaterialDesc` | 42 | 25 559 |
| 15 | `FloatTable` | 65 | 650 026 |

### A.2 Blob BOD (todos los tipos salvo el 0)

Cabecera, 16 bytes:

```text
"BOD\xFD"   u16 versión = 4   u16 = 1 (desconocido)
u32 número de entradas de la tabla interna de nombres
u32 longitud máxima de nombre
```

Después vienen la **clase raíz** y sus **campos**.

- **Nombre** (token internado):
  - `01` + u64 hash + u16 len + char[len]: se añade a la tabla;
  - `00` + u32 índice: referencia a una entrada ya definida.

  Nombres de campo, nombres de clase y cadenas `0F` comparten la misma tabla.
- **Clase**:
  - `01` + nombre: clase nativa;
  - `04` + u32 grupo + nombre: clase de script.
- **Campos**: u32 n, seguido de n × { nombre, valor }.
- **Valor**: u8 tag + carga útil:

| Tag | Tipo | Carga útil | Apariciones |
|---|---|---|---|
| 02 | int32 con signo | 4 bytes | 196 222 |
| 03 | float32 | 4 bytes | 127 484 |
| 04 | bool | u8 | 34 997 |
| 05 | cadena sin hash | `FF` + u16 len + char[len] | 2 865 |
| 07 | objeto | u32 índice (secuencial desde 0, en orden de aparición) + clase + campos | 146 328 |
| 09 | lista | u32 n + u8 modo (0: n valores; 1: n pares clave/valor) | 37 046 |
| 0A | mapa | u32 n + u8 modo (siempre 1 aquí) + pares | 39 |
| 0B | tupla | u32 n + n valores | 1 716 |
| 0F | cadena con hash | nombre (token internado) | 151 488 |
| FC | referencia externa | u32 grupo + u64 idObjeto | 3 406 |
| FE | nulo | sin carga | 220 |

Reglas del codificador canónico, verificadas sobre los 4 172 blobs:

- se interna por (hash, texto) en el orden de un recorrido en profundidad: clase antes que
  campos, nombre del campo antes que su valor;
- los objetos se numeran en ese mismo orden;
- los dos contadores de la cabecera se recalculan.

### A.3 Script compilado (tipo 0)

Verificado en los 3 690 scripts:

```text
u32 versión = 1
u32 número de símbolos
u32 longitud máxima de símbolo
símbolos: { u64 hash; u32 len; char[len] }
u64 hashRuta   (= el del índice)
u32 grupo      (= el del índice)
```

Detrás de la cabecera viene el cuerpo, formalizado en la fase 7 (2026-10-04) y verificado en
los 3 690 scripts: se interpretan hasta el último byte y vuelven a serializarse idénticos.

```text
u64 hash del nombre corto   (= símbolo 1, el último tramo de la ruta)
u64 hash de la clase base   (= símbolo 2)
u32 n; n × miembro:          u64 hash; u8 banderas; u8 tipo; [valor si banderas & 0x08]
u32 n; n × valor inicial:    u64 hash; valor
u32 n; n × función:          u64 hash; u32 tamaño; código[tamaño]
u32 n; n × estado:           u64 hash; u32 n; n × función
```

- Todos los hashes del cuerpo están en la tabla de símbolos del propio script.
- **Valores:** la codificación de los BOD (apéndice A.2), con los nombres como fichas
  `00` + u32 que indexan la tabla de símbolos; nunca hay fichas `01`. Cada valor numera sus
  objetos `07` desde 0.
- **Miembros (8 244):** banderas `0x0A` (con valor), `0x04`, `0x02` y `0x00`. El valor aparece
  si y solo si está el bit `0x08`. El tipo usa los tags BOD (2 int32, 3 float32, 4 bool,
  5 cadena, 7 objeto, 9 lista, 10 mapa, 11 tupla) y además el 1, cuyo significado no se conoce.
- **Valores iniciales (7 671):** 3 417 son de miembros del propio script declarados sin valor;
  el resto, de variables que no se declaran en él. Ninguno repite un miembro con valor.
- **Funciones (9 721, 12 vacías con tamaño 0) y estados (983).**

**Código de una función:** el byte 0 es el número de parámetros (igual al número de
instrucciones `0x28` en las 9 709 funciones con código), y después vienen instrucciones de
longitud variable. Con esta tabla de 57 opcodes, todas las funciones se decodifican de forma
lineal justo hasta su tamaño, y la última instrucción es siempre `0x2F`. Formatos de operando:
N = u8 longitud + u64 hash + texto + NUL; los 111 603 nombres en línea llevan el hash de su texto.

| Opcode | Nombre | Operando | Apariciones | Qué se comprobó |
|---|---|---|---|---|
| `0x3B` | línea | u32 | 64 366 | siempre crece dentro de una función (54 657 de 54 657) |
| `0x23` | int / args | i32 | 32 353 | 25 090 son el número de argumentos de una llamada (ver abajo) |
| `0x22` | float | f32 | 1 113 | 1 109 tienen 3 decimales o menos |
| `0x25` | bool | u8 | 5 039 | solo 0 (2 529) o 1 (2 510) |
| `0x24` | cadena | N | 12 391 | texto libre (frases, nombres de estado) |
| `0x28` | parámetro | N | 3 702 | tantos como indica el byte 0 |
| `0x38` | método | N | 18 756 | siempre precedido de `int n` + `0x2C` variable |
| `0x39` | llamada | N | 6 329 | siempre precedido de `int n` |
| `0x2F` | fin | — | 9 709 | último byte de cada función con código |
| `0x10` | op_10 | u32 destino | 6 751 | destino absoluto en la función; siempre hacia delante |
| `0x12` | op_12 | u32 destino | 2 415 | destino absoluto; hacia delante (2 001) o atrás (414) |
| `0x2D` | op_2D | u32 | 9 091 | significado desconocido |
| `0x20` `0x26` `0x27` `0x2C` `0x36` `0x3A` | op_XX | N | 314 · 42 · 3 308 · 47 470 · 5 · 19 286 | nombres en línea; `0x36` va precedido de `int n` |
| resto (39) | op_XX | — | | `0x00`–`0x0A`, `0x0C`–`0x0F`, `0x13`–`0x1B`, `0x1E`, `0x1F`, `0x21`, `0x29`–`0x2B`, `0x2E`, `0x30`–`0x32`, `0x34`, `0x35`, `0x3D`, `0x3E`, `0x43` |

- **Número de argumentos:** el `int n` que precede a una llamada vale entre 0 y 7. De los 2 102
  destinos distintos, 2 063 se llaman siempre con el mismo n; los otros 39 admiten argumentos
  opcionales (`setSaveValue` con 2 o 3, `setPosition` con 1 o 3). Esos literales no se parchean.
- **Saltos:** de los 9 166, todos caen al principio de una instrucción salvo uno de
  `maker_male/maker_youngin_emote_component`, que apunta a 6503 en una función de 336 bytes. Es
  un dato del original y el desensamblador lo muestra tal cual.
- **Hipótesis** (deducidas de la posición, sin comprobar): `0x29` asignación (`a.b = 21;` es
  `0x2C a`, `0x3A b`, `int 21`, `0x29`, `0x32`), `0x32` fin de sentencia, `0x35` inicio de
  sentencia, `0x10` salto si falso, `0x2A`/`0x2B` entrada y salida de bloque (5 026 cada uno).

**Editable sin cambiar tamaños** (fase 7): los literales int (los que no son número de
argumentos), float y bool del código, y los int, float y bool de los valores por defecto e
iniciales. En el juego son 31 145.

### A.4 Función de hash de 64 bits

Identificada el 2026-10-04 (fase 6) a partir de los 70 182 pares del archivo y comprobada en
todos ellos:

```text
CRC-64 reflejado (entrada y salida reflejadas), sobre los bytes de la cadena, sin NUL final
polinomio      0x0060034000F0D50B   (forma reflejada 0xD0AB0F0002C00600)
valor inicial  0xFFFFFFFFFFFFFFFF
XOR final      0xFFFFFFFFFFFFFFFF
control        "123456789" → 0x9AFB180E4C211BB4;  "" → 0
```

- Distingue mayúsculas y es la misma en la tabla de cadenas del contenedor, en las tablas de
  nombres de los BOD y en los símbolos de los scripts.
- `idObjeto` = hash del nombre en minúsculas (`death/death`, nombre `Death` → hash de `death`
  = `8C882C7C958E9802`), en los 7 862 objetos. `hashRuta`, `hashNombre`, `hashCarpeta` y
  `hashClase` son los hashes de sus textos.
- Cómo se dedujo, en `research/FORMATO.md`.

## Apéndice B — Interacción con Darksiders2DLL

- El juego lee `media\scripts.obsp` directamente. Sobrescribirlo, con su copia del original, no
  necesita la DLL.
- La DLL no lee, fija ni redirige `scripts.obsp`. El mod de inventario de la 0.7.0
  (`scripts=inventory`, que exigía el instalado original y solo admitía los siete `NumSlots` de
  `death/death`) se retiró el 2026-10-04. Una línea `scripts=` en su INI ahora desactiva el cargador.
- Integración posible a futuro, fuera de este plan: una acción "Guardar como mod" en
  D2ScriptViewer más un modo general en la DLL que valide la estructura OBSP. La DLL podría
  reutilizar las comprobaciones de la sección 4.2. Así no habría que tocar el archivo instalado
  y se convivía con Steam.
