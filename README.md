# D2ScriptViewer

Visor y editor de escritorio para `media\scripts.obsp` de **Darksiders II Deathinitive Edition**
(PC), escrito en Python con solo la biblioteca estándar y tkinter.

Permite ver los 7 862 objetos del archivo, editar sus valores y su estructura, crear cadenas
nuevas, ver y parchear los scripts compilados, exportar a JSON y CSV, y guardar en el mismo
formato `.obsp` con una copia intacta del original. Todo se ha probado en el juego. El plan y su
historial están en [PLAN_MAESTRO.md](PLAN_MAESTRO.md).

Los atajos de teclado y lo que se suele modificar están en la
[guía del modder](GUIA_MODDER.md).

## Antes de empezar

- **La primera vez que guardas** encima de `scripts.obsp` se crea `scripts.original.obsp`: una
  copia exacta del archivo tal como estaba, verificada y de solo lectura. Nunca se sobrescribe y
  **Archivo → Restaurar original** la vuelve a poner en su sitio.
- **Cierra Darksiders II antes de guardar.** Mientras el juego está abierto, el archivo está en
  uso y no se puede escribir.
- **Steam** («Verificar integridad», o una actualización) devuelve el archivo original y borra
  tus cambios. Guarda antes un parche (**Archivo → Exportar parche…**) para reaplicarlos luego.
- Haz cambios pequeños y pruébalos: muchos valores del juego no tienen un significado
  documentado.

## Descarga

Cada release publica `D2ScriptViewer.exe`, un único ejecutable para Windows que no necesita
Python. Junto a él van los textos de licencia del software de terceros que lleva dentro
(CPython, Tcl/Tk y el bootloader de PyInstaller); ver
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). La línea de órdenes y los tests necesitan el
código fuente y Python.

## Requisitos (desde el código fuente)

Python 3.10 o posterior en Windows. No hace falta instalar ningún paquete.

## Uso

Interfaz gráfica (o doble clic en `D2ScriptViewer.exe` o en `D2ScriptViewer.pyw`):

```powershell
python -m d2scriptviewer
```

Abre el último archivo usado, el de `D2SV_OBSP` o el del juego. Abrir no bloquea ni modifica
el archivo.

- **Objetos** (izquierda): agrupados por carpeta del editor, ruta o tipo; filtros por tipo,
  clase y texto.
- **Propiedades** (centro): el árbol del objeto. Doble clic en una referencia (`→ …`) lleva a su
  destino; Alt+← y Alt+→ recorren el historial.
- **Detalles** (derecha): metadatos, volcado hexadecimal, referencias ("apunta a" / "usado por")
  y símbolos de los scripts compilados.
- **Buscar** (Ctrl+F): rutas, nombres, clases, valores (texto o número) y símbolos.

### Editar

Doble clic, F2 o Intro sobre un valor lo editan en la propia celda: Intro confirma y Escape
cancela. La línea bajo el árbol avisa de errores y muestra cómo quedará el valor (hexadecimal de
un entero, redondeo de un float).

- **Enteros:** decimal o `0x…` (patrón de 32 bits). **Floats:** admiten coma decimal; no se
  aceptan NaN ni infinitos. **Bools:** true/false.
- **Cadenas sin hash** (`'…'`): cualquier texto ASCII.
- **Nombres** (cadenas con hash): con autocompletado entre los que ya aparecen en el archivo.
  También se admite un nombre nuevo (ASCII): la herramienta calcula su hash y pide
  confirmación, porque el juego solo lo reconocerá si existe algo con ese nombre. Distingue
  mayúsculas, y avisa si el nombre nuevo solo se diferencia en eso de uno conocido.
- **Referencias** (`→ …`): F2 abre un selector de objetos; el doble clic sigue llevando al
  destino.
- Ctrl+Z / Ctrl+Y deshacen y rehacen; el menú Editar y el clic derecho permiten revertir una
  propiedad o el objeto entero; Ctrl+P abre los cambios pendientes.
- Los campos con aspecto de identificador (`…ID`, enteros enormes con pinta de hash) piden
  confirmación antes de cambiar.

Los scripts compilados se ven en el panel central: miembros con sus valores por defecto, valores
iniciales y el código desensamblado de cada función y estado (líneas, literales, llamadas,
nombres). Solo se pueden cambiar, sin alterar tamaños, los literales int, float y bool del código
y los valores de esos tipos; el número de argumentos de una llamada y el resto de filas son de
solo lectura.

### Cambiar la estructura

Sobre un elemento de una lista o una entrada de un mapa: **Ctrl+D** lo duplica (la copia queda
justo detrás), **Supr** lo elimina y **Alt+↑ / Alt+↓** lo mueven. Con el clic derecho (o Editar →
Estructura) también se puede **poner a nulo** un objeto o una referencia, y **rellenar un nulo**
copiando un objeto de una clase que ya aparece en ese mismo hueco en el archivo.

- Las tuplas (vectores, colores) tienen tamaño fijo: solo se editan sus valores.
- Al duplicar una entrada de un mapa, la clave queda repetida: cámbiala antes de guardar, porque
  una clave repetida impide guardar. Una referencia sin destino también lo impide.
