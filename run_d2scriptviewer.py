# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Punto de entrada del ejecutable de Windows (``D2ScriptViewer.spec``): siempre la GUI.

Un ejecutable sin consola no puede mostrar la salida de la línea de órdenes, así que
solo se atiende la autoprueba oculta, ``--autoprueba archivo``, que escribe su
informe en ``archivo`` y sale con 0 si todo va bien. La CLI sigue en
``python -m d2scriptviewer``.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--autoprueba":
        from d2scriptviewer.selftest import run_self_test

        ok, lines = run_self_test()
        Path(sys.argv[2]).write_text("\n".join(lines) + "\n", encoding="utf-8")
        raise SystemExit(0 if ok else 1)
    from d2scriptviewer.gui.app import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
