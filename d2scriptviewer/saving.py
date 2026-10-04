# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Guardar en ``.obsp``, copia del original, copias rotativas y restaurar (sección 4 del plan).

Secuencia de :func:`execute_save`:

1. **Construir en memoria** (:func:`prepare_save`, en el hilo de la interfaz): los
   blobs sin cambios se copian tal cual y los modificados se recodifican; se
   regeneran tabla de cadenas, índice y cabecera.
2. **Autoverificar**: se vuelve a parsear el resultado y se comprueba que tiene los
   mismos objetos e identidades, que los blobs no modificados son idénticos, que
   los modificados decodifican al árbol editado y que los hashes de la tabla de
   cadenas y de los objetos modificados son los de sus textos.
3. **Comprobar que el destino se puede escribir** (juego abierto, solo lectura, permisos).
4. **Copia del original**: si no existe ``X.original.obsp``, se copia el archivo tal
   como está en disco, se verifica su SHA-256 y se marca de solo lectura. Si ya
   existe, no se toca nunca.
5. **Copia rotativa** de la versión anterior en ``.d2sv_backups`` (las últimas 5).
6. **Escribir** en ``X.obsp.tmp`` con ``flush`` + ``fsync`` y sustituir con ``os.replace``.
7. **Comprobar**: se relee el archivo final y su SHA-256 se compara con el de memoria.

Si algo falla antes del paso 6, el archivo de destino queda intacto.
"""

from __future__ import annotations

import datetime as _dt
import errno
import hashlib
import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .document import Document
from .errors import D2ScriptViewerError, FormatError, SaveError
from .formats import bod
from .formats.hashes import document_names, first_wrong_name, name_hash
from .formats.obsp import STEAM_ORIGINAL_SHA256, ObspFile
from .validation import validate

ORIGINAL_SUFFIX = ".original.obsp"
TMP_SUFFIX = ".tmp"
BACKUP_DIR = ".d2sv_backups"
KEEP_BACKUPS = 5

#: Puntos donde los tests pueden simular un fallo (``fail_at``).
STEPS = ("verified", "checked", "original", "backup", "tmp_written", "replaced")

#: Errores de Windows que significan «otro proceso tiene el archivo abierto».
_SHARING_VIOLATION = 32
_LOCK_VIOLATION = 33
_ACCESS_DENIED = 5


class WrittenMismatchError(SaveError):
    """Se escribió el destino pero al releerlo no coincide: hay que ofrecer restaurar."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def is_original_copy(path: Path) -> bool:
    return path.name.casefold().endswith(ORIGINAL_SUFFIX)


def original_copy_path(path: Path) -> Path:
    """``scripts.obsp`` → ``scripts.original.obsp``, en la misma carpeta."""
    stem = path.name[: -len(path.suffix)] if path.suffix else path.name
    return path.with_name(stem + ORIGINAL_SUFFIX)


def tmp_path(path: Path) -> Path:
    return path.with_name(path.name + TMP_SUFFIX)


def backup_folder(path: Path) -> Path:
    return path.parent / BACKUP_DIR


def cleanup_orphan_tmp(path: Path) -> bool:
    """Borra un ``X.obsp.tmp`` que dejó un guardado interrumpido. Devuelve si había uno."""
    orphan = tmp_path(path)
    if orphan.is_file():
        try:
            orphan.unlink()
        except OSError:
            return False
        return True
    return False


# --- Estado del archivo -----------------------------------------------------------------------


@dataclass(frozen=True)
class FileStatus:
    kind: str
    """``steam``, ``modified``, ``unknown`` u ``original-copy``."""
    text: str
    original_copy: Path | None


