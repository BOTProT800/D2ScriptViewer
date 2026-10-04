# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Ventana de búsqueda global. La búsqueda corre en un hilo y llega por lotes a la cola."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..document import Document
from ..search import SearchHit, SearchOptions, search
from . import theme

Navigate = Callable[[int, "tuple | None"], None]


class SearchWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, document: Document, on_navigate: Navigate) -> None:
        super().__init__(master)
        self.title("Buscar — D2ScriptViewer")
        self.geometry("900x560")
        self.configure(bg=theme.BACKGROUND)
        self.transient(master)
        self.document = document
        self.on_navigate = on_navigate
        self.messages: queue.Queue[tuple[int, str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.token = 0
        self.hits: dict[str, SearchHit] = {}

        self.query_var = tk.StringVar()
        self.metadata_var = tk.BooleanVar(value=True)
        self.values_var = tk.BooleanVar(value=True)
        self.fields_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Escribe un texto o un número y pulsa Intro.")

        top = ttk.Frame(self, padding=(14, 12, 14, 6))
        top.pack(fill="x")
        entry = ttk.Entry(top, textvariable=self.query_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda _event: self.start())
        self.search_button = ttk.Button(top, text="Buscar", style="Accent.TButton", command=self.start)
        self.search_button.pack(side="left", padx=(8, 0))
        self.cancel_button = ttk.Button(top, text="Cancelar", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(8, 0))

        options = ttk.Frame(self, padding=(14, 0, 14, 6))
        options.pack(fill="x")
        ttk.Checkbutton(options, text="Rutas, nombres, carpetas y clases", variable=self.metadata_var).pack(side="left")
        ttk.Checkbutton(options, text="Valores y símbolos", variable=self.values_var).pack(side="left", padx=(12, 0))
        ttk.Checkbutton(options, text="Nombres de campo", variable=self.fields_var).pack(side="left", padx=(12, 0))

        frame, self.tree = theme.scrolled(
            self,
            lambda parent: ttk.Treeview(
                parent, columns=("object", "where", "property", "value"), show="headings", selectmode="browse"
            ),
        )
        frame.pack(fill="both", expand=True, padx=14)
        for column, title, width in (
            ("object", "Objeto", 260),
            ("where", "Dónde", 80),
            ("property", "Propiedad", 230),
            ("value", "Coincidencia", 260),
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, stretch=column != "where")
        self.tree.bind("<Double-1>", lambda _event: self._open_selected())
        self.tree.bind("<Return>", lambda _event: self._open_selected())
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel", padding=(14, 6, 14, 10)).pack(fill="x")

        self.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id: str | None = self.after(100, self._poll)
        entry.focus_set()

    def start(self) -> None:
        text = self.query_var.get().strip()
        if not text:
            return
        self.cancel_event.set()
        self.cancel_event = threading.Event()
        self.token += 1
        token = self.token
        cancel = self.cancel_event
        options = SearchOptions(
            metadata=self.metadata_var.get(), values=self.values_var.get(), field_names=self.fields_var.get()
        )
        self.tree.delete(*self.tree.get_children())
        self.hits = {}
        self.status_var.set(f"Buscando «{text}»…")
        self.search_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        def run() -> None:
            try:
                hits, truncated = search(
                    self.document,
                    text,
                    options,
                    cancel=cancel,
                    on_hits=lambda batch: self.messages.put((token, "hits", batch)),
                )
                self.messages.put((token, "done", (len(hits), truncated, cancel.is_set())))
            except Exception as error:  # noqa: BLE001 - se muestra al usuario
                self.messages.put((token, "error", error))

        threading.Thread(target=run, daemon=True).start()

    def cancel(self) -> None:
        self.cancel_event.set()

    def close(self) -> None:
        self.cancel_event.set()
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        self.destroy()

    def _poll(self) -> None:
        try:
            while True:
                token, kind, payload = self.messages.get_nowait()
                if token != self.token:
                    continue
                if kind == "hits":
                    for hit in payload:  # type: ignore[union-attr]
                        info = self.document.objects[hit.position]
                        iid = self.tree.insert("", "end", values=(info.label(), hit.where, hit.label, hit.text))
                        self.hits[iid] = hit
                    self.status_var.set(f"{len(self.hits):,} resultados…")
                elif kind == "done":
                    count, truncated, cancelled = payload  # type: ignore[misc]
                    suffix = " (búsqueda cancelada)" if cancelled else " (límite alcanzado; afina la búsqueda)" if truncated else ""
                    self.status_var.set(f"{count:,} resultados{suffix}. Doble clic para ir al objeto.")
                    self.search_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                elif kind == "error":
                    self.status_var.set(f"Error: {payload}")
                    self.search_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
        except queue.Empty:
            pass
        if self.winfo_exists():
            self._poll_id = self.after(100, self._poll)

    def _open_selected(self) -> str:
        selection = self.tree.selection()
        if selection and selection[0] in self.hits:
            hit = self.hits[selection[0]]
            self.on_navigate(hit.position, hit.path)
        return "break"