- Si un campo `…ID` pasa a repetirse en una lista donde antes era único (lo normal tras duplicar
  un elemento), la herramienta avisa y pide confirmación al guardar.

### Guardar

- **Guardar** (Ctrl+S) reescribe el archivo en el mismo formato `.obsp`. La primera vez que se
  guarda encima de `scripts.obsp` se crea antes `scripts.original.obsp` en la misma carpeta:
  una copia exacta del archivo tal como estaba, verificada por SHA-256 y de solo lectura. Esa
  copia **nunca** se sobrescribe ni se borra, y no se puede guardar encima de ella.
- Cada guardado deja además la versión anterior en `.d2sv_backups\` (las últimas 5); se puede
  desactivar en el menú Archivo.
- El archivo se construye en memoria, se vuelve a leer y se compara antes de escribir; se
  escribe en un `.tmp` y se sustituye de forma atómica; al terminar se relee y se compara su
  SHA-256. Si algo falla antes de sustituirlo, el archivo queda intacto.
- **Guardar como…** escribe en otro archivo.
- **Restaurar original…** copia `scripts.original.obsp` encima de `scripts.obsp` y lo verifica.
- La barra de estado indica si el archivo es el original de Steam, si está modificado (y hay
  copia del original) o si es desconocido.

Avisos:

- **Cierra Darksiders II antes de guardar.** Con el juego abierto no se puede escribir, y la
  herramienta lo dice.
- «Verificar integridad de los archivos» de Steam, o una actualización, devuelven el original.

### Exportar y parches

- **Exportar a JSON y CSV…** escribe, en una carpeta vacía y nunca dentro de la del juego, un
  JSON por objeto (árbol con tipos y referencias resueltas; los scripts, con sus miembros y su
  código desensamblado), un `manifest.json` con el índice y un CSV por cada `FloatTable`. Es
  solo para leer o comparar: no se vuelve a importar.
- **Exportar parche…** guarda un `.d2svpatch.json` con lo que cambió respecto al original
  (`scripts.original.obsp` si existe). Lleva solo valores, rutas y operaciones de estructura que
  copian contenido del propio original: se puede compartir sin distribuir datos del juego.
  Antes de escribirlo, la herramienta lo reaplica sobre el original y comprueba que da
  exactamente el archivo actual.
- **Aplicar parche…** aplica un parche como cambios pendientes (se deshacen de una vez con
  Ctrl+Z) que luego se guardan como siempre. Sirve, por ejemplo, para recuperar tus cambios
  después de que Steam restaure el original. Si algún objeto, propiedad o valor no es el que
  espera el parche, no se aplica nada.

Línea de órdenes:

```powershell
python -m d2scriptviewer info
python -m d2scriptviewer list --tipo Desc --filtro death
python -m d2scriptviewer show death/death_desc --profundidad 3
python -m d2scriptviewer verify
python -m d2scriptviewer hash Death death/death_desc
python -m d2scriptviewer disasm death/death
python -m d2scriptviewer export --salida C:\exportado --tipo FloatTable
python -m d2scriptviewer patch crear --salida cambios.d2svpatch.json
python -m d2scriptviewer patch aplicar cambios.d2svpatch.json --salida C:\copia\scripts.obsp
```

Todas salvo `hash` aceptan `--archivo ruta\a\scripts.obsp`. `patch crear` usa como base
`--base` o el `*.original.obsp` junto al archivo, y `patch aplicar` escribe siempre un archivo
nuevo. `hash` calcula el hash de 64 bits
del juego para cada texto y el `idObjeto` que tendría un objeto con ese nombre, sin leer ningún
archivo.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Los tests que necesitan el archivo real del juego buscan la variable `D2SV_OBSP` o la ruta por
defecto de Steam, y se omiten si no lo encuentran:

```powershell
$env:D2SV_OBSP = 'C:\ruta\a\scripts.obsp'
```

## Construir el ejecutable

El workflow [release.yml](.github/workflows/release.yml) lo construye al subir una etiqueta
`v*`: pasa los tests, construye la rueda, el código fuente y el `.exe`, ejecuta la autoprueba
del `.exe` y publica la release con los avisos de terceros. En local:

```powershell
python -m venv build\venv-pyinstaller
build\venv-pyinstaller\Scripts\python -m pip install pyinstaller==6.22.3
build\venv-pyinstaller\Scripts\python -m PyInstaller --noconfirm --workpath build\pyinstaller D2ScriptViewer.spec
```

El resultado es `dist\D2ScriptViewer.exe`. `D2ScriptViewer.exe --autoprueba informe.txt`
comprueba el ejecutable sin abrir la ventana: escribe el informe y sale con 0 si todo va bien.

## Datos del juego

El repositorio no contiene ningún dato del juego: `*.obsp` está excluido y los tests usan
fixtures sintéticos.

## Licencia

MIT. Ver [LICENSE](LICENSE) y [CREDITS.md](CREDITS.md).
