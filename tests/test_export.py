# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Fase 8: exportación a JSON y CSV."""

from __future__ import annotations

import csv
import io
import json
import unittest

from d2scriptviewer import export
from d2scriptviewer.document import Document
from d2scriptviewer.errors import D2ScriptViewerError
from d2scriptviewer.formats import bod
from d2scriptviewer.formats.bod import BodDocument, BodList, BodObject, Float32, HashedString
from d2scriptviewer.formats.hashes import name_hash, object_id
from d2scriptviewer.formats.obsp import IndexEntry, ObspHeader, build_obsp
from d2scriptviewer.settings import DEFAULT_GAME
from tests import fixtures
from tests.fixtures import F, N, native
from tests.support import TempDirMixin, real_bytes, requires_real_file


def float_table_document() -> Document:
    """Un OBSP con una sola FloatTable (tipo 15) con nombres de fila y de columna."""
    rows = [
        BodObject(index, native("FloatTableRow"), [F("Row", BodList(bod.MODE_VALUES, [Float32.of(v) for v in values]))])
        for index, values in enumerate(((1.0, 375.0, 0.1), (2.0, 450.5, 0.25)))
    ]
    root = BodObject(None, native("FloatTable"), [
        F("Data", BodList(bod.MODE_VALUES, rows)),
        F("ColumnNames", BodList(bod.MODE_VALUES, [HashedString(N(t)) for t in ("Level", "Health", "Crit")])),
        F("RowNames", BodList(bod.MODE_VALUES, [HashedString(N(t)) for t in ("1", "2")])),
    ])
    blob = bod.encode(BodDocument(4, 1, root))
    strings = {name_hash(text): text for text in ("base/char_test", "Char_Test", "tables", "")}
    entry = IndexEntry(name_hash("base/char_test"), object_id("Char_Test"), 0, len(blob), fixtures.GROUP, 15,
                       name_hash("Char_Test"), name_hash("tables"), 0)
    return Document.from_bytes(build_obsp(ObspHeader(10, 1, 0, 0, 0, 0), [entry], [blob], strings))


