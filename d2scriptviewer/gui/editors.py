# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Editores de valores: edición en la propia celda y selector de objetos para las referencias."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..document import Document
from ..formats.obsp import identity_text
from . import theme

#: Devuelve un mensaje de error para dejar el editor abierto, o ``None`` para cerrarlo.
Commit = Callable[[str], "str | None"]


class InlineEditor:
    """Un ``Entry`` o ``Combobox`` colocado encima de la celda «Valor» de un ``Treeview``.

    Intro confirma, Escape cancela y perder el foco cancela. Mientras se escribe,
    ``on_change`` recibe el texto para mostrar una pista (rango, redondeo, hash…).
    """

    def __init__(
        self,
        tree: ttk.Treeview,
        iid: str,
        initial: str,
        *,
        on_commit: Commit,
        on_close: Callable[[], None],
        on_change: Callable[[str], None] | None = None,
        choices: tuple[str, ...] | None = None,
        suggest: Callable[[str], list[str]] | None = None,
    ) -> None:
        self.tree = tree
        self.iid = iid
        self.on_commit = on_commit
        self.on_close = on_close
        self.on_change = on_change
        self.suggest = suggest
        self.closed = False
        self.var = tk.StringVar(value=initial)
        if choices is not None:
            self.widget: ttk.Entry = ttk.Combobox(tree, textvariable=self.var, values=choices, state="readonly")
            self.widget.bind("<<ComboboxSelected>>", lambda _event: self.commit())
        elif suggest is not None:
            self.widget = ttk.Combobox(tree, textvariable=self.var, values=suggest(initial), height=14)
            self.widget.bind("<<ComboboxSelected>>", lambda _event: self._changed())
        else:
            self.widget = ttk.Entry(tree, textvariable=self.var)
        self.widget.bind("<Return>", lambda _event: self.commit() or "break")
        self.widget.bind("<KP_Enter>", lambda _event: self.commit() or "break")
        self.widget.bind("<Escape>", lambda _event: self.cancel() or "break")
        self.widget.bind("<FocusOut>", lambda _event: self.widget.after(150, self._check_focus))
        self.var.trace_add("write", lambda *_: self._changed())
        self.place()
        self.widget.focus_set()
        if isinstance(self.widget, ttk.Entry) and choices is None:
            self.widget.select_range(0, "end")
            self.widget.icursor("end")
        self._changed()

    def place(self) -> bool:
        box = self.tree.bbox(self.iid, "value")
        if not box:
            return False
        x, y, width, height = box
        self.widget.place(x=x, y=y, width=max(width, 160), height=height)
        return True

    def _changed(self) -> None:
        text = self.var.get()
        if self.suggest is not None and isinstance(self.widget, ttk.Combobox):
            self.widget.configure(values=self.suggest(text))
        if self.on_change is not None:
            self.on_change(text)

    def _check_focus(self) -> None:
        if self.closed:
            return
        try:
            focused = str(self.widget.tk.call("focus"))
        except tk.TclError:
            focused = ""
        # El desplegable de un Combobox es un hijo suyo: no cuenta como perder el foco.
        if not focused.startswith(str(self.widget)):
            self.cancel()

    def commit(self) -> None:
        if self.closed:
            return
        error = self.on_commit(self.var.get())
        if error is None:
            self.close()

    def cancel(self) -> None:
        self.close()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.widget.destroy()
        self.on_close()


class ReferencePicker(tk.Toplevel):
    """Diálogo modal para elegir el objeto al que apunta una referencia ``FC``."""

    LIMIT = 800

    def __init__(self, master: tk.Misc, document: Document, current: tuple[int, int], title: str) -> None:
        super().__init__(master)
        self.title("Cambiar referencia — D2ScriptViewer")
        self.geometry("820x540")
        self.configure(bg=theme.BACKGROUND)
        self.transient(master)
        self.document = document
        self.result: tuple[int, int] | None = None
        self.filter_var = tk.StringVar()
        self.status_var = tk.StringVar()

        current_info = document.object_by_identity(current)
        current_text = current_info.label() if current_info else "(no existe)"
        ttk.Label(self, text=title, style="TLabel", padding=(14, 12, 14, 0), font=("Segoe UI Semibold", 11)).pack(anchor="w")
        ttk.Label(
            self,
            text=f"Ahora apunta a: {current_text}  [{identity_text(*current)}]",
            style="Muted.TLabel",
            padding=(14, 2, 14, 8),
        ).pack(anchor="w")
        top = ttk.Frame(self, padding=(14, 0, 14, 6))
        top.pack(fill="x")
        ttk.Label(top, text="Filtrar").pack(side="left")
        entry = ttk.Entry(top, textvariable=self.filter_var)
        entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        frame, self.tree = theme.scrolled(
            self,
            lambda parent: ttk.Treeview(parent, columns=("path", "kind", "identity"), show="headings", selectmode="browse"),
        )
        frame.pack(fill="both", expand=True, padx=14)
        for column, heading, width in (("path", "Objeto", 380), ("kind", "Tipo", 150), ("identity", "Identidad", 210)):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, stretch=column == "path")
        self.tree.bind("<Double-1>", lambda _event: self.accept())
        self.tree.bind("<Return>", lambda _event: self.accept())

        bottom = ttk.Frame(self, padding=(14, 8, 14, 12))
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")
        ttk.Button(bottom, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(bottom, text="Aceptar", style="Accent.TButton", command=self.accept).pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _event: self.destroy())
        self.filter_var.trace_add("write", lambda *_: self.refresh())
        if current_info is not None:
            self.filter_var.set(current_info.path)
        else:
            self.refresh()
        entry.focus_set()

    def refresh(self) -> None:
        needle = self.filter_var.get().strip().replace("\\", "/").casefold()
        self.tree.delete(*self.tree.get_children())
        shown = 0
        matches = 0
        for info in self.document.objects:
            if needle and needle not in info.path.casefold() and needle not in info.name.casefold():
                continue
            matches += 1
            if shown < self.LIMIT:
                self.tree.insert(
                    "", "end", iid=str(info.position),
                    values=(info.path, info.kind_label, identity_text(*info.identity)),
                )
                shown += 1
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
        extra = f" (se muestran {self.LIMIT}; afina el filtro)" if matches > shown else ""
        self.status_var.set(f"{matches:,} objetos{extra}")

    def accept(self) -> None:
        selection = self.tree.selection()
        if selection:
            self.result = self.document.objects[int(selection[0])].identity
        self.destroy()

    def choose(self) -> tuple[int, int] | None:
        """Muestra el diálogo y espera; devuelve la identidad elegida o ``None``."""
        self.grab_set()
        self.wait_window()
        return self.result
