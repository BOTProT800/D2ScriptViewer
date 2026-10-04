# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Panel de propiedades: el árbol BOD de un objeto con columnas Nombre | Tipo | Valor.

Los hijos se insertan al abrir cada nodo, y las listas largas se reparten en
tramos de :data:`CHUNK` elementos para que abrir una nunca congele la ventana.

Edición: doble clic o F2 abre un editor en la celda (Intro confirma, Escape
cancela). En una referencia ``FC``, doble clic e Intro navegan al destino y F2
abre el selector de objetos. La validación y el cambio los hace el núcleo a
través de los callbacks que recibe el panel.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .. import edits
from ..formats import bod
from . import theme
from .editors import InlineEditor

CHUNK = 500
_DUMMY = "dummy"

RefLabel = Callable[[tuple[int, int]], str]
#: (nodo, ruta, texto) → mensaje de error, o ``None`` si se aplicó o se descartó.
EditText = Callable[[object, tuple, str], "str | None"]
#: (nodo, ruta, texto) → (válido, pista).
Hint = Callable[[object, tuple, str], "tuple[bool, str]"]

HINT_STYLES = {"info": "PanelMuted.TLabel", "ok": "HintOk.TLabel", "error": "HintError.TLabel", "warn": "HintWarn.TLabel"}


