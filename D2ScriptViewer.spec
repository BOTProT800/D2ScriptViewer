# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Receta de PyInstaller para el ejecutable de Windows (fase 9).

Un solo archivo y sin consola: el destinatario es quien no tiene Python. Dentro van
la licencia, los créditos y el historial, porque la MIT obliga a acompañar el aviso
de copyright allá donde se redistribuya el software.

El ejecutable incluye también software de terceros (el bootloader de PyInstaller,
CPython y las bibliotecas de su compilación de Windows, y Tcl/Tk). Sus textos de
licencia se copian aquí, en ``build/licencias``, desde el entorno que construye,
junto con un ``VERSIONES.txt`` con la versión exacta de cada componente. Van dentro
del ejecutable (carpeta ``licencias``) y el workflow de release los adjunta a la
descarga. ``THIRD_PARTY_NOTICES.md`` explica qué es cada uno.

No se excluyen módulos de la biblioteca estándar: recortar el bundle a mano ahorra
unos megas y arriesga un fallo de importación que solo aparece en la máquina del
usuario, ya congelado y sin consola donde leer el error.
"""

import importlib.metadata
import shutil
import ssl
import sys
import tkinter
import zlib
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 - lo define PyInstaller
sys.path.insert(0, str(ROOT))
from d2scriptviewer import __version__  # noqa: E402
from d2scriptviewer.selftest import MODULES  # noqa: E402

LICENSES = ROOT / "build" / "licencias"
shutil.rmtree(LICENSES, ignore_errors=True)
LICENSES.mkdir(parents=True)

base = Path(sys.base_prefix)
shutil.copyfile(base / "LICENSE.txt", LICENSES / "LICENSE-Python.txt")

pyinstaller = importlib.metadata.distribution("pyinstaller")
copying = next(item for item in pyinstaller.files if item.name == "COPYING.txt")
shutil.copyfile(pyinstaller.locate_file(copying), LICENSES / "LICENSE-PyInstaller.txt")

tcl_terms = sorted(base.glob("tcl/tcl8*/license.terms")) + sorted(base.glob("tcl/tk8*/license.terms"))
if not tcl_terms:
    raise SystemExit("No se encontraron los license.terms de Tcl/Tk en " + str(base / "tcl"))
(LICENSES / "LICENSE-TclTk.txt").write_text(
    "\n\n".join(f"===== {path.parent.name}/license.terms =====\n\n{path.read_text(encoding='latin-1')}"
                for path in tcl_terms),
    encoding="utf-8",
)

root = tkinter.Tcl()
(LICENSES / "VERSIONES.txt").write_text(
    "\n".join([
        f"D2ScriptViewer {__version__}",
        f"Python (CPython) {sys.version}",
        f"PyInstaller {pyinstaller.version} (bootloader)",
        f"Tcl/Tk {root.call('info', 'patchlevel')}",
        f"OpenSSL: {ssl.OPENSSL_VERSION}",
        f"zlib {zlib.ZLIB_RUNTIME_VERSION}",
        "libffi, bzip2 y el runtime de Microsoft: los de la compilación de Windows de esa versión de Python",
        "",
    ]),
    encoding="utf-8",
)

analysis = Analysis(  # noqa: F821
    [str(ROOT / "run_d2scriptviewer.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "LICENSE"), "."),
        (str(ROOT / "CREDITS.md"), "."),
        (str(ROOT / "CHANGELOG.md"), "."),
        (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
        (str(LICENSES / "*"), "licencias"),
    ],
    # La autoprueba importa todos los módulos por nombre: así ninguno se queda fuera.
    hiddenimports=list(MODULES),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="D2ScriptViewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
