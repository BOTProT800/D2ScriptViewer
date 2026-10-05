# Changelog

Todos los cambios relevantes de D2ScriptViewer se registran aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto sigue
[Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

## [1.0.0] - 2026-10-04

Primer release.

### Added

- Ejecutable de Windows (fase 9): `D2ScriptViewer.spec` construye con PyInstaller un único
  `D2ScriptViewer.exe` sin consola, con la licencia, los créditos, el historial y los textos de
  licencia de los componentes de terceros que lleva dentro (`THIRD_PARTY_NOTICES.md`, carpeta
  `licencias` y `VERSIONES.txt` con la versión exacta de cada uno).
- `--autoprueba informe.txt` en el ejecutable: módulos, función de hash, un OBSP sintético con
  `verify`, archivos incluidos y la ventana principal, sin mostrarla. También se ejecuta en la CI.
- Workflow de release: con una etiqueta `v*` pasa los tests, construye la rueda, el código fuente y
  el `.exe` (PyInstaller 6.22.3, versión fija), ejecuta su autoprueba y publica la release con
  los avisos de terceros.
- Exportación (fase 8): un JSON por objeto con el árbol tipado y las referencias resueltas (los
  scripts, con miembros y código desensamblado), `manifest.json` y un CSV por cada `FloatTable`.
  Archivo → Exportar a JSON y CSV… y `python -m d2scriptviewer export`.
- Parches `.d2svpatch.json` (fase 8): lo que cambió respecto al original, por objeto, con valores
  y operaciones de estructura que solo copian contenido del original (sin datos del juego). Al
  crearlo se reaplica sobre la base y debe dar el mismo archivo. Al aplicarlo se comprueban
  objeto, propiedad, valor anterior y huellas; o se aplica entero, como un paso de deshacer, o no
  se aplica. Archivo → Exportar parche… / Aplicar parche…, y `patch crear` / `patch aplicar`.
- Prueba en el juego del parche (`research/PRUEBAS_EN_JUEGO.md`): tras restaurar, el parche
  reaplicado da el mismo archivo, byte a byte, que el guardado a mano.
- Scripts compilados (fase 7): estructura completa del cuerpo (miembros con sus valores por
  defecto, valores iniciales, funciones y estados) y desensamblador de los 57 opcodes, verificados
  en los 3 690 scripts del juego, que se reserializan idénticos. El panel central muestra los
  miembros y el código de cada función con sus líneas, literales, llamadas y nombres.
- Parches de scripts sin cambiar tamaños: literales int, float y bool del código (salvo el número
  de argumentos de una llamada) y valores por defecto e iniciales de esos tipos, con deshacer,
  marcas y cambios pendientes. Al guardar se comprueba que solo cambiaron esos valores.
- `python -m d2scriptviewer disasm <script>`, y `verify` comprueba también el cuerpo y el
  bytecode de los scripts y los hashes de los 111 603 nombres en línea.
- Prueba en el juego de un parche de script (`research/PRUEBAS_EN_JUEGO.md`): con el literal de
  `Game.setPaused` del menú de pausa a `false`, el juego sigue corriendo con el menú abierto.
- Función de hash de 64 bits del juego (fase 6): un CRC-64 reflejado con polinomio
  `0x0060034000F0D50B`, deducido de los 70 182 pares del archivo y comprobado en todos ellos.
  `idObjeto` es el hash del nombre en minúsculas en los 7 862 objetos.
- Cadenas con hash nuevas: los valores `0F` admiten cualquier texto ASCII, con el hash
  calculado. Si no aparece en el archivo se pide confirmación, con un aviso si solo difiere en
  mayúsculas de una conocida; una colisión de hash con otra cadena da error. La pista del editor
  muestra el hash.
- `python -m d2scriptviewer hash <texto>…`: hash e `idObjeto` de cada texto, sin leer archivos.
- `verify` comprueba la función de hash en todos los pares y que `idObjeto` es el hash del
  nombre en minúsculas. Guardar se bloquea si un hash de la tabla de cadenas o de un objeto
  modificado no cuadra con su texto.
- Prueba en el juego de una cadena nueva (`research/PRUEBAS_EN_JUEGO.md`): tres
  `AnimationName` de Death apuntan a `D_WScy_Combo04`, una animación del `.upak` que no aparecía
  en `scripts.obsp`, y el juego la reproduce.
- Edición estructural de BOD (fase 5): duplicar, eliminar, subir y bajar elementos de listas y
  entradas de mapas (Ctrl+D, Supr, Alt+↑/↓, clic derecho o Editar → Estructura); poner a nulo un
  objeto o una referencia; rellenar un nulo con la copia de un objeto de una clase que ya aparece
  en ese hueco del archivo, o con una referencia. Las tuplas, de tamaño fijo en el juego, solo
  admiten editar sus valores. Todo se puede deshacer y revertir.
- «Cambios pendientes» muestra también los cambios de estructura (añadido, eliminado, movido,
  reemplazado), calculados comparando con el árbol de partida.
- Validación al guardar: una clave repetida en un mapa o lista de pares, o una referencia sin
  destino, impiden guardar; un `*ID` que pasa a repetirse pide confirmación.
- Prueba en el juego de la edición estructural (`research/PRUEBAS_EN_JUEGO.md`): el juego carga
  un BOD con objetos insertados (índices internos renumerados) y refleja el cambio.
- Base del repositorio: paquete `d2scriptviewer` con `python -m d2scriptviewer --version`,
  `pyproject.toml` sin dependencias, licencia MIT, cabeceras SPDX, `CREDITS.md` y `README.md`.
- CI de tests en Windows con Python 3.10–3.13, que comprueba que no hacen falta dependencias.
- Apoyo para tests con el archivo real: `D2SV_OBSP` o la ruta por defecto del juego; si no
  existe, esos tests se omiten.
- Núcleo de formato: contenedor OBSP (lector y escritor que regenera tabla de cadenas, índice
  y cabecera), BOD (árbol tipado con los 11 tags, decodificador y codificador canónico que
  conserva los bytes crudos de int32, float32 y bool), cabecera y símbolos de los scripts de
  tipo 0 y diccionario global hash↔cadena.
- Línea de órdenes: `info`, `list` (`--tipo`, `--clase`, `--filtro`), `show <ruta|nombre>`,
  `roundtrip` (`--salida`) y `verify`, con `--archivo` o `D2SV_OBSP`.
- Tests de oro con el archivo real (SHA reconstruido, 4 172 BOD idénticos, 3 690 cabeceras de
  script coherentes, 70 182 pares hash↔cadena) y tests sintéticos sin datos del juego.
- Visor de solo lectura (`python -m d2scriptviewer` o `D2ScriptViewer.pyw`): árbol de objetos
  por carpeta, ruta o tipo con filtros por tipo, clase y texto; propiedades con columnas
  Nombre, Tipo y Valor; detalles con metadatos, hexadecimal, referencias ("apunta a" / "usado
  por") y símbolos de los scripts; búsqueda global (Ctrl+F); doble clic en una referencia
  para ir a su destino e historial con Alt+←/→. El trabajo pesado corre en hilos y los árboles
  se cargan al abrirlos, así que ningún objeto tarda más de 0,25 s en mostrarse.
- Edición de valores en el visor: enteros, floats, bools, cadenas sin hash, cadenas ya
  presentes en el archivo (con autocompletado) y referencias (con un selector de objetos).
  Doble clic, F2 o Intro editan en la celda con validación y una pista en vivo (hexadecimal,
  redondeo a float32, hash de la cadena); deshacer y rehacer (Ctrl+Z / Ctrl+Y); revertir una
  propiedad o un objeto; ventana «Cambios pendientes» (Ctrl+P) con antes → después; marcas de
  modificado en el árbol, las propiedades, el título y la barra de estado; aviso y
  confirmación al editar campos con aspecto de identificador o de hash.
- Guardar en `.obsp` (Ctrl+S) y Guardar como: el archivo se construye en memoria, se
  autoverifica, se escribe en un `.tmp` con `fsync`, se sustituye con `os.replace` y se relee
  para comparar su SHA-256. El primer guardado encima de `X.obsp` crea `X.original.obsp`,
  verificado y de solo lectura, que nunca se sobrescribe; guardar encima de un
  `*.original.obsp` se rechaza.
- Copias rotativas de la versión anterior en `.d2sv_backups\` (las últimas 5), activadas por
  defecto y desactivables desde el menú Archivo.
- Restaurar original, estado del archivo en la barra (original de Steam, modificado o
  desconocido), mensajes claros con el juego abierto, archivos de solo lectura o sin permisos,
  limpieza de un `.tmp` huérfano al abrir y pregunta de guardar al salir o al abrir otro archivo.
- `research/PRUEBAS_EN_JUEGO.md` con el protocolo y los resultados de la prueba en el juego: el
  juego carga un `scripts.obsp` guardado por la herramienta, refleja la edición, acepta un
  archivo de otro tamaño con los offsets recalculados, y restaurar devuelve el original de Steam.
  Con eso se cierra el primer hito (fases 0 a 4).

### Changed

- Versión 1.0.0. El README explica la descarga, las advertencias de uso y cómo construir el
  ejecutable; la CI de tests comprueba todos los módulos y ejecuta la autoprueba.
- Los floats se muestran en notación decimal (`200`, no `2e+02`) salvo en magnitudes extremas.
- Darksiders2DLL ya no lee ni fija `scripts.obsp` (su modo `scripts=inventory` se retiró): el
  diálogo de guardado, el README y el plan dejan de mencionarlo.

### Fixed

- Dos copias rotativas creadas en el mismo instante del reloj (en Windows avanza a saltos de
  milisegundos) recibían el mismo nombre y la segunda pisaba a la primera. Ahora el nombre
  siempre es posterior a la última copia y el archivo se crea en modo exclusivo.
