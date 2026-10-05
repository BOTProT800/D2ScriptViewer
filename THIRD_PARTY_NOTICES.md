# Avisos de terceros

D2ScriptViewer es obra de **BOTProT800** con la Licencia MIT (ver [LICENSE](LICENSE)). El
código fuente de este repositorio no incluye nada de terceros: solo usa la biblioteca estándar
de Python.

Este archivo se refiere al **ejecutable de Windows** (`D2ScriptViewer.exe`), que se construye
con PyInstaller a partir de [D2ScriptViewer.spec](D2ScriptViewer.spec). Para que funcione sin
Python instalado, el ejecutable lleva dentro software de terceros, cada uno con su licencia. Los
textos completos van dentro del propio ejecutable (carpeta `licencias`) y se publican junto a
cada descarga:

| Archivo | Qué cubre |
|---|---|
| `licencias/LICENSE-Python.txt` | CPython y las bibliotecas de su compilación oficial de Windows |
| `licencias/LICENSE-PyInstaller.txt` | El bootloader y los módulos de arranque de PyInstaller |
| `licencias/LICENSE-TclTk.txt` | Tcl/Tk, que dibuja la interfaz (tkinter) |
| `licencias/VERSIONES.txt` | La versión exacta de cada componente usado en esa compilación |

## Componentes

- **CPython** (el intérprete y su biblioteca estándar): Python Software Foundation License
  Version 2. `LICENSE-Python.txt` es el `LICENSE.txt` de la instalación de Python que construye
  el ejecutable, e incluye también los avisos de lo que lleva su compilación de Windows y usa el
  ejecutable:
  - **OpenSSL**, por `hashlib`: Apache License 2.0;
  - **libffi**, por `ctypes`: MIT;
  - **bzip2** y **zlib**;
  - el **código distribuible de Microsoft** (runtime de Visual C++), con las condiciones que
    detalla ese archivo.
- **PyInstaller**: GNU GPL versión 2 o posterior, con la *Bootloader Exception*. Esa excepción
  permite incrustar el bootloader en otros programas y distribuirlos sin las restricciones de la
  GPL; los módulos de arranque que se incrustan (*run-time hooks*) son Apache License 2.0.
  `LICENSE-PyInstaller.txt` es el `COPYING.txt` de la versión usada, con los textos completos de
  la GPL y de Apache 2.0.
- **Tcl/Tk**: licencia propia de estilo BSD. `LICENSE-TclTk.txt` reúne los `license.terms` de Tcl
  y de Tk de la instalación de Python que construye el ejecutable.

## Código fuente de cada componente

`VERSIONES.txt` indica la release exacta de cada componente. Su código fuente está en:

- CPython: <https://www.python.org/downloads/source/> y <https://github.com/python/cpython>;
- PyInstaller: <https://github.com/pyinstaller/pyinstaller>;
- Tcl/Tk: <https://www.tcl-lang.org/software/tcltk/>;
- OpenSSL: <https://www.openssl.org/source/>;
- libffi: <https://github.com/libffi/libffi>.

Ninguno se ha modificado.
