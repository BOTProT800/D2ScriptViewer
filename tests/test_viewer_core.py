# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Núcleo del visor sin interfaz: documento, índice de referencias, búsqueda y volcado hex."""

from __future__ import annotations

import threading
import unittest

from d2scriptviewer.binary import hex_dump
from d2scriptviewer.document import Document
from d2scriptviewer.references import Cancelled, Reference, ReferenceIndex, build_indexes, references_in
from d2scriptviewer.search import SearchOptions, search
from tests import fixtures


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
        self.assertEqual(indexes.dictionary.text(fixtures.fake_hash("death_mesh")), "death_mesh")
        self.assertEqual(indexes.dictionary.text(fixtures.fake_hash("NumSlots")), "NumSlots")

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
