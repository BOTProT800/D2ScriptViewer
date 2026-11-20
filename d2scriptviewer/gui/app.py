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

import gc
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .. import __version__, edits, export, i18n, patches, saving, vocabulary
from ..document import Document, Location
from ..edits import EditGroup
from ..errors import D2ScriptViewerError, EditError, PathError
from ..formats import bod, script
from ..formats.obsp import identity_text
from ..i18n import _, ngettext
from ..references import Cancelled, FileIndexes, build_indexes, references_in, slot_key
from ..settings import DEFAULT_GAME, find_default_obsp, load_settings, save_settings
from . import theme
from .details import DetailsPanel
from .editors import FillNullDialog, ReferencePicker
from .object_tree import GROUP_MODES, ObjectTree
from .pending_view import PendingChangesWindow
from .property_view import PropertyView
from .search_view import SearchWindow

APP_NAME = "D2ScriptViewer"
#: Por encima de este tamaño el objeto se decodifica en un hilo para no congelar la ventana.
SYNC_DECODE_LIMIT = 48 * 1024


class ViewerApp(tk.Tk):
    def __init__(
        self,
        initial: Path | None = None,
        *,
        auto_open: bool = True,
        persist_settings: bool = True,
        language: str | None = None,
    ) -> None:
        """``language`` fija el idioma de la interfaz. Sin él, el de ``D2SV_LANG``, el guardado o el
        de Windows; sin preferencias (los tests), el español.
        """
        super().__init__()
        self.persist_settings = persist_settings
        self.settings = load_settings() if persist_settings else {}
        if language is None:
            language = i18n.initial_language(self.settings.get("language")) if persist_settings else i18n.SPANISH
        i18n.set_language(language)
        self.language_var = tk.StringVar(value=language)
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
        self.tokens = {"open": 0, "index": 0, "decode": 0, "save": 0, "restore": 0, "export": 0, "patch": 0}
        #: Hay una exportación o un parche en curso (trabajan sobre una instantánea).
        self.exporting = False
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
        self.alert: Callable[[str, str], None] = lambda title, message: messagebox.showerror(title, message, parent=self)
        #: Texto del portapapeles o ``None``; los tests lo sustituyen para no depender del sistema.
        self.read_clipboard: Callable[[], "str | None"] = self._clipboard_text
        self.saving = False
        #: Objeto que se está decodificando en un hilo, y la ruta pedida mientras tanto (fase 11).
        self._decoding: int | None = None
        self._pending_location: tuple[int, Location] | None = None
        self._after_save: Callable[[], None] | None = None
        self._game_save_confirmed: set[Path] = set()
        #: Segundos que tardó en mostrarse el último objeto (para medir el criterio < 1 s).
        self.last_display_seconds = 0.0
        self._display_started = 0.0

        self.summary_var = tk.StringVar(value=_("Sin archivo"))
        self.state_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value=_("Abre un scripts.obsp con Archivo → Abrir (Ctrl+O)"))
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
        self.file_menu.add_command(label=_("Abrir…"), accelerator="Ctrl+O", command=self.choose_file)
        self.file_menu.add_command(label=_("Guardar"), accelerator="Ctrl+S", command=self.save)
        self.file_menu.add_command(label=_("Guardar como…"), accelerator=_("Ctrl+Mayús+S"), command=self.save_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=_("Restaurar original…"), command=self.restore_original_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=_("Exportar a JSON y CSV…"), command=self.export_files)
        self.file_menu.add_command(label=_("Exportar parche…"), command=self.export_patch)
        self.file_menu.add_command(label=_("Aplicar parche…"), command=self.apply_patch_file)
        self.file_menu.add_checkbutton(
            label=_("Copia rotativa de la versión anterior (últimas {count})").format(count=saving.KEEP_BACKUPS),
            variable=self.rotating_var,
        )
        self.file_menu.add_separator()
        self.file_menu.add_command(label=_("Salir"), command=self._on_close)
        menubar.add_cascade(label=_("Archivo"), menu=self.file_menu)

        self.edit_menu = tk.Menu(menubar, tearoff=False)
        self.edit_menu.add_command(label=_("Deshacer"), accelerator="Ctrl+Z", command=self.undo, state="disabled")
        self.edit_menu.add_command(label=_("Rehacer"), accelerator="Ctrl+Y", command=self.redo, state="disabled")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label=_("Editar valor"), accelerator="F2", command=self.property_view_edit)
        self.edit_menu.add_command(label=_("Revertir objeto"), command=self.revert_current_object)
        structure_menu = tk.Menu(self.edit_menu, tearoff=False)
        for label, accelerator, action in (
            (_("Duplicar elemento"), "Ctrl+D", "duplicate"),
            (_("Eliminar elemento"), _("Supr"), "remove"),
            (_("Subir"), "Alt+↑", "up"),
            (_("Bajar"), "Alt+↓", "down"),
            (_("Poner a nulo"), "", "null"),
            (_("Rellenar nulo con un objeto…"), "", "fill"),
        ):
            structure_menu.add_command(
                label=label, accelerator=accelerator, command=lambda action=action: self._structure_from_menu(action)
            )
        self.edit_menu.add_cascade(label=_("Estructura"), menu=structure_menu)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label=_("Cambios pendientes…"), accelerator="Ctrl+P", command=self.open_pending)
        menubar.add_cascade(label=_("Editar"), menu=self.edit_menu)

        search_menu = tk.Menu(menubar, tearoff=False)
        search_menu.add_command(label=_("Buscar en el objeto"), accelerator="Ctrl+F", command=self.focus_object_search)
        search_menu.add_command(label=_("Buscar en todo el archivo…"), accelerator=_("Ctrl+Mayús+F"),
                                command=self.open_search)
        menubar.add_cascade(label=_("Buscar"), menu=search_menu)

        go_menu = tk.Menu(menubar, tearoff=False)
        go_menu.add_command(label=_("Atrás"), accelerator=_("Alt+Izquierda"), command=self.go_back)
        go_menu.add_command(label=_("Adelante"), accelerator=_("Alt+Derecha"), command=self.go_forward)
        go_menu.add_separator()
        go_menu.add_command(label=_("Ir a la ruta…"), accelerator="Ctrl+G", command=self.open_goto)
        menubar.add_cascade(label=_("Ir"), menu=go_menu)

        # El menú de idioma se entiende en los dos idiomas, y cada uno se nombra en el suyo.
        self.language_menu = tk.Menu(menubar, tearoff=False)
        for code, name in i18n.LANGUAGES.items():
            self.language_menu.add_radiobutton(
                label=name, value=code, variable=self.language_var,
                command=lambda: self.change_language(self.language_var.get()),
            )
        menubar.add_cascade(label=i18n.MENU_LABEL, menu=self.language_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label=_("Acerca de"), command=self._about)
        menubar.add_cascade(label=_("Ayuda"), menu=help_menu)
        self.configure(menu=menubar)
        self.menubar = menubar

        self.bind_all("<Control-o>", lambda _event: self.choose_file())
        self.bind_all("<Control-s>", lambda _event: self.save() or "break")
        self.bind_all("<Control-S>", lambda _event: self.save_as() or "break")
        self.bind_all("<Control-f>", self._on_find_key)
        self.bind_all("<Control-F>", lambda _event: self.open_search() or "break")
        self.bind_all("<Control-g>", self._on_goto_key)
        self.bind_all("<Control-G>", self._on_goto_key)
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
            text=_("Visor y editor de scripts.obsp — Darksiders II Deathinitive Edition"),
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w")
        ttk.Label(header, textvariable=self.summary_var, style="Muted.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")
        header.columnconfigure(1, weight=1)

        pane = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=12)
        self.object_tree = ObjectTree(pane, on_select=lambda position: self.navigate(position))
        group_by = self.settings.get("group_by")
        if group_by in GROUP_MODES:
            self.object_tree.set_group_mode(str(group_by))
        self.property_view = PropertyView(
            pane,
            ref_label=self.ref_label,
            on_follow_ref=self.follow_reference,
            on_edit_text=self.commit_text_edit,
            on_pick_reference=self.pick_reference,
            on_revert_property=self.revert_property,
            on_structure=self.structure_action,
            hint=self.edit_hint,
            suggest=self.suggest_names,
            on_goto=self.go_to_location,
            on_goto_cancel=self.cancel_goto,
            full_label=self.full_label,
        )
        self.details = DetailsPanel(pane, on_navigate=self.navigate)
        pane.add(self.object_tree, weight=3)
        pane.add(self.property_view, weight=5)
        pane.add(self.details, weight=3)
        self.pane = pane
        # Los pesos solo reparten el espacio sobrante: el reparto inicial se fija a mano.
        self._sash_after: str | None = self.after_idle(self._place_sashes)

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
        self._sash_after = None
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

    def _resolve_unsaved(self, question: str, then: Callable[[], None]) -> bool:
        """Pregunta qué hacer con los cambios sin guardar; ``question`` dice antes de qué.

        Devuelve ``True`` si se puede seguir ya (no hay cambios o se descartan). Si el
        usuario elige guardar, el guardado corre en segundo plano y ``then`` se llama
        al terminar bien; entonces devuelve ``False``, igual que al cancelar.
        """
        document = self.document
        if self.saving:
            self.status_var.set(_("Espera a que termine el guardado"))
            return False
        if document is None or not document.change_count:
            return True
        changes = document.change_count
        answer = self.ask_save(
            APP_NAME,
            ngettext("Hay {count:,} cambio sin guardar.", "Hay {count:,} cambios sin guardar.", changes).format(
                count=changes) + "\n\n" + question + "\n" + _("(«No» los descarta.)"),
            icon="warning",
        )
        if answer is None:
            return False
        if not answer:
            return True
        target = document.path
        if target is None or saving.is_original_copy(target):
            self.inform(APP_NAME, _("Este archivo es la copia del original: guarda los cambios con «Guardar como»."))
            return False
        self._start_save(target, then=then)
        return False

    def choose_file(self) -> None:
        if not self._resolve_unsaved(_("¿Guardarlos antes de abrir otro archivo?"), then=self.choose_file):
            return
        current = self.document.path if self.document and self.document.path else None
        selected = filedialog.askopenfilename(
            parent=self,
            title=_("Abrir scripts.obsp"),
            initialdir=str(current.parent) if current else None,
            filetypes=[(_("Scripts de Darksiders II"), "*.obsp"), (_("Todos los archivos"), "*.*")],
        )
        if selected:
            self.open_file(Path(selected))

    def open_file(self, path: Path) -> None:
        self.status_var.set(_("Abriendo {name}…").format(name=path.name))
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
            self.status_var.set(_("No se pudo abrir el archivo"))
            message = str(payload) if isinstance(payload, (D2ScriptViewerError, OSError)) else repr(payload)
            messagebox.showerror(APP_NAME, _("No se pudo abrir el archivo.\n\n{message}").format(message=message),
                                 parent=self)
            return
        document, removed_tmp = payload  # type: ignore[misc]
        self.set_document(document)
        if removed_tmp:
            self.status_var.set(_("Se borró {name}, resto de un guardado interrumpido").format(
                name=saving.tmp_path(document.path).name))

    def set_document(self, document: Document) -> None:
        self.index_cancel.set()
        self.document = document
        self.indexes = None
        self.position = None
        self.history_back.clear()
        self.history_forward.clear()
        self._update_history_buttons()
        self._close_secondary_windows()
        self._decoding = None
        self._pending_location = None
        if self.property_view.goto_visible:
            self.property_view.hide_goto()
        self._show_document()
        if document.path is not None:
            self.settings["last_file"] = str(document.path)
        self.status_var.set(_("Indexando referencias y cadenas en segundo plano…"))
        self._start_indexing()

    def _close_secondary_windows(self) -> None:
        if self.search_window is not None and self.search_window.winfo_exists():
            self.search_window.close()
        self.search_window = None
        if self.pending_window is not None and self.pending_window.winfo_exists():
            self.pending_window.destroy()
        self.pending_window = None

    def _show_document(self) -> None:
        """Pinta el documento abierto en los paneles, sin objeto seleccionado (abrir y cambiar de idioma)."""
        document = self.document
        assert document is not None
        self.object_tree.set_document(document)
        self.object_tree.set_modified(document.modified_positions)
        self.property_view.show_message("", _("Selecciona un objeto en el panel de la izquierda."))
        self.details.clear()
        self.details.set_indexes(self.indexes)
        self._update_file_state()
        size = len(document.obsp.data)
        count = len(document.objects)
        self.summary_var.set(
            ngettext("{count:,} objeto  •  {size}  •  SHA-256 {sha}…", "{count:,} objetos  •  {size}  •  SHA-256 {sha}…",
                     count).format(count=count, size=theme.human_size(size), sha=document.obsp.sha256()[:16])
        )
        if document.path is not None:
            self.path_var.set(str(document.path))
        self._update_change_state()

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
            self.status_var.set(_("No se pudo indexar: {error}").format(error=payload))
            return
        assert isinstance(payload, FileIndexes)
        self.indexes = payload
        self.on_indexes_ready()
        self.details.set_indexes(payload)
        status = _("Índice listo: {references:,} referencias, {strings:,} cadenas conocidas").format(
            references=len(payload.references), strings=len(payload.dictionary))
        if payload.failures:
            failed = len(payload.failures)
            status += ", " + ngettext("{count:,} objeto no decodifica", "{count:,} objetos no decodifican", failed).format(
                count=failed)
        self.status_var.set(status)

    def on_indexes_ready(self) -> None:
        """Gancho para las fases siguientes (autocompletado de cadenas conocidas)."""

    # --- Navegación ----------------------------------------------------------------------

    def ref_label(self, identity: tuple[int, int]) -> str:
        info = self.document.object_by_identity(identity) if self.document else None
        if info is None:
            return _("(no existe) {identity}").format(identity=identity_text(*identity))
        return f"{info.label()}  [{identity_text(*identity)}]"

    def follow_reference(self, identity: tuple[int, int]) -> None:
        info = self.document.object_by_identity(identity) if self.document else None
        if info is None:
            self.status_var.set(_("La referencia {identity} no apunta a ningún objeto de este archivo").format(
                identity=identity_text(*identity)))
            return
        self.navigate(info.position)

    def navigate(self, position: int, path: tuple | Location | None = None, *, record: bool = True) -> None:
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

    def _show_object(self, position: int, path: tuple | Location | None) -> None:
        assert self.document is not None
        document = self.document
        info = document.objects[position]
        self._display_started = time.perf_counter()
        self._decoding = None
        self._pending_location = None
        title = self._object_title(position)
        if document.cached_bod(position) is not None or info.entry.size <= SYNC_DECODE_LIMIT:
            self._display_bod(position, path)
            return
        self.property_view.show_message(title, _("Decodificando {size}…").format(size=theme.human_size(info.entry.size)))
        self.details.show(document, info)
        self._decoding = position
        if isinstance(path, Location):
            # Si la decodificación falla, la barra «Ir a» tiene que enterarse.
            self._pending_location, path = (position, path), None
        self._spawn("decode", lambda: (position, path, document.bod(position)))

    def _on_decode(self, token: int, payload: object) -> None:
        if token != self.tokens["decode"]:
            return
        decoding, self._decoding = self._decoding, None
        if isinstance(payload, BaseException):
            if decoding is None or decoding != self.position:
                return  # el fallo es de un objeto que ya no se muestra
            pending, self._pending_location = self._pending_location, None
            if self.position is not None and self.document is not None:
                self.property_view.show_message(self._object_title(self.position),
                                                _("No se pudo decodificar: {error}").format(error=payload))
                if pending is not None:
                    self.property_view.goto_failed(_("Este objeto no se pudo decodificar: no tiene propiedades a las que ir"))
            return
        position, path, _tree = payload  # type: ignore[misc]
        if position == self.position:
            self._display_bod(position, path)

    def _display_bod(self, position: int, path: tuple | Location | None) -> None:
        assert self.document is not None
        document = self.document
        info = document.objects[position]
        title = self._object_title(position)
        # Una ruta de «Ir a» pedida durante la decodificación es posterior a la de la navegación.
        if self._pending_location is not None and self._pending_location[0] == position:
            path = self._pending_location[1]
        self._pending_location = None
        try:
            tree = document.bod(position)
        except D2ScriptViewerError as error:
            self.property_view.show_message(title, _("No se pudo decodificar: {error}").format(error=error))
            self.details.show(document, info)
            if isinstance(path, Location):
                self.property_view.goto_failed(_("Este objeto no se pudo decodificar: {error}").format(error=error))
            return
        self.property_view.show_bod(title, tree, document.edited_paths(position))
        if isinstance(path, Location):
            self._reveal_location(position, path)
        elif path:
            self.property_view.reveal(path)
        self._show_details(position)
        self._finish_display()

    def _show_details(self, position: int) -> None:
        assert self.document is not None
        document = self.document
        info = document.objects[position]
        extra: list[tuple[str, str]] = []
        tree = document.cached_bod(position)
        if isinstance(tree, script.ScriptTree):
            body = tree.script
            parts = (
                ngettext("{count:,} miembro", "{count:,} miembros", len(body.members)).format(count=len(body.members)),
                ngettext("{count:,} valor inicial", "{count:,} valores iniciales", len(body.initial_values)).format(
                    count=len(body.initial_values)),
                ngettext("{count:,} función", "{count:,} funciones", len(body.functions)).format(count=len(body.functions)),
                ngettext("{count:,} estado", "{count:,} estados", len(body.states)).format(count=len(body.states)),
            )
            extra.append((_("Script"), ", ".join(parts)))
            editable = len(script.editable_leaves(body))
            extra.append((_("Editables"), ngettext("{count:,} literal o valor", "{count:,} literales o valores",
                                                   editable).format(count=editable)))
        elif tree is not None:
            extra.append((_("BOD"), _("versión {version}, campo desconocido {flags}").format(
                version=tree.version, flags=tree.flags)))
            extra.append(
                (_("Nombres internos"),
                 _("{count:,} al abrir (máx. {length} caracteres)").format(
                     count=tree.declared_name_count, length=tree.declared_max_name_length))
            )
        if document.is_modified(position):
            changed = len(document.edited_paths(position))
            extra.append(
                (_("Estado"), ngettext("modificado: {count:,} propiedad, {size:,} bytes al guardar",
                                      "modificado: {count:,} propiedades, {size:,} bytes al guardar", changed).format(
                    count=changed, size=len(document.blob(position))))
            )
        else:
            extra.append((_("Estado"), _("sin cambios")))
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
            return _("No hay ningún objeto seleccionado")
        if self.saving:
            return _("Espera a que termine el guardado")
        try:
            state = edits.parse_state(node, text, self.indexes.dictionary if self.indexes else None)
        except EditError as error:
            return str(error)
        if state == edits.get_state(node):
            return None
        if not self._confirm_edit(position, path, node, state):
            return None
        try:
            group = document.edit(position, path, state)
        except EditError as error:
            return str(error)
        if group is not None:
            self._after_change(group, reveal=False)
        return None

    def _confirm_edit(self, position: int, path: tuple, node: object, state: object) -> bool:
        """Pide confirmación si el campo parece un identificador o si la cadena es nueva."""
        assert self.document is not None
        warnings = [edits.identifier_warning(edits.field_name(self.document.bod(position), path), node)]
        if isinstance(state, bod.Name):
            warnings.append(edits.new_name_warning(state, self.indexes.dictionary if self.indexes else None))
        message = "\n\n".join(warning for warning in warnings if warning)
        if not message:
            return True
        return bool(self.ask(APP_NAME, message + "\n\n" + _("¿Aplicar el cambio de todos modos?"), icon="warning"))

    def pick_reference(self, node: object, path: tuple) -> None:
        document, position = self.document, self.position
        if document is None or position is None or not isinstance(node, bod.ExternalRef) or self.saving:
            return
        title = i18n.text(document.full_label(position, path))
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
            self.status_var.set(_("Ese objeto no tiene cambios"))
            return
        self._after_change(group, reveal=position != self.position)

    def _structure_from_menu(self, action: str) -> None:
        selected = self.property_view.selected()
        if selected is None:
            self.status_var.set(_("Selecciona antes una propiedad en el panel central"))
            return
        node, path = selected
        if action not in self.property_view.structure_actions(node, path):
            self.status_var.set(_("Esa operación no se puede hacer sobre la propiedad seleccionada"))
            return
        self.structure_action(action, path)

    def structure_action(self, action: str, path: tuple) -> None:
        """Duplicar, eliminar, mover, poner a nulo o rellenar (fase 5) en el objeto mostrado."""
        document, position = self.document, self.position
        if document is None or position is None or self.saving:
            return
        self.property_view.cancel_edit()
        if action == "fill":
            self.fill_null(path)
            return
        try:
            if action == "duplicate":
                group = document.duplicate_item(position, path)
            elif action == "remove":
                group = document.remove_item(position, path)
            elif action in ("up", "down"):
                group = document.move_item(position, path, -1 if action == "up" else 1)
            elif action == "null":
                group = document.set_null(position, path)
            else:
                return
        except EditError as error:
            self.property_view.set_hint(str(error), "error")
            return
        if group is None:
            self.status_var.set(_("El elemento ya está en ese extremo de la lista"))
            return
        self._after_change(group, reveal=True)
        container = bod.resolve(document.bod(position), path[:-1]) if path else None
        if action == "duplicate" and isinstance(container, (bod.BodMap, bod.BodList)) and container.mode == bod.MODE_PAIRS:
            self.property_view.set_hint(
                _("La copia repite la clave de la entrada original: cámbiala antes de guardar (una clave repetida "
                  "impide guardar)."), "warn", hold=True,
            )

    def fill_null(self, path: tuple) -> None:
        document, position = self.document, self.position
        if document is None or position is None:
            return
        if self.indexes is None:
            self.status_var.set(_("Espera a que termine el índice del archivo para rellenar nulos"))
            return
        tree = document.bod(position)
        key = slot_key(tree, path)
        classes = self.indexes.slots.classes(key)
        references = self.indexes.slots.references(key)
        title = i18n.text(document.full_label(position, path))
        if not classes and not references:
            self.inform(APP_NAME, _("En el archivo no aparece ningún objeto ni referencia en el hueco {slot}, así que "
                                    "no hay de dónde copiar uno con seguridad.").format(slot=f"{key[0]}.{key[1]}"))
            return
        choice = FillNullDialog(self, document, title, key, classes, references).choose()
        if choice is None:
            return
        try:
            if choice[0] == "copy":
                value: object = document.copy_example(choice[1], choice[2], choice[3])
            else:
                value = None
        except EditError as error:
            self.alert(APP_NAME, str(error))
            return
        if value is None:
            identity = ReferencePicker(self, document, None, title).choose()
            if identity is None:
                return
            value = bod.ExternalRef(*identity)
        try:
            group = document.fill_null(position, path, value)
        except EditError as error:
            self.alert(APP_NAME, str(error))
            return
        self._after_change(group, reveal=True)

    def undo(self) -> None:
        if self.document is None or self.saving:
            return
        self.property_view.cancel_edit()
        group = self.document.undo()
        if group is not None:
            self._after_change(group, reveal=True, prefix=_("Deshecho: {description}"), forward=False)

    def redo(self) -> None:
        if self.document is None or self.saving:
            return
        self.property_view.cancel_edit()
        group = self.document.redo()
        if group is not None:
            self._after_change(group, reveal=True, prefix=_("Rehecho: {description}"))

    def _after_change(self, group: EditGroup, *, reveal: bool, prefix: str = "", forward: bool = True) -> None:
        """Pone al día todas las vistas tras editar, deshacer, rehacer o revertir.

        Si la operación cambia la estructura (o el árbol entero, al revertir), el
        panel de propiedades se repinta: sus filas apuntaban a nodos que ya no están.
        """
        document = self.document
        assert document is not None
        if self.indexes is not None:
            for position in group.positions:
                self.indexes.references.set_object(position, references_in(position, document.bod(position)))
        self.object_tree.set_modified(document.modified_positions)
        operation = group.edits[-1] if forward else group.edits[0]
        focus = operation.focus(forward)
        if reveal and operation.position != self.position:
            self.navigate(operation.position, focus)
        elif self.position is not None and document.cached_bod(self.position) is not None:
            edited = document.edited_paths(self.position)
            if group.structural and self.position in group.positions:
                tree = document.bod(self.position)
                self.property_view.rebuild(self._object_title(self.position), tree, edited, focus if reveal else None)
            else:
                self.property_view.set_edited(edited)
                if reveal and focus:
                    self.property_view.reveal(focus)
            self._show_details(self.position)
        if self.pending_window is not None and self.pending_window.winfo_exists():
            self.pending_window.refresh()
        self._update_change_state()
        description = i18n.text(group.description)
        self.status_var.set(prefix.format(description=description) if prefix else description)

    def _update_change_state(self) -> None:
        document = self.document
        count = document.change_count if document else 0
        if document is not None and count:
            objects = len(document.modified_positions)
            self.changes_var.set("● " + _("{changes} sin guardar en {objects}").format(
                changes=ngettext("{count:,} cambio", "{count:,} cambios", count).format(count=count),
                objects=ngettext("{count:,} objeto", "{count:,} objetos", objects).format(count=objects)))
            self.changes_label.configure(style="StatusWarn.TLabel")
        else:
            self.changes_var.set(_("Sin cambios") if document else "")
            self.changes_label.configure(style="Status.TLabel")
        undo = document.undo_description if document else None
        redo = document.redo_description if document else None
        self.edit_menu.entryconfigure(
            0, label=_("Deshacer: {action}").format(action=self._short(undo)) if undo else _("Deshacer"),
            state="normal" if undo else "disabled",
        )
        self.edit_menu.entryconfigure(
            1, label=_("Rehacer: {action}").format(action=self._short(redo)) if redo else _("Rehacer"),
            state="normal" if redo else "disabled",
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
        self.title(_("{dirty}{name}{app} {version} — scripts.obsp de Darksiders II Deathinitive Edition").format(
            dirty=dirty, name=name, app=APP_NAME, version=__version__))

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
                self.inform(APP_NAME, _("{name} es la copia del original y nunca se sobrescribe.\n\n"
                                        "Usa «Guardar como» para guardar los cambios en otro archivo.").format(name=target.name))
            self.save_as()
            return
        if not document.change_count:
            self.status_var.set(_("No hay cambios que guardar"))
            return
        self._start_save(target)

    def save_as(self) -> None:
        document = self.document
        if document is None or self.saving or not self._commit_pending_editor():
            return
        current = document.path
        selected = filedialog.asksaveasfilename(
            parent=self,
            title=_("Guardar como"),
            defaultextension=".obsp",
            initialdir=str(current.parent) if current else None,
            initialfile=current.name if current and not saving.is_original_copy(current) else "scripts.obsp",
            filetypes=[(_("Scripts de Darksiders II"), "*.obsp"), (_("Todos los archivos"), "*.*")],
        )
        if not selected:
            return
        target = Path(selected)
        if saving.is_original_copy(target):
            messagebox.showerror(APP_NAME, _("Los archivos *.original.obsp son copias del original y nunca se "
                                             "sobrescriben. Elige otro nombre."), parent=self)
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
                _("{copy} ya existe y no se tocará.").format(copy=copy.name)
                if copy.exists()
                else _("Antes se creará {copy}: copia exacta del archivo actual, verificada y de solo lectura.").format(
                    copy=copy.name)
            )
            if not self.ask(
                APP_NAME,
                _("Vas a sobrescribir {target} en la instalación del juego.\n\n"
                  "• {copy_note}\n"
                  "• Darksiders II debe estar cerrado.\n"
                  "• «Verificar integridad» de Steam devolverá el original.\n\n¿Guardar?").format(
                    target=target.name, copy_note=copy_note),
                icon="warning",
            ):
                return
            self._game_save_confirmed.add(target)
        try:
            plan = saving.prepare_save(document)
        except D2ScriptViewerError as error:
            self.alert(APP_NAME, str(error))
            return
        if plan.warnings:
            listed = "\n".join(f"• {warning}" for warning in plan.warnings[:15])
            hidden = len(plan.warnings) - 15
            more = "\n" + _("… y {count:,} más").format(count=hidden) if hidden > 0 else ""
            if not self.ask(APP_NAME, _("Avisos antes de guardar:\n{warnings}\n\n¿Guardar de todos modos?").format(
                    warnings=listed + more), icon="warning"):
                return
        self.saving = True
        self._after_save = then
        self.status_var.set(_("Guardando {name}…").format(name=target.name))
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
            self.status_var.set(_("No se guardó"))
            message = str(payload) if isinstance(payload, (D2ScriptViewerError, OSError)) else repr(payload)
            if isinstance(payload, saving.WrittenMismatchError) and document is not None and document.path:
                if self.ask(APP_NAME, message + "\n\n" + _("¿Restaurar ahora la copia del original?"), icon="error"):
                    self.restore_original_file(confirm=False)
                return
            messagebox.showerror(APP_NAME, _("No se guardó el archivo.\n\n{message}").format(message=message), parent=self)
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
            self.inform(APP_NAME, _("Este archivo ya es la copia del original."))
            return
        copy = saving.original_copy_path(path)
        if not copy.is_file():
            self.inform(APP_NAME, _("No existe {copy} junto a {name}.\n\n"
                                    "La copia se crea la primera vez que se guarda encima del archivo.").format(
                copy=copy.name, name=path.name))
            return
        if confirm:
            changes = document.change_count
            lost = ("\n" + ngettext("• Se perderá {count:,} cambio sin guardar.", "• Se perderán {count:,} cambios sin guardar.",
                                    changes).format(count=changes) if changes else "")
            if not self.ask(
                APP_NAME,
                _("Se copiará {copy} encima de {name} y se verificará.\n"
                  "• {copy} se conserva.\n"
                  "• La versión actual irá a {folder} si las copias rotativas están activas.{lost}\n\n"
                  "¿Restaurar?").format(copy=copy.name, name=path.name, folder=saving.BACKUP_DIR, lost=lost),
                icon="warning",
            ):
                return
        self.saving = True
        self.status_var.set(_("Restaurando {name}…").format(name=path.name))
        rotating = self.rotating_var.get()
        self._spawn("restore", lambda: saving.restore_original(path, rotating_backups=rotating))

    def _on_restore(self, token: int, payload: object) -> None:
        if token != self.tokens["restore"]:
            return
        self.saving = False
        if isinstance(payload, BaseException):
            self.status_var.set(_("No se restauró"))
            message = str(payload) if isinstance(payload, (D2ScriptViewerError, OSError)) else repr(payload)
            messagebox.showerror(APP_NAME, _("No se restauró el original.\n\n{message}").format(message=message), parent=self)
            return
        assert isinstance(payload, saving.RestoreResult)
        if payload.is_steam:
            restored = _("{name} vuelve a ser el original de Steam.\nSHA-256 {sha}")
        else:
            restored = _("{name} vuelve a ser la copia del original.\nSHA-256 {sha}")
        self.inform(APP_NAME, restored.format(name=payload.path.name, sha=payload.sha256))
        self.open_file(payload.path)

    # --- Exportar y parches (fase 8) --------------------------------------------------

    def _snapshot(self) -> Document | None:
        """Copia del estado actual para trabajar en un hilo sin competir con las ediciones."""
        document = self.document
        if document is None or self.saving or self.exporting or not self._commit_pending_editor():
            return None
        try:
            return Document.from_bytes(document.current_data(), document.path)
        except D2ScriptViewerError as error:
            self.alert(APP_NAME, str(error))
            return None

    def export_files(self, folder: Path | None = None) -> None:
        document = self.document
        if document is None or self.saving or self.exporting:
            return
        if folder is None:
            selected = filedialog.askdirectory(parent=self, title=_("Exportar a JSON y CSV (carpeta vacía)"),
                                               mustexist=False)
            if not selected:
                return
            folder = Path(selected)
        try:
            export.check_destination(folder)
        except D2ScriptViewerError as error:
            self.alert(APP_NAME, str(error))
            return
        snapshot = self._snapshot()
        if snapshot is None:
            return
        unsaved, source = set(document.modified_positions), document.path
        token = self.tokens["export"] + 1

        def progress(done: int, total: int) -> None:
            self.messages.put(("export-progress", token, (done, total)))

        self.exporting = True
        self.status_var.set(_("Exportando a {folder}…").format(folder=folder))
        self._spawn("export", lambda: export.export_document(snapshot, folder, progress=progress,
                                                             unsaved=unsaved, source=source))

    def _on_export_progress(self, token: int, payload: object) -> None:
        if token != self.tokens["export"]:
            return
        done, total = payload  # type: ignore[misc]
        self.progress.configure(maximum=max(total, 1), value=done)

    def _on_export(self, token: int, payload: object) -> None:
        if token != self.tokens["export"]:
            return
        self.exporting = False
        self.progress.configure(value=0)
        if isinstance(payload, BaseException):
            self.status_var.set(_("No se exportó"))
            message = str(payload) if isinstance(payload, (D2ScriptViewerError, OSError)) else repr(payload)
            self.alert(APP_NAME, _("No se exportó.\n\n{message}").format(message=message))
            return
        assert isinstance(payload, export.ExportResult)
        self.status_var.set(payload.summary())
        self.inform(APP_NAME, payload.summary())

    def export_patch(self, target: Path | None = None) -> None:
        document = self.document
        if document is None or self.saving or self.exporting:
            return
        try:
            base_data, base_label = patches.base_for(document)
        except OSError as error:
            self.alert(APP_NAME, _("No se pudo leer el original: {error}").format(error=error))
            return
        snapshot = self._snapshot()
        if snapshot is None:
            return
        if snapshot.obsp.data == base_data:
            self.inform(APP_NAME, _("No hay diferencias con la base ({base}): no hay nada que poner en un parche.").format(
                base=base_label))
            return
        if target is None:
            current = document.path
            selected = filedialog.asksaveasfilename(
                parent=self,
                title=_("Exportar parche"),
                defaultextension=patches.PATCH_SUFFIX,
                initialdir=str(current.parent) if current and not self._in_game_folder(current) else None,
                initialfile=_("cambios") + patches.PATCH_SUFFIX,
                filetypes=[(_("Parches de D2ScriptViewer"), "*" + patches.PATCH_SUFFIX), (_("Todos los archivos"), "*.*")],
            )
            if not selected:
                return
            target = Path(selected)
        destination = target

        def work() -> tuple[Path, str, dict[str, object]]:
            patch = patches.create_patch(base_data, snapshot)
            patches.save_patch(patch, destination)
            return destination, base_label, patch

        self.exporting = True
        self.status_var.set(_("Creando el parche y comprobándolo sobre la base…"))
        self.progress.configure(mode="indeterminate")
        self.progress.start(15)
        self._spawn("patch", work)

    def _on_patch(self, token: int, payload: object) -> None:
        if token != self.tokens["patch"]:
            return
        self.exporting = False
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        if isinstance(payload, BaseException):
            self.status_var.set(_("No se creó el parche"))
            message = str(payload) if isinstance(payload, (D2ScriptViewerError, OSError)) else repr(payload)
            self.alert(APP_NAME, _("No se creó el parche.\n\n{message}").format(message=message))
            return
        target, base_label, patch = payload  # type: ignore[misc]
        steam = _("original de Steam") if patch["base"]["original_de_steam"] else _("no es el original de Steam")
        self.status_var.set(_("Parche guardado en {name}").format(name=target.name))
        self.inform(
            APP_NAME,
            _("Parche guardado en {path}.\n\n• {summary}.\n"
              "• Base: {base} ({steam}).\n"
              "• Comprobado: reaplicado sobre la base da exactamente el archivo actual.").format(
                path=target, summary=patches.patch_summary(patch), base=base_label, steam=steam),
        )

    def apply_patch_file(self, source: Path | None = None) -> None:
        document = self.document
        if document is None or self.saving or self.exporting or not self._commit_pending_editor():
            return
        if source is None:
            selected = filedialog.askopenfilename(
                parent=self,
                title=_("Aplicar parche"),
                filetypes=[(_("Parches de D2ScriptViewer"), "*" + patches.PATCH_SUFFIX), (_("Todos los archivos"), "*.*")],
            )
            if not selected:
                return
            source = Path(selected)
        try:
            patch = patches.load_patch(source)
            group = patches.apply_patch(document, patch, source.name)
        except D2ScriptViewerError as error:
            self.alert(APP_NAME, _("No se aplicó el parche.\n\n{message}").format(message=error))
            return
        if group is None:
            self.inform(APP_NAME, _("El parche no tiene cambios."))
            return
        self._after_change(group, reveal=True)
        self.inform(
            APP_NAME,
            _("Parche aplicado: {summary}.\n\nSon cambios pendientes: revísalos con Ctrl+P, "
              "deshazlos todos con Ctrl+Z o guárdalos con Ctrl+S.").format(summary=patches.patch_summary(patch)),
        )

    # --- Búsqueda ------------------------------------------------------------------------

    def _from_main_window(self, event: tk.Event) -> bool:
        """Si la tecla llegó a la ventana principal: en otra (la búsqueda global, un diálogo) no salta a ella."""
        widget = event.widget
        return isinstance(widget, tk.Misc) and widget.winfo_toplevel() is self

    def _on_find_key(self, event: tk.Event) -> str | None:
        if not self._from_main_window(event):
            return None
        self.focus_object_search()
        return "break"

    def focus_object_search(self) -> None:
        """Ctrl+F: la barra de búsqueda del panel de propiedades (fase 10)."""
        self.property_view.focus_search()

    def open_search(self) -> None:
        if self.document is None:
            return
        if self.search_window is not None and self.search_window.winfo_exists():
            self.search_window.lift()
            self.search_window.focus_set()
            return
        self.search_window = SearchWindow(self, self.document, self.navigate)

    # --- Ir a una ruta (fase 11) -----------------------------------------------------------

    def _on_goto_key(self, event: tk.Event) -> str | None:
        if not self._from_main_window(event):
            return None
        self.open_goto()
        return "break"

    def _clipboard_text(self) -> str | None:
        try:
            return self.clipboard_get()
        except tk.TclError:  # vacío, con una imagen o archivos, o bloqueado por otro programa
            return None

    def open_goto(self) -> None:
        """Ctrl+G: la barra «Ir a», rellena con el portapapeles si parece una ruta.

        Con la barra ya abierta solo vuelve a ella, sin pisar lo escrito.
        """
        if self.document is None:
            self.status_var.set(_("Abre antes un scripts.obsp con Archivo → Abrir (Ctrl+O)"))
            return
        view = self.property_view
        if view.goto_visible:
            view.show_goto()
            return
        clipboard = self.read_clipboard()
        if clipboard is not None and self.document.looks_like_location(clipboard, self.position):
            view.show_goto(clipboard.strip())
        else:
            view.show_goto()

    def full_label(self, path: tuple) -> str:
        """``objeto · propiedad`` de una fila del objeto abierto (Copiar ruta completa), como se ve."""
        assert self.document is not None and self.position is not None
        return i18n.text(self.document.full_label(self.position, path))

    def go_to_location(self, text: str) -> None:
        """Intro en la barra «Ir a»: analiza la ruta y va a ella, quizá en otro objeto."""
        document = self.document
        view = self.property_view
        if document is None:
            return
        self._pending_location = None  # solo cuenta la última petición
        try:
            location = document.parse_location(text)
        except PathError as error:
            view.goto_failed(str(error), error.start, error.end)
            return
        position = self.position if location.position is None else location.position
        if position is None:
            view.goto_failed(_("Selecciona antes un objeto, o escribe el objeto delante: objeto · propiedad"))
            return
        if position != self.position:
            self.navigate(position, location)
        elif view.document is not None:
            self._reveal_location(position, location)
        elif self._decoding == position:
            self._pending_location = (position, location)
        else:
            view.goto_failed(_("Este objeto no se pudo decodificar: no tiene propiedades a las que ir"))

    def cancel_goto(self) -> None:
        """Escape en la barra «Ir a»: un salto que espera a la decodificación ya no se hace."""
        self._pending_location = None

    def _reveal_location(self, position: int, location: Location) -> None:
        """Selecciona la fila de ``location`` en el objeto mostrado o, si falla, la más profunda válida."""
        assert self.document is not None
        view = self.property_view
        view.flush_search()
        if not location.steps:
            view.goto_done()
            return
        match = bod.find_path(self.document.bod(position), list(location.steps), vocabulary.NAMES)
        if match.path:
            view.reveal(match.path)
        if match.failed is None:
            view.goto_done(match.message)
        else:
            view.goto_failed(match.message, match.failed.start, match.failed.end)

    # --- Idioma (fase 12) -------------------------------------------------------------------

    def change_language(self, code: str) -> bool:
        """Cambia el idioma de la interfaz en caliente: reconstruye menús y paneles sin cerrar la ventana.

        Se conservan el documento con sus cambios sin guardar, deshacer y rehacer (sus
        descripciones se muestran en el idioma nuevo), el objeto y la fila seleccionados, el
        historial, el índice, los filtros de la lista, la búsqueda en el objeto y el último texto
        de «Ir a». Se cierran la búsqueda global y los cambios pendientes. Mientras se guarda, se
        restaura o se exporta no se cambia. La elección se guarda al momento en ``config.json``.
        Devuelve si el idioma quedó cambiado.
        """
        if code not in i18n.LANGUAGES:
            raise ValueError(f"Idioma desconocido: {code!r}")
        if code == i18n.language():
            self.language_var.set(code)
            return True
        if self.saving or self.exporting:
            self.language_var.set(i18n.language())
            self.status_var.set(_("Espera a que termine la operación en curso para cambiar el idioma"))
            return False
        self.settings["language"] = code
        if self.persist_settings:
            self._store_settings()
        state = self._view_state()
        i18n.set_language(code)
        self.language_var.set(code)
        self._rebuild_ui(state)
        self.status_var.set(_("Idioma de la interfaz: {language}").format(language=i18n.LANGUAGES[code]))
        return True

    def _view_state(self) -> dict[str, object]:
        """Lo que se ve y no depende del idioma, para recuperarlo tras reconstruir la ventana."""
        view = self.property_view
        selected = view.selected()
        name, kind, value = view.search_query()
        return {
            "path": selected[1] if selected else None,
            "search": (name, vocabulary.canonical_type(kind), value),
            "goto": view.goto_var.get(),
            "filters": self.object_tree.filters(),
            "sashes": [self.pane.sashpos(index) for index in range(2)],
        }

    def _rebuild_ui(self, state: dict[str, object]) -> None:
        view = self.property_view
        view.cancel_edit()
        view.cancel_pending()
        self.object_tree.cancel_pending()
        self._close_secondary_windows()
        _release_traces(self.object_tree)
        _release_traces(view)
        _release_traces(self.details)
        for child in list(self.children.values()):
            child.destroy()
        self._decoding = None
        self._pending_location = None
        self._build_menu()
        self._build_ui()
        view = self.property_view
        name, kind, value = state["search"]  # type: ignore[misc]
        view.set_search_query(name, vocabulary.shown_type(kind), value)
        view.goto_var.set(str(state["goto"]))
        self._update_history_buttons()
        if self.document is not None:
            self._show_document()
            self.object_tree.restore_filters(state["filters"])  # type: ignore[arg-type]
            if self.position is not None:
                self.object_tree.select_position(self.position)
                self._show_object(self.position, state["path"])  # type: ignore[arg-type]
        else:
            self._update_title()
        sashes = state["sashes"]

        def place() -> None:
            self._sash_after = None
            for index, position in enumerate(sashes):  # type: ignore[arg-type]
                self.pane.sashpos(index, position)

        if self._sash_after is not None:
            self.after_cancel(self._sash_after)
        self._sash_after = self.after_idle(place)
        # Los paneles viejos forman ciclos: se recogen aquí, en el hilo de Tk, y no cuando al
        # recolector le toque en un hilo de trabajo (sus variables de Tk no se borran desde otro hilo).
        gc.collect()

    # --- Cierre --------------------------------------------------------------------------

    def _about(self) -> None:
        messagebox.showinfo(
            APP_NAME,
            _("{app} {version}\n\nVisor y editor de scripts.obsp de Darksiders II Deathinitive Edition."
              "\n\nLicencia MIT · BOTProT800").format(app=APP_NAME, version=__version__),
            parent=self,
        )

    def _on_close(self) -> None:
        if not self._resolve_unsaved(_("¿Guardarlos antes de salir?"), then=self._close_now):
            return
        self._close_now()

    def _store_settings(self) -> None:
        self.settings["geometry"] = self.geometry()
        self.settings["group_by"] = self.object_tree.group_mode
        self.settings["rotating_backups"] = bool(self.rotating_var.get())
        save_settings(self.settings)

    def _close_now(self) -> None:
        self.index_cancel.set()
        if self.persist_settings:
            self._store_settings()
        self.destroy()

    def destroy(self) -> None:
        self.index_cancel.set()
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        if self._sash_after is not None:
            self.after_cancel(self._sash_after)
            self._sash_after = None
        if self.search_window is not None and self.search_window.winfo_exists():
            self.search_window.close()
        self.property_view.cancel_edit()
        self.property_view.cancel_pending()
        self.object_tree.cancel_pending()
        super().destroy()
        # El idioma es del proceso: al cerrar la ventana vuelve el de la CLI (y cada test empieza igual).
        i18n.reset()


def _release_traces(panel: object) -> None:
    """Quita las trazas de las variables de Tk de ``panel`` antes de destruirlo.

    Tcl guarda la función de cada traza, y esa función retiene el panel: sin esto, un panel
    sustituido al cambiar de idioma no se liberaría nunca.
    """
    for value in vars(panel).values():
        if isinstance(value, tk.Variable):
            for modes, callback in value.trace_info():
                value.trace_remove(modes, callback)


def main(initial: Path | None = None) -> None:
    app = ViewerApp(initial)
    app.mainloop()