def file_status(path: Path | None, data_sha256: str) -> FileStatus:
    """Original de Steam, modificado (hay copia del original) o desconocido."""
    copy = original_copy_path(path) if path is not None and not is_original_copy(path) else None
    has_copy = copy is not None and copy.is_file()
    if path is not None and is_original_copy(path):
        steam = " (original de Steam)" if data_sha256 == STEAM_ORIGINAL_SHA256 else ""
        return FileStatus("original-copy", f"Copia del original{steam}: solo «Guardar como»", None)
    if data_sha256 == STEAM_ORIGINAL_SHA256:
        return FileStatus("steam", "Original de Steam", copy if has_copy else None)
    if has_copy:
        return FileStatus("modified", f"Modificado (copia del original en {copy.name})", copy)
    return FileStatus("unknown", "No es el original de Steam y no hay copia del original", None)


# --- Construcción y autoverificación ----------------------------------------------------------


@dataclass
class SavePlan:
    """El archivo nuevo ya construido y lo necesario para verificarlo sin tocar el documento."""

    data: bytes
    sha256: str
    source: ObspFile
    modified: dict[int, bytes]
    """Posición → blob esperado de cada objeto modificado."""
    warnings: list[str] = field(default_factory=list)
    """Avisos de la validación que no impiden guardar (la interfaz pide confirmación)."""


def prepare_save(document: Document) -> SavePlan:
    """Paso 1: valida y construye el archivo en memoria. Rápido; se llama desde la interfaz.

    Los errores de validación (claves repetidas, referencias sin destino) impiden
    guardar; los avisos viajan en el plan.
    """
    report = validate(document)
    if report.errors:
        listed = "\n".join(f"• {error}" for error in report.errors[:20])
        more = f"\n… y {len(report.errors) - 20} más" if len(report.errors) > 20 else ""
        raise SaveError(f"No se puede guardar todavía:\n{listed}{more}")
    modified = {position: document.blob(position) for position in document.modified_positions}
    try:
        data = document.current_data()
    except FormatError as error:
        raise SaveError(f"No se pudo construir el archivo: {error}") from error
    return SavePlan(data, sha256(data), document.obsp, modified, list(report.warnings))


def verify_plan(plan: SavePlan) -> None:
    """Paso 2: el resultado se vuelve a leer y se compara con lo esperado."""
    try:
        rebuilt = ObspFile.parse(plan.data)
    except FormatError as error:
        raise SaveError(f"El archivo construido no se puede volver a leer: {error}") from error
    source = plan.source
    if len(rebuilt.entries) != len(source.entries):
        raise SaveError("El archivo construido no tiene el mismo número de objetos")
    if rebuilt.layout_problems():
        raise SaveError("El archivo construido no tiene los blobs contiguos: " + "; ".join(rebuilt.layout_problems()))
    if (rebuilt.header.version, rebuilt.header.unknown) != (source.header.version, source.header.unknown):
        raise SaveError("La cabecera del archivo construido no conserva versión y campo desconocido")
    for position, (old, new) in enumerate(zip(source.entries, rebuilt.entries)):
        same_identity = (
            old.path_hash, old.object_id, old.group, old.kind, old.name_hash, old.folder_hash, old.class_hash,
        ) == (
            new.path_hash, new.object_id, new.group, new.kind, new.name_hash, new.folder_hash, new.class_hash,
        )
        if not same_identity:
            raise SaveError(f"El objeto {position} cambió de identidad al construir el archivo")
        blob = rebuilt.blob(position)
        expected = plan.modified.get(position)
        if expected is None:
            if blob != source.blob(position):
                raise SaveError(f"El objeto {position} no se editó y sus bytes cambiaron")
            continue
        if blob != expected:
            raise SaveError(f"El objeto {position} no contiene el árbol editado")
        try:
            tree = bod.decode(blob)
            if bod.encode(tree) != blob:
                raise SaveError(f"El objeto editado {position} no se recodifica igual")
        except FormatError as error:
            raise SaveError(f"El objeto editado {position} no decodifica: {error}") from error
        wrong = first_wrong_name(document_names(tree))
        if wrong is not None:
            raise SaveError(
                f"El objeto editado {position} tiene la cadena «{wrong.text[:60]}» con un hash que no le "
                f"corresponde ({wrong.hash:016X}; debería ser {name_hash(wrong.text):016X})"
            )
    for value_hash, text in source.strings.items():
        if rebuilt.strings.get(value_hash, text) != text:
            raise SaveError("La tabla de cadenas cambió al construir el archivo")
    for value_hash, text in rebuilt.strings.items():
        if name_hash(text) != value_hash:
            raise SaveError(
                f"La tabla de cadenas tiene «{text[:60]}» con un hash que no le corresponde ({value_hash:016X})"
            )


