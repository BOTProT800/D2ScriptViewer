# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Panel de detalles: metadatos, hexadecimal, referencias y script del objeto seleccionado."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..binary import hex_dump
from ..document import Document, ObjectInfo
from ..formats.obsp import identity_text
from ..references import FileIndexes
from . import theme
from .script_view import ScriptView

Navigate = Callable[[int, "tuple | None"], None]


class DetailsPanel(ttk.Frame):
    def __init__(self, master: tk.Misc, *, on_navigate: Navigate) -> None:
        super().__init__(master, style="Panel.TFrame", padding=10)
        self.on_navigate = on_navigate
        self.document: Document | None = None
        self.info: ObjectInfo | None = None
        self.indexes: FileIndexes | None = None
        self._hex_dirty = True
        self._ref_targets: dict[str, tuple[int, tuple | None]] = {}

        ttk.Label(self, text="DETALLES", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        info_frame, self.info_text = theme.scrolled(self.notebook, lambda parent: theme.text_widget(parent, height=12))
        self.info_text.configure(wrap="word", font=("Segoe UI", 10))
        self.notebook.add(info_frame, text="Detalles")

        hex_tab = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.hex_var = tk.StringVar(value="")
        ttk.Label(hex_tab, textvariable=self.hex_var, style="PanelMuted.TLabel").pack(anchor="w", pady=(4, 4))
        hex_frame, self.hex_text = theme.scrolled(hex_tab, lambda parent: theme.text_widget(parent), horizontal=True)
        hex_frame.pack(fill="both", expand=True)
        self.notebook.add(hex_tab, text="Hex")

        refs_tab = ttk.Panedwindow(self.notebook, orient="vertical")
        self.refs_out = self._ref_tree(refs_tab, "Apunta a", ("Propiedad", "Objeto"))
        self.refs_in = self._ref_tree(refs_tab, "Usado por", ("Objeto", "Propiedad"))
        self.notebook.add(refs_tab, text="Referencias")

        self.script_view = ScriptView(self.notebook)
        self.notebook.add(self.script_view, text="Script")

        self.notebook.bind("<<NotebookTabChanged>>", lambda _event: self._render_hex_if_visible())

    def _ref_tree(self, pane: ttk.Panedwindow, title: str, headings: tuple[str, str]) -> ttk.Treeview:
        container = ttk.Frame(pane, style="Panel.TFrame")
        label_var = tk.StringVar(value=title)
        ttk.Label(container, textvariable=label_var, style="PanelMuted.TLabel").pack(anchor="w", pady=(4, 2))
        frame, tree = theme.scrolled(
            container, lambda parent: ttk.Treeview(parent, columns=("a", "b"), show="headings", selectmode="browse", height=6)
        )
        frame.pack(fill="both", expand=True)
        tree.heading("a", text=headings[0])
        tree.heading("b", text=headings[1])
        tree.column("a", width=200)
        tree.column("b", width=220)
        tree.bind("<Double-1>", lambda _event, widget=tree: self._follow(widget))
        tree.bind("<Return>", lambda _event, widget=tree: self._follow(widget))
        tree.title_var = label_var  # type: ignore[attr-defined]
        tree.base_title = title  # type: ignore[attr-defined]
        pane.add(container, weight=1)
        return tree

    # --- Contenido -----------------------------------------------------------------------

    def clear(self) -> None:
        self.document = None
        self.info = None
        theme.set_text(self.info_text, "")
        theme.set_text(self.hex_text, "")
        self.hex_var.set("")
        for tree in (self.refs_out, self.refs_in):
            tree.delete(*tree.get_children())
        self.script_view.clear()

    def show(self, document: Document, info: ObjectInfo, extra: list[tuple[str, str]] | None = None) -> None:
        self.document = document
        self.info = info
        entry = info.entry
        lines = [
            ("Ruta", info.path),
            ("Nombre", info.name),
            ("Clase", info.class_name or "—"),
            ("Carpeta", info.folder or "—"),
            ("Identidad", identity_text(entry.group, entry.object_id)),
            ("Grupo", str(entry.group)),
            ("Tipo", f"{entry.kind} · {info.kind_label}"),
            ("Offset", f"0x{entry.offset:X} ({entry.offset:,})"),
            ("Tamaño", f"{entry.size:,} bytes"),
            ("Posición en el índice", f"{info.position:,}"),
        ]
        lines.extend(extra or [])
        theme.set_text(self.info_text, "\n".join(f"{key}:  {value}" for key, value in lines))
        self._hex_dirty = True
        self._render_hex_if_visible()
        self.refresh_references()
        if info.is_script:
            try:
                self.script_view.show(document.script_header(info.position), entry.size)
            except Exception as error:  # noqa: BLE001 - se muestra al usuario
                self.script_view.clear(f"No se pudo leer la cabecera: {error}")
        else:
            self.script_view.clear("Este objeto no es un script compilado.")

    def invalidate_hex(self) -> None:
        self._hex_dirty = True
        self._render_hex_if_visible()

    def _render_hex_if_visible(self) -> None:
        if not self._hex_dirty or self.document is None or self.info is None:
            return
        if self.notebook.index("current") != 1:
            return
        self._hex_dirty = False
        blob = self.document.blob(self.info.position)
        modified = self.document.is_modified(self.info.position)
        offset = self.info.entry.offset
        self.hex_var.set(
            f"{len(blob):,} bytes · offsets absolutos en el archivo"
            + (" · versión editada (aún sin guardar)" if modified else "")
        )
        theme.set_text(self.hex_text, hex_dump(blob, offset))

    def set_indexes(self, indexes: FileIndexes | None) -> None:
        self.indexes = indexes
        self.refresh_references()

    def refresh_references(self) -> None:
        self._ref_targets = {}
        for tree in (self.refs_out, self.refs_in):
            tree.delete(*tree.get_children())
        if self.document is None or self.info is None:
            return
        if self.indexes is None:
            for tree in (self.refs_out, self.refs_in):
                tree.title_var.set(f"{tree.base_title} (indexando…)")  # type: ignore[attr-defined]
            return
        document = self.document
        outgoing = self.indexes.references.references_from(self.info.position)
        for reference in outgoing:
            target = document.object_by_identity(reference.target)
            label = target.label() if target else f"(no existe) {identity_text(*reference.target)}"
            iid = self.refs_out.insert("", "end", values=(reference.label, label))
            self._ref_targets[iid] = (target.position, None) if target else (-1, None)
        incoming = self.indexes.references.references_to(self.info.identity)
        for reference in incoming:
            source = document.objects[reference.source]
            iid = self.refs_in.insert("", "end", values=(source.label(), reference.label))
            self._ref_targets[iid] = (reference.source, reference.path)
        self.refs_out.title_var.set(f"Apunta a ({len(outgoing)})")  # type: ignore[attr-defined]
        self.refs_in.title_var.set(f"Usado por ({len(incoming)})")  # type: ignore[attr-defined]

    def _follow(self, tree: ttk.Treeview) -> str:
        selection = tree.selection()
        if selection:
            position, path = self._ref_targets.get(selection[0], (-1, None))
            if position >= 0:
                self.on_navigate(position, path)
        return "break"
