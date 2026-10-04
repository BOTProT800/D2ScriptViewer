# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Fase 5: edición estructural de BOD, diferencias, validación y fuzz sobre los blobs."""

from __future__ import annotations

import hashlib
import random
import unittest

from d2scriptviewer import edits, saving
from d2scriptviewer.diffing import diff_trees
from d2scriptviewer.document import Document
from d2scriptviewer.edits import EditGroup, ReplaceValue
from d2scriptviewer.errors import EditError, SaveError
from d2scriptviewer.formats import bod
from d2scriptviewer.formats.obsp import IndexEntry, ObspFile, ObspHeader, build_obsp
from d2scriptviewer.references import build_indexes, slot_key, slot_occurrences
from d2scriptviewer.validation import validate
from d2scriptviewer.verification import verify_data
from tests import fixtures
from tests.support import ORIGINAL_SHA256, real_bytes, requires_real_file


def make_single_object_document(tree: bod.BodDocument) -> Document:
    """Un OBSP con un único objeto de tipo 8 cuyo árbol es ``tree``."""
    blob = bod.encode(tree)
    strings = {fixtures.fake_hash(text): text for text in ("test/table", "Table", "", "Table")}
    entry = IndexEntry(fixtures.fake_hash("test/table"), 0x99, 0, len(blob), fixtures.GROUP, 8,
                       fixtures.fake_hash("Table"), 0, fixtures.fake_hash("Table"))
    header = ObspHeader(10, 1, 0, 0, 0, 0)
    return Document.from_bytes(build_obsp(header, [entry], [blob], strings))


def label_path(tree: bod.BodDocument, label: str) -> tuple:
    for path, _node in bod.walk(tree.root):
        if bod.path_label(tree, path) == label:
            return path
    raise KeyError(label)


def object_indices(tree: bod.BodDocument) -> list[int]:
    return [node.index for _path, node in bod.walk(tree.root) if isinstance(node, bod.BodObject) and node.index is not None]


class StructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = fixtures.make_obsp()
        self.document = Document.from_bytes(self.data)
        self.desc = self.document.find("death/death_desc")[0].position
        self.tree = self.document.bod(self.desc)

    def path(self, label: str) -> tuple:
        return label_path(self.document.bod(self.desc), label)

    def node(self, label: str) -> object:
        return bod.resolve(self.document.bod(self.desc), self.path(label))

    def assert_canonical(self) -> bod.BodDocument:
        blob = self.document.blob(self.desc)
        decoded = bod.decode(blob)
        self.assertEqual(bod.encode(decoded), blob)
        self.assertEqual(bod.fingerprint(decoded.root), bod.fingerprint(self.document.bod(self.desc).root))
        indices = object_indices(decoded)
        self.assertEqual(indices, list(range(len(indices))))
        return decoded

    def assert_pristine(self) -> None:
        self.assertEqual(self.document.modified_positions, set())
        self.assertEqual(self.document.change_count, 0)
        self.assertEqual(self.document.current_data(), self.data)

    def test_duplicate_list_item_is_a_deep_copy(self) -> None:
        self.document.duplicate_item(self.desc, self.path("Slots[0]"))
        slots = self.node("Slots")
        self.assertEqual(len(slots.items), 3)
        self.assertIsNot(slots.items[1], slots.items[0])
        self.assertEqual(bod.fingerprint(slots.items[1]), bod.fingerprint(slots.items[0]))
        slots.items[1].fields[1].value.raw = bod.Int32.of(99).raw  # tocar la copia no toca el original
        self.assertEqual(slots.items[0].fields[1].value.value, 5)
        decoded = self.assert_canonical()
        self.assertEqual(len(bod.resolve(decoded, self.path("Slots")).items), 3)
        self.document.undo()
        self.assert_pristine()

    def test_remove_and_move(self) -> None:
        tags = self.path("Tags")
        self.document.remove_item(self.desc, tags + (0,))
        self.assertEqual([item.name.text for item in self.node("Tags").items], ["fire"])
        self.assert_canonical()
        self.document.undo()
        self.document.move_item(self.desc, tags + (0,), +1)
        self.assertEqual([item.name.text for item in self.node("Tags").items], ["fire", "death_mesh"])
        self.assert_canonical()
        self.assertIsNone(self.document.move_item(self.desc, tags + (1,), +1))
        self.assertIsNone(self.document.move_item(self.desc, tags + (0,), -1))
        self.document.move_item(self.desc, tags + (1,), -1)
        self.assert_pristine()

    def test_pairs_and_maps(self) -> None:
        pairs = self.path("Pairs")
        self.document.duplicate_item(self.desc, pairs + (1,))
        self.document.move_item(self.desc, pairs + (2,), -1)
        self.document.remove_item(self.desc, pairs + (0,))
        decoded = self.assert_canonical()
        self.assertEqual(len(bod.resolve(decoded, pairs).items), 2)
        self.document.duplicate_item(self.desc, self.path("Lookup[0]"))
        self.assertEqual(len(self.node("Lookup").items), 2)
        self.assert_canonical()
        for _ in range(4):
            self.document.undo()
        self.assert_pristine()

    def test_fixed_shapes_are_refused(self) -> None:
        for label in ("Color[0]", "Health", "Stats", "Pairs[0].valor"):
            with self.subTest(label=label), self.assertRaises(EditError):
                self.document.duplicate_item(self.desc, self.path(label))
        with self.assertRaises(EditError):
            self.document.set_null(self.desc, self.path("Health"))
        with self.assertRaises(EditError):
            self.document.set_null(self.desc, ())
        script = self.document.find("scripts/test")[0].position
        with self.assertRaises(EditError):
            self.document.remove_item(script, (0,))
        self.assert_pristine()

    def test_null_and_fill(self) -> None:
        stats = self.path("Stats")
        self.document.set_null(self.desc, stats)
        self.assertIsInstance(self.node("Stats"), bod.Null)
        decoded = self.assert_canonical()  # los objetos posteriores se renumeran
        self.assertIsInstance(bod.resolve(decoded, stats), bod.Null)
        self.document.set_null(self.desc, self.path("Behavior"))
        self.assertIsInstance(self.node("Behavior"), bod.Null)
        copy = self.document.copy_node(self.desc, self.path("Script"))
        self.document.fill_null(self.desc, stats, copy)
        self.assertEqual(self.node("Stats").cls.name.text, "scripts/weaponbehavior")
        self.assert_canonical()
        with self.assertRaises(EditError):
            self.document.fill_null(self.desc, self.path("Behavior"), bod.ExternalRef(1, 2))
        self.document.fill_null(self.desc, self.path("Behavior"), bod.ExternalRef(fixtures.GROUP, fixtures.TABLE_ID))
        with self.assertRaises(EditError):
            self.document.fill_null(self.desc, self.path("Health"), bod.Null())
        for _ in range(4):
            self.document.undo()
        self.assert_pristine()

    def test_copy_example_reads_the_baseline(self) -> None:
        child = self.path("Script.Child")
        self.document.set_null(self.desc, child)
        copy = self.document.copy_example(self.desc, child, "Stats")
        self.assertEqual(copy.cls.name.text, "Stats")
        self.document.fill_null(self.desc, child, copy)
        self.assert_pristine()
        with self.assertRaises(EditError):
            self.document.copy_example(self.desc, child, "OtraClase")
        with self.assertRaises(EditError):
            self.document.copy_example(self.desc, self.path("Health"), "Stats")

    def test_revert_object_restores_and_can_be_undone(self) -> None:
        self.document.duplicate_item(self.desc, self.path("Tags[0]"))
        self.document.edit_text(self.desc, self.path("Health"), "7")
        self.document.set_null(self.desc, self.path("Stats"))
        self.document.revert_object(self.desc)
        self.assert_pristine()
        self.assertEqual(self.node("Health").value, 100)
        self.document.undo()
        self.assertEqual(self.document.change_count, 3)
        self.assertIsInstance(self.node("Stats"), bod.Null)

    def test_net_zero_changes_are_not_modifications(self) -> None:
        self.document.duplicate_item(self.desc, self.path("Tags[1]"))
        self.document.remove_item(self.desc, self.path("Tags[2]"))
        self.assertFalse(self.document.is_modified(self.desc))
        self.assert_pristine()

    def test_pending_changes_describe_structure(self) -> None:
        self.document.duplicate_item(self.desc, self.path("Slots[1]"))
        self.document.remove_item(self.desc, self.path("Tags[0]"))
        self.document.move_item(self.desc, self.path("Pairs[0]"), +1)
        self.document.set_null(self.desc, self.path("Stats"))
        self.document.edit_text(self.desc, self.path("Health"), "5")
        kinds = {(change.kind, change.label) for _position, change in self.document.pending_changes()}
        self.assertEqual(
            kinds,
            {
                ("valor", "Health"),
                ("reemplazado", "Stats"),
                ("eliminado", "Tags[0] (posición original)"),
                ("movido", "Pairs[1]"),  # el que estaba en [0] ahora está en [1]
                ("añadido", "Slots[2]"),
            },
        )
        self.assertIn(self.path("Slots[2]"), self.document.edited_paths(self.desc))
        stats_change = next(change for _p, change in self.document.pending_changes() if change.label == "Stats")
        self.assertEqual((stats_change.before, stats_change.after), ("objeto Stats", "null"))

    def test_value_change_inside_a_moved_list_is_found(self) -> None:
        self.document.duplicate_item(self.desc, self.path("Slots[0]"))
        self.document.edit_text(self.desc, self.path("Slots[1].SlotID"), "9")
        changes = diff_trees(self.document.baseline_tree(self.desc), self.document.bod(self.desc))
        self.assertEqual([(change.kind, change.label) for change in changes], [("añadido", "Slots[1]")])
        self.document.edit_text(self.desc, self.path("Slots[0].Count"), "6")
        labels = {(change.kind, change.label) for change in self.document.changes(self.desc)}
        self.assertIn(("valor", "Slots[0].Count"), labels)

    def test_revert_property_after_structural_change(self) -> None:
        self.document.edit_text(self.desc, self.path("Health"), "5")
        self.document.remove_item(self.desc, self.path("Tags[0]"))
        self.document.revert_property(self.desc, self.path("Health"))
        self.assertEqual(self.node("Health").value, 100)
        self.assertEqual([change.kind for change in self.document.changes(self.desc)], ["eliminado"])
        self.assertIsNone(self.document.revert_property(self.desc, self.path("Speed")))


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = Document.from_bytes(fixtures.make_obsp())
        self.desc = self.document.find("death/death_desc")[0].position

    def path(self, label: str) -> tuple:
        return label_path(self.document.bod(self.desc), label)

    def test_duplicate_map_key_blocks_saving(self) -> None:
        self.document.duplicate_item(self.desc, self.path("Lookup[0]"))
        report = validate(self.document)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("claves repetidas (Health)", report.errors[0])
        with self.assertRaises(SaveError):
            saving.prepare_save(self.document)
        dictionary = build_indexes(self.document.obsp).dictionary
        self.document.edit_text(self.desc, self.path("Lookup[1].clave"), "fire", dictionary)
        self.assertTrue(validate(self.document).ok)
        saving.prepare_save(self.document)

    def test_duplicate_pair_key_in_list_blocks_saving(self) -> None:
        self.document.duplicate_item(self.desc, self.path("Pairs[0]"))
        self.assertFalse(validate(self.document).ok)
        self.document.edit_text(self.desc, self.path("Pairs[1].clave"), "3")
        self.assertTrue(validate(self.document).ok)

    def test_dangling_reference_blocks_saving(self) -> None:
        path = self.path("Behavior")
        tree = self.document.bod(self.desc)
        broken = ReplaceValue(self.desc, path, bod.resolve(tree, path), bod.ExternalRef(1, 2))
        self.document._push(EditGroup((broken,), "prueba"))
        report = validate(self.document)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("no apunta a ningún objeto", report.errors[0])

    def test_new_repeated_id_only_warns(self) -> None:
        self.document.duplicate_item(self.desc, self.path("Slots[0]"))
        report = validate(self.document)
        self.assertTrue(report.ok)
        self.assertEqual(len(report.warnings), 1)
        self.assertIn("SlotID se repite (1)", report.warnings[0])
        plan = saving.prepare_save(self.document)
        self.assertEqual(plan.warnings, report.warnings)
        self.document.edit_text(self.desc, self.path("Slots[1].SlotID"), "3")
        self.assertEqual(validate(self.document).warnings, [])

    def test_shifted_lists_are_compared_with_their_real_pair(self) -> None:
        # Regresión: al insertar un elemento, las listas anidadas de los elementos de detrás
        # cambian de ruta. Compararlas por ruta daba avisos falsos de *ID repetidos.
        def entry(name: str, ids: tuple[int, ...]) -> bod.BodObject:
            items = [bod.BodObject(0, fixtures.native("Item"), [fixtures.F("ItemID", bod.Int32.of(value))])
                     for value in ids]
            return bod.BodObject(0, fixtures.native("Entry"), [
                fixtures.F("Name", bod.RawString(name)),
                fixtures.F("Items", bod.BodList(bod.MODE_VALUES, items)),
            ])

        root = bod.BodObject(None, fixtures.native("Table"), [fixtures.F("Entries", bod.BodList(
            bod.MODE_VALUES, [entry("a", (1, 2)), entry("b", (3, 3)), entry("c", (4, 4))]
        ))])
        document = make_single_object_document(bod.BodDocument(4, 1, root))
        document.duplicate_item(0, (0, 0))  # «a» se duplica; «b» y «c» se desplazan
        self.assertEqual(validate(document).warnings, [])
        document.edit_text(0, (0, 1, 1, 1, 0), "1")  # la copia de «a» pasa a tener ItemID 1 repetido
        warnings = validate(document).warnings
        self.assertEqual(len(warnings), 1)
        self.assertIn("Entries[1].Items: el campo ItemID se repite (1)", warnings[0])

    def test_unmodified_objects_are_not_validated(self) -> None:
        self.assertEqual((validate(self.document).errors, validate(self.document).warnings), ([], []))


