# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Tema oscuro, el mismo de Darkstractor, y utilidades de presentación."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

BACKGROUND = "#111317"
PANEL = "#1a1e24"
FIELD = "#0f1216"
TREE = "#171b20"
TEXT = "#e7eaf0"
MUTED = "#9299a6"
HEADING = "#aeb5c0"
ACCENT = "#8b5cf6"
SELECTED = "#6d4cc2"
MODIFIED = "#f5a524"
OK = "#4ade80"
WARNING = "#f87171"

#: Color de la columna «Valor» según el tipo.
VALUE_COLORS = {
    "int32": "#7dd3fc",
    "float32": "#67e8f9",
    "bool": "#fca5a5",
    "cadena": "#86efac",
    "nombre": "#bef264",
    "referencia": "#c4b5fd",
    "nulo": MUTED,
}

MONO_FONT = ("Cascadia Mono", 9)


def configure_styles(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BACKGROUND, foreground=TEXT)
    style.configure("TFrame", background=BACKGROUND)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("TLabel", background=BACKGROUND, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
    style.configure("Section.TLabel", background=PANEL, foreground=HEADING, font=("Segoe UI Semibold", 9))
    style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED)
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 18), foreground="#f2f4f8")
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Status.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
    style.configure("StatusOk.TLabel", background=PANEL, foreground=OK, font=("Segoe UI Semibold", 9))
    style.configure("StatusWarn.TLabel", background=PANEL, foreground=MODIFIED, font=("Segoe UI Semibold", 9))
    style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(14, 6), background=ACCENT, foreground="white")
    style.map("Accent.TButton", background=[("active", "#9d72f8"), ("disabled", "#3d344f")])
    style.configure("TButton", font=("Segoe UI", 10), padding=(10, 5), background="#292f38", foreground="#eef0f5")
    style.map("TButton", background=[("active", "#343c48"), ("disabled", "#1f242b")], foreground=[("disabled", "#5b616b")])
    style.configure("TEntry", fieldbackground=FIELD, foreground="#edf0f5", insertcolor="white", padding=5)
    style.configure("TCombobox", fieldbackground=FIELD, foreground="#edf0f5", padding=4, arrowcolor=TEXT)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", FIELD)],
        foreground=[("readonly", "#edf0f5")],
        selectbackground=[("readonly", FIELD)],
    )
    style.configure("TCheckbutton", background=BACKGROUND, foreground="#d7dbe2")
    style.map("TCheckbutton", background=[("active", BACKGROUND)])
    style.configure("Panel.TCheckbutton", background=PANEL, foreground="#d7dbe2")
    style.map("Panel.TCheckbutton", background=[("active", PANEL)])
    style.configure("Treeview", background=TREE, fieldbackground=TREE, foreground="#dfe3ea", rowheight=24, borderwidth=0)
    style.map("Treeview", background=[("selected", SELECTED)], foreground=[("selected", "white")])
    style.configure("Treeview.Heading", background="#242a33", foreground="#cdd2dc", font=("Segoe UI Semibold", 9), relief="flat")
    style.map("Treeview.Heading", background=[("active", "#303744")])
    style.configure("TNotebook", background=PANEL, borderwidth=0)
    style.configure("TNotebook.Tab", background=PANEL, foreground=HEADING, padding=(12, 6))
    style.map("TNotebook.Tab", background=[("selected", "#292f38")], foreground=[("selected", "white")])
    style.configure("Horizontal.TProgressbar", troughcolor="#242a33", background=ACCENT, borderwidth=0)
    style.configure("TPanedwindow", background=BACKGROUND)
    style.configure("Vertical.TScrollbar", background="#292f38", troughcolor=TREE, arrowcolor=TEXT, borderwidth=0)
    style.configure("Horizontal.TScrollbar", background="#292f38", troughcolor=TREE, arrowcolor=TEXT, borderwidth=0)
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECTED)
    root.option_add("*Menu.background", PANEL)
    root.option_add("*Menu.foreground", TEXT)
    root.option_add("*Menu.activeBackground", SELECTED)
    root.option_add("*Menu.activeForeground", "white")
    return style


def text_widget(master: tk.Misc, **options: object) -> tk.Text:
    """Un ``tk.Text`` de solo lectura con los colores del tema."""
    widget = tk.Text(
        master,
        bg="#0d1014",
        fg="#c9d1dc",
        insertbackground="white",
        selectbackground=SELECTED,
        relief="flat",
        padx=8,
        pady=6,
        font=MONO_FONT,
        wrap="none",
        **options,
    )
    widget.configure(state="disabled")
    return widget


def set_text(widget: tk.Text, content: str) -> None:
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.configure(state="disabled")


def scrolled(master: tk.Misc, widget_factory, *, horizontal: bool = False):
    """Crea un widget con barras de desplazamiento dentro de un marco propio."""
    frame = ttk.Frame(master, style="Panel.TFrame")
    widget = widget_factory(frame)
    vertical = ttk.Scrollbar(frame, orient="vertical", command=widget.yview)
    widget.configure(yscrollcommand=vertical.set)
    widget.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    if horizontal:
        bar = ttk.Scrollbar(frame, orient="horizontal", command=widget.xview)
        widget.configure(xscrollcommand=bar.set)
        bar.grid(row=1, column=0, sticky="ew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    return frame, widget


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"
