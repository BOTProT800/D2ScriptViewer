# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Un ``.obsp`` abierto: objetos, decodificación bajo demanda, caché y ediciones.

Abrir solo lee cabecera, cadenas e índice. Cada objeto se decodifica la primera
vez que se pide y queda en caché. El archivo se lee entero y se cierra: abrirlo
no lo bloquea ni escribe nada.

Las ediciones cambian el árbol en caché y se guardan como comandos reversibles.
El documento recuerda el estado original de cada propiedad tocada: un objeto
está modificado mientras alguna difiera de su original, así que editar y volver
al valor de partida (a mano o deshaciendo) lo deja como estaba y sus bytes
vuelven a ser los originales.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import edits
from .edits import EditGroup, State, ValueEdit
from .errors import EditError
from .formats import bod, script
from .formats.hashes import HashDictionary
from .formats.obsp import STEAM_ORIGINAL_SHA256, IndexEntry, ObspFile, identity_text, kind_name, rebuild


@dataclass(frozen=True)
class ObjectInfo:
    """Metadatos legibles de una entrada del índice."""

    position: int
    entry: IndexEntry
    path: str
    name: str
    folder: str
    class_name: str

    @property
    def identity(self) -> tuple[int, int]:
        return self.entry.identity

    @property
    def kind_label(self) -> str:
        return kind_name(self.entry.kind)

    @property
    def is_script(self) -> bool:
        return self.entry.is_script

    def label(self) -> str:
        return self.path or self.name or identity_text(self.entry.group, self.entry.object_id)


def _text(obsp: ObspFile, value_hash: int) -> str:
    text = obsp.text(value_hash)
    return text if text is not None else f"#{value_hash:016X}"


