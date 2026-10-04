# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Ventana «Cambios pendientes»: cada propiedad que difiere de su original, antes → después."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..document import Document
from ..wording import count
from . import theme


class PendingChangesWindow(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        document: Document,
        *,
        ref_label: Callable[[tuple[int, int]], str],
        on_navigate: Callable[[int, "tuple | None"], None],
        on_revert_object: Callable[[int], None],
    ) -> None:
        super().__init__(master)
        self.title("Cambios pendientes — D2ScriptViewer")
        self.geometry("980x460")
        self.configure(bg=theme.BACKGROUND)
        self.transient(master)
        self.document = document
        self.ref_label = ref_label
        self.on_navigate = on_navigate
        self.on_revert_object = on_revert_object
        self.rows: dict[str, tuple[int, tuple]] = {}
        self.summary_var = tk.StringVar()

        ttk.Label(self, textvariable=self.summary_var, padding=(14, 12, 14, 8)).pack(anchor="w")
        frame, self.tree = theme.scrolled(
            self,
            lambda parent: ttk.Treeview(
                parent, columns=("property", "kind", "before", "after"), show="tree headings", selectmode="browse"
            ),
        )
        frame.pack(fill="both", expand=True, padx=14)
        self.tree.heading("#0", text="Objeto")
        self.tree.column("#0", width=230)
        for column, heading, width in (
            ("property", "Propiedad", 230),
            ("kind", "Cambio", 90),
            ("before", "Antes", 190),
            ("after", "Después", 190),
        ):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, stretch=column != "kind")
        self.tree.tag_configure("object", foreground=theme.MODIFIED)
        self.tree.bind("<Double-1>", lambda _event: self._go())
        self.tree.bind("<Return>", lambda _event: self._go())

        bottom = ttk.Frame(self, padding=(14, 8, 14, 12))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Cerrar", command=self.destroy).pack(side="right")
        ttk.Button(bottom, text="Revertir objeto", command=self._revert).pack(side="right", padx=(0, 8))
        ttk.Button(bottom, text="Ir", command=self._go).pack(side="right", padx=(0, 8))
        self.bind("<Escape>", lambda _event: self.destroy())
        self.refresh()

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        changes = self.document.pending_changes(self.ref_label)
        parents: dict[int, str] = {}
        for position, change in changes:
            if position not in parents:
                info = self.document.objects[position]
                parents[position] = self.tree.insert("", "end", text=info.label(), open=True, tags=("object",))
                self.rows[parents[position]] = (position, ())
            iid = self.tree.insert(
                parents[position], "end", values=(change.label, change.kind, change.before, change.after)
            )
            self.rows[iid] = (position, change.path)
        objects = len(parents)
        self.summary_var.set(
            f"{count(len(changes), 'cambio')} en {count(objects, 'objeto')}" if changes else "No hay cambios pendientes."
        )

    def _selected(self) -> tuple[int, tuple] | None:
        selection = self.tree.selection()
        return self.rows.get(selection[0]) if selection else None

    def _go(self) -> str:
        selected = self._selected()
        if selected is not None:
            position, path = selected
            self.on_navigate(position, path or None)
        return "break"

    def _revert(self) -> None:
        selected = self._selected()
        if selected is not None:
            self.on_revert_object(selected[0])
