# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Núcleo del visor sin interfaz: documento, índice de referencias, búsquedas y volcado hex."""

from __future__ import annotations

import threading
import time
import unittest
from unittest import mock

from d2scriptviewer.binary import hex_dump
from d2scriptviewer.document import Document
from d2scriptviewer.errors import PathError
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


def go(tree: bod.BodDocument, text: str) -> bod.PathMatch:
    return bod.find_path(tree, bod.parse_path_label(text))


class PathLabelInverseTests(unittest.TestCase):
    """Ir a una ruta (fase 11): de la ruta legible de :func:`bod.path_label` a la ruta del árbol."""

    def setUp(self) -> None:
        self.document = Document.from_bytes(fixtures.make_obsp())
        self.desc = self.document.bod(0)

    def assert_reaches(self, tree: bod.BodDocument, text: str, label: str, note: str = "") -> bod.PathMatch:
        match = go(tree, text)
        self.assertIsNone(match.failed, match.message)
        self.assertEqual(bod.path_label(tree, match.path), label)
        self.assertEqual(match.message, note)
        return match

    def assert_stops(self, tree: bod.BodDocument, text: str, label: str, step: str, *messages: str) -> bod.PathMatch:
        match = go(tree, text)
        self.assertIsNotNone(match.failed)
        self.assertEqual(bod.path_label(tree, match.path), label)
        self.assertEqual(match.failed.text, step)
        self.assertEqual(text[match.failed.start:match.failed.end], step)  # el tramo que señala la barra
        for message in messages:
            self.assertIn(message, match.message)
        return match

    def test_round_trip_in_every_row_of_the_fixture(self) -> None:
        rows = 0
        for info in self.document.objects:
            tree = self.document.bod(info.position)
            for path, _node in bod.walk(tree.root):
                if not path:
                    continue
                rows += 1
                label = bod.path_label(tree, path)
                with self.subTest(objeto=info.path, ruta=label):
                    self.assertEqual(go(tree, label), bod.PathMatch(path, None, ""))
        self.assertGreater(rows, 80)

    def test_child_is_children_without_the_list(self) -> None:
        for tree in (self.desc, self.document.bod(2), fixtures.big_list_document()):
            for _path, node in bod.walk(tree.root):
                kids = bod.children(node)
                self.assertEqual([bod.child(node, index) for index in range(len(kids))], kids)
                for step in (len(kids), -len(kids) - 1):
                    with self.assertRaises(IndexError):
                        bod.child(node, step)
                if kids:
                    self.assertEqual(bod.child(node, -1), kids[-1])

    def test_child_never_builds_the_list(self) -> None:
        trees = (self.desc, self.document.bod(2), fixtures.big_list_document())
        rows = [(tree, path, bod.path_label(tree, path)) for tree in trees for path, _ in bod.walk(tree.root) if path]
        # bod.children construye la lista entera de hijos: recorrer una ruta con ella sería cuadrático.
        with mock.patch.object(bod, "children", side_effect=AssertionError("children() en un recorrido")):
            for tree, path, label in rows:
                self.assertEqual(bod.path_label(tree, path), label)
                parent = bod.resolve(tree, path[:-1])
                self.assertIs(bod.get_slot(parent, path[-1]), bod.resolve(tree, path))
                self.assertEqual(go(tree, label).path, path)

    def test_pairs(self) -> None:
        self.assert_reaches(self.desc, "Pairs[0].clave", "Pairs[0].clave")
        self.assert_reaches(self.desc, "Pairs[1].valor", "Pairs[1].valor")
        self.assert_reaches(self.desc, "Lookup[0].Clave", "Lookup[0].clave")
        self.assert_reaches(self.desc, "Lookup[0]", "Lookup[0]")
        self.assert_stops(self.desc, "Pairs[0].key", "Pairs[0]", "key", "es un par", ".clave y .valor")
        self.assert_stops(self.desc, "Pairs[0][1]", "Pairs[0]", "[1]", "es un par")
        self.assert_stops(self.desc, "Pairs[0].valor.x", "Pairs[0].valor", "x", "es un valor (cadena)")

    def test_a_list_longer_than_a_chunk(self) -> None:
        tree = fixtures.big_list_document()
        for index in range(1200):
            self.assertEqual(go(tree, bod.path_label(tree, (0, index))).path, (0, index))
        self.assert_reaches(tree, "Values[ 0042 ]", "Values[42]")
        self.assert_stops(tree, "Values[1200]", "Values", "[1200]", "1,200 elementos", "de [0] a [1199]")

    def test_script(self) -> None:
        tree = self.document.bod(2)
        match = self.assert_reaches(tree, "Funciones.OnStart.0x0016", "Funciones.OnStart.0x0016")
        self.assertEqual(bod.type_text(bod.resolve(tree, match.path)), "op_3A")
        # Los desplazamientos se comparan por valor si el texto no coincide.
        self.assert_reaches(tree, "funciones.onstart.0x16", "Funciones.OnStart.0x0016")
        self.assert_stops(tree, "Funciones.OnStart.0x0017", "Funciones.OnStart", "0x0017",
                          "no es el comienzo de ninguna instrucción", "la anterior es 0x0016")
        # Etiquetas con espacios y con tildes, que se pueden escribir sin ellas.
        self.assert_reaches(tree, "Valores iniciales.Speed", "Valores iniciales.Speed")
        self.assert_reaches(tree, "Estados.Active.onEnter.Parametros", "Estados.Active.onEnter.Parámetros")
        self.assert_reaches(tree, "Miembros.Stats.Damage", "Miembros.Stats.Damage")
        self.assert_reaches(tree, "Miembros.Items[1]", "Miembros.Items[1]")

    def test_case(self) -> None:
        self.assert_reaches(self.desc, "stats.CRIT", "Stats.Crit")
        self.assert_reaches(self.desc, "SLOTS[1].slotid", "Slots[1].SlotID")
        root = bod.BodObject(None, fixtures.native("Functions"), [
            fixtures.F("Activate", bod.Int32.of(1)),
            fixtures.F("activate", bod.Int32.of(2)),
            fixtures.F("Twice", bod.Int32.of(3)),
            fixtures.F("Twice", bod.Int32.of(4)),
        ])
        tree = bod.BodDocument(4, 1, root)
        # Primero el nombre exacto; sin él, sin mayúsculas solo si es único.
        self.assert_reaches(tree, "activate", "activate")
        self.assert_reaches(tree, "Activate", "Activate")
        self.assert_stops(tree, "ACTIVATE", "(raíz)", "ACTIVATE", "puede ser «Activate» o «activate»")
        # Dos campos que se llaman igual: el primero, con aviso, también sin mayúsculas.
        for text in ("Twice", "twice"):
            match = self.assert_reaches(tree, text, "Twice", "Hay 2 campos «Twice» en la raíz: se eligió el primero")
            self.assertEqual(match.path, (2,))

    def test_failures_stop_at_the_deepest_valid_node(self) -> None:
        self.assert_stops(self.desc, "Stats.Dmg", "Stats", "Dmg", "«Dmg» no es un campo de Stats", "Parecidos: «Damage»")
        self.assert_stops(self.desc, "Nada.Damage", "(raíz)", "Nada", "«Nada» no es un campo de la raíz")
        self.assert_stops(self.desc, "Color[3]", "Color", "[3]", "Color tiene 3 elementos, de [0] a [2]")
        self.assert_stops(self.desc, "Empty[0]", "Empty", "[0]", "Empty no tiene elementos")
        self.assert_stops(self.desc, "Stats[0]", "Stats", "[0]", "es un objeto y sus campos van por nombre")
        self.assert_stops(self.desc, "[0]", "(raíz)", "[0]", "la raíz es un objeto")
        self.assert_stops(self.desc, "Tags.fire", "Tags", "fire", "es una lista", "se esperaba un índice")
        self.assert_stops(self.desc, "Lookup.Health", "Lookup", "Health", "es un mapa")
        self.assert_stops(self.desc, "Speed.x", "Speed", "x", "es un valor (float32) y no tiene hijos")
        self.assert_stops(self.desc, "Slots[1].Count.x", "Slots[1].Count", "x", "es un valor (int32)")

    def test_syntax(self) -> None:
        for text in ("", "   ", "(raíz)", "(RAIZ)"):
            self.assertEqual(bod.parse_path_label(text), [], text)
        steps = bod.parse_path_label("  Slots [ 1 ] .  SlotID  ")
        self.assertEqual([step.text for step in steps], ["Slots", "[1]", "SlotID"])
        self.assertEqual([(step.start, step.end) for step in steps], [(2, 7), (8, 13), (17, 23)])
        self.assertEqual(bod.parse_path_label("Color[" + "0" * 40 + "2]")[1].index, 2)
        # Los nombres pueden llevar espacios (las etiquetas fijas de los scripts).
        self.assertEqual([step.text for step in bod.parse_path_label("Valores iniciales.Speed")],
                         ["Valores iniciales", "Speed"])
        for text, span, message in (
            ("Stats..Damage", (5, 6), "Falta un nombre de campo tras el «.»"),
            ("Stats.", (5, 6), "Falta un nombre de campo"),
            ("Stats[x]", (5, 8), "los índices por nombre no están disponibles"),
            ("MoveStates[Jump]", (10, 16), "Entre corchetes va un número"),
            ("Stats[]", (5, 7), "Falta el número"),
            ("Stats[-1]", (5, 9), "Entre corchetes va un número"),
            ("Tags[0", (4, 6), "Falta el «]»"),
            ("Stats]", (5, 6), "Sobra un «]»"),
            ("·Stats", (0, 1), "Una ruta empieza por un nombre de campo"),
            ("Stats::Damage", (5, 6), "Se esperaba «.» o «[» antes de «:»"),
            ("Stats[0]x", (8, 9), "Se esperaba «.» o «[» antes de «x»"),
            ("Color[" + "9" * 5000 + "]", (5, 5007), "demasiado grande"),
        ):
            with self.subTest(text=text[:60]):
                with self.assertRaises(PathError) as raised:
                    bod.parse_path_label(text)
                self.assertIn(message, str(raised.exception))
                self.assertEqual((raised.exception.start, raised.exception.end), span)


