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

Línea de órdenes:

```powershell
python -m d2scriptviewer info
python -m d2scriptviewer list --tipo Desc --filtro death
python -m d2scriptviewer show death/death_desc --profundidad 3
python -m d2scriptviewer verify
```

Todas aceptan `--archivo ruta\a\scripts.obsp`.

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