class SlotTests(unittest.TestCase):
    def test_slots_and_examples(self) -> None:
        document = Document.from_bytes(fixtures.make_obsp())
        indexes = build_indexes(document.obsp)
        desc = document.find("death/death_desc")[0].position
        tree = document.bod(desc)
        self.assertEqual(slot_key(tree, label_path(tree, "Stats")), ("ActorDesc", "Stats", "campo"))
        self.assertEqual(slot_key(tree, label_path(tree, "Slots[0]")), ("ActorDesc", "Slots", "elemento"))
        self.assertEqual(slot_key(tree, label_path(tree, "Pairs[1].valor")), ("ActorDesc", "Pairs", "par"))
        self.assertEqual(slot_key(tree, label_path(tree, "Script.Child")), ("scripts/weaponbehavior", "Child", "campo"))
        classes = indexes.slots.classes(("ActorDesc", "Slots", "elemento"))
        self.assertEqual([(label, count) for label, count, _examples in classes], [("Slot", 2)])
        position, path = classes[0][2][0]
        self.assertEqual((position, document.property_label(position, path)), (desc, "Slots[0]"))
        self.assertEqual(indexes.slots.references(("ActorDesc", "Behavior", "campo")), 1)
        nulls = [key for key, _path, node in slot_occurrences(tree) if isinstance(node, bod.Null)]
        self.assertIn(("ActorDesc", "Parent", "campo"), nulls)


