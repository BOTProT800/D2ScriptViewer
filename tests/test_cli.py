# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""La línea de órdenes sobre el OBSP sintético y, si está, sobre el archivo real."""

from __future__ import annotations

import contextlib
import io
import unittest

from d2scriptviewer.cli import main
from d2scriptviewer.formats.hashes import name_hash
from tests import fixtures
from tests.support import REAL_OBSP, TempDirMixin, requires_real_file


def run(*argv: str) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = main(list(argv))
        except SystemExit as exit_:
            code = int(exit_.code or 0)
    return code, stdout.getvalue(), stderr.getvalue()


class CliTests(TempDirMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.folder = self.make_temp_dir()
        self.file = self.folder / "scripts.obsp"
        self.file.write_bytes(fixtures.make_obsp())

    def test_info(self) -> None:
        code, out, _err = run("info", "--archivo", str(self.file))
        self.assertEqual(code, 0)
        self.assertIn("modificado o desconocido", out)
        self.assertIn("FloatTable", out)

    def test_list_filters(self) -> None:
        code, out, err = run("list", "--archivo", str(self.file), "--tipo", "Desc")
        self.assertEqual(code, 0)
        self.assertIn("death/death_desc", out)
        self.assertEqual(err.strip(), "1 objeto")
        _code, out, _err = run("list", "--archivo", str(self.file), "--clase", "weapon")
        self.assertIn("scripts/weaponbehavior_inst", out)
        _code, out, _err = run("list", "--archivo", str(self.file), "--filtro", "oc/body")
        self.assertIn("weaponbehavior_inst", out)
        code, _out, err = run("list", "--archivo", str(self.file), "--tipo", "Nada")
        self.assertEqual(code, 2)
        self.assertIn("Tipo desconocido", err)

    def test_show(self) -> None:
        code, out, _err = run("show", "--archivo", str(self.file), "Death_Desc")
        self.assertEqual(code, 0)
        self.assertIn("Health: int32 = 100", out)
        self.assertIn("(scripts/weaponbehavior_inst)", out)  # referencia resuelta
        code, out, _err = run("show", "--archivo", str(self.file), "scripts/test")
        self.assertEqual(code, 0)
        self.assertIn("NumSlots", out)
        code, _out, err = run("show", "--archivo", str(self.file), "scripts")
        self.assertEqual(code, 1)
        self.assertIn("coinciden", err)
        code, _out, _err = run("show", "--archivo", str(self.file), "noexiste")
        self.assertEqual(code, 2)

    def test_roundtrip_and_output_rules(self) -> None:
        output = self.folder / "out" / "rebuilt.obsp"
        code, out, _err = run("roundtrip", "--archivo", str(self.file), "--salida", str(output))
        self.assertEqual(code, 0)
        self.assertIn("idéntico", out)
        self.assertEqual(output.read_bytes(), self.file.read_bytes())
        for target in (output, self.file, self.folder / "scripts.original.obsp"):
            with self.subTest(target=target.name):
                code, _out, err = run("roundtrip", "--archivo", str(self.file), "--salida", str(target))
                self.assertEqual(code, 2)
                self.assertIn("error", err)

    def test_verify(self) -> None:
        code, out, _err = run("verify", "--archivo", str(self.file))
        self.assertEqual(code, 0, out)
        self.assertIn("Todo correcto", out)
        broken = self.folder / "broken.obsp"
        broken.write_bytes(b"OBSP" + b"\x00" * 40)
        code, _out, _err = run("verify", "--archivo", str(broken))
        self.assertEqual(code, 1)

    def test_missing_file(self) -> None:
        code, _out, err = run("info", "--archivo", str(self.folder / "nope.obsp"))
        self.assertEqual(code, 2)
        self.assertIn("No existe", err)

    def test_disasm(self) -> None:
        code, out, _err = run("disasm", "--archivo", str(self.file), "scripts/test")
        self.assertEqual(code, 0, out)
        for expected in ("clase base ScriptBase", "Health: int32, banderas 0x0A = 100", "0x0029  int 21",
                         "args 3", "método getInventory", "función Unused: sin código",
                         "estado Active · función onEnter (1 parámetro, 25 bytes):"):
            with self.subTest(expected=expected):
                self.assertIn(expected, out)
        code, _out, err = run("disasm", "--archivo", str(self.file), "death/death_desc")
        self.assertEqual(code, 2)
        self.assertIn("no es un script", err)

    def test_hash_needs_no_file(self) -> None:
        code, out, _err = run("hash", "123456789", "Death")
        self.assertEqual(code, 0, out)
        self.assertIn("9AFB180E4C211BB4  9AFB180E4C211BB4  123456789", out)
        self.assertIn(f"{name_hash('Death'):016X}  {name_hash('death'):016X}  Death", out)
        code, _out, err = run("hash", "año")
        self.assertEqual(code, 2)
        self.assertIn("ASCII", err)


@requires_real_file
class RealCliTests(unittest.TestCase):
    def test_show_death_desc(self) -> None:
        code, out, _err = run("show", "--archivo", str(REAL_OBSP), "death/death_desc", "--profundidad", "2")
        self.assertEqual(code, 0)
        self.assertIn("DeathDesc", out)


if __name__ == "__main__":
    unittest.main()
