# Créditos

D2ScriptViewer es obra original de **BOTProT800**, publicada con la Licencia MIT (ver
[LICENSE](LICENSE)). Este archivo registra todo lo de procedencia externa que haya influido en el
proyecto, según la política de [CLAUDE.md](CLAUDE.md), que hereda el formato de
`AGENTS.md` de Darkstractor.

## Estado de redistribución

**Este repositorio no redistribuye binarios ni código de terceros.** Comprobado el 2026-10-03
y de nuevo el 2026-10-04:

- [pyproject.toml](pyproject.toml): `dependencies = []`. Todos los `import` del paquete se
  resuelven a la biblioteca estándar de Python; `tests/test_repository.py` lo comprueba.
- [.gitignore](.gitignore) excluye `*.obsp`, `build/` y `dist/`: ningún dato del juego ni ningún
  binario entra en el repositorio. Los tests usan fixtures sintéticos generados con el propio
  codificador.

**El ejecutable de Windows sí redistribuye binarios de terceros** (fase 9, 2026-10-04).
`D2ScriptViewer.exe` no se versiona; lo construye el workflow de release (o una compilación
local en `dist/`). Lleva dentro el bootloader de PyInstaller, CPython con las bibliotecas de su
compilación de Windows, y Tcl/Tk. Sus textos de licencia y la versión exacta de cada componente
viajan dentro del ejecutable y en cada descarga; lo explica
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Ver las entradas de abajo.

## Procedencia propia (no externa)

Lo siguiente es trabajo del mismo autor y no requiere entrada, pero se deja constancia:

- **Formato OBSP, BOD y cabecera de scripts:** análisis local del 3 de octubre de 2026,
  documentado en el apéndice A de [PLAN_MAESTRO.md](PLAN_MAESTRO.md).
- **Patrón `NumSlots` del bytecode:** `Darksiders2DLL/research/INVENTORY_SCRIPT.md`.
- **Función de hash de 64 bits** (fase 6, 2026-10-04): un CRC-64 reflejado, algoritmo de manual
  implementado en `formats/hashes.py` sin copiar código de nadie. Sus parámetros (polinomio
  `0x0060034000F0D50B`, valor inicial y XOR final `~0`) se dedujeron analizando los pares
  hash↔cadena del propio archivo (`research/FORMATO.md`).
- **Tema oscuro, estructura del repositorio, CI y preferencias:** Darkstractor.
- **Ubicación del audio en la instalación** (`sounds_streamed/PC`, `core.pck` y un `.pck` por
  idioma): guía Darksiders2-Modding del mismo autor, citada en `research/FORMATO.md` (2026-10-09).

## Tools

### PyInstaller

- **Autor(es):** PyInstaller Development Team (antes, Giovanni Bajo y McMillan Enterprises, Inc.,
  según el aviso de copyright).
- **Fuente:** https://github.com/pyinstaller/pyinstaller (paquete `pyinstaller` de PyPI).
- **Licencia:** GNU GPL versión 2 o posterior **con la *Bootloader Exception***, que da permiso
  ilimitado para incrustar el bootloader y sus archivos relacionados en otros programas y
  distribuir esas combinaciones sin las restricciones de la GPL. Los *run-time hooks* y los
  módulos de arranque adicionales que se incrustan en el ejecutable son Apache License 2.0.
- **Verificado en:** `pyinstaller-6.22.3.dist-info/licenses/COPYING.txt` y el campo `License` de
  `METADATA` de PyInstaller 6.22.3, instalado el 2026-10-04 en un entorno virtual de `build/`
  (fuera del repositorio). Es la versión que fija `.github/workflows/release.yml`; cambiarla exige
  volver a comprobarlo.
- **Redistribución:** No en el repositorio. Sí dentro de `D2ScriptViewer.exe` (el bootloader y los
  módulos de arranque), acompañado de su `COPYING.txt` como `licencias/LICENSE-PyInstaller.txt` y
  de la versión en `licencias/VERSIONES.txt`.