# --- Escritura --------------------------------------------------------------------------------


def _locked_message(path: Path) -> str:
    return f"{path.name} está abierto por otro programa. Cierra Darksiders II y vuelve a intentarlo."


def describe_os_error(error: OSError, path: Path) -> str:
    winerror = getattr(error, "winerror", None)
    if winerror in (_SHARING_VIOLATION, _LOCK_VIOLATION):
        return _locked_message(path)
    if winerror == _ACCESS_DENIED or error.errno in (errno.EACCES, errno.EPERM):
        if path.exists() and not os.access(path, os.W_OK):
            return f"{path.name} es de solo lectura. Quítale ese atributo o usa «Guardar como»."
        return (
            f"No hay permiso para escribir en {path.parent}. Si el juego sigue abierto, ciérralo; "
            "si no, ejecuta la herramienta con permisos suficientes o guarda en otra carpeta."
        )
    if error.errno == errno.ENOSPC:
        return f"No queda espacio en el disco de {path.parent}."
    return f"No se pudo escribir {path}: {error}"


def _probe_write(path: Path) -> None:
    """Abre ``path`` para escritura sin modificarlo; lanza ``OSError`` con el código de Windows.

    ``open()`` no sirve para distinguir «en uso» de «sin permiso»: la CRT convierte
    los dos en ``EACCES``. ``CreateFileW`` devuelve el código exacto.
    """
    if sys.platform != "win32":
        with open(path, "r+b"):
            return
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.restype = wintypes.HANDLE
    create.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    generic_read_write = 0x80000000 | 0x40000000
    share_all = 0x1 | 0x2 | 0x4
    open_existing = 3
    handle = create(str(path), generic_read_write, share_all, None, open_existing, 0x80, None)
    if handle is None or handle == wintypes.HANDLE(-1).value:
        code = ctypes.get_last_error()
        raise OSError(errno.EACCES, ctypes.FormatError(code).strip(), str(path), code)
    kernel32.CloseHandle(handle)


def check_writable(path: Path) -> None:
    """Paso 3: falla con un mensaje claro si el destino está bloqueado o protegido.

    Abre el archivo para escritura sin modificarlo: con el juego abierto (que lo abre
    con ``FILE_SHARE_READ``) Windows lo impide.
    """
    if path.exists():
        if path.is_dir():
            raise SaveError(f"{path} es una carpeta")
        if not os.access(path, os.W_OK):
            raise SaveError(f"{path.name} es de solo lectura. Quítale ese atributo o usa «Guardar como».")
        try:
            _probe_write(path)
        except OSError as error:
            raise SaveError(describe_os_error(error, path)) from error
    elif not path.parent.is_dir():
        raise SaveError(f"No existe la carpeta {path.parent}")


