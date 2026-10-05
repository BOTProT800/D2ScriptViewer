# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Fase 8: parches .d2svpatch.json (crear, comprobar y aplicar)."""

from __future__ import annotations

import copy
import hashlib
import json
import random
import unittest

from d2scriptviewer import patches, saving
from d2scriptviewer.document import Document
from d2scriptviewer.formats import bod
from d2scriptviewer.formats.hashes import name_hash
from d2scriptviewer.patches import PatchError
from d2scriptviewer.references import build_indexes
from tests import fixtures
from tests.support import ORIGINAL_SHA256, TempDirMixin, real_bytes, requires_real_file
from tests.test_cli import run
from tests.test_structure import random_operation


def path_of(document: Document, position: int, label: str) -> tuple:
    tree = document.bod(position)
    return next(path for path, _node in bod.walk(tree.root) if bod.path_label(tree, path) == label)


class PatchRoundtripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = fixtures.make_obsp()
        self.document = Document.from_bytes(self.base)
        self.desc = self.document.find("death/death_desc")[0].position
        self.instance = self.document.find("scripts/weaponbehavior_inst")[0].position
        self.script = self.document.find("scripts/test")[0].position
        self.dictionary = build_indexes(self.document.obsp).dictionary

    def path(self, label: str, position: int | None = None) -> tuple:
        return path_of(self.document, self.desc if position is None else position, label)

    def roundtrip(self) -> dict:
        """Crea el parche, lo pasa por JSON y comprueba que reaplicado da el mismo archivo."""
        patch = json.loads(patches.dumps(patches.create_patch(self.base, self.document)))
        fresh = Document.from_bytes(self.base)
        group = patches.apply_patch(fresh, patch)
        self.assertIsNotNone(group)
        self.assertEqual(fresh.current_data(), self.document.current_data())
        fresh.undo()
        self.assertEqual(fresh.current_data(), self.base)
        return patch

    def operations(self, patch: dict) -> list[str]:
        return [operation["op"] for item in patch["objetos"] for operation in item["operaciones"]]

    def test_value_of_every_type(self) -> None:
        edit = self.document.edit_text
        edit(self.desc, self.path("Health"), "250")
        edit(self.desc, self.path("Speed"), "2.75")
        edit(self.desc, self.path("Visible"), "false")
        edit(self.desc, self.path("Comment"), "adios y hola")
        edit(self.desc, self.path("Mesh"), "malla_nueva", self.dictionary)
        self.document.edit(self.desc, self.path("Behavior"), (fixtures.GROUP, fixtures.TABLE_ID))
        edit(self.desc, self.path("Lookup[0].clave"), "fire", self.dictionary)
        patch = self.roundtrip()
        self.assertEqual(self.operations(patch), ["valor"] * 7)
        operation = patch["objetos"][0]["operaciones"][0]
        self.assertEqual(operation["etiqueta"], "Health")
        self.assertEqual((operation["antes"]["texto"], operation["despues"]["texto"]), ("100", "250"))
        mesh = patch["objetos"][0]["operaciones"][4]["despues"]
        self.assertEqual(mesh, {"texto": "malla_nueva"})
        self.assertEqual(patch["fuentes"], [])
        self.assertEqual(patch["resultado"]["sha256"], hashlib.sha256(self.document.current_data()).hexdigest().upper())

    def test_structure_without_game_data(self) -> None:
        self.document.duplicate_item(self.desc, self.path("Slots[0]"))
        self.document.edit_text(self.desc, self.path("Slots[1].Count"), "9")  # editar la copia
        self.document.remove_item(self.desc, self.path("Tags[1]"))
        self.document.move_item(self.desc, self.path("Slots[2]"), -2)
        self.document.duplicate_item(self.desc, self.path("Pairs[0]"))
        self.document.edit_text(self.desc, self.path("Pairs[1].clave"), "5")
        patch = self.roundtrip()
        kinds = self.operations(patch)
        for kind in ("insertar", "quitar", "mover", "valor"):
            self.assertIn(kind, kinds)
        text = patches.dumps(patch)
        self.assertNotIn('"clase"', text)  # solo valores y rutas, nunca los objetos copiados
        self.assertNotIn('"campos"', text)
        self.assertEqual(patch["fuentes"], [])

    def test_null_fill_with_copy_and_reference(self) -> None:
        stats = self.document.copy_node(self.desc, self.path("Stats"))
        self.document.set_null(self.desc, self.path("Stats"))
        self.document.fill_null(self.desc, self.path("Parent"), stats)
        self.document.set_null(self.instance, path_of(self.document, self.instance, "Owner"))
        patch = self.roundtrip()
        self.assertEqual(sorted(self.operations(patch)), ["copiar", "nulo", "nulo"])
        copy_operation = next(op for item in patch["objetos"] for op in item["operaciones"] if op["op"] == "copiar")
        self.assertEqual(copy_operation["copia_de"]["objeto"]["ruta"], "death/death_desc")
        self.assertEqual([source["ruta"] for source in patch["fuentes"]], ["death/death_desc"])
        # Rellenar con una referencia.
        document = Document.from_bytes(self.base)
        document.fill_null(self.desc, path_of(document, self.desc, "Parent"), bod.ExternalRef(fixtures.GROUP, fixtures.TABLE_ID))
        self.document = document
        self.assertEqual(self.operations(self.roundtrip()), ["referencia"])

    def test_script_literals(self) -> None:
        self.document.edit_text(self.script, self.path("Funciones.OnStart.0x0029", self.script), "42")
        self.document.edit_text(self.script, self.path("Miembros.Stats.Damage", self.script), "-9")
        patch = self.roundtrip()
        self.assertEqual([op["etiqueta"] for op in patch["objetos"][0]["operaciones"]],
                         ["Miembros.Stats.Damage", "Funciones.OnStart.0x0029"])

    def test_fuzz(self) -> None:
        for seed in range(80):
            with self.subTest(seed=seed):
                self.document = Document.from_bytes(self.base)
                rng = random.Random(seed)
                positions = [info.position for info in self.document.objects if not info.is_script]
                for _ in range(rng.randint(3, 60)):
                    random_operation(self.document, rng.choice(positions), rng)
                if self.document.current_data() != self.base:
                    self.roundtrip()


class PatchRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = fixtures.make_obsp()
        source = Document.from_bytes(self.base)
        self.desc = source.find("death/death_desc")[0].position
        self.instance = source.find("scripts/weaponbehavior_inst")[0].position
        source.edit_text(self.desc, path_of(source, self.desc, "Health"), "250")
        source.duplicate_item(self.desc, path_of(source, self.desc, "Slots[0]"))
        source.edit_text(self.instance, path_of(source, self.instance, "Enabled"), "false")
        self.patch = patches.create_patch(self.base, source)
        self.expected = source.current_data()

    def refused(self, document: Document, patch: dict, message: str) -> None:
        before = document.current_data()
        with self.assertRaises(PatchError) as raised:
            patches.apply_patch(document, patch)
        self.assertIn(message, str(raised.exception))
        self.assertEqual(document.current_data(), before)

    def test_a_different_object_is_refused(self) -> None:
        document = Document.from_bytes(self.base)
        document.edit_text(self.desc, path_of(document, self.desc, "Speed"), "9")
        saved = document.current_data()
        other = Document.from_bytes(saved)
        self.refused(other, self.patch, "no es el que espera el parche")

    def test_pending_changes_are_refused(self) -> None:
        document = Document.from_bytes(self.base)
        document.edit_text(self.desc, path_of(document, self.desc, "Speed"), "9")
        with self.assertRaises(PatchError) as raised:
            patches.apply_patch(document, self.patch)
        self.assertIn("cambios sin guardar", str(raised.exception))

    def test_tampered_patches_change_nothing(self) -> None:
        def operation(patch: dict, kind: str) -> dict:
            return next(op for op in patch["objetos"][0]["operaciones"] if op["op"] == kind)

        cases = []
        label = copy.deepcopy(self.patch)
        operation(label, "valor")["etiqueta"] = "Speed"
        cases.append((label, "en esa ruta está"))
        before = copy.deepcopy(self.patch)
        operation(before, "valor")["antes"] = {"hex": "07000000", "texto": "7"}
        cases.append((before, "no es el que espera el parche"))
        footprint = copy.deepcopy(self.patch)
        operation(footprint, "insertar")["huella"] = "0" * 16
        cases.append((footprint, "no es lo que espera el parche"))
        unknown = copy.deepcopy(self.patch)
        unknown["objetos"][0]["operaciones"][0]["op"] = "borrar_todo"
        cases.append((unknown, "operación desconocida"))
        version = copy.deepcopy(self.patch)
        version["version"] = 99
        cases.append((version, "no admitida"))
        missing = copy.deepcopy(self.patch)
        missing["objetos"][0]["id"] = "0000000000000001"
        cases.append((missing, "no existe en este archivo"))
        # Falla el último objeto: el primero tampoco se queda aplicado.
        late = copy.deepcopy(self.patch)
        late["objetos"][-1]["sha256_resultado"] = "0" * 64
        cases.append((late, "el resultado no es el que espera el parche"))
        for patch, message in cases:
            with self.subTest(message=message):
                document = Document.from_bytes(self.base)
                self.refused(document, patch, message)
                self.assertEqual(document.modified_positions, set())
        with self.assertRaises(PatchError):
            patches.apply_patch(Document.from_bytes(self.base), {"formato": "otro"})

    def test_patches_combine_when_other_objects_differ(self) -> None:
        only_desc = copy.deepcopy(self.patch)
        only_desc["objetos"] = [item for item in only_desc["objetos"] if item["ruta"] == "death/death_desc"]
        other = Document.from_bytes(self.base)
        other.edit_text(self.instance, path_of(other, self.instance, "Enabled"), "false")
        combined = Document.from_bytes(other.current_data())
        patches.apply_patch(combined, only_desc)
        self.assertEqual(combined.current_data(), self.expected)

    def test_apply_is_one_undo_step(self) -> None:
        document = Document.from_bytes(self.base)
        group = patches.apply_patch(document, self.patch, "prueba.d2svpatch.json")
        self.assertEqual(group.description, "Aplicar prueba.d2svpatch.json")
        self.assertEqual(document.current_data(), self.expected)
        document.undo()
        self.assertEqual(document.current_data(), self.base)
        document.redo()
        self.assertEqual(document.current_data(), self.expected)