class Document:
    def __init__(self, obsp: ObspFile, path: Path | None = None) -> None:
        self.obsp = obsp
        self.path = path
        self._index_objects()
        self._bod_cache: dict[int, bod.BodDocument] = {}
        self._script_cache: dict[int, script.ScriptHeader] = {}
        #: posición → ruta → estado original de cada propiedad que hoy difiere de él.
        self._originals: dict[int, dict[tuple, State]] = {}
        self._encoded: dict[int, bytes] = {}
        self._undo: list[EditGroup] = []
        self._redo: list[EditGroup] = []
        #: Crece con cada cambio; sirve para saber si una vista está al día.
        self.version = 0

    def _index_objects(self) -> None:
        obsp = self.obsp
        self.objects = [
            ObjectInfo(
                position,
                entry,
                _text(obsp, entry.path_hash),
                _text(obsp, entry.name_hash),
                _text(obsp, entry.folder_hash),
                _text(obsp, entry.class_hash),
            )
            for position, entry in enumerate(obsp.entries)
        ]
        self._by_identity = {info.identity: info for info in self.objects}

    def mark_saved(self, data: bytes, path: Path) -> None:
        """El archivo recién escrito pasa a ser la base: ya no hay cambios pendientes.

        Los árboles en caché siguen valiendo (son justo lo que se escribió) y el
        historial de deshacer se conserva: deshacer después de guardar vuelve a
        dejar cambios pendientes respecto a lo guardado.
        """
        obsp = ObspFile.parse(data)
        if [entry.identity for entry in obsp.entries] != [entry.identity for entry in self.obsp.entries]:
            raise EditError("El archivo guardado no tiene los mismos objetos que el documento")
        self.obsp = obsp
        self.path = path
        self._index_objects()
        self._originals.clear()
        self._encoded.clear()
        self.version += 1

    @classmethod
    def open(cls, path: Path) -> "Document":
        # read_bytes abre, lee y cierra: el archivo no queda bloqueado.
        return cls(ObspFile.parse(path.read_bytes()), path)

    @classmethod
    def from_bytes(cls, data: bytes, path: Path | None = None) -> "Document":
        return cls(ObspFile.parse(data), path)

    @property
    def is_steam_original(self) -> bool:
        return self.obsp.sha256() == STEAM_ORIGINAL_SHA256

    def object_by_identity(self, identity: tuple[int, int]) -> ObjectInfo | None:
        return self._by_identity.get(identity)

    def find(self, query: str) -> list[ObjectInfo]:
        """Objetos cuya ruta o nombre coincide con ``query`` (sin distinguir mayúsculas).

        Primero se buscan coincidencias exactas; si no hay ninguna, las que lo contienen.
        """
        needle = query.strip().replace("\\", "/").casefold()
        exact = [info for info in self.objects if needle in (info.path.casefold(), info.name.casefold())]
        if exact:
            return exact
        return [info for info in self.objects if needle in info.path.casefold() or needle in info.name.casefold()]

    def original_blob(self, position: int) -> bytes:
        return self.obsp.blob(position)

    def is_modified(self, position: int) -> bool:
        return position in self._originals

    @property
    def modified_positions(self) -> set[int]:
        return set(self._originals)

    @property
    def change_count(self) -> int:
        """Número de propiedades que hoy difieren de su valor original."""
        return sum(len(paths) for paths in self._originals.values())

    def blob(self, position: int) -> bytes:
        """Bytes actuales del objeto: los originales o, si se editó, el árbol recodificado."""
        if position not in self._originals:
            return self.obsp.blob(position)
        encoded = self._encoded.get(position)
        if encoded is None:
            encoded = self._encoded[position] = bod.encode(self.bod(position))
        return encoded

    def current_data(self) -> bytes:
        """El archivo completo tal como quedaría al guardar ahora."""
        return rebuild(self.obsp, {position: self.blob(position) for position in self._originals})

    # --- Ediciones -----------------------------------------------------------------------

    def node_at(self, position: int, path: tuple) -> object:
        if self.objects[position].is_script:
            raise EditError("Los scripts compilados son de solo lectura")
        return bod.resolve(self.bod(position), path)

    def property_label(self, position: int, path: tuple) -> str:
        return bod.path_label(self.bod(position), path)

    def edit(self, position: int, path: tuple, state: State) -> EditGroup | None:
        """Aplica un estado nuevo ya validado; devuelve ``None`` si no cambia nada."""
        node = self.node_at(position, path)
        before = edits.get_state(node)
        if before == state:
            return None
        if isinstance(node, bod.ExternalRef) and state not in self._by_identity:
            raise EditError(f"No existe ningún objeto {identity_text(*state)} en este archivo")  # type: ignore[misc]
        label = f"{self.objects[position].label()} · {self.property_label(position, path)}"
        group = EditGroup((ValueEdit(position, path, before, state),), f"Editar {label}")
        self._push(group)
        return group

    def edit_text(
        self, position: int, path: tuple, text: str, dictionary: HashDictionary | None = None
    ) -> EditGroup | None:
        """Valida el texto del usuario y lo aplica (enteros, floats, bools y cadenas)."""
        return self.edit(position, path, edits.parse_state(self.node_at(position, path), text, dictionary))

    def revert_property(self, position: int, path: tuple) -> EditGroup | None:
        original = self._originals.get(position, {}).get(path)
        if original is None:
            return None
        group = self.edit(position, path, original)
        if group is not None:
            group = EditGroup(group.edits, f"Revertir {self.objects[position].label()} · "
                                           f"{self.property_label(position, path)}")
            self._undo[-1] = group
        return group

    def revert_object(self, position: int) -> EditGroup | None:
        originals = self._originals.get(position)
        if not originals:
            return None
        tree = self.bod(position)
        changes = tuple(
            ValueEdit(position, path, edits.get_state(bod.resolve(tree, path)), original)
            for path, original in sorted(originals.items())
        )
        group = EditGroup(changes, f"Revertir {self.objects[position].label()}")
        self._push(group)
        return group

    def undo(self) -> EditGroup | None:
        if not self._undo:
            return None
        group = self._undo.pop()
        self._apply(group, forward=False)
        self._redo.append(group)
        return group

    def redo(self) -> EditGroup | None:
        if not self._redo:
            return None
        group = self._redo.pop()
        self._apply(group, forward=True)
        self._undo.append(group)
        return group

    @property
    def undo_description(self) -> str | None:
        return self._undo[-1].description if self._undo else None

    @property
    def redo_description(self) -> str | None:
        return self._redo[-1].description if self._redo else None

    def _push(self, group: EditGroup) -> None:
        self._apply(group, forward=True)
        self._undo.append(group)
        self._redo.clear()

    def _apply(self, group: EditGroup, *, forward: bool) -> None:
        changes = group.edits if forward else tuple(reversed(group.edits))
        for change in changes:
            self._set(change.position, change.path, change.after if forward else change.before)
        self.version += 1

    def _set(self, position: int, path: tuple, state: State) -> None:
        node = self.node_at(position, path)
        originals = self._originals.setdefault(position, {})
        if path not in originals:
            originals[path] = edits.get_state(node)
        edits.set_state(node, state)
        if originals[path] == state:
            del originals[path]
        if not originals:
            del self._originals[position]
        self._encoded.pop(position, None)

    def edited_paths(self, position: int) -> set[tuple]:
        return set(self._originals.get(position, ()))

    def pending_changes(self) -> list[tuple[int, tuple, object, State, State]]:
        """(posición, ruta, nodo, estado original, estado actual) de cada propiedad cambiada."""
        result = []
        for position in sorted(self._originals):
            tree = self.bod(position)
            for path, original in sorted(self._originals[position].items()):
                node = bod.resolve(tree, path)
                result.append((position, path, node, original, edits.get_state(node)))
        return result

    def bod(self, position: int) -> bod.BodDocument:
        """Árbol BOD del objeto, decodificado una sola vez.

        Se puede llamar desde un hilo de trabajo: si dos hilos decodifican a la vez
        el mismo objeto, ``setdefault`` garantiza que todos reciben el mismo árbol,
        que es el único que se edita.
        """
        cached = self._bod_cache.get(position)
        if cached is None:
            cached = self._bod_cache.setdefault(position, bod.decode(self.obsp.blob(position)))
        return cached

    def cached_bod(self, position: int) -> bod.BodDocument | None:
        """El árbol si ya se decodificó; nunca decodifica."""
        return self._bod_cache.get(position)

    def script_header(self, position: int) -> script.ScriptHeader:
        cached = self._script_cache.get(position)
        if cached is None:
            cached = script.parse_header(self.obsp.blob(position))
            self._script_cache[position] = cached
        return cached