def walk_with_parent(node: object, path: tuple = (), parent: object = None):
    """Como :func:`bod.walk`, pero con el padre de cada nodo (evita resolver rutas desde la raíz)."""
    stack = [(path, node, parent)]
    while stack:
        current_path, current, current_parent = stack.pop()
        yield current_path, current, current_parent
        for index, (_label, child) in enumerate(bod.children(current)):
            stack.append((current_path + (index,), child, current))


def random_operation(document: Document, position: int, rng: random.Random) -> bool:
    """Aplica una operación estructural o de valor al azar; devuelve si aplicó alguna."""
    tree = document.bod(position)
    items, nullable, nulls, values = [], [], [], []
    for path, node, parent in walk_with_parent(tree.root):
        if not path:
            continue
        in_pair_key = isinstance(parent, bod.Pair) and path[-1] == 0
        if isinstance(parent, (bod.BodList, bod.BodMap)):
            items.append(path)
        if isinstance(node, (bod.BodObject, bod.ExternalRef)) and not isinstance(parent, bod.BodTuple) and not in_pair_key:
            nullable.append(path)
        if isinstance(node, bod.Null) and not isinstance(parent, bod.BodTuple) and not in_pair_key:
            nulls.append(path)
        if isinstance(node, (bod.Int32, bod.Float32)):
            values.append((path, node))
    choices = []
    if items:
        choices += ["duplicate", "remove", "move"]
    if nullable:
        choices.append("null")
    if nulls and nullable:
        choices.append("fill")
    if values:
        choices.append("value")
    if not choices:
        return False
    action = rng.choice(choices)
    if action == "duplicate":
        document.duplicate_item(position, rng.choice(items))
    elif action == "remove":
        document.remove_item(position, rng.choice(items))
    elif action == "move":
        return document.move_item(position, rng.choice(items), rng.choice((-1, 1))) is not None
    elif action == "null":
        document.set_null(position, rng.choice(nullable))
    elif action == "fill":
        source = rng.choice(nullable)
        document.fill_null(position, rng.choice(nulls), document.copy_node(position, source))
    else:
        path, node = rng.choice(values)
        if isinstance(node, bod.Int32):
            document.edit(position, path, bod.Int32.of(rng.randint(-1000, 1000)).raw)
        else:
            document.edit(position, path, bod.Float32.of(rng.uniform(-10, 10)).raw)
    return True