- **Incorporado:** 2026-10-04
- **Dónde se usa:** [D2ScriptViewer.spec](D2ScriptViewer.spec),
  [run_d2scriptviewer.py](run_d2scriptviewer.py) y
  [.github/workflows/release.yml](.github/workflows/release.yml).
- **Uso:** se invoca como herramienta de construcción. No se copia ni se adapta su código.
- **¿Modificado?:** No.
- **Para qué nos sirvió:** genera un ejecutable de Windows de un solo archivo, para que la
  herramienta llegue a quien no tiene Python instalado. Nada del paquete lo importa.

### CPython y Tcl/Tk (runtime del ejecutable)

- **Autor(es):** Python Software Foundation y colaboradores de CPython; Tcl/Tk, de la Universidad
  de California, Sun Microsystems y otros, según sus avisos. La compilación de Windows de CPython
  incluye además OpenSSL, libffi, bzip2, zlib y el código distribuible de Microsoft, cada uno con
  su autoría en el `LICENSE.txt` de Python.
- **Fuente:** https://www.python.org/ (instalador oficial de Windows) y
  https://www.tcl-lang.org/.
- **Licencia:**
  - CPython: Python Software Foundation License Version 2;
  - OpenSSL: Apache License 2.0;
  - libffi: MIT;
  - bzip2 y zlib: licencias permisivas propias;
  - código distribuible de Microsoft: condiciones en el `LICENSE.txt` de Python;
  - Tcl/Tk: licencia de estilo BSD (`license.terms`).

  Todas permisivas, sin copyleft.
- **Verificado en:** `LICENSE.txt` de Python 3.12.5 (incluida su sección «Additional Conditions for
  this Windows binary build») y `tcl/tcl8.6/license.terms` y `tcl/tk8.6/license.terms` de esa
  instalación, el 2026-10-04.
- **Redistribución:** No en el repositorio. Sí dentro de `D2ScriptViewer.exe`, acompañados de
  `licencias/LICENSE-Python.txt`, `licencias/LICENSE-TclTk.txt` y `licencias/VERSIONES.txt`, que
  `D2ScriptViewer.spec` copia del entorno que construye.
- **Incorporado:** 2026-10-04
- **Dónde se usa:** dentro del ejecutable que produce [D2ScriptViewer.spec](D2ScriptViewer.spec).
- **Uso:** se incluyen tal cual como runtime del programa.
- **¿Modificado?:** No.
- **Para qué nos sirvió:** son el intérprete y la biblioteca gráfica sobre los que corre la
  herramienta; el ejecutable los lleva para no depender de una instalación de Python.

## Adapted code

Ninguno.

## References and documentation

### wwiser: documentación sobre los ID de Wwise

- **Autor(es):** bnnm.
- **Fuente:** https://github.com/bnnm/wwiser (`doc/WWISER.md` y `wwiser/wfnv.py`, leídos el
  2026-10-09).
- **Licencia:** **pendiente de confirmar.** No se encontró `LICENSE`, `LICENSE.md`, `LICENSE.txt`
  ni `COPYING` en la rama `master` el 2026-10-09, y desde este entorno no se pudo consultar la API
  de GitHub. No se copia código ni texto, solo se cita un dato.
- **Redistribución:** No.
- **Incorporado:** 2026-10-09
- **Dónde se usa:** [research/FORMATO.md](research/FORMATO.md), sección «Audio» del 2026-10-09.
- **Uso:** referencia. Documenta que los ID de bancos, eventos y game syncs de Wwise son el FNV-1
  de 32 bits del nombre en minúsculas (según wwiser, el algoritmo lo da Audiokinetic en su
  documentación) y que `init.bnk` aparece a veces como `1355168291.bnk`. FNV-1 es un algoritmo de
  dominio público; la comprobación se hizo con una implementación propia en scripts fuera del
  repositorio.
- **¿Modificado?:** No aplica.
- **Para qué nos sirvió:** descartar que los int32 de `scripts.obsp` sean ShortID de Wwise, y
  comprobar que la implementación de FNV-1 da el ID de `init`.

## History

Sin entradas.
