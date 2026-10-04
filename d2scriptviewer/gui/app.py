# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Ventana principal: objetos a la izquierda, propiedades en el centro y detalles a la derecha.

El trabajo pesado (abrir, indexar referencias, decodificar objetos grandes y
buscar) corre en hilos que hablan con la interfaz a través de ``self.messages``.
Los hilos nunca tocan Tk: solo encolan mensajes que ``_poll_messages`` atiende.

Las ediciones las valida y aplica el núcleo (``edits`` y ``Document``); la
ventana solo recoge el texto, pide confirmación en los campos con aspecto de
identificador y refresca las vistas con :meth:`ViewerApp._after_change`.
"""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .. import __version__, edits, saving
from ..document import Document
from ..edits import EditGroup
from ..errors import D2ScriptViewerError, EditError
from ..formats import bod
from ..formats.obsp import identity_text
from ..references import Cancelled, FileIndexes, build_indexes, references_in
from ..settings import DEFAULT_GAME, find_default_obsp, load_settings, save_settings
from ..wording import count as count_text
from . import theme
from .details import DetailsPanel
from .editors import ReferencePicker
from .object_tree import GROUP_MODES, ObjectTree
from .pending_view import PendingChangesWindow
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
        self.document: Document | None = None
        self._update_title()
        geometry = self.settings.get("geometry")
        self.geometry(str(geometry) if isinstance(geometry, str) else "1500x900")
        self.minsize(1100, 640)
        self.configure(bg=theme.BACKGROUND)
        theme.configure_styles(self)

        self.messages: queue.Queue[tuple[str, int, object]] = queue.Queue()
        self.indexes: FileIndexes | None = None
        self.position: int | None = None
        self.history_back: list[int] = []
        self.history_forward: list[int] = []
        self.index_cancel = threading.Event()
        self.tokens = {"open": 0, "index": 0, "decode": 0, "save": 0, "restore": 0}
        self.search_window: SearchWindow | None = None
        self.pending_window: PendingChangesWindow | None = None
        #: Confirmaciones sí/no y sí/no/cancelar; los tests las sustituyen para no abrir diálogos.
        self.ask: Callable[..., bool] = lambda title, message, **options: messagebox.askyesno(
            title, message, parent=self, **options
        )
        self.ask_save: Callable[..., "bool | None"] = lambda title, message, **options: messagebox.askyesnocancel(
            title, message, parent=self, **options
        )
        #: Avisos informativos (resumen del primer guardado); también sustituibles.
        self.inform: Callable[[str, str], None] = lambda title, message: messagebox.showinfo(title, message, parent=self)
        self.saving = False
        self._after_save: Callable[[], None] | None = None
        self._game_save_confirmed: set[Path] = set()
        #: Segundos que tardó en mostrarse el último objeto (para medir el criterio < 1 s).
        self.last_display_seconds = 0.0
        self._display_started = 0.0

        self.summary_var = tk.StringVar(value="Sin archivo")
        self.state_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Abre un scripts.obsp con Archivo → Abrir (Ctrl+O)")
        self.path_var = tk.StringVar(value="")
        self.changes_var = tk.StringVar(value="")
        self.rotating_var = tk.BooleanVar(value=bool(self.settings.get("rotating_backups", True)))

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
        self.file_menu.add_command(label="Guardar", accelerator="Ctrl+S", command=self.save)
        self.file_menu.add_command(label="Guardar como…", accelerator="Ctrl+Mayús+S", command=self.save_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Restaurar original…", command=self.restore_original_file)
        self.file_menu.add_checkbutton(
            label=f"Copia rotativa de la versión anterior (últimas {saving.KEEP_BACKUPS})",
            variable=self.rotating_var,
        )
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Salir", command=self._on_close)
        menubar.add_cascade(label="Archivo", menu=self.file_menu)

        self.edit_menu = tk.Menu(menubar, tearoff=False)
        self.edit_menu.add_command(label="Deshacer", accelerator="Ctrl+Z", command=self.undo, state="disabled")
        self.edit_menu.add_command(label="Rehacer", accelerator="Ctrl+Y", command=self.redo, state="disabled")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Editar valor", accelerator="F2", command=self.property_view_edit)
        self.edit_menu.add_command(label="Revertir objeto", command=self.revert_current_object)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cambios pendientes…", accelerator="Ctrl+P", command=self.open_pending)
        menubar.add_cascade(label="Editar", menu=self.edit_menu)

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
        self.bind_all("<Control-s>", lambda _event: self.save() or "break")
        self.bind_all("<Control-S>", lambda _event: self.save_as() or "break")
        self.bind_all("<Control-f>", lambda _event: self.open_search())
        self.bind_all("<Alt-Left>", lambda _event: self.go_back())
        self.bind_all("<Alt-Right>", lambda _event: self.go_forward())
        for sequence, action in (
            ("<Control-z>", self.undo),
            ("<Control-Z>", self.undo),
            ("<Control-y>", self.redo),
            ("<Control-Y>", self.redo),
            ("<Control-p>", self.open_pending),
        ):
            self.bind_all(sequence, self._shortcut(action))

    def _shortcut(self, action: Callable[[], object]) -> Callable[[tk.Event], "str | None"]:
        """Atajo global que respeta los campos de texto (allí Ctrl+Z es del propio campo)."""

        def handler(event: tk.Event) -> str | None:
            if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text)) or self.property_view.editing:
                return None
            action()
            return "break"

        return handler

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
        self.property_view = PropertyView(
            pane,
            ref_label=self.ref_label,
            on_follow_ref=self.follow_reference,
            on_edit_text=self.commit_text_edit,
            on_pick_reference=self.pick_reference,
            on_revert_property=self.revert_property,
            hint=self.edit_hint,
            suggest=self.suggest_names,
        )
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
        self.changes_label = ttk.Label(status, textvariable=self.changes_var, style="Status.TLabel")
        self.changes_label.pack(side="left", padx=(16, 0))
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

    def _resolve_unsaved(self, action: str, then: Callable[[], None]) -> bool:
        """Pregunta qué hacer con los cambios sin guardar antes de ``action``.

        Devuelve ``True`` si se puede seguir ya (no hay cambios o se descartan). Si el
        usuario elige guardar, el guardado corre en segundo plano y ``then`` se llama
        al terminar bien; entonces devuelve ``False``, igual que al cancelar.
        """
        document = self.document
        if self.saving:
            self.status_var.set("Espera a que termine el guardado")
            return False
        if document is None or not document.change_count:
            return True
        answer = self.ask_save(
            APP_NAME,
            f"Hay {count_text(document.change_count, 'cambio')} sin guardar.\n\n"
            f"¿Guardarlos antes de {action}?\n(«No» los descarta.)",
            icon="warning",
        )
        if answer is None:
            return False
        if not answer:
            return True
        target = document.path
        if target is None or saving.is_original_copy(target):
            self.inform(APP_NAME, "Este archivo es la copia del original: guarda los cambios con «Guardar como».")
            return False
        self._start_save(target, then=then)
        return False

    def choose_file(self) -> None:
        if not self._resolve_unsaved("abrir otro archivo", then=self.choose_file):
            return
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

        def work() -> tuple[Document, bool]:
            removed = saving.cleanup_orphan_tmp(path)
            return Document.open(path), removed

        self._spawn("open", work)

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
        document, removed_tmp = payload  # type: ignore[misc]
        self.set_document(document)
        if removed_tmp:
            self.status_var.set(f"Se borró {saving.tmp_path(document.path).name}, resto de un guardado interrumpido")

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
        if self.pending_window is not None and self.pending_window.winfo_exists():
            self.pending_window.destroy()
        self.pending_window = None
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
        self._update_change_state()
        self._start_indexing()

    def _update_file_state(self) -> None:
        if self.document is None:
            self.state_var.set("")
            return
        status = saving.file_status(self.document.path, self.document.obsp.sha256())
        self.state_var.set(f"● {status.text}")
        self.state_label.configure(style="StatusOk.TLabel" if status.kind == "steam" else "StatusWarn.TLabel")

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
        self.property_view.show_bod(title, tree, document.edited_paths(position))
        if path:
            self.property_view.reveal(path)
        self._show_details(position)
        self._finish_display()

    def _show_details(self, position: int) -> None:
        assert self.document is not None
        document = self.document
        info = document.objects[position]
        extra: list[tuple[str, str]] = []
        tree = document.cached_bod(position)
        if tree is not None:
            extra.append(("BOD", f"versión {tree.version}, campo desconocido {tree.flags}"))
            extra.append(
                ("Nombres internos",
                 f"{tree.declared_name_count:,} al abrir (máx. {tree.declared_max_name_length} caracteres)")
            )
        if document.is_modified(position):
            changed = len(document.edited_paths(position))
            extra.append(
                ("Estado", f"modificado: {count_text(changed, 'propiedad', 'propiedades')}, {len(document.blob(position)):,} bytes al guardar")
            )
        else:
            extra.append(("Estado", "sin cambios"))
        self.details.show(document, info, extra)

    def _finish_display(self) -> None:
        self.last_display_seconds = time.perf_counter() - self._display_started

    # --- Edición ------------------------------------------------------------------------

    def edit_hint(self, node: object, _path: tuple, text: str) -> tuple[bool, str]:
        return edits.input_hint(node, text, self.indexes.dictionary if self.indexes else None)

    def suggest_names(self, text: str) -> list[str]:
        if self.indexes is None:
            return []
        return edits.suggestions(self.indexes.dictionary, text)

    def property_view_edit(self) -> None:
        self.property_view.begin_edit()

    def commit_text_edit(self, node: object, path: tuple, text: str) -> str | None:
        """Valida y aplica lo escrito en el editor; devuelve el error o ``None``."""
        document, position = self.document, self.position
        if document is None or position is None:
            return "No hay ningún objeto seleccionado"
        if self.saving:
            return "Espera a que termine el guardado"
        try:
            state = edits.parse_state(node, text, self.indexes.dictionary if self.indexes else None)
        except EditError as error:
            return str(error)
        if state == edits.get_state(node):
            return None
        if not self._confirm_identifier(position, path, node):
            return None
        try:
            group = document.edit(position, path, state)
        except EditError as error:
            return str(error)
        if group is not None:
            self._after_change(group, reveal=False)
        return None

    def _confirm_identifier(self, position: int, path: tuple, node: object) -> bool:
        assert self.document is not None
        warning = edits.identifier_warning(edits.field_name(self.document.bod(position), path), node)
        if warning is None:
            return True
        return bool(self.ask(APP_NAME, f"{warning}\n\n¿Aplicar el cambio de todos modos?", icon="warning"))

    def pick_reference(self, node: object, path: tuple) -> None:
        document, position = self.document, self.position
        if document is None or position is None or not isinstance(node, bod.ExternalRef) or self.saving:
            return
        title = f"{document.objects[position].label()} · {document.property_label(position, path)}"
        identity = ReferencePicker(self, document, node.identity, title).choose()
        if identity is None:
            return
        try:
            group = document.edit(position, path, identity)
        except EditError as error:
            messagebox.showerror(APP_NAME, str(error), parent=self)
            return
        if group is not None:
            self._after_change(group, reveal=False)

    def revert_property(self, path: tuple) -> None:
        if self.document is None or self.position is None or self.saving:
            return
        group = self.document.revert_property(self.position, path)
        if group is not None:
            self._after_change(group, reveal=False)

    def revert_current_object(self) -> None:
        if self.position is not None:
            self.revert_object(self.position)

    def revert_object(self, position: int) -> None:
        if self.document is None or self.saving:
            return
        group = self.document.revert_object(position)
        if group is None:
            self.status_var.set("Ese objeto no tiene cambios")
            return
        self._after_change(group, reveal=position != self.position)

    def undo(self) -> None:
        if self.document is None or self.saving:
            return
        self.property_view.cancel_edit()
        group = self.document.undo()
        if group is not None:
            self._after_change(group, reveal=True, prefix="Deshecho")

    def redo(self) -> None:
        if self.document is None or self.saving:
            return
        self.property_view.cancel_edit()
        group = self.document.redo()
        if group is not None:
            self._after_change(group, reveal=True, prefix="Rehecho")

    def _after_change(self, group: EditGroup, *, reveal: bool, prefix: str = "") -> None:
        """Pone al día todas las vistas tras editar, deshacer, rehacer o revertir."""
        document = self.document
        assert document is not None
        if self.indexes is not None:
            for position in group.positions:
                self.indexes.references.set_object(position, references_in(position, document.bod(position)))
        self.object_tree.set_modified(document.modified_positions)
        first = group.edits[0]
        if reveal and first.position != self.position:
            self.navigate(first.position, first.path)
        elif self.position is not None and document.cached_bod(self.position) is not None:
            self.property_view.set_edited(document.edited_paths(self.position))
            if reveal:
                self.property_view.reveal(first.path)
            self._show_details(self.position)
        if self.pending_window is not None and self.pending_window.winfo_exists():
            self.pending_window.refresh()
        self._update_change_state()
        self.status_var.set(f"{prefix}: {group.description}" if prefix else group.description)

    def _update_change_state(self) -> None:
        document = self.document
        count = document.change_count if document else 0
        if document is not None and count:
            objects = len(document.modified_positions)
            self.changes_var.set(f"● {count_text(count, 'cambio')} sin guardar en {count_text(objects, 'objeto')}")
            self.changes_label.configure(style="StatusWarn.TLabel")
        else:
            self.changes_var.set("Sin cambios" if document else "")
            self.changes_label.configure(style="Status.TLabel")
        undo = document.undo_description if document else None
        redo = document.redo_description if document else None
        self.edit_menu.entryconfigure(
            0, label=f"Deshacer: {self._short(undo)}" if undo else "Deshacer", state="normal" if undo else "disabled"
        )
        self.edit_menu.entryconfigure(
            1, label=f"Rehacer: {self._short(redo)}" if redo else "Rehacer", state="normal" if redo else "disabled"
        )
        self._update_title()

    @staticmethod
    def _short(text: str | None, limit: int = 60) -> str:
        text = text or ""
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def _update_title(self) -> None:
        document = self.document
        dirty = "* " if document is not None and document.change_count else ""
        name = f"{document.path.name} — " if document is not None and document.path is not None else ""
        self.title(f"{dirty}{name}{APP_NAME} {__version__} — scripts.obsp de Darksiders II Deathinitive Edition")

    def open_pending(self) -> None:
        if self.document is None:
            return
        if self.pending_window is not None and self.pending_window.winfo_exists():
            self.pending_window.refresh()
            self.pending_window.lift()
            return
        self.pending_window = PendingChangesWindow(
            self,
            self.document,
            ref_label=self.ref_label,
            on_navigate=self.navigate,
            on_revert_object=self.revert_object,
        )

    # --- Guardar -------------------------------------------------------------------------

    def _commit_pending_editor(self) -> bool:
        """Confirma un editor abierto antes de guardar; ``False`` si su texto no es válido."""
        if self.property_view.editing and self.property_view.editor is not None:
            self.property_view.editor.commit()
        return not self.property_view.editing

    def save(self) -> None:
        document = self.document
        if document is None or self.saving or not self._commit_pending_editor():
            return
        target = document.path
        if target is None or saving.is_original_copy(target):
            if target is not None:
                self.inform(APP_NAME, f"{target.name} es la copia del original y nunca se sobrescribe.\n\n"
                                      "Usa «Guardar como» para guardar los cambios en otro archivo.")
            self.save_as()
            return
        if not document.change_count:
            self.status_var.set("No hay cambios que guardar")
            return
        self._start_save(target)

    def save_as(self) -> None:
        document = self.document
        if document is None or self.saving or not self._commit_pending_editor():
            return
        current = document.path
        selected = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar como",
            defaultextension=".obsp",
            initialdir=str(current.parent) if current else None,
            initialfile=current.name if current and not saving.is_original_copy(current) else "scripts.obsp",
            filetypes=[("Scripts de Darksiders II", "*.obsp"), ("Todos los archivos", "*.*")],
        )
        if not selected:
            return
        target = Path(selected)
        if saving.is_original_copy(target):
            messagebox.showerror(APP_NAME, "Los archivos *.original.obsp son copias del original y nunca se "
                                           "sobrescriben. Elige otro nombre.", parent=self)
            return
        self._start_save(target)

    @staticmethod
    def _in_game_folder(path: Path) -> bool:
        try:
            return path.resolve().is_relative_to(DEFAULT_GAME.resolve())
        except OSError:
            return False

    def _start_save(self, target: Path, then: Callable[[], None] | None = None) -> None:
        document = self.document
        if document is None or self.saving:
            return
        if self._in_game_folder(target) and target not in self._game_save_confirmed:
            copy = saving.original_copy_path(target)
            copy_note = (
                f"{copy.name} ya existe y no se tocará."
                if copy.exists()
                else f"Antes se creará {copy.name}: copia exacta del archivo actual, verificada y de solo lectura."
            )
            if not self.ask(
                APP_NAME,
                f"Vas a sobrescribir {target.name} en la instalación del juego.\n\n"
                f"• {copy_note}\n"
                "• Darksiders II debe estar cerrado.\n"
                "• «Verificar integridad» de Steam devolverá el original.\n\n¿Guardar?",
                icon="warning",
            ):
                return
            self._game_save_confirmed.add(target)
        try:
            plan = saving.prepare_save(document)
        except D2ScriptViewerError as error:
            messagebox.showerror(APP_NAME, str(error), parent=self)
            return
        self.saving = True
        self._after_save = then
        self.status_var.set(f"Guardando {target.name}…")
        self.progress.configure(mode="indeterminate")
        self.progress.start(15)
        rotating = self.rotating_var.get()
        self._spawn("save", lambda: (target, plan, saving.execute_save(plan, target, rotating_backups=rotating)))

    def _on_save(self, token: int, payload: object) -> None:
        if token != self.tokens["save"]:
            return
        self.saving = False
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        then, self._after_save = self._after_save, None
        document = self.document
        if isinstance(payload, BaseException):
            self.status_var.set("No se guardó")
            message = str(payload) if isinstance(payload, (D2ScriptViewerError, OSError)) else repr(payload)
            if isinstance(payload, saving.WrittenMismatchError) and document is not None and document.path:
                if self.ask(APP_NAME, f"{message}\n\n¿Restaurar ahora la copia del original?", icon="error"):
                    self.restore_original_file(confirm=False)
                return
            messagebox.showerror(APP_NAME, f"No se guardó el archivo.\n\n{message}", parent=self)
            return
        target, plan, result = payload  # type: ignore[misc]
        assert document is not None
        document.mark_saved(plan.data, target)
        self.path_var.set(str(target))
        self.settings["last_file"] = str(target)
        self.object_tree.set_modified(set())
        if self.position is not None and document.cached_bod(self.position) is not None:
            self.property_view.set_edited(set())
        if self.position is not None:
            self._show_details(self.position)
        if self.pending_window is not None and self.pending_window.winfo_exists():
            self.pending_window.refresh()
        self._update_file_state()
        self._update_change_state()
        self.status_var.set(result.summary().splitlines()[0])
        if result.original_created or result.warnings:
            self.inform(APP_NAME, result.summary())
        if then is not None:
            then()

    def restore_original_file(self, confirm: bool = True) -> None:
        document = self.document
        if document is None or document.path is None or self.saving:
            return
        path = document.path
        if saving.is_original_copy(path):
            self.inform(APP_NAME, "Este archivo ya es la copia del original.")
            return
        copy = saving.original_copy_path(path)
        if not copy.is_file():
            self.inform(APP_NAME, f"No existe {copy.name} junto a {path.name}.\n\n"
                                  "La copia se crea la primera vez que se guarda encima del archivo.")
            return
        if confirm:
            lost = (f"\n• Se perderán {count_text(document.change_count, 'cambio')} sin guardar."
                    if document.change_count else "")
            if not self.ask(
                APP_NAME,
                f"Se copiará {copy.name} encima de {path.name} y se verificará.\n"
                f"• {copy.name} se conserva.\n"
                f"• La versión actual irá a {saving.BACKUP_DIR} si las copias rotativas están activas.{lost}\n\n"
                "¿Restaurar?",
                icon="warning",
            ):
                return
        self.saving = True
        self.status_var.set(f"Restaurando {path.name}…")
        rotating = self.rotating_var.get()
        self._spawn("restore", lambda: saving.restore_original(path, rotating_backups=rotating))

    def _on_restore(self, token: int, payload: object) -> None:
        if token != self.tokens["restore"]:
            return
        self.saving = False
        if isinstance(payload, BaseException):
            self.status_var.set("No se restauró")
            message = str(payload) if isinstance(payload, (D2ScriptViewerError, OSError)) else repr(payload)
            messagebox.showerror(APP_NAME, f"No se restauró el original.\n\n{message}", parent=self)
            return
        assert isinstance(payload, saving.RestoreResult)
        origin = "el original de Steam" if payload.is_steam else "la copia del original"
        self.inform(APP_NAME, f"{payload.path.name} vuelve a ser {origin}.\nSHA-256 {payload.sha256}")
        self.open_file(payload.path)

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
        if not self._resolve_unsaved("salir", then=self._close_now):
            return
        self._close_now()

    def _close_now(self) -> None:
        self.index_cancel.set()
        if self.persist_settings:
            self.settings["geometry"] = self.geometry()
            self.settings["group_by"] = self.object_tree.group_var.get()
            self.settings["rotating_backups"] = bool(self.rotating_var.get())
            save_settings(self.settings)
        self.destroy()

    def destroy(self) -> None:
        self.index_cancel.set()
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        if self.search_window is not None and self.search_window.winfo_exists():
            self.search_window.close()
        self.property_view.cancel_edit()
        self.object_tree.cancel_pending()
        super().destroy()


def main(initial: Path | None = None) -> None:
    app = ViewerApp(initial)
    app.mainloop()
