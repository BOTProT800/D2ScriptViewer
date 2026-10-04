# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Pruebas de humo de la interfaz: crear la ventana, cargar un OBSP y navegar.

Se omiten si Tk no puede abrir una ventana (por ejemplo, sin escritorio).
"""

from __future__ import annotations

import hashlib
import time
import tkinter as tk
import unittest

from d2scriptviewer.document import Document
from d2scriptviewer.formats import bod
from tests import fixtures
from tests.support import REAL_OBSP, requires_real_file


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
            largest = sorted(app.document.objects, key=lambda info: -info.entry.size)[:15]
            for info in largest:
                started = time.perf_counter()
                app.navigate(info.position)
                self.assertTrue(pump(app, lambda: app.property_view.document is not None or info.is_script))
                self.assertLess(time.perf_counter() - started, 1.0, info.path)
        finally:
            app.destroy()

        after_stat = REAL_OBSP.stat()
        self.assertEqual(sorted(path.name for path in folder.iterdir()), before_listing)
        self.assertEqual((after_stat.st_size, after_stat.st_mtime_ns), (before_stat.st_size, before_stat.st_mtime_ns))
        self.assertEqual(hashlib.sha256(REAL_OBSP.read_bytes()).hexdigest(), before_sha)


if __name__ == "__main__":
    unittest.main()
