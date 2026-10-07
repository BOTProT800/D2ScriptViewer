# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Núcleo del visor sin interfaz: documento, índice de referencias, búsquedas y volcado hex."""

from __future__ import annotations

import threading
import time
import unittest

from d2scriptviewer.binary import hex_dump
from d2scriptviewer.document import Document
from d2scriptviewer.formats import bod
from d2scriptviewer.formats.hashes import name_hash
from d2scriptviewer.references import Cancelled, Reference, ReferenceIndex, build_indexes, references_in
from d2scriptviewer.search import ANY_TYPE, SearchOptions, find_in_tree, row_value_text, search, tree_types
from tests import fixtures
from tests.support import real_bytes, requires_real_file


class DocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = Document.from_bytes(fixtures.make_obsp())

    def test_objects_and_lookup(self) -> None:
        self.assertEqual([info.path for info in self.document.objects], [row[0] for row in fixtures.OBJECTS])
        desc = self.document.find("Death_Desc")
        self.assertEqual(len(desc), 1)
        self.assertEqual(self.document.find("death\\death_desc"), desc)
        self.assertEqual(len(self.document.find("scripts")), 2)
        self.assertIs(self.document.object_by_identity((fixtures.GROUP, fixtures.DESC_ID)), desc[0])
        self.assertIsNone(self.document.object_by_identity((1, 2)))
        self.assertFalse(self.document.is_steam_original)

    def test_decode_is_cached(self) -> None:
        self.assertIsNone(self.document.cached_bod(0))
        first = self.document.bod(0)
        self.assertIs(self.document.bod(0), first)
        self.assertIs(self.document.cached_bod(0), first)
        self.assertEqual(self.document.script_header(2).group, fixtures.SCRIPT_GROUP)

    def test_concurrent_decodes_share_one_tree(self) -> None:
        trees = []
        workers = [threading.Thread(target=lambda: trees.append(self.document.bod(0))) for _ in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertTrue(all(tree is trees[0] for tree in trees))


class ReferenceTests(unittest.TestCase):
    def test_build_indexes(self) -> None:
        document = Document.from_bytes(fixtures.make_obsp())
        indexes = build_indexes(document.obsp)
        self.assertEqual(indexes.failures, [])
        self.assertEqual(len(indexes.references), 2)
        outgoing = indexes.references.references_from(0)
        self.assertEqual([(ref.label, ref.target) for ref in outgoing], [("Behavior", (fixtures.SCRIPT_GROUP, fixtures.INSTANCE_ID))])
        incoming = indexes.references.references_to((fixtures.GROUP, fixtures.DESC_ID))
        self.assertEqual([(ref.source, ref.label) for ref in incoming], [(1, "Owner")])
        self.assertEqual(indexes.dictionary.text(name_hash("death_mesh")), "death_mesh")
        self.assertEqual(indexes.dictionary.text(name_hash("NumSlots")), "NumSlots")

    def test_set_object_replaces_old_references(self) -> None:
        index = ReferenceIndex()
        index.set_object(5, [Reference(5, (0,), (1, 2), "A")])
        index.set_object(6, [Reference(6, (1,), (1, 2), "B")])
        self.assertEqual(len(index.references_to((1, 2))), 2)
        index.set_object(5, [Reference(5, (0,), (3, 4), "A")])
        self.assertEqual([ref.source for ref in index.references_to((1, 2))], [6])
        self.assertEqual(len(index.references_to((3, 4))), 1)
        index.set_object(5, [])
        self.assertEqual(index.references_from(5), [])
        self.assertEqual(len(index), 1)

    def test_references_in(self) -> None:
        tree = fixtures.instance_document()
        self.assertEqual([ref.label for ref in references_in(1, tree)], ["Owner"])

    def test_cancel(self) -> None:
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(Cancelled):
            build_indexes(Document.from_bytes(fixtures.make_obsp()).obsp, cancel=cancel)


class SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = Document.from_bytes(fixtures.make_obsp())

    def find(self, text: str, **options: object) -> list[tuple[str, str, str]]:
        hits, _truncated = search(self.document, text, SearchOptions(**options))
        return [(self.document.objects[hit.position].path, hit.where, hit.label or hit.text) for hit in hits]

    def test_metadata(self) -> None:
        self.assertIn(("base/char_test", "ruta", "base/char_test"), self.find("char_test", values=False))
        self.assertIn(("scripts/weaponbehavior_inst", "carpeta", "oc\\Body\\slayer"), self.find("slayer"))

    def test_values(self) -> None:
        self.assertEqual(self.find("UNO", metadata=False), [("death/death_desc", "valor", "Pairs[0].valor")])
        self.assertEqual(self.find("100", metadata=False), [("death/death_desc", "valor", "Health")])
        self.assertEqual(self.find("20.5", metadata=False), [("base/char_test", "valor", "Data[1].Values[0]")])
        self.assertEqual(self.find("-7", metadata=False), [("death/death_desc", "valor", "Stats.Damage")])
        self.assertIn(("death/death_desc", "valor", "Script"), self.find("weaponbehavior", metadata=False))
        self.assertEqual(self.find("NumSlots", metadata=False), [("scripts/test", "símbolo", "NumSlots")])

    def test_field_names(self) -> None:
        self.assertEqual(self.find("crit", metadata=False), [])
        self.assertEqual(self.find("crit", metadata=False, field_names=True), [("death/death_desc", "campo", "Stats.Crit")])

    def test_limit_cancel_and_batches(self) -> None:
        hits, truncated = search(self.document, "e", SearchOptions(limit=3))
        self.assertEqual(len(hits), 3)
        self.assertTrue(truncated)
        cancel = threading.Event()
        cancel.set()
        self.assertEqual(search(self.document, "e", cancel=cancel), ([], False))
        batches: list[int] = []
        hits, _ = search(self.document, "a", on_hits=lambda batch: batches.append(len(batch)))
        self.assertEqual(sum(batches), len(hits))
        self.assertEqual(search(self.document, "   "), ([], False))

    def test_edited_trees_are_searched(self) -> None:
        tree = self.document.bod(0)
        tree.root.fields[3].value.text = "cambiado"
        self.assertEqual(self.find("cambiado", metadata=False), [("death/death_desc", "valor", "Comment")])


class TreeSearchTests(unittest.TestCase):
    """Búsqueda dentro del objeto (fase 10): columnas Nombre, Tipo y Valor tal como se ven."""

    def setUp(self) -> None:
        self.document = Document.from_bytes(fixtures.make_obsp())
        self.desc = self.document.bod(0)

    def ref_label(self, identity: tuple[int, int]) -> str:
        info = self.document.object_by_identity(identity)
        return info.label() if info is not None else "(no existe)"

    def find(self, tree: bod.BodDocument | None = None, **criteria: str) -> list[str]:
        tree = tree or self.desc
        return [bod.path_label(tree, path) for path in find_in_tree(tree, ref_label=self.ref_label, **criteria)]

    def test_each_column(self) -> None:
        self.assertEqual(self.find(name="crit"), ["Stats.Crit"])
        self.assertEqual(self.find(name="id"), ["ItemID", "Slots[0].SlotID", "Slots[1].SlotID"])
        self.assertEqual(self.find(type_name="bool"), ["Visible", "Script.Enabled"])
        self.assertEqual(self.find(type_name="nombre"), ["Mesh", "Tags[0]", "Tags[1]", "Lookup[0].clave"])
        self.assertEqual(self.find(value="death_mesh"), ["Mesh", "Tags[0]"])
        # Valor como se ve en la columna: un par es «clave → valor» y una cadena sin hash va entre comillas.
        self.assertEqual(self.find(value="'hola'"), ["Comment"])
        self.assertEqual(self.find(value="1 → 'uno'"), ["Pairs[0]"])

    def test_columns_combine_with_and(self) -> None:
        self.assertEqual(self.find(type_name="nombre", value="fire"), ["Tags[1]"])
        self.assertEqual(self.find(name="count", value="7"), ["Slots[1].Count"])
        self.assertEqual(self.find(name="slotid", type_name="int32", value="2"), ["Slots[1].SlotID"])
        self.assertEqual(self.find(name="health", type_name="float32"), [])

    def test_case_and_type_is_exact(self) -> None:
        self.assertEqual(self.find(name="HEALTH"), ["Health"])
        self.assertEqual(self.find(value="HEALTH"), ["Lookup[0]", "Lookup[0].clave"])
        self.assertEqual(self.find(type_name="FLOAT32"),
                         ["Speed", "Stats.Crit", "Lookup[0].valor", "Color[0]", "Color[1]", "Color[2]"])
        # El tipo no es texto contenido: «lista» no encuentra los «pares».
        self.assertEqual(self.find(type_name="lista"), ["Tags", "Empty", "Slots"])
        self.assertEqual(self.find(type_name="list"), [])

    def test_references_by_their_target(self) -> None:
        self.assertEqual(self.find(value="weaponbehavior_inst"), ["Behavior"])
        self.assertEqual(self.find(value="→ scripts/"), ["Behavior"])
        # Sin etiquetas de destino se ve la identidad, como en el volcado.
        self.assertEqual(find_in_tree(self.desc, value="weaponbehavior_inst"), [])
        node = bod.resolve(self.desc, find_in_tree(self.desc, type_name="referencia")[0])
        self.assertEqual(row_value_text(node, self.ref_label), "→ scripts/weaponbehavior_inst")
        self.assertEqual(row_value_text(node), bod.value_text(node))

    def test_row_order(self) -> None:
        paths = find_in_tree(self.desc, value="e")
        self.assertGreater(len(paths), 5)
        self.assertEqual(paths, sorted(paths))
        found = set(paths)
        walked = [path for path, _node in bod.walk(self.desc.root) if path in found]
        self.assertEqual(paths, walked)
        self.assertNotIn((), find_in_tree(self.desc, type_name="objeto"))  # la raíz no es una fila

    def test_a_list_longer_than_a_chunk(self) -> None:
        tree = fixtures.big_list_document()
        self.assertEqual(find_in_tree(tree, name="[1100]"), [(0, 1100)])
        self.assertEqual(find_in_tree(tree, value="1199"), [(0, 1199)])
        every = find_in_tree(tree, type_name="int32")
        self.assertEqual(every, [(0, index) for index in range(1200)])
        self.assertEqual(self.find(tree, value="999"), ["Values[999]"])

    def test_empty_criteria_and_no_results(self) -> None:
        self.assertEqual(find_in_tree(self.desc), [])
        self.assertEqual(find_in_tree(self.desc, name="  ", type_name=ANY_TYPE, value=""), [])
        self.assertEqual(find_in_tree(self.desc, type_name=ANY_TYPE.upper()), [])
        self.assertEqual(self.find(name="crit", type_name=ANY_TYPE), ["Stats.Crit"])
        self.assertEqual(self.find(name="no-existe"), [])
        self.assertEqual(self.find(type_name="op_3A"), [])

    def test_types_of_the_object(self) -> None:
        self.assertEqual(
            tree_types(self.desc),
            ["bool", "cadena", "float32", "int32", "lista", "mapa", "nombre", "nulo", "objeto", "par", "pares",
             "referencia", "tupla"],
        )
        self.assertEqual(tree_types(fixtures.instance_document()), ["bool", "referencia"])

    def test_scripts_are_searched_by_mnemonic_and_operand(self) -> None:
        tree = self.document.bod(2)
        self.assertIn("op_3A", tree_types(tree))
        paths = find_in_tree(tree, type_name="op_3A", value="numslots")
        self.assertEqual([bod.path_label(tree, path) for path in paths], ["Funciones.OnStart.0x0016"])
        following = bod.resolve(tree, paths[0][:-1] + (paths[0][-1] + 1,))
        self.assertEqual((bod.type_text(following), bod.value_text(following)), ("int32", "21"))


@requires_real_file
class RealTreeSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = Document.from_bytes(real_bytes())

    def ref_label(self, identity: tuple[int, int]) -> str:
        info = self.document.object_by_identity(identity)
        return info.label() if info is not None else "(no existe)"

    def test_num_slots_in_death(self) -> None:
        tree = self.document.bod(self.document.find("death/death")[0].position)
        paths = find_in_tree(tree, type_name="op_3A", value="NumSlots", ref_label=self.ref_label)
        labels = [bod.path_label(tree, path) for path in paths]
        self.assertEqual(len(labels), 7, labels)
        self.assertTrue(all(label.startswith("Funciones.onInit.0x") for label in labels), labels)
        self.assertEqual((labels[0], labels[-1]), ("Funciones.onInit.0x0770", "Funciones.onInit.0x0A4A"))
        following = [bod.resolve(tree, path[:-1] + (path[-1] + 1,)) for path in paths]
        self.assertTrue(all(isinstance(node, bod.Int32) for node in following))
        self.assertEqual([node.value for node in following], [21, 21, 21, 22, 22, 22, 21])

    def test_largest_object_is_searched_fast(self) -> None:
        largest = max(self.document.objects, key=lambda info: info.entry.size)
        self.assertEqual(largest.path, "base/itemfoleytable")
        tree = self.document.bod(largest.position)
        self.assertGreater(sum(1 for _ in bod.walk(tree.root)), 26_000)  # unas 26 040 filas
        for criteria in (
            {"value": "no-existe-en-el-archivo"},
            {"type_name": "referencia"},
            {"name": "a", "type_name": "nombre", "value": "e"},
            {"value": "→"},
        ):
            with self.subTest(**criteria):
                started = time.perf_counter()
                find_in_tree(tree, ref_label=self.ref_label, **criteria)
                self.assertLess(time.perf_counter() - started, 0.2)


class HexDumpTests(unittest.TestCase):
    def test_format(self) -> None:
        dump = hex_dump(b"BOD\xfd" + bytes(range(14)), base=0x100)
        lines = dump.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("00000100  42 4f 44 fd 00 01"))
        self.assertTrue(lines[0].endswith("BOD............."))
        self.assertTrue(lines[1].startswith("00000110  0c 0d"))
        self.assertEqual(hex_dump(b""), "")


if __name__ == "__main__":
    unittest.main()