def write_atomic(path: Path, data: bytes) -> None:
    """Escribe en ``X.tmp`` con fsync y sustituye ``X`` con ``os.replace``."""
    temporary = tmp_path(path)
    try:
        with open(temporary, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        _discard(temporary)
        raise SaveError(describe_os_error(error, path)) from error


def _discard(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _write_new_file(path: Path, data: bytes) -> None:
    """Escribe un archivo que no debe existir (la copia del original): nunca sobrescribe."""
    temporary = tmp_path(path)
    try:
        with open(temporary, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise SaveError(f"{path.name} apareció mientras se creaba; no se sobrescribe")
        os.replace(temporary, path)
    except OSError as error:
        _discard(temporary)
        raise SaveError(describe_os_error(error, path)) from error
    except SaveError:
        _discard(temporary)
        raise


@dataclass
class SaveResult:
    path: Path
    sha256: str
    size: int
    original_copy: Path | None = None
    original_created: bool = False
    original_is_steam: bool = False
    backup: Path | None = None
    removed_backups: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"Guardado {self.path.name}: {self.size:,} bytes, SHA-256 {self.sha256[:16]}…"]
        if self.original_created and self.original_copy is not None:
            origin = "original de Steam" if self.original_is_steam else "archivo previo, que ya venía modificado"
            lines.append(f"Copia del original creada: {self.original_copy.name} ({origin}), verificada y de solo lectura.")
        elif self.original_copy is not None:
            lines.append(f"La copia del original ({self.original_copy.name}) ya existía y no se ha tocado.")
        if self.backup is not None:
            lines.append(f"Versión anterior guardada en {BACKUP_DIR}\\{self.backup.name}.")
        lines.extend(self.warnings)
        return "\n".join(lines)


def ensure_original_copy(path: Path, current: bytes, result: SaveResult) -> None:
    """Paso 4 (sección 4.1): crea ``X.original.obsp`` una sola vez y nunca lo toca después."""
    copy = original_copy_path(path)
    result.original_copy = copy
    if copy.exists():
        return
    expected = sha256(current)
    _write_new_file(copy, current)
    written = copy.read_bytes()
    if sha256(written) != expected:
        raise SaveError(f"La copia {copy.name} no coincide con el archivo copiado; no se guarda nada")
    try:
        os.chmod(copy, stat.S_IREAD)
    except OSError as error:
        result.warnings.append(f"No se pudo marcar {copy.name} como solo lectura: {error}")
    result.original_created = True
    result.original_is_steam = expected == STEAM_ORIGINAL_SHA256
    if not result.original_is_steam:
        result.warnings.append(
            f"Aviso: {path.name} ya venía modificado (no es el original de Steam); la copia lo conserva tal cual."
        )


_STAMP_FORMAT = "%Y%m%d-%H%M%S-%f"


def rotate_backup(path: Path, previous: bytes, keep: int = KEEP_BACKUPS, now: _dt.datetime | None = None) -> tuple[Path, list[Path]]:
    """Paso 5: guarda la versión anterior en ``.d2sv_backups`` y deja solo las ``keep`` más recientes.

    El orden de los nombres es el orden cronológico, porque la poda borra los
    primeros. En Windows el reloj avanza a saltos de milisegundos: si el instante
    no es posterior a la última copia, se toma esa más un microsegundo. Además, la
    copia se crea en modo exclusivo, así que nunca pisa otra.
    """
    folder = backup_folder(path)
    folder.mkdir(exist_ok=True)
    stem = path.name[: -len(path.suffix)] if path.suffix else path.name
    pattern = f"{stem}.????????-??????-??????{path.suffix}"
    moment = now or _dt.datetime.now()
    previous_backups = sorted(folder.glob(pattern), key=lambda item: item.name)
    if previous_backups:
        stamp_text = previous_backups[-1].name[len(stem) + 1:len(stem) + 1 + 22]
        try:
            latest = _dt.datetime.strptime(stamp_text, _STAMP_FORMAT)
        except ValueError:
            latest = None
        if latest is not None and moment <= latest:
            moment = latest + _dt.timedelta(microseconds=1)
    while True:
        backup = folder / f"{stem}.{moment.strftime(_STAMP_FORMAT)}{path.suffix}"
        try:
            handle = open(backup, "xb")
        except FileExistsError:
            moment += _dt.timedelta(microseconds=1)
            continue
        break
    with handle:
        handle.write(previous)
        handle.flush()
        os.fsync(handle.fileno())
    existing = sorted(folder.glob(pattern), key=lambda item: item.name)
    removed = []
    for old in existing[: max(len(existing) - keep, 0)]:
        try:
            old.unlink()
            removed.append(old)
        except OSError:
            pass
    return backup, removed


def execute_save(
    plan: SavePlan,
    target: Path,
    *,
    rotating_backups: bool = True,
    keep: int = KEEP_BACKUPS,
    fail_at: Callable[[str], None] | None = None,
) -> SaveResult:
    """Pasos 2 a 7. Puede correr en un hilo: solo usa ``plan`` y el disco."""
    step = fail_at or (lambda _name: None)
    if is_original_copy(target):
        raise SaveError(f"No se guarda nunca encima de {target.name}: es la copia del original. Usa «Guardar como».")
    verify_plan(plan)
    step("verified")
    check_writable(target)
    step("checked")
    result = SaveResult(target, plan.sha256, len(plan.data))
    if target.exists():
        try:
            previous = target.read_bytes()
        except OSError as error:
            raise SaveError(describe_os_error(error, target)) from error
        ensure_original_copy(target, previous, result)
        step("original")
        if rotating_backups:
            try:
                result.backup, result.removed_backups = rotate_backup(target, previous, keep)
            except OSError as error:
                result.warnings.append(f"No se pudo guardar la copia rotativa: {error}")
        step("backup")
    temporary = tmp_path(target)
    try:
        with open(temporary, "wb") as handle:
            handle.write(plan.data)
            handle.flush()
            os.fsync(handle.fileno())
        step("tmp_written")
        os.replace(temporary, target)
    except OSError as error:
        _discard(temporary)
        raise SaveError(describe_os_error(error, target)) from error
    except BaseException:
        _discard(temporary)
        raise
    step("replaced")
    try:
        final = target.read_bytes()
    except OSError as error:
        raise WrittenMismatchError(f"Se escribió {target.name} pero no se pudo releer: {error}") from error
    if sha256(final) != plan.sha256:
        raise WrittenMismatchError(
            f"{target.name} no coincide con lo que se quería escribir. "
            "Restaura el original desde Archivo → Restaurar original."
        )
    return result


@dataclass
class RestoreResult:
    path: Path
    sha256: str
    is_steam: bool
    backup: Path | None


def restore_original(path: Path, *, rotating_backups: bool = True, keep: int = KEEP_BACKUPS) -> RestoreResult:
    """Copia ``X.original.obsp`` encima de ``X.obsp`` con verificación. La copia se conserva."""
    if is_original_copy(path):
        raise SaveError("Ese archivo ya es la copia del original")
    copy = original_copy_path(path)
    if not copy.is_file():
        raise SaveError(f"No existe {copy.name} junto a {path.name}: no hay copia del original que restaurar")
    try:
        data = copy.read_bytes()
    except OSError as error:
        raise SaveError(f"No se pudo leer {copy.name}: {error}") from error
    try:
        ObspFile.parse(data)
    except FormatError as error:
        raise SaveError(f"{copy.name} no es un OBSP válido: {error}") from error
    expected = sha256(data)
    check_writable(path)
    backup = None
    if path.exists() and rotating_backups:
        try:
            current = path.read_bytes()
            if sha256(current) != expected:
                backup, _removed = rotate_backup(path, current, keep)
        except OSError:
            backup = None
    write_atomic(path, data)
    if sha256(path.read_bytes()) != expected:
        raise SaveError(f"{path.name} no quedó idéntico a {copy.name} tras restaurar")
    return RestoreResult(path, expected, expected == STEAM_ORIGINAL_SHA256, backup)


def save_document(
    document: Document,
    target: Path | None = None,
    *,
    rotating_backups: bool = True,
    keep: int = KEEP_BACKUPS,
) -> SaveResult:
    """Construye, guarda y deja el documento al día. Atajo síncrono para la CLI y los tests."""
    destination = target or document.path
    if destination is None:
        raise D2ScriptViewerError("El documento no tiene ruta: indica dónde guardarlo")
    plan = prepare_save(document)
    result = execute_save(plan, destination, rotating_backups=rotating_backups, keep=keep)
    document.mark_saved(plan.data, destination)
    return result