class FuzzMixin:
    def check(self, document: Document, positions: list[int], operations: int, seed: int) -> int:
        rng = random.Random(seed)
        applied = 0
        for _ in range(operations):
            position = rng.choice(positions)
            if random_operation(document, position, rng):
                applied += 1
                blob = document.blob(position)
                decoded = bod.decode(blob)
                self.assertEqual(bod.encode(decoded), blob)
                self.assertEqual(bod.fingerprint(decoded.root), bod.fingerprint(document.bod(position).root))
        return applied


class FuzzTests(FuzzMixin, unittest.TestCase):
    def test_synthetic_fuzz(self) -> None:
        data = fixtures.make_obsp()
        document = Document.from_bytes(data)
        positions = [info.position for info in document.objects if not info.is_script]
        applied = self.check(document, positions, 300, seed=5)
        # No todo aplica: mover un extremo hacia fuera no hace nada, y la instancia se
        # queda sin candidatas cuando anula su única referencia.
        self.assertGreater(applied, 100)
        self.assertTrue(verify_data(document.current_data()).ok)
        while document.undo() is not None:
            pass
        self.assertEqual(document.current_data(), data)


@requires_real_file
class RealValidationTests(unittest.TestCase):
    def test_duplicating_a_move_state_warns_only_about_its_id(self) -> None:
        document = Document.from_bytes(real_bytes())
        position = document.find("death/playercommon_movestates")[0].position
        document.duplicate_item(position, (0, 0))
        report = validate(document)
        self.assertEqual(report.errors, [])
        self.assertEqual(len(report.warnings), 1)
        self.assertIn("MoveStates: el campo ID se repite (100000)", report.warnings[0])


@requires_real_file
class RealFuzzTests(FuzzMixin, unittest.TestCase):
    def test_real_fuzz(self) -> None:
        data = real_bytes()
        document = Document.from_bytes(data)
        bods = [info for info in document.objects if not info.is_script]
        sample = bods[::60] + sorted(bods, key=lambda info: -info.entry.size)[:3]
        positions = sorted({info.position for info in sample})
        applied = self.check(document, positions, 400, seed=2026)
        self.assertGreater(applied, 250)
        rebuilt = document.current_data()
        report = verify_data(rebuilt)
        self.assertTrue(report.ok, [check for check in report.checks if not check.ok])
        parsed = ObspFile.parse(rebuilt)
        untouched = [p for p in range(len(parsed.entries)) if p not in document.modified_positions]
        self.assertTrue(all(parsed.blob(p) == document.obsp.blob(p) for p in untouched))
        while document.undo() is not None:
            pass
        self.assertEqual(hashlib.sha256(document.current_data()).hexdigest().upper(), ORIGINAL_SHA256)


if __name__ == "__main__":
    unittest.main()
