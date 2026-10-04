# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Fase 7: estructura completa de los scripts, desensamblador y parches de literales."""

from __future__ import annotations

import collections
import hashlib
import struct
import unittest

from d2scriptviewer import saving
from d2scriptviewer.document import Document
from d2scriptviewer.errors import EditError, FormatError, SaveError
from d2scriptviewer.formats import bod, bytecode, script
from d2scriptviewer.formats.bod import Name
from d2scriptviewer.formats.hashes import name_hash
from d2scriptviewer.formats.obsp import ObspFile, rebuild
from d2scriptviewer.verification import verify_data
from tests import fixtures
from tests.support import ORIGINAL_SHA256, TempDirMixin, real_bytes, requires_real_file


def label_path(tree: bod.BodDocument, label: str) -> tuple:
    return next(path for path, _node in bod.walk(tree.root) if bod.path_label(tree, path) == label)


class ScriptModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.blob = fixtures.script_blob()
        self.script = script.parse(self.blob)

    def test_roundtrip_and_structure(self) -> None:
        self.assertEqual(script.encode(self.script), self.blob)
        body = self.script
        self.assertEqual((body.name.text, body.base.text), ("test", "ScriptBase"))
        self.assertEqual(
            [(m.name.text, m.flags, m.type_label, bod.value_text(m.default) if m.default else None) for m in body.members],
            [("Health", 0x0A, "int32", "100"), ("Label", 0x0A, "cadena", "'hola'"), ("Speed", 0x04, "float32", None),
             ("Stats", 0x0A, "objeto", "Stats"), ("Items", 0x0A, "lista", "2 elementos")],
        )
        self.assertEqual([(v.name.text, bod.value_text(v.value)) for v in body.initial_values],
                         [("Speed", "2.5"), ("Enabled", "false")])
        self.assertEqual([(f.name.text, f.params) for f in body.functions], [("OnStart", 0), ("Unused", None)])
        self.assertEqual([(s.name.text, [(f.name.text, f.params) for f in s.functions]) for s in body.states],
                         [("Active", [("onEnter", 1)])])

    def test_disassembly(self) -> None:
        on_start = self.script.functions[0]
        texts = [bytecode.instruction_text(instruction) for instruction in on_start.instructions]
        self.assertEqual(texts[:5], ["0x0001  línea 1", "0x0006  op_35", "0x0007  op_2C this",
                                     "0x0016  op_3A NumSlots", "0x0029  int 21"])
        for expected in ("float 0.5", "bool true", "cadena 'hola mundo'", "args 3", "método getInventory",
                         "args 0", "llamada print", "op_12 → 0x00A4", "0x00A4  fin"):
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in text for text in texts), texts)
        argc = [instruction for instruction in on_start.instructions if instruction.argc]
        self.assertEqual([bod.value_text(instruction.operand) for instruction in argc], ["3", "0"])
        literals = [instruction for instruction in on_start.instructions if instruction.is_literal]
        self.assertEqual([bod.value_text(instruction.operand) for instruction in literals], ["21", "0.5", "true"])
        self.assertEqual(self.script.states[0].functions[0].params, 1)

    def test_assemble_is_the_inverse(self) -> None:
        for _state, function in self.script.all_functions():
            if function.params is not None:
                params, instructions = bytecode.disassemble(function.code)
                self.assertEqual(bytecode.assemble(params, instructions), function.code)

    def test_disassembler_rejects_what_it_does_not_know(self) -> None:
        with self.assertRaises(FormatError):
            bytecode.disassemble(b"")
        with self.assertRaises(FormatError):
            bytecode.disassemble(bytes([0, 0x11]))  # 0x11 no aparece en el juego
        with self.assertRaises(FormatError):
            bytecode.disassemble(bytes([0, 0x23, 1, 0]))  # literal truncado
        named = bytes([0, 0x2C, 4]) + struct.pack("<Q", name_hash("this")) + b"this"
        with self.assertRaises(FormatError):
            bytecode.disassemble(named + b"X")  # sin NUL
        self.assertEqual(bytecode.disassemble(named + b"\x00")[1][0].operand, Name(name_hash("this"), "this"))

    def test_parser_rejects_inconsistent_bodies(self) -> None:
        with self.assertRaises(FormatError):
            script.parse(self.blob + b"\x00")
        with self.assertRaises(FormatError):
            script.parse(self.blob[:-3])
        body = self.script
        body.members[0].name = Name(name_hash("Fuera"), "Fuera")  # no está en los símbolos
        with self.assertRaises(FormatError):
            script.encode(body)
        header = body.header
        unknown = bytearray(self.blob)
        struct.pack_into("<Q", unknown, header.body_offset, 12345)  # hash del nombre corto inventado
        with self.assertRaises(FormatError):
            script.parse(bytes(unknown))

    def test_only_literals_changed(self) -> None:
        patched = script.parse(self.blob)
        patched.functions[0].instructions[4].operand.raw = struct.pack("<i", 99)
        self.assertTrue(script.only_literals_changed(self.blob, script.encode(patched)))
        line = script.parse(self.blob)
        line.functions[0].instructions[0].operand = 7  # número de línea: no es un literal editable
        self.assertFalse(script.only_literals_changed(self.blob, script.encode(line)))
        argc = script.parse(self.blob)
        argc.functions[0].instructions[12].operand.raw = struct.pack("<i", 4)
        self.assertFalse(script.only_literals_changed(self.blob, script.encode(argc)))
        self.assertFalse(script.only_literals_changed(self.blob, self.blob[:-1] + b"\x30"))

    def test_presentation_shares_the_editable_leaves(self) -> None:
        tree = script.present(self.script)
        literal = bod.resolve(tree, label_path(tree, "Funciones.OnStart.0x0029"))
        self.assertIs(literal, self.script.functions[0].instructions[4].operand)
        self.assertIs(bod.resolve(tree, label_path(tree, "Miembros.Health")), self.script.members[0].default)
        damage = bod.resolve(tree, label_path(tree, "Miembros.Stats.Damage"))
        self.assertIs(damage, self.script.members[3].default.fields[0].value)
        argc = bod.resolve(tree, label_path(tree, "Funciones.OnStart.0x0052"))
        self.assertIsInstance(argc, bod.Note)
        self.assertEqual((bod.type_text(argc), bod.value_text(argc)), ("args", "3"))
        self.assertIsInstance(bod.resolve(tree, label_path(tree, "Miembros.Label")), bod.Note)
        editable = [node for _path, node in bod.walk(tree.root) if isinstance(node, script.EDITABLE_VALUES)]
        self.assertEqual(len(editable), len(script.editable_leaves(self.script)))


