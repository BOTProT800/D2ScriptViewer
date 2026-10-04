# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Panel de objetos: árbol por carpeta del editor, por ruta o por tipo, con filtros.

Los grupos se insertan vacíos y se rellenan al abrirlos, así que los 7 862 objetos
nunca entran a la vez en el ``Treeview``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..document import Document, ObjectInfo
from ..formats.obsp import kind_name
from . import theme

GROUP_MODES = ("Carpeta", "Ruta", "Tipo")
ALL_TYPES = "Todos los tipos"
#: Con tan pocos resultados se abren todos los grupos al filtrar.
AUTO_EXPAND_LIMIT = 150
_DUMMY = "dummy"


class _Group:
    __slots__ = ("label", "groups", "objects", "iid", "count", "populated")

    def __init__(self, label: str) -> None:
        self.label = label
        self.groups: dict[str, _Group] = {}
        self.objects: list[int] = []
        self.iid = ""
        self.count = 0
        self.populated = False


class ObjectTree(ttk.Frame):
    def __init__(self, master: tk.Misc, on_select: Callable[[int], None]) -> None:
        super().__init__(master, style="Panel.TFrame", padding=10)
        self.on_select = on_select
        self.document: Document | None = None
        self.modified: set[int] = set()
        self._root = _Group("")
        self._groups_by_iid: dict[str, _Group] = {}
        self._last_reported: int | None = None
        self._pending_refresh: str | None = None

        self.group_var = tk.StringVar(value=GROUP_MODES[0])
        self.type_var = tk.StringVar(value=ALL_TYPES)
        self.class_var = tk.StringVar()
        self.filter_var = tk.StringVar()
        self.count_var = tk.StringVar(value="Sin archivo")

        ttk.Label(self, text="OBJETOS", style="Section.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(self, textvariable=self.count_var, style="PanelMuted.TLabel").grid(row=0, column=2, columnspan=2, sticky="e")

        ttk.Label(self, text="Agrupar", style="PanelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(self, textvariable=self.group_var, values=GROUP_MODES, state="readonly", width=9).grid(
            row=1, column=1, sticky="ew", padx=(6, 8), pady=(8, 0)
        )
        ttk.Label(self, text="Tipo", style="PanelMuted.TLabel").grid(row=1, column=2, sticky="w", pady=(8, 0))
        self.type_box = ttk.Combobox(self, textvariable=self.type_var, values=(ALL_TYPES,), state="readonly", width=22)
        self.type_box.grid(row=1, column=3, sticky="ew", padx=(6, 0), pady=(8, 0))

        ttk.Label(self, text="Clase", style="PanelMuted.TLabel").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.class_box = ttk.Combobox(self, textvariable=self.class_var, values=())
        self.class_box.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(6, 0), pady=(6, 0))
        ttk.Label(self, text="Filtrar", style="PanelMuted.TLabel").grid(row=3, column=0, sticky="w", pady=(6, 8))
        self.filter_entry = ttk.Entry(self, textvariable=self.filter_var)
        self.filter_entry.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(6, 0), pady=(6, 8))

        frame, self.tree = theme.scrolled(
            self, lambda parent: ttk.Treeview(parent, columns=("kind", "size"), show="tree headings", selectmode="browse")
        )
        frame.grid(row=4, column=0, columnspan=4, sticky="nsew")
        self.tree.heading("#0", text="Objeto")
        self.tree.heading("kind", text="Tipo")
        self.tree.heading("size", text="Tamaño")
        self.tree.column("#0", width=190, minwidth=120, stretch=True)
        self.tree.column("kind", width=105, minwidth=60, stretch=False)
        self.tree.column("size", width=62, minwidth=50, stretch=False, anchor="e")
        self.tree.tag_configure("group", foreground=theme.HEADING)
        self.tree.tag_configure("modified", foreground=theme.MODIFIED)
        self.tree.tag_configure("script", foreground="#93c5fd")
        self.columnconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)

        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        for variable in (self.group_var, self.type_var, self.class_var, self.filter_var):
            variable.trace_add("write", lambda *_: self._schedule_refresh())

    # --- Datos ---------------------------------------------------------------------------

    def set_document(self, document: Document | None) -> None:
        self.document = document
        self.modified = set()
        self._last_reported = None
        if document is None:
            self.type_box.configure(values=(ALL_TYPES,))
            self.class_box.configure(values=())
        else:
            kinds = sorted({info.entry.kind for info in document.objects})
            self.type_box.configure(values=(ALL_TYPES, *[f"{kind} · {kind_name(kind)}" for kind in kinds]))
            classes = sorted({info.class_name for info in document.objects if info.class_name}, key=str.casefold)
            self.class_box.configure(values=classes)
        self._reset_filters()
        self.refresh()

    def set_modified(self, positions: set[int]) -> None:
        changed = positions ^ self.modified
        self.modified = set(positions)
        if self.document is None:
            return
        for position in changed:
            iid = f"o{position}"
            if self.tree.exists(iid):
                info = self.document.objects[position]
                self.tree.item(iid, text=self._leaf_text(info), tags=self._leaf_tags(info))

    def _reset_filters(self) -> None:
        for variable, value in ((self.type_var, ALL_TYPES), (self.class_var, ""), (self.filter_var, "")):
            if variable.get() != value:
                variable.set(value)

    def cancel_pending(self) -> None:
        if self._pending_refresh is not None:
            self.after_cancel(self._pending_refresh)
            self._pending_refresh = None

    def _schedule_refresh(self) -> None:
        if self._pending_refresh is not None:
            self.after_cancel(self._pending_refresh)
        self._pending_refresh = self.after(200, self.refresh)

    def _kind_filter(self) -> int | None:
        value = self.type_var.get()
        if value == ALL_TYPES or " · " not in value:
            return None
        return int(value.split(" · ", 1)[0])

    def _is_visible(self, info: ObjectInfo, kind: int | None, class_text: str, needle: str) -> bool:
        if kind is not None and info.entry.kind != kind:
            return False
        if class_text and class_text not in info.class_name.casefold():
            return False
        if needle:
            return any(needle in value.replace("\\", "/").casefold() for value in (info.path, info.name, info.folder))
        return True

    def _group_keys(self, info: ObjectInfo) -> list[str]:
        # En el juego toda ruta es «directorio/objeto»: el directorio siempre es el
        # último nivel de agrupación, para que ningún grupo tenga miles de objetos.
        directory = info.path.split("/")[:-1] or ["(raíz)"]
        mode = self.group_var.get()
        if mode == "Ruta":
            return directory
        if mode == "Tipo":
            return [f"{info.entry.kind} · {info.kind_label}", *directory]
        folder = info.folder.split("\\") if info.folder else ["(sin carpeta)"]
        return [*folder, *directory]

    def _leaf_text(self, info: ObjectInfo) -> str:
        text = info.path.rsplit("/", 1)[-1]
        return ("● " if info.position in self.modified else "") + text

    def _leaf_tags(self, info: ObjectInfo) -> tuple[str, ...]:
        if info.position in self.modified:
            return ("modified",)
        return ("script",) if info.is_script else ()

    # --- Árbol ---------------------------------------------------------------------------

    def refresh(self) -> None:
        self.cancel_pending()
        self.tree.delete(*self.tree.get_children())
        self._groups_by_iid = {}
        self._root = _Group("")
        if self.document is None:
            self.count_var.set("Sin archivo")
            return
        kind = self._kind_filter()
        class_text = self.class_var.get().strip().casefold()
        needle = self.filter_var.get().strip().replace("\\", "/").casefold()
        visible = 0
        for info in self.document.objects:
            if not self._is_visible(info, kind, class_text, needle):
                continue
            visible += 1
            group = self._root
            group.count += 1
            for key in self._group_keys(info):
                child = group.groups.get(key)
                if child is None:
                    child = group.groups[key] = _Group(key)
                child.count += 1
                group = child
            group.objects.append(info.position)
        self._fill("", self._root)
        total = len(self.document.objects)
        self.count_var.set(f"{visible:,} de {total:,}" if visible != total else f"{total:,} objetos")
        if visible and visible <= AUTO_EXPAND_LIMIT and (kind is not None or class_text or needle):
            self._expand_all(self._root)
        self._last_reported = None

    def _fill(self, parent: str, group: _Group) -> None:
        group.populated = True
        objects = self.document.objects if self.document else []
        for key in sorted(group.groups, key=str.casefold):
            child = group.groups[key]
            child.iid = self.tree.insert(parent, "end", text=f"{child.label}  ({child.count:,})", tags=("group",))
            self._groups_by_iid[child.iid] = child
            self.tree.insert(child.iid, "end", text="…", tags=(_DUMMY,))
        for position in sorted(group.objects, key=lambda item: objects[item].path.casefold()):
            info = objects[position]
            self.tree.insert(
                parent,
                "end",
                iid=f"o{position}",
                text=self._leaf_text(info),
                values=(info.kind_label, theme.human_size(info.entry.size)),
                tags=self._leaf_tags(info),
            )

    def _populate(self, group: _Group) -> None:
        if group.populated:
            return
        self.tree.delete(*self.tree.get_children(group.iid))
        self._fill(group.iid, group)

    def _expand_all(self, group: _Group) -> None:
        for child in group.groups.values():
            self._populate(child)
            self.tree.item(child.iid, open=True)
            self._expand_all(child)

    def _on_open(self, _event: object = None) -> None:
        group = self._groups_by_iid.get(self.tree.focus())
        if group is not None:
            self._populate(group)

    def _on_select(self, _event: object = None) -> None:
        selection = self.tree.selection()
        if not selection or not selection[0].startswith("o"):
            return
        position = int(selection[0][1:])
        if position == self._last_reported:
            return
        self._last_reported = position
        self.on_select(position)

    def select_position(self, position: int) -> None:
        """Muestra y selecciona un objeto sin volver a avisar a ``on_select``."""
        if self.document is None:
            return
        info = self.document.objects[position]
        kind = self._kind_filter()
        class_text = self.class_var.get().strip().casefold()
        needle = self.filter_var.get().strip().replace("\\", "/").casefold()
        if not self._is_visible(info, kind, class_text, needle):
            self._reset_filters()
            self.refresh()
        group = self._root
        for key in self._group_keys(info):
            group = group.groups[key]
            self._populate(group)
            self.tree.item(group.iid, open=True)
        iid = f"o{position}"
        self._last_reported = position
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        self.tree.see(iid)
