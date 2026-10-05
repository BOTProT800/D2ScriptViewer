# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Autoprueba del ejecutable de Windows (fase 9).

Un ``.exe`` sin consola no puede imprimir nada, y un fallo de importación solo se ve
en la máquina del usuario. Por eso el ejecutable admite ``--autoprueba archivo``,
que ejecuta estas comprobaciones sin datos del juego y escribe el resultado en un
archivo. La usan la CI de release y las comprobaciones locales.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from . import __version__

#: Todos los módulos del paquete: si falta uno en el ejecutable, se ve aquí.
MODULES = (
    "d2scriptviewer.binary", "d2scriptviewer.cli", "d2scriptviewer.diffing", "d2scriptviewer.document",
    "d2scriptviewer.edits", "d2scriptviewer.errors", "d2scriptviewer.export", "d2scriptviewer.patches",
    "d2scriptviewer.references", "d2scriptviewer.saving", "d2scriptviewer.search", "d2scriptviewer.settings",
    "d2scriptviewer.validation", "d2scriptviewer.verification", "d2scriptviewer.wording",
    "d2scriptviewer.formats.bod", "d2scriptviewer.formats.bytecode", "d2scriptviewer.formats.hashes",
    "d2scriptviewer.formats.obsp", "d2scriptviewer.formats.script",
    "d2scriptviewer.gui.app", "d2scriptviewer.gui.details", "d2scriptviewer.gui.editors",
    "d2scriptviewer.gui.object_tree", "d2scriptviewer.gui.pending_view", "d2scriptviewer.gui.property_view",
    "d2scriptviewer.gui.script_view", "d2scriptviewer.gui.search_view", "d2scriptviewer.gui.theme",
)

#: Lo que el ejecutable debe llevar dentro (la licencia MIT obliga a acompañar el aviso).
BUNDLED = (
    "LICENSE", "CREDITS.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md",
    "licencias/LICENSE-Python.txt", "licencias/LICENSE-PyInstaller.txt", "licencias/LICENSE-TclTk.txt",
    "licencias/VERSIONES.txt",
)


def _synthetic_obsp() -> bytes:
    """Un OBSP mínimo y coherente (un BOD), construido con el propio codificador."""
    from .formats import bod
    from .formats.bod import BodDocument, BodObject, ClassRef, Field
    from .formats.hashes import make_name, name_hash, object_id
    from .formats.obsp import IndexEntry, ObspHeader, build_obsp

    root = BodObject(None, ClassRef(bod.CLASS_NATIVE, None, make_name("SelfTestDesc")), [
        Field(make_name("Value"), bod.Int32.of(21)),
        Field(make_name("Scale"), bod.Float32.of(1.5)),
        Field(make_name("Tag"), bod.HashedString(make_name("autoprueba"))),
    ])
    blob = bod.encode(BodDocument(4, 1, root))
    texts = ("selftest/desc", "SelfTest_Desc", "", "SelfTestDesc")
    entry = IndexEntry(name_hash(texts[0]), object_id(texts[1]), 0, len(blob), 10000, 8,
                       name_hash(texts[1]), 0, name_hash(texts[3]))
    return build_obsp(ObspHeader(10, 1, 0, 0, 0, 0), [entry], [blob], {name_hash(t): t for t in texts})


def resources_dir() -> Path | None:
    """Carpeta de los archivos incluidos en el ejecutable (``None`` si no está congelado)."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else None


def run_self_test(gui: bool = True) -> tuple[bool, list[str]]:
    """(todo bien, líneas del informe). Nunca lanza: los fallos son líneas ``[FALLO]``."""
    lines = [f"D2ScriptViewer {__version__} · Python {sys.version.split()[0]} · "
             f"{'congelado' if resources_dir() else 'sin congelar'}"]
    ok = True

    def check(label: str, action) -> None:  # type: ignore[no-untyped-def]
        nonlocal ok
        try:
            detail = action()
        except BaseException as error:  # noqa: BLE001 - se informa, no se propaga
            ok = False
            lines.append(f"[FALLO] {label}: {type(error).__name__}: {error}")
        else:
            lines.append(f"[OK] {label}" + (f": {detail}" if detail else ""))

    def imports() -> str:
        for name in MODULES:
            importlib.import_module(name)
        return f"{len(MODULES)} módulos"

    def hashing() -> str:
        from .formats.hashes import CRC64_CHECK, name_hash

        if name_hash("123456789") != CRC64_CHECK:
            raise AssertionError("el valor de control del CRC-64 no cuadra")
        return f"{CRC64_CHECK:016X}"

    def roundtrip() -> str:
        from .document import Document
        from .verification import verify_data

        data = _synthetic_obsp()
        report = verify_data(data)
        if not report.ok:
            raise AssertionError("; ".join(c.label for c in report.checks if not c.ok))
        document = Document.from_bytes(data)
        document.edit_text(0, (0,), "42")
        document.undo()
        if document.current_data() != data:
            raise AssertionError("editar y deshacer no devuelve el archivo")
        return f"{len(data)} bytes, verify correcto"

    def bundled() -> str:
        folder = resources_dir()
        if folder is None:
            return "no aplica (sin congelar)"
        missing = [name for name in BUNDLED if not (folder / name).is_file()]
        if missing:
            raise FileNotFoundError(", ".join(missing))
        return f"{len(BUNDLED)} archivos"

    def window() -> str:
        from .gui.app import ViewerApp

        # La ventana entera, oculta antes de dibujarse: sin abrir archivos ni guardar preferencias.
        app = ViewerApp(auto_open=False, persist_settings=False)
        try:
            app.withdraw()
            app.update_idletasks()
            patchlevel = app.tk.call("info", "patchlevel")
        finally:
            app.destroy()
        return f"ventana principal con Tcl/Tk {patchlevel}"

    check("Módulos", imports)
    check("Función de hash", hashing)
    check("OBSP sintético", roundtrip)
    check("Archivos incluidos", bundled)
    if gui:
        check("Interfaz", window)
    lines.append("Todo correcto" if ok else "HAY FALLOS")
    return ok, lines