class LocationTests(unittest.TestCase):
    """Rutas con el objeto delante (fase 11): ``objeto · propiedad``, ``objeto::propiedad`` y el objeto solo."""

    def setUp(self) -> None:
        self.document = Document.from_bytes(fixtures.make_obsp())
        self.desc = self.document.find("death/death_desc")[0].position
        self.table = self.document.find("base/char_test")[0].position

    def locate(self, text: str) -> tuple[int | None, list[str]]:
        location = self.document.parse_location(text)
        return location.position, [step.text for step in location.steps]

    def test_formats(self) -> None:
        damage = (self.desc, ["Stats", "Damage"])
        self.assertEqual(self.locate("death/death_desc · Stats.Damage"), damage)
        self.assertEqual(self.locate("death/death_desc·Stats.Damage"), damage)
        self.assertEqual(self.locate("  death/death_desc  ::  Stats.Damage "), damage)
        # El espacio duro (al copiar de una web) y el tabulador cuentan como espacios.
        self.assertEqual(self.locate("death/death_desc · Stats.Damage "), damage)
        self.assertEqual(self.locate("death/death_desc\t·\tStats.Damage"), damage)
        self.assertEqual(self.locate("DEATH\\Death_Desc · Stats.Damage"), damage)
        # Comillas alrededor, como al copiar la ruta de un .md.
        self.assertEqual(self.locate("`death/death_desc · Stats.Damage`"), damage)
        self.assertEqual(self.locate("«Stats.Damage»"), (None, ["Stats", "Damage"]))
        self.assertEqual(self.locate("Stats.Damage"), (None, ["Stats", "Damage"]))
        # El objeto solo, con o sin separador.
        self.assertEqual(self.locate("base/char_test"), (self.table, []))
        self.assertEqual(self.locate("base/char_test ·"), (self.table, []))
        self.assertEqual(self.locate("base/char_test · (raíz)"), (self.table, []))

    def test_full_label_round_trip_in_every_row(self) -> None:
        for info in self.document.objects:
            tree = self.document.bod(info.position)
            for path, _node in bod.walk(tree.root):
                if not path:
                    continue
                label = self.document.full_label(info.position, path)
                with self.subTest(ruta=label):
                    self.assertTrue(label.startswith(f"{info.path} · "))
                    location = self.document.parse_location(label)
                    self.assertEqual(location.position, info.position)
                    self.assertEqual(bod.find_path(tree, list(location.steps)), bod.PathMatch(path, None, ""))

    def test_errors(self) -> None:
        for text, span, message in (
            ("", (0, 0), "Escribe una ruta"),
            ("  ``  ", (0, 0), "Escribe una ruta"),
            ("death/deth_desc · Health", (0, 15), "No hay ningún objeto «death/deth_desc». Parecidos: «death/death_desc»"),
            (" · Health", (1, 2), "Falta el objeto antes de «·»"),
            (":: Health", (0, 2), "Falta el objeto antes de «::»"),
            ("death/death_desc.Stats.Damage", (0, 16), "sepáralos con « · »: death/death_desc · Stats.Damage"),
            ("death/death_desc · Stats..Damage", (24, 25), "Falta un nombre de campo"),
            ("Stats\nDamage", (5, 6), "una sola línea"),
            ("Stats.​Damage", (6, 7), "un carácter invisible (U+200B)"),
            ("﻿Stats.Damage", (0, 1), "un carácter invisible (U+FEFF)"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(PathError) as raised:
                    self.document.parse_location(text)
                self.assertIn(message, str(raised.exception))
                self.assertEqual((raised.exception.start, raised.exception.end), span)

    def test_looks_like_a_location(self) -> None:
        self.document.bod(self.desc)  # el objeto abierto ya está decodificado
        for text in ("Stats.Damage", "  Pairs[0].valor ", "Color[9]", "Stats.NoExiste", "death/death_desc",
                     "base/char_test · Data[0]", "scripts/test::Funciones.OnStart"):
            self.assertTrue(self.document.looks_like_location(text, self.desc), text)
        for text in ("", "350", "1.5", "-1", "true", "Jump", "Health", "NoExiste.Damage", "hola mundo",
                     "Stats.Damage\nStats.Crit", "Stats.Damage\tStats.Crit", "C:\\Program Files (x86)\\Steam",
                     "media\\scripts.obsp", "https://github.com/BOTProT800/D2ScriptViewer", "death/no_existe",
                     "death/death_desc.Stats", "Stats." + "x" * 300):
            self.assertFalse(self.document.looks_like_location(text, self.desc), text)
        # Una ruta sin objeto delante necesita un objeto abierto que tenga ese campo en la raíz.
        self.assertFalse(self.document.looks_like_location("Stats.Damage", None))
        self.assertFalse(self.document.looks_like_location("Stats.Damage", self.table))


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


@requires_real_file
class RealPathLabelTests(unittest.TestCase):
    """Ir a una ruta (fase 11) con el archivo real."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.document = Document.from_bytes(real_bytes())

    def test_round_trip_in_every_row(self) -> None:
        document = self.document
        trees = [(info, document.bod(info.position)) for info in document.objects]
        started = time.perf_counter()
        rows = 0
        misses = []
        for info, tree in trees:
            for path, _node in bod.walk(tree.root):
                if not path:
                    continue
                rows += 1
                location = document.parse_location(document.full_label(info.position, path))
                match = bod.find_path(tree, list(location.steps))
                if location.position != info.position or match != bod.PathMatch(path, None, ""):
                    misses.append((info.path, path, match.path, match.message))
        elapsed = time.perf_counter() - started
        self.assertEqual((len(trees), rows), (7_862, 1_145_518))
        # La única fila a la que no se llega: el segundo de dos miembros con el mismo nombre.
        note = "Hay 2 campos «StageThreeHealthPct» en Miembros: se eligió el primero"
        self.assertEqual(misses, [
            ("wailing_host/wailing_host", (6, 6), (6, 6), note),
            ("wailing_host/wailing_host", (6, 7), (6, 6), note),
        ])
        # Medido: unos 19 s en Linux (16 µs por fila). El límite es una red de seguridad; que el
        # recorrido no construya listas de hijos lo vigila test_child_never_builds_the_list.
        self.assertLess(elapsed, 120, f"{elapsed:.1f} s para {rows:,} filas")

    def test_paths_from_the_modder_guide(self) -> None:
        document = self.document
        for path, label, kind, value in (
            ("death/playercommon_movestates", "MoveStates[44].JumpImpulse", "float32", "350"),
            ("ui_core/pausemenu", "Funciones.onInit.0x004E", "bool", "true"),
            ("base/quest_test_dialog", "Dialogs[0].Actions[1].FlagID", "cadena", "'flag_quest_debug_question_asked'"),
        ):
            info = document.object_by_path(path)
            assert info is not None
            tree = document.bod(info.position)
            for text in (label, f"{path} · {label}", f"{path}::{label}", f"`{label}`"):
                with self.subTest(text=text):
                    location = document.parse_location(text)
                    self.assertIn(location.position, (None, info.position))
                    started = time.perf_counter()
                    match = bod.find_path(tree, list(location.steps))
                    self.assertLess(time.perf_counter() - started, 0.05)
                    self.assertIsNone(match.failed, match.message)
                    node = bod.resolve(tree, match.path)
                    self.assertEqual((bod.path_label(tree, match.path), bod.type_text(node), bod.value_text(node)),
                                     (label, kind, value))

    def test_names_that_differ_only_in_case(self) -> None:
        info = self.document.object_by_path("base/simpleinteractive")
        assert info is not None
        tree = self.document.bod(info.position)
        for text in ("Funciones.Activate", "Funciones.activate"):
            self.assertEqual(bod.path_label(tree, go(tree, text).path), text)
        match = go(tree, "funciones.ACTIVATE")
        self.assertEqual(bod.path_label(tree, match.path), "Funciones")
        self.assertIn("puede ser «Activate» o «activate»", match.message)


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