class PropertyView(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        ref_label: RefLabel,
        on_follow_ref: Callable[[tuple[int, int]], None],
        on_edit_text: EditText | None = None,
        on_pick_reference: Callable[[object, tuple], None] | None = None,
        on_revert_property: Callable[[tuple], None] | None = None,
        on_structure: Callable[[str, tuple], None] | None = None,
        hint: Hint | None = None,
        suggest: Callable[[str], list[str]] | None = None,
    ) -> None:
        super().__init__(master, style="Panel.TFrame", padding=10)
        self.ref_label = ref_label
        self.on_follow_ref = on_follow_ref
        self.on_edit_text = on_edit_text
        self.on_pick_reference = on_pick_reference
        self.on_revert_property = on_revert_property
        #: (acción, ruta): ``duplicate``, ``remove``, ``up``, ``down``, ``null`` o ``fill``.
        self.on_structure = on_structure
        self.hint = hint
        self.suggest = suggest
        self.document: bod.BodDocument | None = None
        self.edited_paths: set[tuple] = set()
        self.editor: InlineEditor | None = None
        #: iid → (nodo, ruta) o, para un tramo, (contenedor, ruta, inicio, fin).
        self._items: dict[str, tuple] = {}
        self._iid_by_path: dict[tuple, str] = {}
        self._populated: set[str] = set()

        self.title_var = tk.StringVar(value="")
        self.hint_var = tk.StringVar(value="")
        header = ttk.Frame(self, style="Panel.TFrame")
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="PROPIEDADES", style="Section.TLabel").pack(side="left")
        self.toolbar = ttk.Frame(header, style="Panel.TFrame")
        self.toolbar.pack(side="right")
        ttk.Label(self, textvariable=self.title_var, style="Panel.TLabel", font=("Segoe UI Semibold", 11)).pack(
            fill="x", pady=(0, 6)
        )
        self.hint_label = ttk.Label(self, textvariable=self.hint_var, style="PanelMuted.TLabel", wraplength=600, justify="left")
        self.hint_label.pack(side="bottom", fill="x", pady=(6, 0))

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
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._show_selection_hint())
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", self._on_return)
        self.tree.bind("<F2>", lambda _event: self.begin_edit() or "break")
        self.tree.bind("<Button-3>", self._on_context_menu)
        self.tree.bind("<MouseWheel>", lambda _event: self.cancel_edit())
        for sequence, action in (
            ("<Control-d>", "duplicate"),
            ("<Delete>", "remove"),
            ("<Alt-Up>", "up"),
            ("<Alt-Down>", "down"),
        ):
            self.tree.bind(sequence, lambda _event, action=action: self._structure_key(action))
        self.bind("<Configure>", lambda event: self.hint_label.configure(wraplength=max(event.width - 30, 200)))

    # --- Contenido -----------------------------------------------------------------------

    def _reset(self, title: str) -> None:
        self.cancel_edit()
        self.tree.delete(*self.tree.get_children())
        self._items = {}
        self._iid_by_path = {}
        self._populated = set()
        self.document = None
        self.edited_paths = set()
        self.title_var.set(title)
        self.set_hint("")

    def show_message(self, title: str, message: str) -> None:
        self._reset(title)
        self.tree.insert("", "end", text=message, tags=("message",))

    def show_rows(self, title: str, rows: list[tuple[str, str, str]], hint: str = "") -> None:
        """Filas fijas de solo lectura (cabecera de un script)."""
        self._reset(title)
        for name, type_text, value in rows:
            self.tree.insert("", "end", text=name, values=(type_text, value))
        self.set_hint(hint)

    def show_bod(self, title: str, document: bod.BodDocument, edited_paths: set[tuple] | None = None) -> None:
        self._reset(title)
        self.document = document
        self.edited_paths = set(edited_paths or ())
        self._insert_children("", document.root, ())
        self._populated.add("")
        self.set_hint("Doble clic o F2 para editar un valor · clic derecho para más opciones")

    def set_edited(self, paths: set[tuple]) -> None:
        self.edited_paths = set(paths)
        self.refresh_values()

    def rebuild(self, title: str, document: bod.BodDocument, edited_paths: set[tuple], focus: tuple | None) -> None:
        """Vuelve a pintar el árbol tras un cambio de estructura, con los nodos abiertos de antes."""
        opened = [
            item[1]
            for iid, item in self._items.items()
            if len(item) == 2 and self.tree.exists(iid) and self.tree.item(iid, "open")
        ]
        top = self.tree.yview()[0]
        self.show_bod(title, document, edited_paths)
        for path in sorted(opened, key=len):
            self.expand(path)
        if focus:
            self.reveal(focus)
        else:
            self.tree.yview_moveto(top)

    def expand(self, path: tuple) -> None:
        """Abre el nodo de ``path`` si todavía existe en el árbol."""
        self.reveal(path, select=False)
        iid = self._iid_by_path.get(path)
        if iid is not None:
            self._populate(iid)
            self.tree.item(iid, open=True)

    def refresh_values(self) -> None:
        """Vuelve a pintar las filas visibles (tras editar, deshacer o revertir)."""
        for iid, item in self._items.items():
            if len(item) == 2 and self.tree.exists(iid):
                node, path = item
                self.tree.item(
                    iid, values=(bod.type_text(node), self._value_text(node)), tags=self._tags(node, path)
                )

    def set_hint(self, text: str, kind: str = "info") -> None:
        self.hint_var.set(text)
        self.hint_label.configure(style=HINT_STYLES.get(kind, HINT_STYLES["info"]))

    # --- Inserción perezosa --------------------------------------------------------------

    def _value_text(self, node: object) -> str:
        if isinstance(node, bod.ExternalRef):
            return f"→ {self.ref_label(node.identity)}"
        return bod.value_text(node)

    def _tags(self, node: object, path: tuple) -> tuple[str, ...]:
        if path in self.edited_paths:
            return ("edited",)
        if isinstance(node, (bod.BodObject, bod.BodList, bod.BodMap, bod.BodTuple, bod.Pair)):
            return ("container",)
        label = bod.type_text(node)
        return (label,) if label in theme.VALUE_COLORS else ()

    def _insert_node(self, parent: str, label: str, node: object, path: tuple) -> None:
        iid = self.tree.insert(
            parent, "end", text=label, values=(bod.type_text(node), self._value_text(node)), tags=self._tags(node, path)
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

    def reveal(self, path: tuple, select: bool = True) -> None:
        """Abre el árbol hasta ``path`` y, si ``select``, selecciona esa fila."""
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
        if parent and select:
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

    def _show_selection_hint(self) -> None:
        if self.editing or self.document is None:
            return
        selected = self.selected()
        if selected is None:
            return
        node, path = selected
        warning = edits.identifier_warning(edits.field_name(self.document, path), node) if edits.is_editable(node) else None
        actions = self.structure_actions(node, path)
        structure = ""
        if "duplicate" in actions:
            structure = " · Ctrl+D duplica, Supr elimina, Alt+↑/↓ mueve"
        if "null" in actions:
            structure += " · clic derecho: poner a nulo"
        if "fill" in actions:
            structure += " · clic derecho: rellenar con un objeto"
        if warning:
            self.set_hint(warning, "warn")
        elif isinstance(node, bod.ExternalRef):
            self.set_hint("Doble clic o Intro para ir al destino · F2 para cambiar la referencia" + structure)
        elif isinstance(node, bod.HashedString):
            self.set_hint("F2 o doble clic para cambiar la cadena: sugiere las del archivo y admite nuevas"
                          " (distingue mayúsculas)" + structure)
        elif edits.is_editable(node):
            self.set_hint("Doble clic o F2 para editar" + structure)
        elif structure:
            self.set_hint(structure.removeprefix(" · ").capitalize())
        elif isinstance(node, bod.BodTuple) or (path and isinstance(bod.resolve(self.document, path[:-1]), bod.BodTuple)):
            self.set_hint("Las tuplas tienen tamaño fijo en el juego: solo se editan sus valores")
        else:
            self.set_hint("")

    def _on_double_click(self, event: tk.Event) -> str | None:
        if self.tree.identify_element(event.x, event.y).endswith("indicator"):
            return None
        selected = self.selected()
        if selected is None:
            return None
        node, _path = selected
        if isinstance(node, bod.ExternalRef):
            self.on_follow_ref(node.identity)
            return "break"
        if edits.is_editable(node):
            self.begin_edit()
            return "break"
        return None

    def _on_return(self, _event: object = None) -> str | None:
        selected = self.selected()
        if selected and isinstance(selected[0], bod.ExternalRef):
            self.on_follow_ref(selected[0].identity)
            return "break"
        if selected and edits.is_editable(selected[0]):
            self.begin_edit()
            return "break"
        return None

    # --- Edición -------------------------------------------------------------------------

    @property
    def editing(self) -> bool:
        return self.editor is not None and not self.editor.closed

    def cancel_edit(self) -> None:
        if self.editing:
            assert self.editor is not None
            self.editor.cancel()

    def begin_edit(self) -> None:
        """Abre el editor adecuado para la fila seleccionada."""
        selected = self.selected()
        if selected is None or self.document is None or self.on_edit_text is None:
            return
        node, path = selected
        if not edits.is_editable(node):
            self.set_hint("Este valor no se edita escribiendo: usa el clic derecho para las operaciones de estructura",
                          "warn")
            return
        if isinstance(node, bod.ExternalRef):
            if self.on_pick_reference is not None:
                self.on_pick_reference(node, path)
            return
        self.cancel_edit()
        iid = self._iid_by_path[path]
        self.tree.see(iid)
        self.tree.update_idletasks()
        choices = ("true", "false") if isinstance(node, bod.Bool) else None
        suggest = self.suggest if isinstance(node, bod.HashedString) else None
        on_edit_text = self.on_edit_text

        def commit(text: str) -> str | None:
            error = on_edit_text(node, path, text)
            if error is not None:
                self.set_hint(error, "error")
            return error

        def changed(text: str) -> None:
            if self.hint is None:
                return
            valid, message = self.hint(node, path, text)
            self.set_hint(message, "ok" if valid else "error")

        self.editor = InlineEditor(
            self.tree,
            iid,
            edits.editable_text(node),
            on_commit=commit,
            on_close=self._editor_closed,
            on_change=changed,
            choices=choices,
            suggest=suggest,
        )

    def _editor_closed(self) -> None:
        self.tree.focus_set()
        self._show_selection_hint()

    def _on_context_menu(self, event: tk.Event) -> None:
        iid = self.tree.identify_row(event.y)
        if not iid or iid not in self._items or len(self._items[iid]) != 2:
            return
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        node, path = self._items[iid]
        menu = tk.Menu(self, tearoff=False)
        if isinstance(node, bod.ExternalRef):
            menu.add_command(label="Ir al destino", command=lambda: self.on_follow_ref(node.identity))
            menu.add_command(label="Cambiar referencia…", accelerator="F2", command=self.begin_edit)
        elif edits.is_editable(node):
            menu.add_command(label="Editar", accelerator="F2", command=self.begin_edit)
        if path in self.edited_paths and self.on_revert_property is not None:
            menu.add_command(label="Revertir esta propiedad", command=lambda: self.on_revert_property(path))
        self._add_structure_entries(menu, node, path)
        menu.add_separator()
        menu.add_command(label="Copiar valor", command=lambda: self._copy(self._value_text(node)))
        menu.add_command(label="Copiar ruta de la propiedad", command=lambda: self._copy(bod.path_label(self.document, path)))
        menu.tk_popup(event.x_root, event.y_root)

    def structure_actions(self, node: object, path: tuple) -> list[str]:
        """Acciones estructurales que admite la fila (decisiones de la fase 5)."""
        if self.document is None or self.on_structure is None:
            return []
        actions = []
        found = edits.structural_parent(self.document, path)
        if found is not None:
            container, _node = found
            actions += ["duplicate", "remove"]
            if path[-1] > 0:
                actions.append("up")
            if path[-1] < len(container.items) - 1:  # type: ignore[attr-defined]
                actions.append("down")
        if edits.can_null(self.document, path):
            actions.append("null")
        if isinstance(node, bod.Null) and path:
            parent = bod.resolve(self.document, path[:-1])
            if not isinstance(parent, bod.BodTuple) and not (isinstance(parent, bod.Pair) and path[-1] == 0):
                actions.append("fill")
        return actions

    def _add_structure_entries(self, menu: tk.Menu, node: object, path: tuple) -> None:
        actions = self.structure_actions(node, path)
        if not actions:
            return
        menu.add_separator()
        labels = {
            "duplicate": ("Duplicar elemento", "Ctrl+D"),
            "remove": ("Eliminar elemento", "Supr"),
            "up": ("Subir", "Alt+↑"),
            "down": ("Bajar", "Alt+↓"),
            "null": ("Poner a nulo", ""),
            "fill": ("Rellenar con un objeto…", ""),
        }
        assert self.on_structure is not None
        for action in actions:
            label, accelerator = labels[action]
            menu.add_command(
                label=label,
                accelerator=accelerator,
                command=lambda action=action: self.on_structure(action, path),  # type: ignore[misc]
            )

    def _structure_key(self, action: str) -> str | None:
        if self.editing:
            return None
        selected = self.selected()
        if selected is None:
            return "break"
        node, path = selected
        if action in self.structure_actions(node, path) and self.on_structure is not None:
            self.on_structure(action, path)
        return "break"

    def _copy(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
