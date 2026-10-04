# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Fase 3: validación de ediciones, comandos reversibles y efecto sobre los blobs."""

from __future__ import annotations

import hashlib
import struct
import unittest

from d2scriptviewer import edits
from d2scriptviewer.document import Document
from d2scriptviewer.errors import EditError
from d2scriptviewer.formats import bod
from d2scriptviewer.formats.hashes import HashDictionary
from d2scriptviewer.formats.obsp import ObspFile
from d2scriptviewer.references import build_indexes
from tests import fixtures
from tests.fixtures import N
from tests.support import ORIGINAL_SHA256, real_bytes, requires_real_file


def path_of(document: bod.BodDocument, label: str) -> tuple:
    for path, _node in bod.walk(document.root):
        if bod.path_label(document, path) == label:
            return path
    raise KeyError(label)


class ParseTests(unittest.TestCase):
    def test_int32(self) -> None:
        self.assertEqual(edits.parse_int32("42"), struct.pack("<i", 42))
        self.assertEqual(edits.parse_int32(" -2147483648 "), struct.pack("<i", -(2 ** 31)))
        self.assertEqual(edits.parse_int32("1_000"), struct.pack("<i", 1000))
        self.assertEqual(edits.parse_int32("0x4DFA84A3"), struct.pack("<I", 0x4DFA84A3))
        self.assertEqual(edits.parse_int32("0xFFFFFFFF"), struct.pack("<i", -1))
        self.assertEqual(edits.parse_int32("-0x10"), struct.pack("<i", -16))
        for bad in ("", "2147483648", "-2147483649", "0x100000000", "1.5", "doce", "0xZZ", "-0x80000001"):
            with self.subTest(bad=bad), self.assertRaises(EditError):
                edits.parse_int32(bad)

    def test_float32(self) -> None:
        self.assertEqual(edits.parse_float32("1.5"), struct.pack("<f", 1.5))
        self.assertEqual(edits.parse_float32("0,25"), struct.pack("<f", 0.25))
        self.assertEqual(edits.parse_float32("-1e-3"), struct.pack("<f", -0.001))
        self.assertEqual(edits.parse_float32("3.4e38"), struct.pack("<f", 3.4e38))
        for bad in ("", "nan", "NaN", "inf", "-Infinity", "1e39", "-3.5e38", "1,5,3", "uno"):
            with self.subTest(bad=bad), self.assertRaises(EditError):
                edits.parse_float32(bad)

    def test_bool(self) -> None:
        for text in ("true", "True", "1", "sí", "si", "verdadero"):
            self.assertEqual(edits.parse_bool(text), 1)
        for text in ("false", "0", "No", "falso"):
            self.assertEqual(edits.parse_bool(text), 0)
        with self.assertRaises(EditError):
            edits.parse_bool("quizá")

    def test_raw_string(self) -> None:
        self.assertEqual(edits.parse_raw_string(""), "")
        self.assertEqual(edits.parse_raw_string("x" * 65535), "x" * 65535)
        for bad in ("x" * 65536, "año", "a\x00b", "→"):
            with self.subTest(bad=bad[:5]), self.assertRaises(EditError):
                edits.parse_raw_string(bad)

    def test_known_names(self) -> None:
        dictionary = HashDictionary()
        dictionary.update([(1, "Death_Light_Material"), (2, "death_mesh")])
        self.assertEqual(edits.parse_known_name("death_mesh", dictionary), bod.Name(2, "death_mesh"))
        with self.assertRaises(EditError) as raised:
            edits.parse_known_name("Death_Mesh", dictionary)  # distingue mayúsculas
        self.assertIn("death_mesh", str(raised.exception))
        with self.assertRaises(EditError):
            edits.parse_known_name("death_mesh", None)

    def test_suggestions_put_prefixes_first(self) -> None:
        dictionary = HashDictionary()
        dictionary.update([(1, "XDeath"), (2, "death_b"), (3, "Death_a"), (4, "other")])
        self.assertEqual(edits.suggestions(dictionary, "death"), ["Death_a", "death_b", "XDeath"])
        self.assertEqual(edits.suggestions(dictionary, "", limit=2), ["Death_a", "death_b"])

    def test_hints(self) -> None:
        self.assertEqual(edits.input_hint(bod.Int32.of(0), "1034"), (True, "int32 1034 · hex 0x0000040A"))
        valid, message = edits.input_hint(bod.Float32.of(0), "0.1")
        self.assertTrue(valid)
        self.assertIn("float32 0.1 (exacto 0.100000001)", message)
        self.assertFalse(edits.input_hint(bod.Int32.of(0), "x")[0])
        self.assertEqual(edits.input_hint(bod.RawString("ab"), "abc"), (True, "3 caracteres ASCII (antes 2)"))

    def test_identifier_warning(self) -> None:
        self.assertIsNotNone(edits.identifier_warning("ID", bod.Int32.of(3)))
        self.assertIsNotNone(edits.identifier_warning("FidgetMoveStateID", bod.Int32.of(3)))
        self.assertIsNotNone(edits.identifier_warning("PathHash", bod.Int32.of(3)))
        self.assertIsNotNone(edits.identifier_warning("SmallStartMoveState", bod.Int32.of(1_321_400_540)))
        self.assertIsNone(edits.identifier_warning("Health", bod.Int32.of(100)))
        self.assertIsNone(edits.identifier_warning("Speed", bod.Float32.of(2e9)))

    def test_field_name_and_state_text(self) -> None:
        document = fixtures.desc_document()
        self.assertEqual(edits.field_name(document, path_of(document, "Stats.Damage")), "Damage")
        self.assertEqual(edits.field_name(document, path_of(document, "Color[1]")), "Color")
        self.assertEqual(edits.field_name(document, path_of(document, "Pairs[0].valor")), "Pairs")
        self.assertEqual(edits.state_text(bod.Float32.of(0), struct.pack("<f", 0.5)), "0.5")
        self.assertEqual(edits.state_text(bod.ExternalRef(0, 0), (1, 2)), "1:0000000000000002")
        self.assertEqual(edits.editable_text(bod.RawString("hola")), "hola")
        self.assertEqual(edits.editable_text(bod.Bool(5)), "true")

    def test_containers_are_not_editable(self) -> None:
        for node in (bod.Null(), bod.BodTuple([]), bod.BodList(0, [])):
            self.assertFalse(edits.is_editable(node))
            with self.assertRaises(EditError):
                edits.get_state(node)


class DocumentEditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = fixtures.make_obsp()
        self.document = Document.from_bytes(self.data)
        self.dictionary = build_indexes(self.document.obsp).dictionary
        self.desc = self.document.find("death/death_desc")[0].position
        self.tree = self.document.bod(self.desc)

    def path(self, label: str) -> tuple:
        return path_of(self.tree, label)

    def assert_only_blob_changed(self, position: int) -> ObspFile:
        rebuilt = ObspFile.parse(self.document.current_data())
        original = self.document.obsp
        for index in range(len(original.entries)):
            with self.subTest(blob=index):
                if index == position:
                    self.assertNotEqual(rebuilt.blob(index), original.blob(index))
                else:
                    self.assertEqual(rebuilt.blob(index), original.blob(index))
        self.assertEqual(rebuilt.layout_problems(), [])
        return rebuilt

    def assert_pristine(self) -> None:
        self.assertEqual(self.document.modified_positions, set())
        self.assertEqual(self.document.change_count, 0)
        self.assertEqual(self.document.blob(self.desc), self.document.original_blob(self.desc))
        self.assertEqual(self.document.current_data(), self.data)

    def test_each_value_type_edits_only_its_blob_and_undoes(self) -> None:
        # El último valor dice si el blob cambia de tamaño. Con «Mesh» no se comprueba: el
        # nombre nuevo cambia qué aparición define cada nombre, y aquí el saldo es cero.
        cases = [
            ("Health", "250", 250, False),
            ("Speed", "2.75", 2.75, False),
            ("Visible", "false", False, False),
            ("Comment", "una cadena bastante mas larga", "una cadena bastante mas larga", True),
            ("Mesh", "fire", N("fire"), None),
        ]
        for label, text, expected, size_changes in cases:
            with self.subTest(label=label):
                group = self.document.edit_text(self.desc, self.path(label), text, self.dictionary)
                self.assertIsNotNone(group)
                self.assertTrue(self.document.is_modified(self.desc))
                rebuilt = self.assert_only_blob_changed(self.desc)
                decoded = bod.decode(rebuilt.blob(self.desc))
                node = bod.resolve(decoded, self.path(label))
                value = node.name if isinstance(node, bod.HashedString) else getattr(node, "value", None)
                value = node.text if isinstance(node, bod.RawString) else value
                self.assertEqual(value, expected)
                if size_changes is not None:
                    resized = len(rebuilt.blob(self.desc)) != len(self.document.original_blob(self.desc))
                    self.assertEqual(resized, size_changes)
                self.document.undo()
                self.assert_pristine()

    def test_reference_edit(self) -> None:
        path = self.path("Behavior")
        self.document.edit(self.desc, path, (fixtures.GROUP, fixtures.TABLE_ID))
        rebuilt = self.assert_only_blob_changed(self.desc)
        self.assertEqual(bod.resolve(bod.decode(rebuilt.blob(self.desc)), path).identity, (fixtures.GROUP, fixtures.TABLE_ID))
        with self.assertRaises(EditError):
            self.document.edit(self.desc, path, (1, 2))
        self.document.undo()
        self.assert_pristine()

    def test_size_change_shifts_later_offsets_only(self) -> None:
        self.document.edit_text(self.desc, self.path("Comment"), "x" * 40)
        rebuilt = ObspFile.parse(self.document.current_data())
        delta = len(rebuilt.blob(self.desc)) - len(self.document.original_blob(self.desc))
        self.assertEqual(delta, 40 - len("hola"))
        for index, (old, new) in enumerate(zip(self.document.obsp.entries, rebuilt.entries)):
            expected = old.offset + (delta if index > self.desc else 0)
            self.assertEqual(new.offset, expected)
            self.assertEqual(new.identity, old.identity)

    def test_undo_redo_and_descriptions(self) -> None:
        health = self.path("Health")
        self.assertIsNone(self.document.undo())
        self.document.edit_text(self.desc, health, "1")
        self.document.edit_text(self.desc, health, "2")
        self.assertIn("Health", self.document.undo_description)
        self.document.undo()
        self.assertEqual(bod.resolve(self.tree, health).value, 1)
        self.assertIn("Health", self.document.redo_description)
        self.document.redo()
        self.assertEqual(bod.resolve(self.tree, health).value, 2)
        self.document.undo()
        self.document.edit_text(self.desc, health, "3")  # una edición nueva vacía «rehacer»
        self.assertIsNone(self.document.redo())
        self.document.undo()
        self.document.undo()
        self.assert_pristine()

    def test_editing_back_to_the_original_is_not_a_change(self) -> None:
        health = self.path("Health")
        self.document.edit_text(self.desc, health, "5")
        self.document.edit_text(self.desc, health, "100")
        self.assert_pristine()
        self.assertIsNone(self.document.edit_text(self.desc, health, "100"))

    def test_revert_object_and_property(self) -> None:
        self.document.edit_text(self.desc, self.path("Health"), "5")
        self.document.edit_text(self.desc, self.path("Speed"), "9")
        self.document.edit_text(self.desc, self.path("Stats.Damage"), "8")
        self.assertEqual(self.document.change_count, 3)
        self.document.revert_property(self.desc, self.path("Speed"))
        self.assertEqual(self.document.edited_paths(self.desc), {self.path("Health"), self.path("Stats.Damage")})
        self.assertIsNone(self.document.revert_property(self.desc, self.path("Speed")))
        self.document.revert_object(self.desc)
        self.assert_pristine()
        self.document.undo()  # deshacer la reversión devuelve los dos cambios
        self.assertEqual(self.document.change_count, 2)
        self.assertIsNone(self.document.revert_object(2))

    def test_pending_changes(self) -> None:
        self.document.edit_text(self.desc, self.path("Health"), "5")
        instance = self.document.find("scripts/weaponbehavior_inst")[0].position
        enabled = path_of(self.document.bod(instance), "Enabled")
        self.document.edit_text(instance, enabled, "false")
        changes = self.document.pending_changes()
        self.assertEqual([(position, path) for position, path, *_ in changes],
                         [(self.desc, self.path("Health")), (instance, enabled)])
        _position, _path, node, before, after = changes[0]
        self.assertEqual((edits.state_text(node, before), edits.state_text(node, after)), ("100", "5"))
        self.assertEqual(self.document.modified_positions, {self.desc, instance})

    def test_invalid_edits_change_nothing(self) -> None:
        for label, text in (("Health", "9999999999"), ("Speed", "nan"), ("Comment", "ñ"), ("Mesh", "no_existe")):
            with self.subTest(label=label), self.assertRaises(EditError):
                self.document.edit_text(self.desc, self.path(label), text, self.dictionary)
        with self.assertRaises(EditError):
            self.document.edit_text(self.desc, self.path("Stats"), "1")
        script = self.document.find("scripts/test")[0].position
        with self.assertRaises(EditError):
            self.document.edit_text(script, (0,), "1")
        self.assert_pristine()

    def test_float_edit_only_repacks_that_value(self) -> None:
        nan = b"\x01\x00\x80\x7f"
        self.tree.root.fields[1].value.raw = nan  # «Speed» con un NaN de carga útil propia
        speed = self.path("Speed")
        color = self.path("Color[1]")
        self.document.edit_text(self.desc, color, "0.1")
        decoded = bod.decode(self.document.blob(self.desc))
        self.assertEqual(bod.resolve(decoded, speed).raw, nan)
        self.assertEqual(bod.resolve(decoded, color).raw, struct.pack("<f", 0.1))


