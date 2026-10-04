# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Fase 4: guardado, copia del original, copias rotativas, restaurar y casos de error."""

from __future__ import annotations

import ctypes
import os
import shutil
import stat
import sys
import unittest
from pathlib import Path

from d2scriptviewer import saving
from d2scriptviewer.document import Document
from d2scriptviewer.errors import SaveError
from d2scriptviewer.formats import bod
from d2scriptviewer.formats.obsp import STEAM_ORIGINAL_SHA256
from tests import fixtures
from tests.support import ORIGINAL_SHA256, REAL_OBSP, TempDirMixin, requires_real_file


def label_path(tree: bod.BodDocument, label: str) -> tuple:
    return next(path for path, _node in bod.walk(tree.root) if bod.path_label(tree, path) == label)


class SavingTests(TempDirMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.folder = self.make_temp_dir()
        self.target = self.folder / "scripts.obsp"
        self.original_bytes = fixtures.make_obsp()
        self.target.write_bytes(self.original_bytes)
        self.document = Document.open(self.target)
        self.desc = self.document.find("death/death_desc")[0].position

    def edit(self, label: str, text: str) -> None:
        tree = self.document.bod(self.desc)
        self.document.edit_text(self.desc, label_path(tree, label), text)

    def copy_path(self) -> Path:
        return self.folder / "scripts.original.obsp"

    def test_paths(self) -> None:
        self.assertEqual(saving.original_copy_path(self.target), self.copy_path())
        self.assertEqual(saving.original_copy_path(Path("x/data")), Path("x/data.original.obsp"))
        self.assertTrue(saving.is_original_copy(Path("A/Scripts.Original.OBSP")))
        self.assertFalse(saving.is_original_copy(self.target))
        self.assertEqual(saving.tmp_path(self.target).name, "scripts.obsp.tmp")

    def test_first_save_creates_verified_read_only_copy(self) -> None:
        self.edit("Health", "321")
        result = saving.save_document(self.document)
        copy = self.copy_path()
        self.assertTrue(result.original_created)
        self.assertFalse(result.original_is_steam)
        self.assertEqual(copy.read_bytes(), self.original_bytes)
        self.assertFalse(os.access(copy, os.W_OK))
        self.assertTrue(any("ya venía modificado" in warning for warning in result.warnings))
        self.assertIn("Copia del original creada", result.summary())
        reopened = Document.open(self.target)
        tree = reopened.bod(self.desc)
        self.assertEqual(bod.resolve(tree, label_path(tree, "Health")).value, 321)
        self.assertEqual(saving.sha256(self.target.read_bytes()), result.sha256)
        self.assertEqual(self.document.change_count, 0)
        self.assertEqual(self.document.obsp.data, self.target.read_bytes())
        self.assertFalse(saving.tmp_path(self.target).exists())

    def test_later_saves_never_touch_the_copy(self) -> None:
        self.edit("Health", "1")
        saving.save_document(self.document)
        copy = self.copy_path()
        before = (copy.read_bytes(), copy.stat().st_mtime_ns)
        for value in ("2", "3"):
            self.edit("Health", value)
            result = saving.save_document(self.document)
            self.assertFalse(result.original_created)
            self.assertEqual(result.original_copy, copy)
            self.assertIn("ya existía y no se ha tocado", result.summary())
        self.assertEqual((copy.read_bytes(), copy.stat().st_mtime_ns), before)

    def test_existing_copy_is_kept_even_if_different(self) -> None:
        self.copy_path().write_bytes(b"copia previa del usuario")
        self.edit("Health", "7")
        saving.save_document(self.document)
        self.assertEqual(self.copy_path().read_bytes(), b"copia previa del usuario")

    def test_refuses_to_save_over_original_copy(self) -> None:
        self.edit("Health", "7")
        forbidden = self.folder / "Scripts.Original.obsp"
        forbidden.write_bytes(b"intocable")
        with self.assertRaises(SaveError):
            saving.save_document(self.document, forbidden)
        self.assertEqual(forbidden.read_bytes(), b"intocable")
        with self.assertRaises(SaveError):
            saving.save_document(self.document, self.folder / "otra.original.obsp")
        self.assertFalse((self.folder / "otra.original.obsp").exists())
        self.assertEqual(self.document.change_count, 1)

    def test_simulated_failures_leave_the_target_intact(self) -> None:
        self.edit("Speed", "4")
        for step in ("verified", "checked", "original", "backup", "tmp_written"):
            with self.subTest(step=step):

                def fail(name: str, step: str = step) -> None:
                    if name == step:
                        raise SaveError(f"fallo simulado en {step}")

                plan = saving.prepare_save(self.document)
                with self.assertRaises(SaveError):
                    saving.execute_save(plan, self.target, fail_at=fail)
                self.assertEqual(self.target.read_bytes(), self.original_bytes)
                self.assertFalse(saving.tmp_path(self.target).exists())
                self.assertEqual(self.document.change_count, 1)

    def test_corrupt_build_writes_nothing(self) -> None:
        self.edit("Health", "5")
        plan = saving.prepare_save(self.document)
        broken = bytearray(plan.data)
        offset = saving.ObspFile.parse(plan.data).entries[3].offset
        broken[offset + 20] ^= 0xFF  # un blob no editado cambia
        plan.data = bytes(broken)
        with self.assertRaises(SaveError):
            saving.execute_save(plan, self.target)
        self.assertEqual(self.target.read_bytes(), self.original_bytes)
        self.assertFalse(self.copy_path().exists())
        self.assertFalse((self.folder / saving.BACKUP_DIR).exists())

    def test_read_only_target(self) -> None:
        self.edit("Health", "5")
        os.chmod(self.target, stat.S_IREAD)
        with self.assertRaises(SaveError) as raised:
            saving.save_document(self.document)
        self.assertIn("solo lectura", str(raised.exception))
        self.assertFalse(self.copy_path().exists())

    @unittest.skipUnless(sys.platform == "win32", "el bloqueo con FILE_SHARE_READ es de Windows")
    def test_locked_file_gives_a_clear_error(self) -> None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.restype = ctypes.c_void_p
        kernel32.CreateFileW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        generic_read, file_share_read, open_existing = 0x80000000, 0x1, 3
        # Como el juego: lectura y solo se comparte la lectura.
        handle = kernel32.CreateFileW(str(self.target), generic_read, file_share_read, None, open_existing, 0, None)
        self.assertNotIn(handle, (None, ctypes.c_void_p(-1).value))
        try:
            self.edit("Health", "5")
            with self.assertRaises(SaveError) as raised:
                saving.save_document(self.document)
            self.assertIn("Cierra Darksiders II", str(raised.exception))
        finally:
            kernel32.CloseHandle(handle)
        self.assertEqual(self.target.read_bytes(), self.original_bytes)
        self.assertFalse(self.copy_path().exists())
        self.assertFalse(saving.tmp_path(self.target).exists())
        saving.save_document(self.document)  # ya sin bloqueo, guarda
        self.assertTrue(self.copy_path().exists())

    def test_rotating_backups_keep_the_last_five(self) -> None:
        versions = []
        for value in range(7):
            versions.append(self.target.read_bytes())
            self.edit("Health", str(1000 + value))
            saving.save_document(self.document)
        backups = sorted((self.folder / saving.BACKUP_DIR).iterdir())
        self.assertEqual(len(backups), 5)
        self.assertTrue(all(item.name.startswith("scripts.") and item.suffix == ".obsp" for item in backups))
        self.assertEqual([item.read_bytes() for item in backups], versions[-5:])

    def test_rotating_backups_never_overwrite_each_other(self) -> None:
        # En Windows dos guardados seguidos pueden caer en el mismo instante del reloj.
        import datetime

        moment = datetime.datetime(2026, 10, 4, 12, 0, 0, 500)
        first, _ = saving.rotate_backup(self.target, b"uno", now=moment)
        second, _ = saving.rotate_backup(self.target, b"dos", now=moment)
        earlier, _ = saving.rotate_backup(self.target, b"tres", now=moment - datetime.timedelta(seconds=5))
        self.assertEqual(first.read_bytes(), b"uno")
        self.assertEqual(second.read_bytes(), b"dos")
        self.assertEqual(earlier.read_bytes(), b"tres")
        names = sorted(item.name for item in (self.folder / saving.BACKUP_DIR).iterdir())
        self.assertEqual(names, [first.name, second.name, earlier.name])  # orden de nombre = orden real
        for _ in range(5):
            saving.rotate_backup(self.target, b"mas", now=moment)
        kept = sorted((self.folder / saving.BACKUP_DIR).iterdir())
        self.assertEqual(len(kept), saving.KEEP_BACKUPS)
        self.assertEqual([item.read_bytes() for item in kept], [b"mas"] * 5)

    def test_rotating_backups_can_be_disabled(self) -> None:
        self.edit("Health", "5")
        result = saving.save_document(self.document, rotating_backups=False)
        self.assertIsNone(result.backup)
        self.assertFalse((self.folder / saving.BACKUP_DIR).exists())

    def test_save_as_new_file(self) -> None:
        self.edit("Comment", "una cadena mas larga que antes")
        other = self.folder / "sub" / "copia.obsp"
        other.parent.mkdir()
        result = saving.save_document(self.document, other)
        self.assertIsNone(result.original_copy)
        self.assertIsNone(result.backup)
        self.assertEqual(self.target.read_bytes(), self.original_bytes)
        self.assertEqual(self.document.path, other)
        self.assertEqual(Document.open(other).obsp.data, other.read_bytes())

    def test_edit_and_revert_saves_identical_bytes(self) -> None:
        self.edit("Health", "5")
        self.document.undo()
        self.edit("Speed", "3")
        self.edit("Speed", "1.5")
        saving.save_document(self.document)
        self.assertEqual(self.target.read_bytes(), self.original_bytes)

    def test_undo_after_save(self) -> None:
        self.edit("Health", "5")
        saving.save_document(self.document)
        self.document.undo()
        self.assertEqual(self.document.change_count, 1)
        saving.save_document(self.document)
        self.assertEqual(self.target.read_bytes(), self.original_bytes)

    def test_restore_original(self) -> None:
        with self.assertRaises(SaveError):
            saving.restore_original(self.target)  # todavía no hay copia
        self.edit("Health", "5")
        saving.save_document(self.document)
        self.assertNotEqual(self.target.read_bytes(), self.original_bytes)
        result = saving.restore_original(self.target)
        self.assertEqual(self.target.read_bytes(), self.original_bytes)
        self.assertEqual(result.sha256, saving.sha256(self.original_bytes))
        self.assertFalse(result.is_steam)
        self.assertIsNotNone(result.backup)
        self.assertTrue(self.copy_path().exists())
        with self.assertRaises(SaveError):
            saving.restore_original(self.copy_path())

    def test_file_status(self) -> None:
        sha = saving.sha256(self.original_bytes)
        self.assertEqual(saving.file_status(self.target, sha).kind, "unknown")
        self.assertEqual(saving.file_status(self.target, STEAM_ORIGINAL_SHA256).kind, "steam")
        self.edit("Health", "5")
        saving.save_document(self.document)
        status = saving.file_status(self.target, self.document.obsp.sha256())
        self.assertEqual(status.kind, "modified")
        self.assertEqual(status.original_copy, self.copy_path())
        self.assertEqual(saving.file_status(self.copy_path(), sha).kind, "original-copy")
        self.assertEqual(saving.file_status(None, sha).kind, "unknown")

    def test_orphan_tmp_cleanup(self) -> None:
        self.assertFalse(saving.cleanup_orphan_tmp(self.target))
        saving.tmp_path(self.target).write_bytes(b"resto")
        self.assertTrue(saving.cleanup_orphan_tmp(self.target))
        self.assertFalse(saving.tmp_path(self.target).exists())


@requires_real_file
class RealSavingTests(TempDirMixin, unittest.TestCase):
    """Sobre una copia del archivo real en una carpeta temporal; nunca junto al original."""

    def setUp(self) -> None:
        self.folder = self.make_temp_dir()
        self.target = self.folder / "scripts.obsp"
        shutil.copyfile(REAL_OBSP, self.target)

    def test_save_edit_restore_cycle(self) -> None:
        document = Document.open(self.target)
        position = document.find("death/death_desc")[0].position
        tree = document.bod(position)
        document.edit_text(position, label_path(tree, "PanicHitTime"), "9.5")
        result = saving.save_document(document)
        self.assertTrue(result.original_created)
        self.assertTrue(result.original_is_steam)
        self.assertEqual(saving.sha256((self.folder / "scripts.original.obsp").read_bytes()), ORIGINAL_SHA256)
        self.assertEqual(self.target.stat().st_size, 18_334_463)
        self.assertEqual(saving.file_status(self.target, result.sha256).kind, "modified")
        reopened = Document.open(self.target)
        reopened_tree = reopened.bod(position)
        self.assertEqual(bod.resolve(reopened_tree, label_path(reopened_tree, "PanicHitTime")).value, 9.5)
        restored = saving.restore_original(self.target)
        self.assertTrue(restored.is_steam)
        self.assertEqual(saving.sha256(self.target.read_bytes()), ORIGINAL_SHA256)

    def test_saving_without_net_changes_keeps_the_sha(self) -> None:
        document = Document.open(self.target)
        position = document.find("base/char_death")[0].position
        tree = document.bod(position)
        path = next(path for path, node in bod.walk(tree.root) if isinstance(node, bod.Float32))
        document.edit_text(position, path, "12345")
        document.undo()
        saving.save_document(document)
        self.assertEqual(saving.sha256(self.target.read_bytes()), ORIGINAL_SHA256)


if __name__ == "__main__":
    unittest.main()
