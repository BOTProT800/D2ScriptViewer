# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Comprobaciones sobre el propio repositorio: versión, cabeceras y dependencias."""

from __future__ import annotations

import ast
import contextlib
import io
import sys
import unittest
from pathlib import Path

import d2scriptviewer
from d2scriptviewer.cli import main

ROOT = Path(__file__).resolve().parent.parent
SPDX = (
    "# SPDX-FileCopyrightText: 2026 BOTProT800",
    "# SPDX-License-Identifier: MIT",
)


def python_sources() -> list[Path]:
    sources = []
    for folder in ("d2scriptviewer", "tests"):
        sources.extend(sorted((ROOT / folder).rglob("*.py")))
    sources.extend(sorted(ROOT.glob("*.py")))
    sources.extend(sorted(ROOT.glob("*.pyw")))
    return sources


class RepositoryTests(unittest.TestCase):
    def test_version_option(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), d2scriptviewer.__version__)

    def test_spdx_headers(self) -> None:
        for path in python_sources():
            with self.subTest(path=path.relative_to(ROOT)):
                lines = path.read_text(encoding="utf-8").splitlines()
                self.assertEqual(tuple(lines[:2]), SPDX)

    def test_syntax_is_python_310(self) -> None:
        # La CI cubre 3.10–3.13; esto atrapa sintaxis más nueva aunque solo
        # haya un intérprete instalado.
        for path in python_sources():
            with self.subTest(path=path.relative_to(ROOT)):
                ast.parse(path.read_text(encoding="utf-8"), str(path), feature_version=(3, 10))

    def test_only_standard_library(self) -> None:
        allowed = set(sys.stdlib_module_names) | {"d2scriptviewer", "tests", "__future__"}
        for path in python_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    with self.subTest(path=path.relative_to(ROOT), module=name):
                        self.assertIn(name.split(".")[0], allowed)

    def test_self_test_lists_every_module(self) -> None:
        """Un módulo nuevo que no esté en la autoprueba podría quedarse fuera del ejecutable."""
        from d2scriptviewer.selftest import MODULES

        package = ROOT / "d2scriptviewer"
        modules = {
            "d2scriptviewer." + ".".join(path.relative_to(package).with_suffix("").parts)
            for path in package.rglob("*.py")
            if path.name not in ("__init__.py", "__main__.py") and path.stem != "selftest"
        }
        self.assertEqual(modules, set(MODULES))

    def test_release_recipe(self) -> None:
        spec = (ROOT / "D2ScriptViewer.spec").read_text(encoding="utf-8").splitlines()
        self.assertEqual(tuple(spec[:2]), SPDX)
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        pinned = next(line.split('"')[1] for line in workflow.splitlines() if "PYINSTALLER_VERSION:" in line)
        credits = (ROOT / "CREDITS.md").read_text(encoding="utf-8")
        self.assertIn(f"PyInstaller {pinned}", credits)  # la versión cuya licencia se verificó
        for name in ("LICENSE", "CREDITS.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md"):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_self_test_passes(self) -> None:
        from d2scriptviewer.selftest import run_self_test

        try:
            import tkinter

            tkinter.Tcl()
            gui = True
        except Exception:  # noqa: BLE001 - sin Tk, la parte gráfica se omite
            gui = False
        ok, lines = run_self_test(gui=gui)
        self.assertTrue(ok, "\n".join(lines))
        self.assertEqual(lines[-1], "Todo correcto")

    def test_version_lives_only_in_package(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('version = { attr = "d2scriptviewer.__version__" }', pyproject)
        self.assertNotIn(f'version = "{d2scriptviewer.__version__}"', pyproject)


if __name__ == "__main__":
    unittest.main()