class ExportTests(TempDirMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.document = Document.from_bytes(fixtures.make_obsp())
        self.folder = self.make_temp_dir() / "exportado"

    def read(self, relative: str) -> dict:
        return json.loads((self.folder / relative).read_text(encoding="utf-8"))

    def test_every_object_and_the_manifest(self) -> None:
        result = export.export_document(self.document, self.folder)
        self.assertEqual((result.objects, result.csv_files), (4, 1))
        self.assertEqual(sorted(result.files), sorted([
            "death/death_desc.json", "scripts/weaponbehavior_inst.json", "scripts/test.json",
            "base/char_test.json", "base/char_test.csv", "manifest.json",
        ]))
        manifest = self.read("manifest.json")
        self.assertEqual((manifest["formato"], manifest["version"]), ("d2sv-export", 1))
        self.assertFalse(manifest["archivo"]["original_de_steam"])
        self.assertFalse(manifest["archivo"]["cambios_sin_guardar"])
        self.assertEqual([item["ruta"] for item in manifest["objetos"]],
                         ["death/death_desc", "scripts/weaponbehavior_inst", "scripts/test", "base/char_test"])
        self.assertEqual(manifest["objetos"][3]["csv"], "base/char_test.csv")
        self.assertEqual(manifest["objetos"][0]["id"], f"{fixtures.DESC_ID:016X}")

    def test_typed_tree_with_resolved_references(self) -> None:
        export.export_document(self.document, self.folder)
        desc = self.read("death/death_desc.json")
        self.assertEqual((desc["tipo"], desc["tipo_nombre"], desc["bod"]), (8, "Desc", {"version": 4, "flags": 1}))
        fields = desc["raiz"]["campos"]
        self.assertEqual(desc["raiz"]["clase"], "ActorDesc")
        self.assertEqual(fields["Health"], {"tipo": "int32", "valor": 100})
        self.assertEqual(fields["Speed"], {"tipo": "float32", "valor": 1.5})
        self.assertEqual(fields["Visible"], {"tipo": "bool", "valor": True})
        self.assertEqual(fields["Comment"], {"tipo": "cadena", "valor": "hola"})
        self.assertEqual(fields["Mesh"], {"tipo": "nombre", "valor": "death_mesh"})
        self.assertEqual(fields["Parent"], {"tipo": "nulo"})
        self.assertEqual(fields["Behavior"], {"tipo": "referencia", "grupo": fixtures.SCRIPT_GROUP,
                                              "id": f"{fixtures.INSTANCE_ID:016X}",
                                              "ruta": "scripts/weaponbehavior_inst", "nombre": "WeaponBehavior_Inst"})
        self.assertEqual(fields["Pairs"]["tipo"], "pares")
        self.assertEqual(fields["Pairs"]["elementos"][1], {"clave": {"tipo": "int32", "valor": 2}, "valor": {"tipo": "nulo"}})
        self.assertEqual(fields["Lookup"]["tipo"], "mapa")
        self.assertEqual(fields["Color"]["tipo"], "tupla")
        self.assertEqual(fields["Script"]["grupo_clase"], fixtures.SCRIPT_GROUP)
        self.assertEqual(fields["Script"]["clase"], "scripts/weaponbehavior")

    def test_scripts_export_members_and_code(self) -> None:
        export.export_document(self.document, self.folder)
        body = self.read("scripts/test.json")["script"]
        self.assertEqual((body["nombre"], body["clase_base"]), ("test", "ScriptBase"))
        self.assertEqual(body["miembros"][0], {"nombre": "Health", "banderas": 10, "tipo": "int32",
                                               "valor": {"tipo": "int32", "valor": 100}})
        self.assertIsNone(body["miembros"][2]["valor"])
        on_start, unused = body["funciones"]
        self.assertEqual(unused, {"nombre": "Unused", "codigo": None})
        self.assertIn({"offset": 0x29, "op": "int", "operando": "21", "editable": True}, on_start["codigo"])
        self.assertIn({"offset": 0x52, "op": "args", "operando": "3", "editable": False}, on_start["codigo"])
        self.assertEqual(body["estados"][0]["nombre"], "Active")

    def test_unsaved_changes_are_exported_and_flagged(self) -> None:
        position = self.document.find("death/death_desc")[0].position
        self.document.edit(position, (0,), bod.Int32.of(250).raw)
        export.export_document(self.document, self.folder)
        desc = self.read("death/death_desc.json")
        self.assertEqual(desc["raiz"]["campos"]["Health"]["valor"], 250)
        self.assertTrue(desc["modificado"])
        self.assertTrue(self.read("manifest.json")["archivo"]["cambios_sin_guardar"])

    def test_float_table_csv(self) -> None:
        document = float_table_document()
        rows = list(csv.reader(io.StringIO(export.float_table_csv(document, 0))))
        self.assertEqual(rows, [["", "Level", "Health", "Crit"], ["1", "1", "375", "0.1"], ["2", "2", "450.5", "0.25"]])

    def test_destination_rules(self) -> None:
        export.export_document(self.document, self.folder)
        export.export_document(self.document, self.folder)  # una exportación anterior se puede repetir
        busy = self.make_temp_dir()
        (busy / "notas.txt").write_text("mío", encoding="utf-8")
        with self.assertRaises(D2ScriptViewerError):
            export.export_document(self.document, busy)
        self.assertEqual([item.name for item in busy.iterdir()], ["notas.txt"])
        with self.assertRaises(D2ScriptViewerError):
            export.check_destination(DEFAULT_GAME / "media" / "exportado")
        not_a_folder = busy / "notas.txt"
        with self.assertRaises(D2ScriptViewerError):
            export.check_destination(not_a_folder)


@requires_real_file
class RealExportTests(TempDirMixin, unittest.TestCase):
    def test_float_tables_and_death_objects(self) -> None:
        document = Document.from_bytes(real_bytes())
        positions = [info.position for info in document.objects
                     if info.entry.kind == 15 or info.path.startswith(("death/", "ui_core/pausemenu"))]
        folder = self.make_temp_dir() / "real"
        result = export.export_document(document, folder, positions)
        self.assertEqual(result.csv_files, 65)
        self.assertEqual(result.objects, len(positions))
        for relative in result.files:
            if relative.endswith(".json"):
                json.loads((folder / relative).read_text(encoding="utf-8"))
        rows = list(csv.reader(io.StringIO((folder / "base/char_death.csv").read_text(encoding="utf-8"))))
        self.assertEqual((len(rows), len(rows[0])), (42, 35))
        self.assertEqual(rows[0][1:4], ["Level", "ExperienceRequired", "Health"])
        states = json.loads((folder / "death/playercommon_movestates.json").read_text(encoding="utf-8"))
        jump = states["raiz"]["campos"]["MoveStates"]["elementos"][44]["campos"]
        self.assertEqual((jump["Name"]["valor"], jump["JumpImpulse"]["valor"]), ("Jump", 350.0))
        pause = json.loads((folder / "ui_core/pausemenu.json").read_text(encoding="utf-8"))["script"]
        init = next(function for function in pause["funciones"] if function["nombre"] == "onInit")
        self.assertIn({"offset": 0x4E, "op": "bool", "operando": "true", "editable": True}, init["codigo"])


if __name__ == "__main__":
    unittest.main()
