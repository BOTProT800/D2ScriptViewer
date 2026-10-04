# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Ventana principal: objetos a la izquierda, propiedades en el centro y detalles a la derecha.

El trabajo pesado (abrir, indexar referencias, decodificar objetos grandes y
buscar) corre en hilos que hablan con la interfaz a través de ``self.messages``.
Los hilos nunca tocan Tk: solo encolan mensajes que ``_poll_messages`` atiende.
"""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .. import __version__
from ..document import Document
from ..errors import D2ScriptViewerError
from ..formats.obsp import identity_text
from ..references import Cancelled, FileIndexes, build_indexes
from ..settings import find_default_obsp, load_settings, save_settings
from . import theme
from .details import DetailsPanel
from .object_tree import GROUP_MODES, ObjectTree
from .property_view import PropertyView
from .search_view import SearchWindow

APP_NAME = "D2ScriptViewer"
#: Por encima de este tamaño el objeto se decodifica en un hilo para no congelar la ventana.
SYNC_DECODE_LIMIT = 48 * 1024


class ViewerApp(tk.Tk):
    def __init__(self, initial: Path | None = None, *, auto_open: bool = True, persist_settings: bool = True) -> None:
        super().__init__()
        self.persist_settings = persist_settings
        self.settings = load_settings() if persist_settings else {}
        self.title(f"{APP_NAME} {__version__} — scripts.obsp de Darksiders II Deathinitive Edition")
        geometry = self.settings.get("geometry")
        self.geometry(str(geometry) if isinstance(geometry, str) else "1500x900")
        self.minsize(1100, 640)
        self.configure(bg=theme.BACKGROUND)
        theme.configure_styles(self)

        self.messages: queue.Queue[tuple[str, int, object]] = queue.Queue()
        self.document: Document | None = None
        self.indexes: FileIndexes | None = None
        self.position: int | None = None
        self.history_back: list[int] = []
        self.history_forward: list[int] = []
        self.index_cancel = threading.Event()
        self.tokens = {"open": 0, "index": 0, "decode": 0}
        self.search_window: SearchWindow | None = None
        #: Segundos que tardó en mostrarse el último objeto (para medir el criterio < 1 s).
        self.last_display_seconds = 0.0
        self._display_started = 0.0

        self.summary_var = tk.StringVar(value="Sin archivo")
        self.state_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Abre un scripts.obsp con Archivo → Abrir (Ctrl+O)")
        self.path_var = tk.StringVar(value="")

        self._build_menu()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_id: str | None = self.after(50, self._poll_messages)

        if auto_open:
            path = initial or self._remembered_file() or find_default_obsp()
            if path is not None:
                self.after(10, lambda: self.open_file(path))

    # --- Construcción --------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.file_menu = tk.Menu(menubar, tearoff=False)
        self.file_menu.add_command(label="Abrir…", accelerator="Ctrl+O", command=self.choose_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Salir", command=self._on_close)
        menubar.add_cascade(label="Archivo", menu=self.file_menu)

        search_menu = tk.Menu(menubar, tearoff=False)
        search_menu.add_command(label="Buscar…", accelerator="Ctrl+F", command=self.open_search)
        menubar.add_cascade(label="Buscar", menu=search_menu)

        go_menu = tk.Menu(menubar, tearoff=False)
        go_menu.add_command(label="Atrás", accelerator="Alt+Izquierda", command=self.go_back)
        go_menu.add_command(label="Adelante", accelerator="Alt+Derecha", command=self.go_forward)
        menubar.add_cascade(label="Ir", menu=go_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Acerca de", command=self._about)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        self.configure(menu=menubar)
        self.menubar = menubar

        self.bind_all("<Control-o>", lambda _event: self.choose_file())
        self.bind_all("<Control-f>", lambda _event: self.open_search())
        self.bind_all("<Alt-Left>", lambda _event: self.go_back())
        self.bind_all("<Alt-Right>", lambda _event: self.go_forward())

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(18, 12, 18, 8))
        header.pack(fill="x")
        ttk.Label(header, text="D2SCRIPTVIEWER", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Visor y editor de scripts.obsp — Darksiders II Deathinitive Edition",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w")
        ttk.Label(header, textvariable=self.summary_var, style="Muted.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")
        header.columnconfigure(1, weight=1)

        pane = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=12)
        self.object_tree = ObjectTree(pane, on_select=lambda position: self.navigate(position))
        group_by = self.settings.get("group_by")
        if group_by in GROUP_MODES:
            self.object_tree.group_var.set(str(group_by))
        self.property_view = PropertyView(pane, ref_label=self.ref_label, on_follow_ref=self.follow_reference)
        self.details = DetailsPanel(pane, on_navigate=self.navigate)
        pane.add(self.object_tree, weight=3)
        pane.add(self.property_view, weight=5)
        pane.add(self.details, weight=3)
        self.pane = pane
        # Los pesos solo reparten el espacio sobrante: el reparto inicial se fija a mano.
        self.after_idle(self._place_sashes)

        self.back_button = ttk.Button(self.property_view.toolbar, text="←", width=3, command=self.go_back, state="disabled")
        self.back_button.pack(side="left")
        self.forward_button = ttk.Button(
            self.property_view.toolbar, text="→", width=3, command=self.go_forward, state="disabled"
        )
        self.forward_button.pack(side="left", padx=(4, 0))

        status = ttk.Frame(self, style="Panel.TFrame", padding=(12, 6))
        status.pack(fill="x", side="bottom")
        self.state_label = ttk.Label(status, textvariable=self.state_var, style="Status.TLabel")
        self.state_label.pack(side="left")
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel").pack(side="left", padx=(16, 0))
        ttk.Label(status, textvariable=self.path_var, style="Status.TLabel").pack(side="right")
        self.progress = ttk.Progressbar(status, mode="determinate", length=160, maximum=1)
        self.progress.pack(side="right", padx=(0, 12))
        self.status_frame = status

    def _place_sashes(self) -> None:
        self.update_idletasks()
        width = self.pane.winfo_width()
        if width > 300:
            self.pane.sashpos(0, int(width * 0.30))
            self.pane.sashpos(1, int(width * 0.67))

    # --- Hilos ---------------------------------------------------------------------------

    def _spawn(self, kind: str, work: Callable[[], object]) -> int:
        """Ejecuta ``work`` en un hilo y encola ``(kind, token, resultado o excepción)``."""
        self.tokens[kind] += 1
        token = self.tokens[kind]

        def run() -> None:
            try:
                result: object = work()
            except BaseException as error:  # noqa: BLE001 - se entrega a la interfaz
                result = error
            self.messages.put((kind, token, result))

        threading.Thread(target=run, daemon=True, name=f"d2sv-{kind}").start()
        return token

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, token, payload = self.messages.get_nowait()
                handler = getattr(self, f"_on_{kind.replace('-', '_')}", None)
                if handler is not None:
                    handler(token, payload)
        except queue.Empty:
            pass
        self._poll_id = self.after(50, self._poll_messages)

    # --- Abrir ---------------------------------------------------------------------------

    def _remembered_file(self) -> Path | None:
        value = self.settings.get("last_file")
        if isinstance(value, str) and value and Path(value).is_file():
            return Path(value)
        return None

    def choose_file(self) -> None:
        current = self.document.path if self.document and self.document.path else None
        selected = filedialog.askopenfilename(
            parent=self,
            title="Abrir scripts.obsp",
            initialdir=str(current.parent) if current else None,
            filetypes=[("Scripts de Darksiders II", "*.obsp"), ("Todos los archivos", "*.*")],
        )
        if selected:
            self.open_file(Path(selected))

    def open_file(self, path: Path) -> None:
        self.status_var.set(f"Abriendo {path.name}…")
        self.progress.configure(mode="indeterminate")
        self.progress.start(15)
        self._spawn("open", lambda: Document.open(path))

    def _on_open(self, token: int, payload: object) -> None:
        if token != self.tokens["open"]:
            return
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        if isinstance(payload, BaseException):
            self.status_var.set("No se pudo abrir el archivo")
            message = str(payload) if isinstance(payload, (D2ScriptViewerError, OSError)) else repr(payload)
            messagebox.showerror(APP_NAME, f"No se pudo abrir el archivo.\n\n{message}", parent=self)
            return
        assert isinstance(payload, Document)
        self.set_document(payload)

    def set_document(self, document: Document) -> None:
        self.index_cancel.set()
        self.document = document
        self.indexes = None
        self.position = None
        self.history_back.clear()
        self.history_forward.clear()
        self._update_history_buttons()
        if self.search_window is not None and self.search_window.winfo_exists():
            self.search_window.close()
        self.search_window = None
        self.object_tree.set_document(document)
        self.property_view.show_message("", "Selecciona un objeto en el panel de la izquierda.")
        self.details.clear()
        self.details.set_indexes(None)
        self._update_file_state()
        size = len(document.obsp.data)
        self.summary_var.set(
            f"{len(document.objects):,} objetos  •  {theme.human_size(size)}  •  SHA-256 {document.obsp.sha256()[:16]}…"
        )
        if document.path is not None:
            self.path_var.set(str(document.path))
            self.settings["last_file"] = str(document.path)
        self.status_var.set("Indexando referencias y cadenas en segundo plano…")
        self._start_indexing()

    def _update_file_state(self) -> None:
        if self.document is None:
            self.state_var.set("")
            return
        if self.document.is_steam_original:
            self.state_var.set("● Original de Steam")
            self.state_label.configure(style="StatusOk.TLabel")
        else:
            self.state_var.set("● No es el original de Steam")
            self.state_label.configure(style="StatusWarn.TLabel")

    # --- Índice de referencias -----------------------------------------------------------

    def _start_indexing(self) -> None:
        assert self.document is not None
        self.index_cancel = threading.Event()
        cancel = self.index_cancel
        obsp = self.document.obsp
        index_token = self.tokens["index"] + 1

        def progress(done: int, total: int) -> None:
            self.messages.put(("index-progress", index_token, (done, total)))

        self._spawn("index", lambda: build_indexes(obsp, progress=progress, cancel=cancel))

    def _on_index_progress(self, token: int, payload: object) -> None:
        if token != self.tokens["index"]:
            return
        done, total = payload  # type: ignore[misc]
        self.progress.configure(maximum=max(total, 1), value=done)

    def _on_index(self, token: int, payload: object) -> None:
        if token != self.tokens["index"] or isinstance(payload, Cancelled):
            return
        self.progress.configure(value=0)
        if isinstance(payload, BaseException):
            self.status_var.set(f"No se pudo indexar: {payload}")
            return
        assert isinstance(payload, FileIndexes)
        self.indexes = payload
        self.on_indexes_ready()
        self.details.set_indexes(payload)
        failures = f", {len(payload.failures)} objetos no decodifican" if payload.failures else ""
        self.status_var.set(
            f"Índice listo: {len(payload.references):,} referencias, "
            f"{len(payload.dictionary):,} cadenas conocidas{failures}"
        )

    def on_indexes_ready(self) -> None:
        """Gancho para las fases siguientes (autocompletado de cadenas conocidas)."""

    # --- Navegación ----------------------------------------------------------------------

    def ref_label(self, identity: tuple[int, int]) -> str:
        info = self.document.object_by_identity(identity) if self.document else None
        if info is None:
            return f"(no existe) {identity_text(*identity)}"
        return f"{info.label()}  [{identity_text(*identity)}]"

    def follow_reference(self, identity: tuple[int, int]) -> None:
        info = self.document.object_by_identity(identity) if self.document else None
        if info is None:
            self.status_var.set(f"La referencia {identity_text(*identity)} no apunta a ningún objeto de este archivo")
            return
        self.navigate(info.position)

    def navigate(self, position: int, path: tuple | None = None, *, record: bool = True) -> None:
        if self.document is None:
            return
        if record and self.position is not None and position != self.position:
            self.history_back.append(self.position)
            self.history_forward.clear()
        self.position = position
        self._update_history_buttons()
        self.object_tree.select_position(position)
        self._show_object(position, path)

    def go_back(self) -> None:
        if self.history_back and self.position is not None:
            self.history_forward.append(self.position)
            self.navigate(self.history_back.pop(), record=False)

    def go_forward(self) -> None:
        if self.history_forward and self.position is not None:
            self.history_back.append(self.position)
            self.navigate(self.history_forward.pop(), record=False)

    def _update_history_buttons(self) -> None:
        self.back_button.configure(state="normal" if self.history_back else "disabled")
        self.forward_button.configure(state="normal" if self.history_forward else "disabled")

    def _object_title(self, position: int) -> str:
        assert self.document is not None
        info = self.document.objects[position]
        return f"{info.path}   ·   {info.class_name or info.kind_label}"

    def _show_object(self, position: int, path: tuple | None) -> None:
        assert self.document is not None
        document = self.document
        info = document.objects[position]
        self._display_started = time.perf_counter()
        title = self._object_title(position)
        if info.is_script:
            try:
                header = document.script_header(position)
            except D2ScriptViewerError as error:
                self.property_view.show_message(title, f"No se pudo leer la cabecera del script: {error}")
            else:
                self.property_view.show_rows(
                    title,
                    [
                        ("Versión", "u32", str(header.version)),
                        ("Símbolos", "u32", f"{len(header.symbols):,} (ver pestaña Script)"),
                        ("Hash de ruta", "u64", f"{header.path_hash:016X}"),
                        ("Grupo", "u32", str(header.group)),
                        ("Cuerpo", "bytecode", f"{info.entry.size - header.body_offset:,} bytes, solo lectura"),
                    ],
                )
            self.details.show(document, info)
            self._finish_display()
            return
        if document.cached_bod(position) is not None or info.entry.size <= SYNC_DECODE_LIMIT:
            self._display_bod(position, path)
            return
        self.property_view.show_message(title, f"Decodificando {theme.human_size(info.entry.size)}…")
        self.details.show(document, info)
        self._spawn("decode", lambda: (position, path, document.bod(position)))

    def _on_decode(self, token: int, payload: object) -> None:
        if token != self.tokens["decode"]:
            return
        if isinstance(payload, BaseException):
            if self.position is not None and self.document is not None:
                self.property_view.show_message(self._object_title(self.position), f"No se pudo decodificar: {payload}")
            return
        position, path, _tree = payload  # type: ignore[misc]
        if position == self.position:
            self._display_bod(position, path)

    def _display_bod(self, position: int, path: tuple | None) -> None:
        assert self.document is not None
        document = self.document
        info = document.objects[position]
        title = self._object_title(position)
        try:
            tree = document.bod(position)
        except D2ScriptViewerError as error:
            self.property_view.show_message(title, f"No se pudo decodificar: {error}")
            self.details.show(document, info)
            return
        self.property_view.show_bod(title, tree)
        if path:
            self.property_view.reveal(path)
        self.details.show(
            document,
            info,
            [("BOD", f"versión {tree.version}, campo desconocido {tree.flags}"),
             ("Nombres internos", f"{tree.declared_name_count:,} (máx. {tree.declared_max_name_length} caracteres)")],
        )
        self._finish_display()

    def _finish_display(self) -> None:
        self.last_display_seconds = time.perf_counter() - self._display_started

    # --- Búsqueda ------------------------------------------------------------------------

    def open_search(self) -> None:
        if self.document is None:
            return
        if self.search_window is not None and self.search_window.winfo_exists():
            self.search_window.lift()
            self.search_window.focus_set()
            return
        self.search_window = SearchWindow(self, self.document, self.navigate)

    # --- Cierre --------------------------------------------------------------------------

    def _about(self) -> None:
        messagebox.showinfo(
            APP_NAME,
            f"{APP_NAME} {__version__}\n\nVisor y editor de scripts.obsp de Darksiders II "
            "Deathinitive Edition.\n\nLicencia MIT · BOTProT800",
            parent=self,
        )

    def _on_close(self) -> None:
        self.index_cancel.set()
        if self.persist_settings:
            self.settings["geometry"] = self.geometry()
            self.settings["group_by"] = self.object_tree.group_var.get()
            save_settings(self.settings)
        self.destroy()

    def destroy(self) -> None:
        self.index_cancel.set()
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        if self.search_window is not None and self.search_window.winfo_exists():
            self.search_window.close()
        self.object_tree.cancel_pending()
        super().destroy()


def main(initial: Path | None = None) -> None:
    app = ViewerApp(initial)
    app.mainloop()
