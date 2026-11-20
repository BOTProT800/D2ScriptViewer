# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Pestaña «Script»: cabecera y tabla de símbolos de un script compilado (tipo 0).

El cuerpo (miembros, funciones desensambladas y estados) se ve y se parchea en el
panel de propiedades.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..formats.script import ScriptHeader
from ..i18n import N_, _, term
from . import theme


#: El texto de la pestaña sin script; se muestra con :func:`.i18n.term`.
NO_SCRIPT = N_("Selecciona un script (tipo 0).")


class ScriptView(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Panel.TFrame", padding=8)
        self.summary_var = tk.StringVar(value=term(NO_SCRIPT))
        ttk.Label(self, textvariable=self.summary_var, style="Panel.TLabel", wraplength=420, justify="left").pack(
            fill="x", pady=(0, 6)
        )
        frame, self.tree = theme.scrolled(
            self, lambda parent: ttk.Treeview(parent, columns=("hash", "text"), show="headings", selectmode="browse")
        )
        frame.pack(fill="both", expand=True)
        self.tree.heading("hash", text=_("Hash"))
        self.tree.heading("text", text=_("Símbolo"))
        self.tree.column("hash", width=150, stretch=False)
        self.tree.column("text", width=260, stretch=True)

    def clear(self, message: str | None = None) -> None:
        self.summary_var.set(term(NO_SCRIPT) if message is None else message)
        self.tree.delete(*self.tree.get_children())

    def show(self, header: ScriptHeader, blob_size: int) -> None:
        self.tree.delete(*self.tree.get_children())
        self.summary_var.set(
            _("Versión {version} · {symbols:,} símbolos · cuerpo de {size:,} bytes a partir de 0x{offset:X}. "
              "Los miembros y el código desensamblado están en el panel central.").format(
                version=header.version, symbols=len(header.symbols), size=blob_size - header.body_offset,
                offset=header.body_offset)
        )
        for symbol in header.symbols:
            self.tree.insert("", "end", values=(f"{symbol.hash:016X}", symbol.text))
