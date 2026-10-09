# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Panel de propiedades: el árbol BOD de un objeto con columnas Nombre | Tipo | Valor.

Los hijos se insertan al abrir cada nodo, y las listas largas se reparten en
tramos de :data:`CHUNK` elementos para que abrir una nunca congele la ventana.

Edición: doble clic o F2 abre un editor en la celda (Intro confirma, Escape
cancela). En una referencia ``FC``, doble clic e Intro navegan al destino y F2
abre el selector de objetos. La validación y el cambio los hace el núcleo a
través de los callbacks que recibe el panel.

Búsqueda en el objeto (fase 10): una barra bajo el título con un campo por
columna (Nombre, Tipo y Valor). :func:`search.find_in_tree` da las rutas en el
orden de las filas, que es el lexicográfico de las rutas, y el panel recorre los
resultados de uno en uno con :meth:`reveal`.

Ir a una ruta (fase 11): una barra «Ir a», oculta hasta Ctrl+G, entre la de
búsqueda y el árbol. El panel solo muestra el campo y el resultado; la ruta la
analiza y la resuelve la aplicación con el núcleo (``on_goto``). Un mensaje
puesto al saltar se retiene (``set_hint(..., hold=True)``): la selección que
provoca el salto llega después por la cola de eventos y no lo pisa.
"""

from __future__ import annotations

import tkinter as tk
from bisect import bisect_left, bisect_right
from tkinter import ttk
from typing import Callable

from .. import edits, search
from ..formats import bod, script
from ..wording import count as count_text
from . import theme
from .editors import InlineEditor

CHUNK = 500
_DUMMY = "dummy"
#: Milisegundos sin teclear antes de recalcular la búsqueda.
SEARCH_DELAY = 200

RefLabel = Callable[[tuple[int, int]], str]
#: (nodo, ruta, texto) → mensaje de error, o ``None`` si se aplicó o se descartó.
EditText = Callable[[object, tuple, str], "str | None"]
#: (nodo, ruta, texto) → (válido, pista).
Hint = Callable[[object, tuple, str], "tuple[bool, str]"]

HINT_STYLES = {"info": "PanelMuted.TLabel", "ok": "HintOk.TLabel", "error": "HintError.TLabel", "warn": "HintWarn.TLabel"}


def _tk_index(text: str, index: int) -> int:
    """Posición de ``text[index]`` para un widget de Tk 8.6, que cuenta en UTF-16: los caracteres
    fuera del plano básico (un emoji) ocupan dos posiciones."""
    if tk.TkVersion >= 9:
        return index
    return index + sum(1 for char in text[:index] if ord(char) > 0xFFFF)


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
        on_goto: Callable[[str], None] | None = None,
        on_goto_cancel: Callable[[], None] | None = None,
        full_label: Callable[[tuple], str] | None = None,
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
        #: Intro en la barra «Ir a» (fase 11), con el texto escrito, y Escape, que anula un salto pendiente.
        self.on_goto = on_goto
        self.on_goto_cancel = on_goto_cancel
        #: ``objeto · propiedad`` de una ruta, para «Copiar ruta completa».
        self.full_label = full_label
        self.document: bod.BodDocument | None = None
        self.edited_paths: set[tuple] = set()
        self.editor: InlineEditor | None = None
        #: iid → (nodo, ruta) o, para un tramo, (contenedor, ruta, inicio, fin).
        self._items: dict[str, tuple] = {}
        self._iid_by_path: dict[tuple, str] = {}
        self._populated: set[str] = set()
        #: Resultados de la búsqueda en el objeto, en el orden de las filas, y su posición.
        self.search_results: list[tuple] = []
        self._search_rank: dict[tuple, int] = {}
        self._search_after: str | None = None
        self._search_types: list[str] | None = None
        #: Fila (iid, o "" sin selección) cuya selección no borra la pista retenida.
        self._hint_hold: str | None = None
        #: Si la pista retenida es de la barra «Ir a»: Escape o un salto correcto la retiran; un aviso
        #: de otro origen (la clave repetida tras Ctrl+D) sigue hasta que se elige otra fila.
        self._hint_from_goto = False

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
        self._build_search_bar()
        self._build_goto_bar()

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
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<F3>", lambda _event: self.next_result() or "break")
        self.tree.bind("<Shift-F3>", lambda _event: self.previous_result() or "break")
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

    def _build_search_bar(self) -> None:
        self.search_name_var = tk.StringVar()
        self.search_type_var = tk.StringVar(value=search.ANY_TYPE)
        self.search_value_var = tk.StringVar()
        self.search_count_var = tk.StringVar(value="")
        bar = ttk.Frame(self, style="Panel.TFrame")
        bar.pack(fill="x", pady=(0, 6))
        self.search_bar = bar
        ttk.Label(bar, text="Nombre", style="PanelMuted.TLabel").grid(row=0, column=0, sticky="w")
        self.search_name = ttk.Entry(bar, textvariable=self.search_name_var, width=8)
        self.search_name.grid(row=0, column=1, sticky="ew", padx=(4, 8))
        ttk.Label(bar, text="Tipo", style="PanelMuted.TLabel").grid(row=0, column=2, sticky="w")
        self.search_type = ttk.Combobox(
            bar, textvariable=self.search_type_var, values=(search.ANY_TYPE,), width=9, height=20,
            postcommand=self._fill_type_choices,
        )
        self.search_type.grid(row=0, column=3, sticky="ew", padx=(4, 8))
        ttk.Label(bar, text="Valor", style="PanelMuted.TLabel").grid(row=0, column=4, sticky="w")
        self.search_value = ttk.Entry(bar, textvariable=self.search_value_var, width=8)
        self.search_value.grid(row=0, column=5, sticky="ew", padx=(4, 8))
        self.search_previous = ttk.Button(bar, text="‹", width=2, style="Small.TButton", command=self.previous_result)
        self.search_previous.grid(row=0, column=6, sticky="ns")
        self.search_next = ttk.Button(bar, text="›", width=2, style="Small.TButton", command=self.next_result)
        self.search_next.grid(row=0, column=7, sticky="ns", padx=(2, 0))
        ttk.Label(bar, textvariable=self.search_count_var, style="PanelMuted.TLabel", anchor="e").grid(
            row=0, column=8, sticky="e", padx=(6, 0)
        )
        # Los campos ceden espacio antes que el resto, pero nunca por debajo de un mínimo legible.
        for column, weight in ((1, 3), (3, 2), (5, 3)):
            bar.columnconfigure(column, weight=weight, minsize=56)
        self.search_fields = (self.search_name, self.search_type, self.search_value)
        self._last_search_field: ttk.Entry = self.search_name
        for field in self.search_fields:
            for sequence in ("<Return>", "<KP_Enter>", "<F3>"):
                field.bind(sequence, lambda _event: self.next_result() or "break")
            for sequence in ("<Shift-Return>", "<Shift-KP_Enter>", "<Shift-F3>"):
                field.bind(sequence, lambda _event: self.previous_result() or "break")
            field.bind("<Escape>", lambda _event: self.tree.focus_set() or "break")
            field.bind("<F2>", lambda _event: self.begin_edit() or "break")
            field.bind("<FocusIn>", lambda _event, field=field: setattr(self, "_last_search_field", field))
        for variable in (self.search_name_var, self.search_type_var, self.search_value_var):
            variable.trace_add("write", lambda *_: self._schedule_search())

    def _build_goto_bar(self) -> None:
        """La barra «Ir a» (fase 11): se construye una vez y se muestra con :meth:`show_goto`."""
        self.goto_var = tk.StringVar()
        bar = ttk.Frame(self, style="Panel.TFrame")
        self.goto_bar = bar
        ttk.Label(bar, text="Ir a", style="PanelMuted.TLabel").pack(side="left")
        self.goto_entry = ttk.Entry(bar, textvariable=self.goto_var)
        self.goto_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        for sequence in ("<Return>", "<KP_Enter>"):
            self.goto_entry.bind(sequence, lambda _event: self._submit_goto() or "break")
        self.goto_entry.bind("<Escape>", lambda _event: self.hide_goto() or "break")

    # --- Ir a una ruta -------------------------------------------------------------------

    @property
    def goto_visible(self) -> bool:
        return bool(self.goto_bar.winfo_manager())

    def show_goto(self, text: str | None = None) -> None:
        """Muestra la barra «Ir a» con el foco en el campo y su texto seleccionado.

        ``text`` sustituye lo escrito; con ``None`` queda el último texto usado.
        """
        self.cancel_edit()
        if not self.goto_visible:
            self.goto_bar.pack(fill="x", pady=(0, 6), after=self.search_bar)
        if text is not None:
            self.goto_var.set(text)
        self.goto_entry.focus_set()
        self.goto_entry.select_range(0, "end")
        self.goto_entry.icursor("end")

    def hide_goto(self) -> None:
        """Escape: oculta la barra, anula el salto pendiente y devuelve el foco al árbol.

        Un error retenido de la barra da paso a la pista de la fila.
        """
        if self.goto_visible:
            self.goto_bar.pack_forget()
        if self.on_goto_cancel is not None:
            self.on_goto_cancel()
        self._release_goto_hint()
        self.tree.focus_set()

    def _release_goto_hint(self) -> None:
        if self._hint_hold is not None and self._hint_from_goto:
            self.set_hint("")
            self._show_selection_hint()

    def _submit_goto(self) -> None:
        if self.on_goto is not None:
            self.on_goto(self.goto_var.get())

    def _focus_is_free(self) -> bool:
        """Si el foco sigue en la barra «Ir a» (o en ningún sitio): tras decodificar en un hilo, el
        usuario puede estar ya escribiendo en otro campo, y no hay que quitárselo."""
        try:
            focused = self.focus_get()
        except KeyError:  # un widget interno de Tk (la lista de un desplegable)
            return False
        return focused is None or focused is self.goto_entry

    def goto_done(self, note: str = "") -> None:
        """Se llegó: la barra se cierra y el árbol recibe el foco, con la fila ya seleccionada."""
        free = self._focus_is_free()
        if self.goto_visible:
            self.goto_bar.pack_forget()
        if free:
            self.tree.focus_set()
        if note:
            self.set_hint(note, "warn", hold=True)
            self._hint_from_goto = True
        else:
            # Un error de un intento anterior sobre esta misma fila ya no vale.
            self._release_goto_hint()

    def goto_failed(self, message: str, start: int = 0, end: int = 0) -> None:
        """La ruta no llegó: la pista dice por qué y el campo señala el tramo culpable."""
        if not self.goto_visible:
            self.goto_bar.pack(fill="x", pady=(0, 6), after=self.search_bar)
        self.set_hint(message, "error", hold=True)
        self._hint_from_goto = True
        if self._focus_is_free():
            self.goto_entry.focus_set()
        if end > start:
            text = self.goto_var.get()
            self.goto_entry.select_range(_tk_index(text, start), _tk_index(text, end))
            self.goto_entry.icursor(_tk_index(text, end))
        else:
            self.goto_entry.select_range(0, "end")

    # --- Contenido -----------------------------------------------------------------------

    def _reset(self, title: str) -> None:
        self.cancel_edit()
        self.tree.delete(*self.tree.get_children())
        self._items = {}
        self._iid_by_path = {}
        self._populated = set()
        self.document = None
        self.edited_paths = set()
        self._search_types = None
        self.title_var.set(title)
        self.set_hint("")

    def show_message(self, title: str, message: str) -> None:
        self._reset(title)
        self.tree.insert("", "end", text=message, tags=("message",))
        self.run_search()

    def show_rows(self, title: str, rows: list[tuple[str, str, str]], hint: str = "") -> None:
        """Filas fijas de solo lectura (cabecera de un script)."""
        self._reset(title)
        for name, type_text, value in rows:
            self.tree.insert("", "end", text=name, values=(type_text, value))
        self.set_hint(hint)
        self.run_search()

    def show_bod(self, title: str, document: bod.BodDocument, edited_paths: set[tuple] | None = None) -> None:
        self._reset(title)
        self.document = document
        self.edited_paths = set(edited_paths or ())
        self._insert_children("", document.root, ())
        self._populated.add("")
        if isinstance(document, script.ScriptTree):
            self.set_hint("Script compilado: doble clic o F2 edita los literales int, float y bool y los valores "
                          "de esos tipos; lo demás es de solo lectura")
        else:
            self.set_hint("Doble clic o F2 para editar un valor · clic derecho para más opciones")
        # Al cambiar de objeto los criterios se conservan y la selección no se mueve.
        self.run_search()

    def set_edited(self, paths: set[tuple]) -> None:
        self.edited_paths = set(paths)
        self.refresh_values()
        self.run_search()

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

    def set_hint(self, text: str, kind: str = "info", *, hold: bool = False) -> None:
        """Escribe la pista bajo el árbol.

        Con ``hold``, el mensaje sigue mientras la fila seleccionada sea la de ahora: la selección
        de un salto llega después por la cola de eventos y, sin esto, lo sustituiría por la pista
        de la fila.
        """
        self.hint_var.set(text)
        self.hint_label.configure(style=HINT_STYLES.get(kind, HINT_STYLES["info"]))
        selection = self.tree.selection()
        self._hint_hold = (selection[0] if selection else "") if hold else None
        self._hint_from_goto = False

    # --- Inserción perezosa --------------------------------------------------------------

    def _value_text(self, node: object) -> str:
        return search.row_value_text(node, self.ref_label)

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
            self._update_search_count()

    # --- Búsqueda en el objeto -----------------------------------------------------------

    def focus_search(self) -> None:
        """Ctrl+F: lleva el foco al último campo usado de la barra, con su texto seleccionado."""
        self.cancel_edit()
        field = self._last_search_field
        field.focus_set()
        field.select_range(0, "end")
        field.icursor("end")

    def _fill_type_choices(self) -> None:
        """Los tipos del objeto abierto, calculados al desplegar la lista."""
        if self._search_types is None:
            self._search_types = search.tree_types(self.document) if self.document is not None else []
        self.search_type.configure(values=(search.ANY_TYPE, *self._search_types))

    def _query(self) -> tuple[str, str, str]:
        return self.search_name_var.get(), self.search_type_var.get(), self.search_value_var.get()

    def _schedule_search(self) -> None:
        self.cancel_pending()
        self._search_after = self.after(SEARCH_DELAY, lambda: self.run_search(move=True))

    def cancel_pending(self) -> None:
        """Anula el recálculo programado al teclear (al cerrar la ventana)."""
        if self._search_after is not None:
            self.after_cancel(self._search_after)
            self._search_after = None

    def flush_search(self) -> None:
        """Recalcula ya, sin mover la selección, si había un recálculo pendiente de lo tecleado.

        Antes de un salto (fase 11): el temporizador, al vencer, iría al primer resultado.
        """
        if self._search_after is not None:
            self.run_search()

    def run_search(self, move: bool = False) -> None:
        """Recalcula los resultados. Con ``move`` (al escribir) va al primero desde la fila actual."""
        self.cancel_pending()
        if self.document is None:
            self.search_results = []
        else:
            self.search_results = search.find_in_tree(self.document, *self._query(), ref_label=self.ref_label)
        self._search_rank = {path: index for index, path in enumerate(self.search_results)}
        current = self._selected_path()
        if move and self.search_results and current not in self._search_rank:
            self._go_to_result(self._step(forward=True))
        self._update_search_count()

    def next_result(self) -> None:
        if self.search_results:
            self._go_to_result(self._step(forward=True))

    def previous_result(self) -> None:
        if self.search_results:
            self._go_to_result(self._step(forward=False))

    def _step(self, forward: bool) -> int:
        """Índice del resultado siguiente o anterior a la fila seleccionada, con vuelta al principio."""
        results = self.search_results
        anchor = self._anchor()
        if anchor is None:
            return 0 if forward else len(results) - 1
        path, is_row = anchor
        if forward:
            index = bisect_right(results, path) if is_row else bisect_left(results, path)
            return index if index < len(results) else 0
        index = bisect_left(results, path) - 1
        return index if index >= 0 else len(results) - 1

    def _anchor(self) -> tuple[tuple, bool] | None:
        """Ruta de la fila seleccionada y si es un valor; un tramo cuenta como su primer elemento."""
        selection = self.tree.selection()
        item = self._items.get(selection[0]) if selection else None
        if item is None:
            return None
        if len(item) == 4:
            _node, path, start, _end = item
            return path + (start,), False
        return item[1], True

    def _selected_path(self) -> tuple | None:
        selected = self.selected()
        return selected[1] if selected else None

    def _go_to_result(self, index: int) -> None:
        self.cancel_edit()
        self.reveal(self.search_results[index])

    def _update_search_count(self) -> None:
        if self.document is None or search.is_empty_query(*self._query()):
            text = ""
        elif not self.search_results:
            text = "Sin resultados"
        else:
            rank = self._search_rank.get(self._selected_path())  # type: ignore[arg-type]
            total = len(self.search_results)
            text = f"{rank + 1:,} de {total:,}" if rank is not None else count_text(total, "resultado")
        self.search_count_var.set(text)

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

    def _on_select(self, _event: object = None) -> None:
        self._update_search_count()
        self._show_selection_hint()

    def _show_selection_hint(self) -> None:
        if self.editing or self.document is None:
            return
        if self._hint_hold is not None:
            selection = self.tree.selection()
            if (selection[0] if selection else "") == self._hint_hold:
                return
            self._hint_hold = None
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
        elif isinstance(node, bod.Note):
            self.set_hint("Solo lectura: en los scripts solo se editan los literales int, float y bool y los "
                          "valores de esos tipos, sin cambiar tamaños")
        elif edits.is_editable(node):
            self.set_hint("Doble clic o F2 para editar" + structure)
        elif structure:
            text = structure.removeprefix(" · ")
            self.set_hint(text[:1].upper() + text[1:])
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
        if isinstance(self.document, script.ScriptTree) and not isinstance(node, script.EDITABLE_VALUES):
            self.set_hint("Solo lectura: en los scripts solo se editan los literales int, float y bool y los "
                          "valores de esos tipos, sin cambiar tamaños", "warn")
            return
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
        menu = self.context_menu(self.tree.identify_row(event.y))
        if menu is not None:
            menu.tk_popup(event.x_root, event.y_root)

    def context_menu(self, iid: str) -> tk.Menu | None:
        """El menú del clic derecho sobre la fila ``iid``, que queda seleccionada."""
        if not iid or iid not in self._items or len(self._items[iid]) != 2:
            return None
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
        if self.full_label is not None:
            full_label = self.full_label
            menu.add_command(label="Copiar ruta completa", command=lambda: self._copy(full_label(path)))
        return menu

    def structure_actions(self, node: object, path: tuple) -> list[str]:
        """Acciones estructurales que admite la fila (decisiones de la fase 5)."""
        if self.document is None or self.on_structure is None or isinstance(self.document, script.ScriptTree):
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
