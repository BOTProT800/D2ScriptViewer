# D2ScriptViewer

Visor y editor de escritorio para `media\scripts.obsp` de **Darksiders II Deathinitive Edition**
(PC), escrito en Python con solo la biblioteca estándar y tkinter.

> En desarrollo: primer hito (visualizar, editar y guardar en `.obsp` con copia del original).
> El plan completo está en [PLAN_MAESTRO.md](PLAN_MAESTRO.md).

## Requisitos

Python 3.10 o posterior en Windows. No hace falta instalar ningún paquete.

## Uso

```powershell
python -m d2scriptviewer --version
```

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
