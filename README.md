# D2ScriptViewer

Visor y editor de escritorio para `media\scripts.obsp` de **Darksiders II Deathinitive Edition**
(PC), escrito en Python con solo la biblioteca estándar y tkinter.

> En desarrollo: primer hito (visualizar, editar y guardar en `.obsp` con copia del original).
> El plan completo está en [PLAN_MAESTRO.md](PLAN_MAESTRO.md).

## Requisitos

Python 3.10 o posterior en Windows. No hace falta instalar ningún paquete.

## Uso

Interfaz gráfica (o doble clic en `D2ScriptViewer.pyw`):

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

Los objetos de script compilado son de solo lectura.

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

Línea de órdenes:

```powershell
python -m d2scriptviewer info
python -m d2scriptviewer list --tipo Desc --filtro death
python -m d2scriptviewer show death/death_desc --profundidad 3
python -m d2scriptviewer verify
python -m d2scriptviewer hash Death death/death_desc
```

Todas salvo `hash` aceptan `--archivo ruta\a\scripts.obsp`. `hash` calcula el hash de 64 bits
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

## Datos del juego

El repositorio no contiene ningún dato del juego: `*.obsp` está excluido y los tests usan
fixtures sintéticos.

## Licencia

MIT. Ver [LICENSE](LICENSE) y [CREDITS.md](CREDITS.md).
