# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Utilidades compartidas por los tests.

Los tests con el archivo real buscan ``D2SV_OBSP`` o la ruta por defecto del
juego y se omiten si no lo encuentran. Solo leen: nunca escriben junto al
archivo real.
"""

from __future__ import annotations

import functools
import shutil
import tempfile
import unittest
from pathlib import Path

from d2scriptviewer.settings import find_default_obsp

ORIGINAL_SIZE = 18_334_463
ORIGINAL_SHA256 = "B46DD3DA7F17A0ED016E30AF523BFBA86D358C9920DFFA866C69D4A0F4F67C7C"

REAL_OBSP = find_default_obsp()

requires_real_file = unittest.skipUnless(
    REAL_OBSP is not None, "falta scripts.obsp: define D2SV_OBSP para activar este test"
)


@functools.lru_cache(maxsize=1)
def real_bytes() -> bytes:
    """El contenido del archivo real, leído una sola vez por proceso."""
    assert REAL_OBSP is not None
    return REAL_OBSP.read_bytes()


class TempDirMixin:
    """Da a cada test una carpeta temporal propia que se borra al terminar."""

    def make_temp_dir(self) -> Path:
        path = Path(tempfile.mkdtemp(prefix="d2sv_test_"))
        self.addCleanup(_remove_tree, path)  # type: ignore[attr-defined]
        return path


def _remove_tree(path: Path) -> None:
    # La copia del original queda en solo lectura: hay que quitárselo para borrarla.
    for item in path.rglob("*"):
        try:
            item.chmod(0o666)
        except OSError:
            pass
    shutil.rmtree(path, ignore_errors=True)
