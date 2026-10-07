# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Pruebas de humo de la interfaz: crear la ventana, cargar un OBSP y navegar.

Se omiten si Tk no puede abrir una ventana (por ejemplo, sin escritorio).
"""

from __future__ import annotations

import hashlib
import re
import time
import tkinter as tk
import unittest

from d2scriptviewer.document import Document
from d2scriptviewer.formats import bod
from d2scriptviewer.search import ANY_TYPE
from d2scriptviewer.formats.hashes import name_hash
from tests import fixtures
from tests.support import REAL_OBSP, TempDirMixin, requires_real_file


def _tk_available() -> bool:
    try:
        root = tk.Tk()
    except tk.TclError:
        return False
    root.destroy()
    return True


TK_AVAILABLE = _tk_available()
requires_tk = unittest.skipUnless(TK_AVAILABLE, "Tk no puede abrir ventanas en este entorno")


def pump(app: tk.Tk, condition, timeout: float = 15.0) -> bool:
    """Procesa eventos hasta que ``condition()`` se cumpla o venza el plazo."""
    end = time.perf_counter() + timeout
    while time.perf_counter() < end:
        app.update()
        if condition():
            return True
        time.sleep(0.005)
    return False


def invoke_binding(widget: tk.Misc, sequence: str, target: tk.Misc | None = None, *, everywhere: bool = False) -> object:
    """Llama al callback enlazado a ``sequence`` como si el evento llegara a ``target``.

    Con la ventana oculta, Tk descarta las teclas sintéticas (no hay foco), así que se
    invoca el comando que tkinter registró para el enlace, con ``%W`` apuntando a ``target``.
    """
    script = widget.bind_all(sequence) if everywhere else widget.bind(sequence)
    match = re.search(r"\[(\S+) %#", script)
    assert match is not None, f"{sequence} no está enlazado"
    fields = ["0"] * len(widget._subst_format)
    fields[widget._subst_format.index("%W")] = str(target or widget)
    return widget.tk.call(match.group(1), *fields)


@requires_tk
class ViewerSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        from d2scriptviewer.gui.app import ViewerApp

        self.app = ViewerApp(auto_open=False, persist_settings=False)
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.document = Document.from_bytes(fixtures.make_obsp())
        self.app.set_document(self.document)
        self.assertTrue(pump(self.app, lambda: self.app.indexes is not None))
        self.desc = self.document.find("death/death_desc")[0]
        self.instance = self.document.find("scripts/weaponbehavior_inst")[0]

    def test_select_object_shows_properties(self) -> None:
        self.app.navigate(self.desc.position)
        tree = self.app.property_view.tree
        names = [tree.item(iid, "text") for iid in tree.get_children()]
        self.assertEqual(names[:3], ["Health", "Speed", "Visible"])
        self.assertEqual(tree.item(tree.get_children()[0], "values"), ("int32", "100"))
        self.assertEqual(self.app.object_tree.tree.selection(), (f"o{self.desc.position}",))

    def test_reveal_nested_path(self) -> None:
        tree_doc = self.document.bod(self.desc.position)
        path = next(path for path, _node in bod.walk(tree_doc.root) if bod.path_label(tree_doc, path) == "Pairs[0].valor")
        self.app.navigate(self.desc.position, path)
        view = self.app.property_view
        node, selected_path = view.selected()
        self.assertEqual(selected_path, path)
        self.assertEqual(node.text, "uno")

    def test_follow_reference_and_history(self) -> None:
        self.app.navigate(self.desc.position)
        self.app.follow_reference((fixtures.SCRIPT_GROUP, fixtures.INSTANCE_ID))
        self.assertEqual(self.app.position, self.instance.position)
        self.app.go_back()
        self.assertEqual(self.app.position, self.desc.position)
        self.app.go_forward()
        self.assertEqual(self.app.position, self.instance.position)

    def test_references_panel(self) -> None:
        self.app.navigate(self.instance.position)
        details = self.app.details
        outgoing = [details.refs_out.item(iid, "values") for iid in details.refs_out.get_children()]
        incoming = [details.refs_in.item(iid, "values") for iid in details.refs_in.get_children()]
        self.assertEqual(outgoing, [("Owner", "death/death_desc")])
        self.assertEqual(incoming, [("death/death_desc", "Behavior")])

    def test_script_and_hex(self) -> None:
        script = self.document.find("scripts/test")[0]
        self.app.navigate(script.position)
        rows = [self.app.property_view.tree.item(iid, "text") for iid in self.app.property_view.tree.get_children()]
        self.assertIn("Símbolos", rows)
        symbols = self.app.details.script_view.tree.get_children()
        self.assertEqual(len(symbols), len(fixtures.SCRIPT_SYMBOLS))
        self.app.details.notebook.select(1)
        self.app.update()
        self.assertIn("0000", self.app.details.hex_text.get("1.0", "end"))

    def test_filters(self) -> None:
        objects = self.app.object_tree
        objects.filter_var.set("char_test")
        objects.refresh()
        self.assertEqual(objects.count_var.get(), "1 de 4")
        objects.select_position(self.desc.position)  # quita los filtros para poder mostrarlo
        self.assertEqual(objects.count_var.get(), "4 objetos")
        for mode in ("Ruta", "Tipo", "Carpeta"):
            objects.group_var.set(mode)
            objects.refresh()
            objects.select_position(self.instance.position)
            self.assertEqual(objects.tree.selection(), (f"o{self.instance.position}",))

    def test_search_window(self) -> None:
        self.app.open_search()
        window = self.app.search_window
        window.query_var.set("uno")
        window.start()
        self.assertTrue(pump(self.app, lambda: str(window.search_button.cget("state")) == "normal"))
        hits = list(window.hits.values())
        self.assertEqual([(hit.where, hit.label) for hit in hits], [("valor", "Pairs[0].valor")])
        window.tree.selection_set(next(iter(window.hits)))
        window._open_selected()
        self.assertEqual(self.app.position, self.desc.position)


@requires_tk
class EditingGuiTests(TempDirMixin, unittest.TestCase):
    def setUp(self) -> None:
        from d2scriptviewer.gui.app import ViewerApp

        self.app = ViewerApp(auto_open=False, persist_settings=False)
        self.app.withdraw()
        self.addCleanup(self._destroy)
        self.questions: list[str] = []
        self.notes: list[str] = []
        self.answer = True
        self.save_answer: bool | None = None

        def ask(_title: str, message: str, **_options: object) -> bool:
            self.questions.append(message)
            return self.answer

        def ask_save(_title: str, message: str, **_options: object) -> bool | None:
            self.questions.append(message)
            return self.save_answer

        self.app.ask = ask
        self.app.ask_save = ask_save
        self.app.inform = lambda _title, message: self.notes.append(message)
        self.folder = self.make_temp_dir()
        self.file = self.folder / "scripts.obsp"
        self.file.write_bytes(fixtures.make_obsp())
        self.document = Document.open(self.file)
        self.app.set_document(self.document)
        self.assertTrue(pump(self.app, lambda: self.app.indexes is not None))
        self.desc = self.document.find("death/death_desc")[0].position
        self.app.navigate(self.desc)
        self.view = self.app.property_view

    def _destroy(self) -> None:
        try:
            self.app.destroy()
        except tk.TclError:
            pass  # el test ya cerró la ventana

    def closed(self) -> bool:
        try:
            return not self.app.winfo_exists()
        except tk.TclError:
            return True

    def row(self, label: str) -> str:
        tree = self.document.bod(self.desc)
        path = next(path for path, _node in bod.walk(tree.root) if bod.path_label(tree, path) == label)
        self.view.reveal(path)
        return self.view._iid_by_path[path]

    def type_into_editor(self, label: str, text: str) -> None:
        self.row(label)
        self.view.begin_edit()
        self.assertTrue(self.view.editing)
        self.view.editor.var.set(text)
        self.view.editor.commit()

    def test_inline_edit_marks_and_undo_restores(self) -> None:
        self.type_into_editor("Health", "250")
        iid = self.row("Health")
        self.assertFalse(self.view.editing)
        self.assertEqual(self.view.tree.item(iid, "values"), ("int32", "250"))
        self.assertIn("edited", self.view.tree.item(iid, "tags"))
        objects = self.app.object_tree.tree
        self.assertTrue(objects.item(f"o{self.desc}", "text").startswith("● "))
        self.assertIn("1 cambio sin guardar", self.app.changes_var.get())
        self.assertTrue(self.app.title().startswith("* "))
        self.assertIn("Health", self.app.edit_menu.entrycget(0, "label"))

        self.app.undo()
        self.assertEqual(self.view.tree.item(iid, "values"), ("int32", "100"))
        self.assertNotIn("edited", self.view.tree.item(iid, "tags"))
        self.assertFalse(objects.item(f"o{self.desc}", "text").startswith("● "))
        self.assertEqual(self.app.changes_var.get(), "Sin cambios")
        self.assertEqual(self.document.current_data(), fixtures.make_obsp())
        self.app.redo()
        self.assertEqual(self.view.tree.item(iid, "values"), ("int32", "250"))

    def test_invalid_input_keeps_the_editor_open(self) -> None:
        self.type_into_editor("Health", "muchos")
        self.assertTrue(self.view.editing)
        self.assertIn("no es un número entero", self.view.hint_var.get())
        self.view.cancel_edit()
        self.assertEqual(self.document.change_count, 0)

    def test_bool_and_name_editors(self) -> None:
        self.type_into_editor("Visible", "false")
        self.assertEqual(self.view.tree.item(self.row("Visible"), "values"), ("bool", "false"))
        self.row("Mesh")
        self.view.begin_edit()
        self.assertIn("death_mesh", self.view.editor.widget.cget("values"))
        self.view.editor.var.set("fi")
        self.assertIn("fire", self.view.editor.widget.cget("values"))
        self.view.editor.var.set("fire")
        self.view.editor.commit()
        self.assertEqual(self.view.tree.item(self.row("Mesh"), "values"), ("nombre", "fire"))
        self.assertEqual(self.questions, [])
        # «Fire» no aparece en el archivo (distingue mayúsculas): es una cadena nueva y pide confirmación.
        self.row("Mesh")
        self.view.begin_edit()
        self.view.editor.var.set("Fire")
        self.assertIn("Cadena nueva", self.view.hint_var.get())
        self.assertIn(f"{name_hash('Fire'):016X}", self.view.hint_var.get())
        self.answer = False
        self.view.editor.commit()
        self.assertEqual(len(self.questions), 1)
        self.assertIn("cadena nueva", self.questions[0])
        self.assertIn("«fire»", self.questions[0])
        self.assertEqual(self.view.tree.item(self.row("Mesh"), "values"), ("nombre", "fire"))
        self.answer = True
        self.type_into_editor("Mesh", "Fire")
        self.assertEqual(self.view.tree.item(self.row("Mesh"), "values"), ("nombre", "Fire"))
        self.assertEqual(len(self.questions), 2)

    def test_script_literal_edit_in_cell(self) -> None:
        position = self.document.find("scripts/test")[0].position
        self.app.navigate(position)
        tree = self.document.bod(position)
        path = next(p for p, _n in bod.walk(tree.root) if bod.path_label(tree, p) == "Funciones.OnStart.0x0029")
        self.view.reveal(path)
        iid = self.view._iid_by_path[path]
        self.assertEqual(self.view.tree.item(iid, "values"), ("int32", "21"))
        self.view.begin_edit()
        self.view.editor.var.set("42")
        self.view.editor.commit()
        self.assertEqual(self.view.tree.item(iid, "values"), ("int32", "42"))
        self.assertIn("edited", self.view.tree.item(iid, "tags"))
        self.assertEqual(self.document.modified_positions, {position})
        self.assertEqual(self.view.structure_actions(bod.resolve(tree, path), path), [])
        # Una fila de solo lectura (número de argumentos) no abre el editor.
        argc = next(p for p, _n in bod.walk(tree.root) if bod.path_label(tree, p) == "Funciones.OnStart.0x0052")
        self.view.reveal(argc)
        self.view.begin_edit()
        self.assertFalse(self.view.editing)
        self.assertIn("Solo lectura", self.view.hint_var.get())
        self.app.undo()
        self.assertEqual(self.document.current_data(), fixtures.make_obsp())

    def test_export_and_patch_round_trip(self) -> None:
        alerts: list[str] = []
        self.app.alert = lambda _title, message: alerts.append(message)
        folder = self.folder / "exportado"
        self.app.export_files(folder)
        self.assertTrue(pump(self.app, lambda: not self.app.exporting))
        self.assertTrue((folder / "manifest.json").is_file())
        self.assertIn("Exportados 4 objetos y 1 tablas CSV", self.notes[-1])
        self.type_into_editor("Health", "250")
        patch_path = self.folder / "cambios.d2svpatch.json"
        self.app.export_patch(patch_path)
        self.assertTrue(pump(self.app, lambda: not self.app.exporting))
        self.assertTrue(patch_path.is_file())
        self.assertIn("1 objetos, 1 operaciones (1 valor)", self.notes[-1])
        edited = self.document.current_data()
        self.app.undo()
        self.app.apply_patch_file(patch_path)
        self.assertEqual(self.document.current_data(), edited)
        self.assertIn("Parche aplicado", self.notes[-1])
        self.assertEqual(alerts, [])
        self.app.apply_patch_file(patch_path)  # el objeto ya tiene cambios pendientes
        self.assertIn("cambios sin guardar", alerts[-1])
        self.assertEqual(self.document.current_data(), edited)

    def test_identifier_fields_ask_first(self) -> None:
        self.answer = False
        self.type_into_editor("ItemID", "99")
        self.assertEqual(len(self.questions), 1)
        self.assertIn("ItemID", self.questions[0])
        self.assertEqual(self.document.change_count, 0)
        self.answer = True
        self.type_into_editor("ItemID", "99")
        self.assertEqual(self.document.change_count, 1)

    def test_reference_picker(self) -> None:
        from d2scriptviewer.gui import app as app_module
        from d2scriptviewer.gui.editors import ReferencePicker

        picker = ReferencePicker(self.app, self.document, (fixtures.SCRIPT_GROUP, fixtures.INSTANCE_ID), "prueba")
        picker.filter_var.set("char_test")
        picker.refresh()
        picker.accept()
        self.assertEqual(picker.result, (fixtures.GROUP, fixtures.TABLE_ID))

        class FakePicker:
            def __init__(self, *_args: object) -> None:
                pass

            def choose(self) -> tuple[int, int]:
                return (fixtures.GROUP, fixtures.TABLE_ID)

        original = app_module.ReferencePicker
        app_module.ReferencePicker = FakePicker
        try:
            self.row("Behavior")
            self.view.begin_edit()
        finally:
            app_module.ReferencePicker = original
        self.assertIn("base/char_test", self.view.tree.item(self.row("Behavior"), "values")[1])
        outgoing = [self.app.details.refs_out.item(iid, "values") for iid in self.app.details.refs_out.get_children()]
        self.assertEqual(outgoing, [("Behavior", "base/char_test")])

    def test_pending_window_and_revert(self) -> None:
        self.type_into_editor("Health", "5")
        self.type_into_editor("Speed", "3")
        self.app.open_pending()
        window = self.app.pending_window
        rows = [window.tree.item(iid, "values") for parent in window.tree.get_children()
                for iid in window.tree.get_children(parent)]
        self.assertEqual(rows, [("Health", "valor", "100", "5"), ("Speed", "valor", "1.5", "3")])
        window.tree.selection_set(window.tree.get_children()[0])
        window._revert()
        self.assertEqual(window.tree.get_children(), ())
        self.assertEqual(self.document.change_count, 0)
        self.app.undo()
        self.assertEqual(self.document.change_count, 2)

    def test_closing_with_changes_asks(self) -> None:
        self.type_into_editor("Health", "5")
        self.save_answer = None  # Cancelar
        self.app._on_close()
        self.assertFalse(self.closed())
        self.assertIn("1 cambio sin guardar", self.questions[-1])

    def test_closing_and_discarding(self) -> None:
        self.type_into_editor("Health", "5")
        self.save_answer = False
        self.app._on_close()
        self.assertTrue(self.closed())
        self.assertEqual(self.file.read_bytes(), fixtures.make_obsp())

    def test_closing_and_saving_first(self) -> None:
        self.type_into_editor("Health", "5")
        self.save_answer = True
        self.app._on_close()
        self.assertTrue(pump(self.app, self.closed))
        self.assertNotEqual(self.file.read_bytes(), fixtures.make_obsp())
        self.assertEqual((self.folder / "scripts.original.obsp").read_bytes(), fixtures.make_obsp())

    def wait_saved(self) -> None:
        self.assertTrue(pump(self.app, lambda: not self.app.saving))

    def test_save_creates_the_copy_and_clears_marks(self) -> None:
        self.app.save()
        self.assertEqual(self.app.status_var.get(), "No hay cambios que guardar")
        self.type_into_editor("Health", "250")
        self.app.save()
        self.assertTrue(self.app.saving)
        self.wait_saved()
        copy = self.folder / "scripts.original.obsp"
        self.assertEqual(copy.read_bytes(), fixtures.make_obsp())
        self.assertEqual(len(self.notes), 1)
        self.assertIn("Copia del original creada", self.notes[0])
        self.assertEqual(self.app.changes_var.get(), "Sin cambios")
        self.assertFalse(self.app.title().startswith("*"))
        self.assertFalse(self.app.object_tree.tree.item(f"o{self.desc}", "text").startswith("● "))
        self.assertNotIn("edited", self.view.tree.item(self.row("Health"), "tags"))
        self.assertIn("Modificado", self.app.state_var.get())
        reopened = Document.open(self.file)
        tree = reopened.bod(self.desc)
        health = next(path for path, _node in bod.walk(tree.root) if bod.path_label(tree, path) == "Health")
        self.assertEqual(bod.resolve(tree, health).value, 250)
        # Un segundo guardado no avisa de nuevo ni toca la copia.
        self.type_into_editor("Health", "251")
        self.app.save()
        self.wait_saved()
        self.assertEqual(len(self.notes), 1)
        self.assertEqual(copy.read_bytes(), fixtures.make_obsp())

    def test_restore_original_reopens_the_file(self) -> None:
        self.app.restore_original_file()
        self.assertIn("No existe scripts.original.obsp", self.notes[-1])
        self.type_into_editor("Speed", "7")
        self.app.save()
        self.wait_saved()
        self.app.restore_original_file()
        self.assertTrue(pump(self.app, lambda: self.app.document is not self.document and not self.app.saving))
        self.assertEqual(self.file.read_bytes(), fixtures.make_obsp())
        self.assertEqual(self.app.document.obsp.data, fixtures.make_obsp())
        self.assertIn("vuelve a ser la copia del original", self.notes[-1])


@requires_tk
class StructureGuiTests(TempDirMixin, unittest.TestCase):
    def setUp(self) -> None:
        from d2scriptviewer.gui.app import ViewerApp

        self.app = ViewerApp(auto_open=False, persist_settings=False)
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.alerts: list[str] = []
        self.answers: list[bool] = []
        self.app.alert = lambda _title, message: self.alerts.append(message)
        self.app.inform = lambda _title, message: None
        self.app.ask = lambda _title, message, **_options: self.answers.pop(0) if self.answers else True
        self.folder = self.make_temp_dir()
        self.file = self.folder / "scripts.obsp"
        self.file.write_bytes(fixtures.make_obsp())
        self.document = Document.open(self.file)
        self.app.set_document(self.document)
        self.assertTrue(pump(self.app, lambda: self.app.indexes is not None))
        self.desc = self.document.find("death/death_desc")[0].position
        self.app.navigate(self.desc)
        self.view = self.app.property_view

    def path(self, label: str) -> tuple:
        tree = self.document.bod(self.desc)
        return next(path for path, _node in bod.walk(tree.root) if bod.path_label(tree, path) == label)

    def rows(self, label: str) -> list[str]:
        iid = self.view._iid_by_path[self.path(label)]
        self.view._populate(iid)
        return [self.view.tree.item(child, "text") for child in self.view.tree.get_children(iid)]

    def selected_label(self) -> str:
        _node, path = self.view.selected()
        return bod.path_label(self.document.bod(self.desc), path)

    def test_duplicate_remove_and_move_rebuild_the_view(self) -> None:
        self.view.expand(self.path("Tags"))
        self.app.structure_action("duplicate", self.path("Tags[0]"))
        self.assertEqual(self.rows("Tags"), ["[0]", "[1]", "[2]"])
        self.assertTrue(self.view.tree.item(self.view._iid_by_path[self.path("Tags")], "open"))
        self.assertEqual(self.selected_label(), "Tags[1]")
        self.assertIn("edited", self.view.tree.item(self.view._iid_by_path[self.path("Tags[1]")], "tags"))
        self.assertIn("1 cambio sin guardar", self.app.changes_var.get())
        self.app.structure_action("down", self.path("Tags[1]"))
        self.assertEqual(self.selected_label(), "Tags[2]")
        self.app.structure_action("remove", self.path("Tags[2]"))
        self.assertEqual(self.rows("Tags"), ["[0]", "[1]"])
        self.assertEqual(self.app.changes_var.get(), "Sin cambios")
        self.app.undo()
        self.assertEqual(self.rows("Tags"), ["[0]", "[1]", "[2]"])
        self.assertEqual(self.selected_label(), "Tags[2]")

    def test_keyboard_shortcuts(self) -> None:
        self.view.reveal(self.path("Slots[0]"))
        self.view._structure_key("duplicate")
        self.assertEqual(len(self.document.bod(self.desc).root.fields[self.path("Slots")[0]].value.items), 3)
        self.view._structure_key("remove")
        self.assertEqual(self.document.change_count, 0)
        self.view.reveal(self.path("Health"))
        self.view._structure_key("remove")  # no es elemento de una lista: no hace nada
        self.assertEqual(self.document.change_count, 0)

    def test_context_actions(self) -> None:
        cases = {
            "Tags[0]": ["duplicate", "remove", "down"],
            "Slots[1]": ["duplicate", "remove", "up", "null"],
            "Stats": ["null"],
            "Behavior": ["null"],
            "Parent": ["fill"],
            "Color[0]": [],
            "Health": [],
        }
        for label, expected in cases.items():
            with self.subTest(label=label):
                path = self.path(label)
                self.assertEqual(self.view.structure_actions(bod.resolve(self.document.bod(self.desc), path), path), expected)

    def test_null_and_a_slot_without_examples(self) -> None:
        from d2scriptviewer.gui import app as app_module

        self.app.structure_action("null", self.path("Stats"))
        self.assertEqual(self.view.tree.item(self.view._iid_by_path[self.path("Stats")], "values"), ("nulo", "null"))
        notes: list[str] = []
        self.app.inform = lambda _title, message: notes.append(message)
        opened: list[tuple] = []

        class FakeDialog:
            def __init__(self, *args: object) -> None:
                opened.append(args)

            def choose(self) -> None:
                return None

        original = app_module.FillNullDialog
        app_module.FillNullDialog = FakeDialog
        try:
            # En el archivo, ActorDesc.Parent nunca tiene un objeto ni una referencia: nada que copiar.
            self.app.structure_action("fill", self.path("Parent"))
        finally:
            app_module.FillNullDialog = original
        self.assertEqual(opened, [])
        self.assertIn("ActorDesc.Parent", notes[-1])
        self.assertEqual(self.document.change_count, 1)

    def test_fill_offers_classes_seen_in_the_slot(self) -> None:
        from d2scriptviewer.gui import app as app_module

        self.app.structure_action("null", self.path("Script.Child"))
        offered = {}

        class FakeDialog:
            def __init__(self, _master, _document, _title, slot, classes, references) -> None:
                offered.update(slot=slot, classes=[row[0] for row in classes])
                self.example = (*classes[0][2][0], classes[0][0])

            def choose(self) -> tuple:
                return ("copy", *self.example)

        original = app_module.FillNullDialog
        app_module.FillNullDialog = FakeDialog
        try:
            self.app.structure_action("fill", self.path("Script.Child"))
        finally:
            app_module.FillNullDialog = original
        self.assertEqual(offered, {"slot": ("scripts/weaponbehavior", "Child", "campo"), "classes": ["Stats"]})
        self.assertEqual(self.document.change_count, 0)  # nulo y relleno con un Stats igual: sin cambios netos

    def test_saving_is_blocked_by_a_repeated_key_and_warns_on_ids(self) -> None:
        self.app.structure_action("duplicate", self.path("Lookup[0]"))
        self.assertIn("clave", self.view.hint_var.get())
        self.app.save()
        self.assertFalse(self.app.saving)
        self.assertEqual(len(self.alerts), 1)
        self.assertIn("claves repetidas", self.alerts[0])
        self.assertEqual(self.file.read_bytes(), fixtures.make_obsp())
        self.app.undo()
        self.app.structure_action("duplicate", self.path("Slots[0]"))
        self.answers = [False]
        self.app.save()
        self.assertFalse(self.app.saving)
        self.assertEqual(self.file.read_bytes(), fixtures.make_obsp())
        self.answers = [True]
        self.app.save()
        self.assertTrue(pump(self.app, lambda: not self.app.saving))
        reopened = Document.open(self.file)
        slots = bod.resolve(reopened.bod(self.desc), self.path("Slots"))
        self.assertEqual(len(slots.items), 3)

    def test_pending_window_lists_structural_changes(self) -> None:
        self.app.structure_action("remove", self.path("Tags[0]"))
        self.app.structure_action("null", self.path("Stats"))
        self.app.open_pending()
        window = self.app.pending_window
        rows = [window.tree.item(iid, "values") for parent in window.tree.get_children()
                for iid in window.tree.get_children(parent)]
        self.assertEqual(
            sorted(rows),
            sorted([("Tags[0] (posición original)", "eliminado", "death_mesh", "—"),
                    ("Stats", "reemplazado", "objeto Stats", "null")]),
        )
        window.tree.selection_set(window.tree.get_children()[0])
        window._revert()
        self.assertEqual(self.document.change_count, 0)
        self.assertEqual(self.rows("Tags"), ["[0]", "[1]"])


@requires_tk
class ObjectSearchGuiTests(unittest.TestCase):
    """La barra de búsqueda del panel de propiedades (fase 10)."""

    def setUp(self) -> None:
        from d2scriptviewer.gui.app import ViewerApp

        self.app = ViewerApp(auto_open=False, persist_settings=False)
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.app.ask = lambda _title, _message, **_options: True
        self.app.inform = lambda _title, _message: None
        self.document = Document.from_bytes(fixtures.make_obsp())
        self.app.set_document(self.document)
        self.assertTrue(pump(self.app, lambda: self.app.indexes is not None))
        self.desc = self.document.find("death/death_desc")[0].position
        self.app.navigate(self.desc)
        self.view = self.app.property_view

    def path(self, label: str, position: int | None = None) -> tuple:
        tree = self.view.document if position is None else self.document.bod(position)
        return next(path for path, _node in bod.walk(tree.root) if bod.path_label(tree, path) == label)

    def search(self, name: str = "", type_name: str = ANY_TYPE, value: str = "") -> None:
        self.view.search_name_var.set(name)
        self.view.search_type_var.set(type_name)
        self.view.search_value_var.set(value)
        self.view.run_search(move=True)  # lo que hace el temporizador tras 200 ms sin teclear

    def selected_label(self) -> str | None:
        selected = self.view.selected()
        return bod.path_label(self.view.document, selected[1]) if selected else None

    def state(self) -> tuple[str | None, str]:
        return self.selected_label(), self.view.search_count_var.get()

    def test_typing_waits_and_goes_to_the_first_result(self) -> None:
        self.assertEqual(self.view.search_count_var.get(), "")
        self.view.search_name_var.set("cri")
        self.view.search_name_var.set("crit")
        self.assertEqual(self.view.search_results, [])  # todavía no: espera 200 ms sin teclear
        self.assertTrue(pump(self.app, lambda: self.view.search_results != []))
        self.assertEqual(self.state(), ("Stats.Crit", "1 de 1"))
        self.search(name="no-existe")
        self.assertEqual(self.state(), ("Stats.Crit", "Sin resultados"))
        self.search()
        self.assertEqual(self.view.search_count_var.get(), "")

    def test_counter_next_previous_and_wrap(self) -> None:
        self.search(type_name="float32")
        self.assertEqual(self.state(), ("Speed", "1 de 6"))
        for expected in ("Stats.Crit", "Lookup[0].valor", "Color[0]", "Color[1]"):
            self.view.next_result()
            self.assertEqual(self.selected_label(), expected)
        self.view.search_next.invoke()
        self.assertEqual(self.state(), ("Color[2]", "6 de 6"))
        self.view.next_result()
        self.assertEqual(self.state(), ("Speed", "1 de 6"))  # vuelta al principio
        self.view.search_previous.invoke()
        self.assertEqual(self.state(), ("Color[2]", "6 de 6"))
        # Desde una fila que no es un resultado, se sigue a partir de ella.
        self.view.reveal(self.path("Mesh"))
        self.assertEqual(self.state(), ("Mesh", "6 resultados"))
        self.view.next_result()
        self.assertEqual(self.selected_label(), "Stats.Crit")
        self.view.reveal(self.path("Mesh"))
        self.view.previous_result()
        self.assertEqual(self.selected_label(), "Speed")

    def test_keys(self) -> None:
        self.search(type_name="float32")
        for field in self.view.search_fields:
            with self.subTest(field=str(field)):
                self.assertEqual(self.selected_label(), "Speed")
                invoke_binding(field, "<Return>")
                self.assertEqual(self.selected_label(), "Stats.Crit")
                invoke_binding(field, "<F3>")
                self.assertEqual(self.selected_label(), "Lookup[0].valor")
                invoke_binding(field, "<Shift-Return>")
                invoke_binding(field, "<Shift-F3>")
                self.assertEqual(self.selected_label(), "Speed")
        invoke_binding(self.view.tree, "<F3>")
        self.assertEqual(self.selected_label(), "Stats.Crit")
        invoke_binding(self.view.tree, "<Shift-F3>")
        self.assertEqual(self.selected_label(), "Speed")
        focused: list[str] = []
        self.view.tree.focus_set = lambda: focused.append("árbol")  # type: ignore[method-assign]
        invoke_binding(self.view.search_value, "<Escape>")
        self.assertEqual(focused, ["árbol"])

    def test_result_inside_a_chunk(self) -> None:
        self.view.show_bod("grande", fixtures.big_list_document())
        self.search(name="[1100]")
        self.assertEqual(self.view.selected()[1], (0, 1100))
        self.assertEqual(self.view.search_count_var.get(), "1 de 1")
        chunk = self.view.tree.parent(self.view._iid_by_path[(0, 1100)])
        self.assertEqual(self.view.tree.item(chunk, "text"), "[1000…1199]")
        self.assertTrue(self.view.tree.item(chunk, "open"))
        # Con otra búsqueda, la fila seleccionada sigue si es un resultado.
        self.search(type_name="int32")
        self.assertEqual(self.state(), ("Values[1100]", "1,101 de 1,200"))
        # Desde la fila de un tramo cerrado, siguiente es su primer elemento y anterior el de antes.
        chunks = self.view.tree.get_children(self.view._iid_by_path[(0,)])
        self.view.tree.selection_set(chunks[1])
        self.view.next_result()
        self.assertEqual(self.state(), ("Values[500]", "501 de 1,200"))
        self.view.tree.selection_set(chunks[1])
        self.view.previous_result()
        self.assertEqual(self.selected_label(), "Values[499]")

    def test_recalculated_after_editing_undo_and_structure(self) -> None:
        self.assertEqual(len(self.view.search_results), 0)
        self.search(value="100")  # también el grupo 10001 de una referencia y de una clase de script
        self.assertEqual(self.state(), ("Health", "1 de 3"))
        self.search(name="health", value="100")
        self.assertEqual(self.state(), ("Health", "1 de 1"))
        self.view.begin_edit()
        self.view.editor.var.set("250")
        self.view.editor.commit()
        self.assertEqual(self.state(), ("Health", "Sin resultados"))
        self.app.undo()
        self.assertEqual(self.state(), ("Health", "1 de 1"))
        self.search(type_name="nombre")
        self.assertEqual(self.state(), ("Mesh", "1 de 4"))
        self.app.structure_action("duplicate", self.path("Tags[0]"))
        self.assertEqual(self.state(), ("Tags[1]", "3 de 5"))
        self.app.undo()
        self.assertEqual(len(self.view.search_results), 4)
        self.app.redo()
        self.assertEqual(len(self.view.search_results), 5)

    def test_changing_object_keeps_criteria_and_selection(self) -> None:
        self.search(type_name="bool")
        self.assertEqual(self.state(), ("Visible", "1 de 2"))
        instance = self.document.find("scripts/weaponbehavior_inst")[0].position
        self.app.navigate(instance)
        pump(self.app, lambda: False, timeout=0.4)  # ningún temporizador pendiente mueve la selección
        self.assertEqual(self.view.search_type_var.get(), "bool")
        self.assertEqual(self.state(), (None, "1 resultado"))
        self.view.next_result()
        self.assertEqual(self.state(), ("Enabled", "1 de 1"))
        # Al llegar con una ruta (desde la búsqueda global o el historial) el contador la sitúa.
        self.app.navigate(self.desc, self.path("Script.Enabled", self.desc))
        self.assertEqual(self.state(), ("Script.Enabled", "2 de 2"))
        # Los tipos del desplegable son los del objeto abierto.
        self.view._fill_type_choices()  # lo que hace el desplegable al abrirse
        self.assertIn("referencia", self.view.search_type.cget("values"))
        self.assertEqual(self.view.search_type.cget("values")[0], ANY_TYPE)

    def test_f2_on_a_result(self) -> None:
        self.search(name="speed")
        self.assertEqual(self.selected_label(), "Speed")
        invoke_binding(self.view.search_name, "<F2>")
        self.assertTrue(self.view.editing)
        self.assertEqual(self.view.editor.iid, self.view._iid_by_path[self.path("Speed")])
        self.view.editor.var.set("3")
        self.view.editor.commit()
        self.assertEqual(self.view.tree.item(self.view._iid_by_path[self.path("Speed")], "values"), ("float32", "3"))
        self.assertEqual(self.state(), ("Speed", "1 de 1"))
        invoke_binding(self.view.tree, "<F2>")
        self.assertTrue(self.view.editing)
        # Ctrl+F con el editor abierto lo cancela y pasa a la barra.
        invoke_binding(self.app, "<Control-f>", self.view.editor.widget, everywhere=True)
        self.assertFalse(self.view.editing)
        self.assertTrue(self.view.search_name.selection_present())
        self.assertEqual(self.document.change_count, 1)

    def test_ctrl_z_in_a_bar_field_does_not_undo(self) -> None:
        self.search(name="health")
        self.view.begin_edit()
        self.view.editor.var.set("250")
        self.view.editor.commit()
        self.assertEqual(self.document.change_count, 1)
        for field in self.view.search_fields:
            for sequence in ("<Control-z>", "<Control-y>", "<Control-p>"):
                invoke_binding(self.app, sequence, field, everywhere=True)
            self.assertEqual(self.document.change_count, 1)
            self.assertIsNone(self.app.pending_window)
        invoke_binding(self.app, "<Control-z>", self.view.tree, everywhere=True)
        self.assertEqual(self.document.change_count, 0)

    def test_ctrl_f_and_ctrl_shift_f(self) -> None:
        menu = self.app.nametowidget(self.app.menubar.entrycget("Buscar", "menu"))
        self.assertEqual(
            [(menu.entrycget(index, "label"), menu.entrycget(index, "accelerator")) for index in range(2)],
            [("Buscar en el objeto", "Ctrl+F"), ("Buscar en todo el archivo…", "Ctrl+Mayús+F")],
        )
        calls: list[str] = []
        self.view.focus_search = lambda: calls.append("barra")  # type: ignore[method-assign]
        invoke_binding(self.app, "<Control-f>", self.view.tree, everywhere=True)
        self.assertEqual(calls, ["barra"])
        self.assertIsNone(self.app.search_window)
        invoke_binding(self.app, "<Control-F>", self.view.tree, everywhere=True)
        window = self.app.search_window
        self.assertIsNotNone(window)
        self.assertTrue(window.winfo_exists())
        # Ctrl+F dentro de la búsqueda global no salta a la ventana principal.
        invoke_binding(self.app, "<Control-f>", window, everywhere=True)
        self.assertEqual(calls, ["barra"])
        invoke_binding(self.app, "<Control-F>", self.view.search_value, everywhere=True)
        self.assertIs(self.app.search_window, window)


@requires_tk
@requires_real_file
class RealViewerTests(unittest.TestCase):
    def test_large_objects_display_fast_and_nothing_is_written(self) -> None:
        from d2scriptviewer.gui.app import ViewerApp

        folder = REAL_OBSP.parent
        before_listing = sorted(path.name for path in folder.iterdir())
        before_stat = REAL_OBSP.stat()
        before_sha = hashlib.sha256(REAL_OBSP.read_bytes()).hexdigest()

        app = ViewerApp(auto_open=False, persist_settings=False)
        app.withdraw()
        try:
            app.open_file(REAL_OBSP)
            self.assertTrue(pump(app, lambda: app.indexes is not None, timeout=60))
            by_size = sorted(app.document.objects, key=lambda info: -info.entry.size)
            largest = by_size[:15] + [info for info in by_size if info.is_script][:10]
            for info in largest:
                started = time.perf_counter()
                app.navigate(info.position)
                self.assertTrue(pump(app, lambda: app.property_view.document is not None))
                self.assertLess(time.perf_counter() - started, 1.0, info.path)
        finally:
            app.destroy()

        after_stat = REAL_OBSP.stat()
        self.assertEqual(sorted(path.name for path in folder.iterdir()), before_listing)
        self.assertEqual((after_stat.st_size, after_stat.st_mtime_ns), (before_stat.st_size, before_stat.st_mtime_ns))
        self.assertEqual(hashlib.sha256(REAL_OBSP.read_bytes()).hexdigest(), before_sha)


if __name__ == "__main__":
    unittest.main()