class PatchFileTests(TempDirMixin, unittest.TestCase):
    def test_base_is_the_original_copy_next_to_the_file(self) -> None:
        folder = self.make_temp_dir()
        target = folder / "scripts.obsp"
        target.write_bytes(fixtures.make_obsp())
        document = Document.open(target)
        self.assertEqual(patches.base_for(document)[0], fixtures.make_obsp())
        position = document.find("death/death_desc")[0].position
        document.edit_text(position, path_of(document, position, "Health"), "250")
        saving.save_document(document)
        base, label = patches.base_for(document)
        self.assertEqual((base, label), (fixtures.make_obsp(), str(folder / "scripts.original.obsp")))

    def test_cli_create_and_apply(self) -> None:
        folder = self.make_temp_dir()
        original = folder / "base.obsp"
        original.write_bytes(fixtures.make_obsp())
        document = Document.open(original)
        position = document.find("death/death_desc")[0].position
        document.duplicate_item(position, path_of(document, position, "Slots[0]"))
        modified = folder / "mod.obsp"
        modified.write_bytes(document.current_data())
        patch_path = folder / "cambios.d2svpatch.json"
        code, out, err = run("patch", "crear", "--archivo", str(modified), "--base", str(original), "--salida", str(patch_path))
        self.assertEqual(code, 0, err)
        self.assertIn("1 objetos, 1 operaciones (1 insertar)", out)
        result = folder / "reaplicado.obsp"
        code, out, err = run("patch", "aplicar", str(patch_path), "--archivo", str(original), "--salida", str(result))
        self.assertEqual(code, 0, err)
        self.assertIn("idéntico al del parche", out)
        self.assertEqual(result.read_bytes(), modified.read_bytes())
        code, _out, err = run("patch", "aplicar", str(patch_path), "--archivo", str(original), "--salida", str(result))
        self.assertEqual(code, 2)
        self.assertIn("ya existe", err)
        code, _out, err = run("patch", "aplicar", str(patch_path), "--archivo", str(modified),
                              "--salida", str(folder / "otra.obsp"))
        self.assertEqual(code, 2)
        self.assertIn("no es el que espera el parche", err)
        code, _out, err = run("patch", "crear", "--archivo", str(modified), "--salida", str(folder / "x.json"))
        self.assertEqual(code, 2)
        self.assertIn("indícala con --base", err)


@requires_real_file
class RealPatchTests(unittest.TestCase):
    def test_phase_5_to_7_edits_reapply_to_the_same_sha(self) -> None:
        data = real_bytes()
        document = Document.from_bytes(data)
        dictionary = build_indexes(document.obsp).dictionary
        states = document.find("death/playercommon_movestates")[0].position
        document.duplicate_item(states, path_of(document, states, "MoveStates[0]"))
        document.edit_text(states, path_of(document, states, "MoveStates[45].JumpImpulse"), "700")
        animations = document.find("death/death_animations")[0].position
        document.edit_text(animations, path_of(document, animations, "Animations[435].AnimationName"),
                           "D_WScy_Combo04", dictionary)
        pause = document.find("ui_core/pausemenu")[0].position
        document.edit_text(pause, path_of(document, pause, "Funciones.onInit.0x004E"), "false")
        patch = patches.create_patch(data, document)
        self.assertEqual(patches.patch_summary(patch), "3 objetos, 4 operaciones (1 insertar, 3 valor)")
        self.assertTrue(patch["base"]["original_de_steam"])
        fresh = Document.from_bytes(data)
        patches.apply_patch(fresh, json.loads(patches.dumps(patch)))
        self.assertEqual(fresh.current_data(), document.current_data())
        fresh.undo()
        self.assertEqual(hashlib.sha256(fresh.current_data()).hexdigest().upper(), ORIGINAL_SHA256)
        self.assertEqual(name_hash("D_WScy_Combo04"), 0x01A97E58BABBD7A8)

    def test_real_fuzz(self) -> None:
        data = real_bytes()
        for seed in (3, 11):
            with self.subTest(seed=seed):
                document = Document.from_bytes(data)
                rng = random.Random(seed)
                bods = [info.position for info in document.objects if not info.is_script][::90]
                for _ in range(40):
                    random_operation(document, rng.choice(bods), rng)
                patch = patches.create_patch(data, document)  # se autoverifica al crearlo
                fresh = Document.from_bytes(data)
                patches.apply_patch(fresh, patch)
                self.assertEqual(fresh.current_data(), document.current_data())


if __name__ == "__main__":
    unittest.main()
