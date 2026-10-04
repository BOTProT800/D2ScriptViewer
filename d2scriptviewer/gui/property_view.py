# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Panel de propiedades: el árbol BOD de un objeto con columnas Nombre | Tipo | Valor.

Los hijos se insertan al abrir cada nodo, y las listas largas se reparten en
tramos de :data:`CHUNK` elementos para que abrir una nunca congele la ventana.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..formats import bod
from . import theme

CHUNK = 500
_DUMMY = "dummy"

RefLabel = Callable[[tuple[int, int]], str]


class PropertyView(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        ref_label: RefLabel,
        on_follow_ref: Callable[[tuple[int, int]], None],
    ) -> None:
        super().__init__(master, style="Panel.TFrame", padding=10)
        self.ref_label = ref_label
        self.on_follow_ref = on_follow_ref
        self.document: bod.BodDocument | None = None
        #: iid → (nodo, ruta) o, para un tramo, (contenedor, ruta, inicio, fin).
        self._items: dict[str, tuple] = {}
        self._iid_by_path: dict[tuple, str] = {}
        self._populated: set[str] = set()

        self.title_var = tk.StringVar(value="")
        header = ttk.Frame(self, style="Panel.TFrame")
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="PROPIEDADES", style="Section.TLabel").pack(side="left")
        self.toolbar = ttk.Frame(header, style="Panel.TFrame")
        self.toolbar.pack(side="right")
        ttk.Label(self, textvariable=self.title_var, style="Panel.TLabel", font=("Segoe UI Semibold", 11)).pack(
            fill="x", pady=(0, 6)
        )

        frame, self.tree = theme.scrolled(
            self,
            lambda parent: ttk.Treeview(parent, columns=("type", "value"), show="tree headings", selectmode="browse"),
            horizontal=True,
        )
        frame.pack(fill="both", expand=True)
        self.tree.heading("#0", text="Nombre")
        self.tree.heading("type", text="Tipo")
        self.tree.heading("value", text="Valor")
        # Anchos iniciales modestos: las columnas elásticas crecen con el panel.
        self.tree.column("#0", width=170, minwidth=120, stretch=True)
        self.tree.column("type", width=75, minwidth=60, stretch=False)
        self.tree.column("value", width=170, minwidth=120, stretch=True)
        for label, color in theme.VALUE_COLORS.items():
            self.tree.tag_configure(label, foreground=color)
        self.tree.tag_configure("container", foreground=theme.HEADING)
        self.tree.tag_configure("message", foreground=theme.MUTED)
        self.tree.tag_configure("edited", foreground=theme.MODIFIED)
        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", self._on_return)

    # --- Contenido -----------------------------------------------------------------------

    def _reset(self, title: str) -> None:
        self.tree.delete(*self.tree.get_children())
        self._items = {}
        self._iid_by_path = {}
        self._populated = set()
        self.document = None
        self.title_var.set(title)

    def show_message(self, title: str, message: str) -> None:
        self._reset(title)
        self.tree.insert("", "end", text=message, tags=("message",))

    def show_rows(self, title: str, rows: list[tuple[str, str, str]]) -> None:
        """Filas fijas de solo lectura (cabecera de un script)."""
        self._reset(title)
        for name, type_text, value in rows:
            self.tree.insert("", "end", text=name, values=(type_text, value))

    def show_bod(self, title: str, document: bod.BodDocument) -> None:
        self._reset(title)
        self.document = document
        self._insert_children("", document.root, ())
        self._populated.add("")

    def refresh_values(self) -> None:
        """Vuelve a pintar el valor de las filas visibles (tras editar o deshacer)."""
        for iid, item in self._items.items():
            if len(item) == 2 and self.tree.exists(iid):
                node, _path = item
                self.tree.item(iid, values=(bod.type_text(node), self._value_text(node)))

    # --- Inserción perezosa --------------------------------------------------------------

    def _value_text(self, node: object) -> str:
        if isinstance(node, bod.ExternalRef):
            return f"→ {self.ref_label(node.identity)}"
        return bod.value_text(node)

    def _tags(self, node: object) -> tuple[str, ...]:
        if isinstance(node, (bod.BodObject, bod.BodList, bod.BodMap, bod.BodTuple, bod.Pair)):
            return ("container",)
        label = bod.type_text(node)
        return (label,) if label in theme.VALUE_COLORS else ()

    def _insert_node(self, parent: str, label: str, node: object, path: tuple) -> None:
        iid = self.tree.insert(
            parent, "end", text=label, values=(bod.type_text(node), self._value_text(node)), tags=self._tags(node)
        )
        self._items[iid] = (node, path)
        self._iid_by_path[path] = iid
        if bod.has_children(node):
            self.tree.insert(iid, "end", text="…", tags=(_DUMMY,))

    def _insert_children(self, parent: str, node: object, path: tuple) -> None:
        kids = bod.children(node)
        if len(kids) > CHUNK:
            for start in range(0, len(kids), CHUNK):
                end = min(start + CHUNK, len(kids))
                iid = self.tree.insert(parent, "end", text=f"[{start}…{end - 1}]", values=("tramo", ""), tags=("container",))
                self._items[iid] = (node, path, start, end)
                self.tree.insert(iid, "end", text="…", tags=(_DUMMY,))
            return
        for index, (label, child) in enumerate(kids):
            self._insert_node(parent, label, child, path + (index,))

    def _populate(self, iid: str) -> None:
        if iid in self._populated or iid not in self._items:
            return
        self._populated.add(iid)
        self.tree.delete(*self.tree.get_children(iid))
        item = self._items[iid]
        if len(item) == 4:
            node, path, start, end = item
            kids = bod.children(node)
            for index in range(start, end):
                label, child = kids[index]
                self._insert_node(iid, label, child, path + (index,))
        else:
            node, path = item
            self._insert_children(iid, node, path)

    def _on_open(self, _event: object = None) -> None:
        self._populate(self.tree.focus())

    def reveal(self, path: tuple) -> None:
        """Abre el árbol hasta ``path`` y selecciona esa fila."""
        if self.document is None:
            return
        parent = ""
        for depth in range(1, len(path) + 1):
            target = path[:depth]
            if target not in self._iid_by_path:
                for candidate in self.tree.get_children(parent):
                    item = self._items.get(candidate)
                    if item is not None and len(item) == 4 and item[2] <= target[-1] < item[3]:
                        self._populate(candidate)
                        self.tree.item(candidate, open=True)
                        break
            iid = self._iid_by_path.get(target)
            if iid is None:
                return
            if depth < len(path):
                self._populate(iid)
                self.tree.item(iid, open=True)
            parent = iid
        if parent:
            self.tree.selection_set(parent)
            self.tree.focus(parent)
            self.tree.see(parent)

    # --- Selección -----------------------------------------------------------------------

    def selected(self) -> tuple[object, tuple] | None:
        """(nodo, ruta) de la fila seleccionada, si es un valor del árbol."""
        selection = self.tree.selection()
        if not selection:
            return None
        item = self._items.get(selection[0])
        if item is None or len(item) != 2:
            return None
        return item

    def _on_double_click(self, event: tk.Event) -> str | None:
        if self.tree.identify_region(event.x, event.y) == "tree" and self.tree.identify_element(event.x, event.y).endswith("indicator"):
            return None
        selected = self.selected()
        if selected and isinstance(selected[0], bod.ExternalRef):
            self.on_follow_ref(selected[0].identity)
            return "break"
        return None

    def _on_return(self, _event: object = None) -> str | None:
        selected = self.selected()
        if selected and isinstance(selected[0], bod.ExternalRef):
            self.on_follow_ref(selected[0].identity)
            return "break"
        return None