class ScriptEditingTests(TempDirMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.folder = self.make_temp_dir()
        self.target = self.folder / "scripts.obsp"
        self.original = fixtures.make_obsp()
        self.target.write_bytes(self.original)
        self.document = Document.open(self.target)
        self.position = self.document.find("scripts/test")[0].position
        self.tree = self.document.bod(self.position)

    def path(self, label: str) -> tuple:
        return label_path(self.tree, label)

    def test_literal_patch_changes_four_bytes_and_undo_restores(self) -> None:
        before = self.document.blob(self.position)
        self.document.edit_text(self.position, self.path("Funciones.OnStart.0x0029"), "42")
        after = self.document.blob(self.position)
        self.assertEqual(len(after), len(before))
        differing = [index for index, (a, b) in enumerate(zip(before, after)) if a != b]
        self.assertEqual(len(differing), 1)  # 21 → 42: solo cambia el byte bajo del int32
        changes = self.document.changes(self.position)
        self.assertEqual([(c.kind, c.label, c.before, c.after) for c in changes],
                         [("valor", "Funciones.OnStart.0x0029", "21", "42")])
        self.document.undo()
        self.assertEqual(self.document.current_data(), self.original)

    def test_every_editable_kind(self) -> None:
        for label, text, shown in (
            ("Funciones.OnStart.0x0036", "2,25", "2.25"),
            ("Funciones.OnStart.0x003B", "false", "false"),
            ("Miembros.Health", "250", "250"),
            ("Miembros.Stats.Damage", "-9", "-9"),
            ("Miembros.Items[0]", "3", "3"),
            ("Valores iniciales.Speed", "7.5", "7.5"),
            ("Valores iniciales.Enabled", "true", "true"),
        ):
            with self.subTest(label=label):
                self.document.edit_text(self.position, self.path(label), text)
                self.assertEqual(bod.value_text(bod.resolve(self.tree, self.path(label))), shown)
        reparsed = script.parse(self.document.blob(self.position))
        self.assertEqual(reparsed.members[0].default.value, 250)
        self.assertEqual(len(self.document.blob(self.position)), len(fixtures.script_blob()))
        self.assertEqual(len(self.document.changes(self.position)), 7)
        self.document.revert_object(self.position)
        self.assertEqual(self.document.current_data(), self.original)

    def test_read_only_rows_and_structure_are_refused(self) -> None:
        for label in ("Funciones.OnStart.0x0052", "Versión", "Miembros.Label", "Funciones.OnStart.0x0001"):
            with self.subTest(label=label), self.assertRaises(EditError):
                self.document.edit_text(self.position, self.path(label), "1")
        with self.assertRaises(EditError):
            self.document.duplicate_item(self.position, self.path("Miembros.Items[0]"))
        with self.assertRaises(EditError):
            self.document.set_null(self.position, self.path("Miembros.Stats"))
        self.assertEqual(self.document.modified_positions, set())

    def test_save_and_reopen(self) -> None:
        self.document.edit_text(self.position, self.path("Funciones.OnStart.0x0029"), "42")
        saving.save_document(self.document)
        report = verify_data(self.target.read_bytes())
        self.assertTrue(report.ok, [check for check in report.checks if not check.ok])
        reopened = Document.open(self.target)
        tree = reopened.bod(self.position)
        self.assertEqual(bod.value_text(bod.resolve(tree, label_path(tree, "Funciones.OnStart.0x0029"))), "42")

    def test_save_refuses_anything_but_literals(self) -> None:
        self.document.edit_text(self.position, self.path("Funciones.OnStart.0x0029"), "42")
        plan = saving.prepare_save(self.document)
        tampered = script.parse(plan.modified[self.position])
        tampered.functions[0].instructions[0].operand = 9  # una línea, que no es un literal
        blob = script.encode(tampered)
        plan.modified[self.position] = blob
        plan.data = rebuild(ObspFile.parse(plan.data), {self.position: blob})
        with self.assertRaises(SaveError) as raised:
            saving.execute_save(plan, self.target)
        self.assertIn("más que literales", str(raised.exception))
        self.assertEqual(self.target.read_bytes(), self.original)


@requires_real_file
class RealScriptTests(unittest.TestCase):
    """Los 3 690 scripts del juego, en una sola pasada."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.data = real_bytes()
        cls.obsp = ObspFile.parse(cls.data)
        cls.scripts = {}
        for position, entry in enumerate(cls.obsp.entries):
            if entry.is_script:
                cls.scripts[position] = script.parse(cls.obsp.blob(position))

    def test_every_script_roundtrips(self) -> None:
        self.assertEqual(len(self.scripts), 3690)
        for position, body in self.scripts.items():
            self.assertEqual(script.encode(body), self.obsp.blob(position))
        counts = collections.Counter()
        for body in self.scripts.values():
            counts["miembros"] += len(body.members)
            counts["iniciales"] += len(body.initial_values)
            counts["estados"] += len(body.states)
            for _state, function in body.all_functions():
                counts["funciones"] += 1
                counts["vacías"] += function.params is None
        self.assertEqual(dict(counts), {"miembros": 8244, "iniciales": 7671, "estados": 983,
                                        "funciones": 9721, "vacías": 12})

    def test_opcode_table_and_invariants(self) -> None:
        opcodes = collections.Counter()
        names = wrong = argc = jumps_outside = 0
        outside = []
        for position, body in self.scripts.items():
            for _state, function in body.all_functions():
                if function.params is None:
                    continue
                starts = {instruction.offset for instruction in function.instructions}
                lines = [instruction.operand for instruction in function.instructions if instruction.opcode == 0x3B]
                self.assertEqual(lines, sorted(set(lines)))  # las líneas siempre crecen
                self.assertEqual(function.params, sum(1 for i in function.instructions if i.opcode == 0x28))
                self.assertEqual(function.instructions[-1].opcode, bytecode.OP_END)
                for instruction in function.instructions:
                    opcodes[instruction.opcode] += 1
                    argc += instruction.argc
                    if isinstance(instruction.operand, Name):
                        names += 1
                        wrong += name_hash(instruction.operand.text) != instruction.operand.hash
                    if instruction.info.operand == bytecode.JUMP and instruction.operand not in starts:
                        jumps_outside += 1
                        outside.append((self.obsp.text(self.obsp.entries[position].path_hash), instruction.operand))
                    if instruction.opcode == bytecode.OP_BOOL:
                        self.assertIn(instruction.operand.raw, (0, 1))
        self.assertEqual(dict(opcodes), {code: op.count for code, op in bytecode.OPCODES.items()})
        self.assertEqual((names, wrong), (111_603, 0))
        self.assertEqual(argc, 25_090)
        # Un único salto del juego apunta fuera de su función (dato original, no un fallo de lectura).
        self.assertEqual(outside, [("maker_male/maker_youngin_emote_component", 6503)])

    def test_real_literal_patch_and_undo(self) -> None:
        document = Document.from_bytes(self.data)
        position = document.find("death/death")[0].position
        body = document.script(position)
        tree = document.bod(position)
        path, node = next((p, n) for p, n in bod.walk(tree.root) if isinstance(n, bod.Int32))
        document.edit_text(position, path, str(node.value + 1))
        self.assertEqual(len(document.blob(position)), len(self.obsp.blob(position)))
        self.assertTrue(script.only_literals_changed(self.obsp.blob(position), document.blob(position)))
        self.assertIs(body, document.script(position))
        document.undo()
        self.assertEqual(hashlib.sha256(document.current_data()).hexdigest().upper(), ORIGINAL_SHA256)


if __name__ == "__main__":
    unittest.main()