@requires_real_file
class RealEditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = real_bytes()
        self.document = Document.from_bytes(self.data)

    def test_same_size_edit_changes_one_blob_and_undo_restores_sha(self) -> None:
        position = self.document.find("death/death_desc")[0].position
        tree = self.document.bod(position)
        self.document.edit_text(position, path_of(tree, "PanicHitTime"), "9.5")
        rebuilt = self.document.current_data()
        self.assertEqual(len(rebuilt), len(self.data))
        parsed = ObspFile.parse(rebuilt)
        changed = [index for index in range(len(parsed.entries)) if parsed.blob(index) != self.document.obsp.blob(index)]
        self.assertEqual(changed, [position])
        self.document.undo()
        self.assertEqual(hashlib.sha256(self.document.current_data()).hexdigest().upper(), ORIGINAL_SHA256)

    def test_longer_raw_string_shifts_offsets_and_undo_restores_sha(self) -> None:
        position, path, text = next(
            (info.position, path, node.text)
            for info in self.document.objects
            if not info.is_script
            for path, node in bod.walk(self.document.bod(info.position).root)
            if isinstance(node, bod.RawString) and node.text
        )
        self.document.edit_text(position, path, text + "_d2sv")
        parsed = ObspFile.parse(self.document.current_data())
        self.assertEqual(len(parsed.data), len(self.data) + 5)
        for index, (old, new) in enumerate(zip(self.document.obsp.entries, parsed.entries)):
            self.assertEqual(new.offset, old.offset + (5 if index > position else 0))
            if index != position:
                self.assertEqual(parsed.blob(index), self.document.obsp.blob(index))
        self.document.undo()
        self.assertEqual(hashlib.sha256(self.document.current_data()).hexdigest().upper(), ORIGINAL_SHA256)

    def test_name_and_reference_edits_roundtrip(self) -> None:
        dictionary = build_indexes(self.document.obsp).dictionary
        position = self.document.find("death/death_desc")[0].position
        tree = self.document.bod(position)
        name_path, ref_path = None, None
        for path, node in bod.walk(tree.root):
            if name_path is None and isinstance(node, bod.HashedString):
                name_path = path
            if ref_path is None and isinstance(node, bod.ExternalRef):
                ref_path = path
        self.document.edit_text(position, name_path, "Death", dictionary)
        other = self.document.find("death/death_animations")[0].identity
        self.document.edit(position, ref_path, other)
        decoded = bod.decode(self.document.blob(position))
        self.assertEqual(bod.resolve(decoded, name_path).name.text, "Death")
        self.assertEqual(bod.resolve(decoded, ref_path).identity, other)
        self.document.undo()
        self.document.undo()
        self.assertEqual(hashlib.sha256(self.document.current_data()).hexdigest().upper(), ORIGINAL_SHA256)


if __name__ == "__main__":
    unittest.main()
