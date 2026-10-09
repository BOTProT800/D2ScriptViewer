# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Un ``.obsp`` abierto: objetos, decodificación bajo demanda, caché y ediciones.

Abrir solo lee cabecera, cadenas e índice. Cada objeto se decodifica la primera
vez que se pide y queda en caché. El archivo se lee entero y se cierra: abrirlo
no lo bloquea ni escribe nada.

Los scripts compilados (tipo 0) también tienen árbol: el de presentación de
:func:`.formats.script.present`, cuyas hojas editables (literales y valores de
tamaño fijo) son las del script, que es lo que se recodifica.

Las ediciones cambian el árbol en caché y se guardan como operaciones reversibles
(:mod:`.edits`). Un objeto está **modificado** si sus bytes actuales difieren de los
de partida: editar y volver al valor original (a mano, deshaciendo o revirtiendo)
lo deja sin cambios y sus bytes vuelven a ser los originales. Los cambios
pendientes se obtienen comparando el árbol actual con el de partida
(:mod:`.diffing`), así que no dependen del historial.
"""

from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import diffing, edits
from .diffing import Change
from .edits import EditGroup, InsertItem, MoveItem, RemoveItem, ReplaceTree, ReplaceValue, State, ValueEdit
from .errors import EditError, PathError
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


#: Lo que se escribe entre el objeto y la propiedad en una ruta completa.
FULL_LABEL_SEPARATOR = " · "
#: Separadores que se aceptan al leer una ruta completa; ninguna ruta ni etiqueta los contiene.
LOCATION_SEPARATORS = ("·", "::")
#: El portapapeles más largo que se considera una ruta (la más larga del juego mide 184).
MAX_LOCATION_LENGTH = 256
#: Comillas que se quitan si envuelven la ruta (al copiarla de un ``.md``).
_QUOTES = {'"': '"', "'": "'", "`": "`", "«": "»", "“": "”"}


@dataclass(frozen=True)
class Location:
    """Una ruta legible analizada (fase 11), todavía sin resolver en el árbol."""

    position: int | None
    """El objeto escrito delante de la propiedad; ``None`` si la ruta es del objeto abierto."""
    steps: tuple[bod.PathStep, ...]
    """Los tramos de la propiedad (:func:`.formats.bod.parse_path_label`); vacío, el objeto entero."""


#: Saltos de línea: una ruta ocupa una sola.
_LINE_BREAKS = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")


def _check_characters(text: str, start: int, end: int) -> None:
    """Rechaza los saltos de línea y los caracteres invisibles, señalando el primero.

    Los espacios de cualquier tipo (también el duro, U+00A0, y el tabulador) cuentan como espacios.
    """
    for index in range(start, end):
        char = text[index]
        if char in _LINE_BREAKS:
            raise PathError("Una ruta ocupa una sola línea", index, index + 1)
        if not char.isspace() and unicodedata.category(char) in ("Cc", "Cf", "Co", "Cs", "Cn"):
            raise PathError(f"La ruta lleva un carácter invisible (U+{ord(char):04X}): bórralo", index, index + 1)


def _path_key(text: str) -> str:
    return text.strip().replace("\\", "/").casefold()


def _strip_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _unwrap(text: str) -> tuple[int, int]:
    """(inicio, fin) de ``text`` sin espacios ni comillas alrededor."""
    start, end = _strip_span(text, 0, len(text))
    while end - start >= 2 and _QUOTES.get(text[start]) == text[end - 1]:
        start, end = _strip_span(text, start + 1, end - 1)
    return start, end


def _find_separator(text: str, start: int, end: int) -> tuple[int, int] | None:
    """El primer separador entre objeto y propiedad dentro de ``text[start:end]``."""
    found = [
        (index, index + len(separator))
        for separator in LOCATION_SEPARATORS
        if (index := text.find(separator, start, end)) >= 0
    ]
    return min(found) if found else None


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
        #: Objetos a los que se ha aplicado alguna operación desde la última base.
        self._touched: set[int] = set()
        self._encoded: dict[int, bytes] = {}
        self._baseline_trees: dict[int, bod.BodDocument] = {}
        self._changes: dict[int, tuple[int, list[Change]]] = {}
        self._undo: list[EditGroup] = []
        self._redo: list[EditGroup] = []
        #: Crece con cada cambio; sirve para saber si una vista o una caché está al día.
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
        self._by_path: dict[str, ObjectInfo] = {}
        for info in self.objects:
            self._by_path.setdefault(_path_key(info.path), info)

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
        self._touched.clear()
        self._encoded.clear()
        self._baseline_trees.clear()
        self._changes.clear()
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

    # --- Estado ---------------------------------------------------------------------------

    def original_blob(self, position: int) -> bytes:
        """Los bytes de partida (los del archivo abierto o del último guardado)."""
        return self.obsp.blob(position)

    def blob(self, position: int) -> bytes:
        """Bytes actuales del objeto: los de partida o, si se tocó, el árbol recodificado."""
        if position not in self._touched:
            return self.obsp.blob(position)
        encoded = self._encoded.get(position)
        if encoded is None:
            tree = self.bod(position)
            if isinstance(tree, script.ScriptTree):
                encoded = script.encode(tree.script)
            else:
                encoded = bod.encode(tree)
            self._encoded[position] = encoded
        return encoded

    def is_modified(self, position: int) -> bool:
        return position in self._touched and self.blob(position) != self.obsp.blob(position)

    @property
    def modified_positions(self) -> set[int]:
        return {position for position in self._touched if self.is_modified(position)}

    def baseline_tree(self, position: int) -> bod.BodDocument:
        """Árbol de partida, decodificado aparte (nunca se edita)."""
        tree = self._baseline_trees.get(position)
        if tree is None:
            tree = self._baseline_trees[position] = self._decode(position)
        return tree

    def changes(self, position: int, ref_label: diffing.RefLabel | None = None) -> list[Change]:
        """Lo que difiere del árbol de partida, en términos legibles."""
        if not self.is_modified(position):
            return []
        if ref_label is not None:
            return diffing.diff_trees(self.baseline_tree(position), self.bod(position), ref_label)
        cached = self._changes.get(position)
        if cached is None or cached[0] != self.version:
            cached = (self.version, diffing.diff_trees(self.baseline_tree(position), self.bod(position)))
            self._changes[position] = cached
        return cached[1]

    @property
    def change_count(self) -> int:
        return sum(len(self.changes(position)) for position in self.modified_positions)

    def edited_paths(self, position: int) -> set[tuple]:
        return diffing.changed_paths(self.changes(position))

    def pending_changes(self, ref_label: diffing.RefLabel | None = None) -> list[tuple[int, Change]]:
        """(posición, cambio) de cada objeto modificado, en orden de índice."""
        return [
            (position, change)
            for position in sorted(self.modified_positions)
            for change in self.changes(position, ref_label)
        ]

    def current_data(self) -> bytes:
        """El archivo completo tal como quedaría al guardar ahora."""
        return rebuild(self.obsp, {position: self.blob(position) for position in self.modified_positions})

    # --- Ediciones de valores --------------------------------------------------------------

    def node_at(self, position: int, path: tuple) -> object:
        node = bod.resolve(self.bod(position), path)
        if self.objects[position].is_script and not isinstance(node, script.EDITABLE_VALUES):
            raise EditError(
                "En los scripts compilados solo se editan, sin cambiar tamaños, los literales int, float y bool "
                "y los valores por defecto e iniciales de esos tipos"
            )
        return node

    def property_label(self, position: int, path: tuple) -> str:
        return bod.path_label(self.bod(position), path)

    def full_label(self, position: int, path: tuple) -> str:
        """``objeto · propiedad``: lo que copia «Copiar ruta completa» y lee :meth:`parse_location`."""
        return f"{self.objects[position].label()}{FULL_LABEL_SEPARATOR}{self.property_label(position, path)}"

    # --- Ir a una ruta (fase 11) ----------------------------------------------------------

    def object_by_path(self, text: str) -> ObjectInfo | None:
        """El objeto de esa ruta, sin distinguir mayúsculas y con «\\» o «/» como separador."""
        return self._by_path.get(_path_key(text))

    def parse_location(self, text: str) -> Location:
        """Analiza una ruta legible sin resolver la propiedad, que necesita el árbol decodificado.

        Formatos: ``propiedad`` (la de :func:`.formats.bod.path_label`, en el objeto abierto),
        ``objeto · propiedad`` u ``objeto::propiedad``, y el ``objeto`` solo. Se quitan las
        comillas que envuelvan el texto. Lanza :class:`PathError` con el tramo culpable.
        """
        start, end = _unwrap(text)
        if start == end:
            raise PathError(
                "Escribe una ruta, como MoveStates[44].JumpImpulse, o el objeto delante: "
                "death/playercommon_movestates · MoveStates[44].JumpImpulse"
            )
        _check_characters(text, start, end)
        separator = _find_separator(text, start, end)
        if separator is not None:
            separator_start, separator_end = separator
            object_start, object_end = _strip_span(text, start, separator_start)
            if object_start == object_end:
                raise PathError(f"Falta el objeto antes de «{text[separator_start:separator_end]}»",
                                separator_start, separator_end)
            info = self._object_in(text, object_start, object_end)
            return Location(info.position, tuple(bod.parse_path_label(text, separator_end, end)))
        steps = bod.parse_path_label(text, start, end)
        first = steps[0] if steps else None
        if first is not None and first.name is not None and ("/" in first.name or "\\" in first.name):
            if len(steps) > 1:
                rest = text[steps[1].start:end].strip()
                raise PathError(
                    f"Para ir a una propiedad de otro objeto, sepáralos con « · »: {first.name}{FULL_LABEL_SEPARATOR}{rest}",
                    first.start, first.end,
                )
            return Location(self._object_in(text, first.start, first.end).position, ())
        return Location(None, tuple(steps))

    def _object_in(self, text: str, start: int, end: int) -> ObjectInfo:
        info = self.object_by_path(text[start:end])
        if info is not None:
            return info
        key = _path_key(text[start:end])
        similar = difflib.get_close_matches(key, list(self._by_path), n=bod.SUGGESTIONS, cutoff=0.6)
        hint = f". Parecidos: {', '.join(f'«{self._by_path[path].path}»' for path in similar)}" if similar else ""
        raise PathError(f"No hay ningún objeto «{text[start:end].strip()}»{hint}", start, end)

    def looks_like_location(self, text: str, position: int | None) -> bool:
        """Si ``text`` (el portapapeles) parece una ruta a la que ir desde el objeto ``position``.

        Una sola línea de hasta :data:`MAX_LOCATION_LENGTH` caracteres, con la sintaxis de
        :meth:`parse_location` y alguno de ``.``, ``[``, ``·``, ``::`` o ``/``. Además, el objeto
        que nombra existe o el primer tramo es un campo de la raíz del objeto abierto. Así no se
        toma por ruta un valor copiado (``350``, ``Jump``, ``true``).
        """
        candidate = text.strip()
        if not candidate or len(candidate) > MAX_LOCATION_LENGTH:
            return False
        if not any(mark in candidate for mark in (".", "[", "·", "::", "/")):
            return False
        try:
            location = self.parse_location(candidate)
        except PathError:
            return False
        if location.position is not None:
            return True
        tree = self.cached_bod(position) if position is not None else None
        return tree is not None and bool(location.steps) and bod.find_path(tree, list(location.steps[:1])).complete

    def edit(self, position: int, path: tuple, state: State) -> EditGroup | None:
        """Aplica un estado nuevo ya validado; devuelve ``None`` si no cambia nada."""
        node = self.node_at(position, path)
        before = edits.get_state(node)
        if before == state:
            return None
        if isinstance(node, bod.ExternalRef) and state not in self._by_identity:
            raise EditError(f"No existe ningún objeto {identity_text(*state)} en este archivo")  # type: ignore[misc]
        return self._push(EditGroup((ValueEdit(position, path, before, state),), f"Editar {self.full_label(position, path)}"))

    def edit_text(
        self, position: int, path: tuple, text: str, dictionary: HashDictionary | None = None
    ) -> EditGroup | None:
        """Valida el texto del usuario y lo aplica (enteros, floats, bools y cadenas)."""
        return self.edit(position, path, edits.parse_state(self.node_at(position, path), text, dictionary))

    def revert_property(self, position: int, path: tuple) -> EditGroup | None:
        """Devuelve una hoja a su valor de partida, si en ese sitio hubo un cambio de valor."""
        for change in self.changes(position):
            if change.kind == "valor" and change.path == path:
                node = self.node_at(position, path)
                operation = ValueEdit(position, path, edits.get_state(node), change.original_state)
                return self._push(EditGroup((operation,), f"Revertir {self.full_label(position, path)}"))
        return None

    def revert_object(self, position: int) -> EditGroup | None:
        if not self.is_modified(position):
            return None
        fresh = self._decode(position)
        operation = ReplaceTree(position, self.bod(position), fresh)
        return self._push(EditGroup((operation,), f"Revertir {self.objects[position].label()}"))

    # --- Ediciones estructurales (fase 5) ------------------------------------------------

    def _sequence_item(self, position: int, path: tuple) -> tuple[object, list]:
        if self.objects[position].is_script:
            raise EditError("Los scripts compilados son de solo lectura")
        found = edits.structural_parent(self.bod(position), path)
        if found is None:
            raise EditError("Solo los elementos de una lista o las entradas de un mapa se pueden duplicar, "
                            "quitar o mover (las tuplas tienen tamaño fijo)")
        container, node = found
        return node, container.items  # type: ignore[attr-defined]

    def duplicate_item(self, position: int, path: tuple) -> EditGroup:
        """Inserta una copia del elemento justo detrás de él."""
        node, _items = self._sequence_item(position, path)
        copy = bod.clone(node)
        operation = InsertItem(position, path[:-1], path[-1] + 1, copy)
        return self._push(EditGroup((operation,), f"Duplicar {self.full_label(position, path)}"))

    def remove_item(self, position: int, path: tuple) -> EditGroup:
        node, _items = self._sequence_item(position, path)
        label = self.full_label(position, path)
        return self._push(EditGroup((RemoveItem(position, path[:-1], path[-1], node),), f"Eliminar {label}"))

    def move_item(self, position: int, path: tuple, delta: int) -> EditGroup | None:
        """Sube (``delta`` < 0) o baja un elemento; ``None`` si ya está en el extremo."""
        _node, items = self._sequence_item(position, path)
        source = path[-1]
        target = source + delta
        if not 0 <= target < len(items):
            return None
        label = self.full_label(position, path)
        verb = "Subir" if delta < 0 else "Bajar"
        return self._push(EditGroup((MoveItem(position, path[:-1], source, target),), f"{verb} {label}"))

    def set_null(self, position: int, path: tuple) -> EditGroup:
        if self.objects[position].is_script:
            raise EditError("Los scripts compilados son de solo lectura")
        tree = self.bod(position)
        if not edits.can_null(tree, path):
            raise EditError("Solo un objeto o una referencia (fuera de tuplas y de claves) puede pasar a nulo")
        node = bod.resolve(tree, path)
        operation = ReplaceValue(position, path, node, bod.Null())
        return self._push(EditGroup((operation,), f"Poner a nulo {self.full_label(position, path)}"))

    def copy_node(self, position: int, path: tuple) -> object:
        """Copia profunda de un nodo del árbol actual, lista para insertarla en otro sitio."""
        return bod.clone(self.node_at(position, path))

    def copy_example(self, position: int, path: tuple, class_label: str) -> bod.BodObject:
        """Copia el objeto de ejemplo que señala el índice de huecos.

        El índice describe el archivo de partida, así que el ejemplo se toma del árbol
        de partida, no del editado (que pudo haberlo anulado o movido).
        """
        if self.objects[position].is_script:
            raise EditError("Los scripts compilados son de solo lectura")
        try:
            node = bod.resolve(self.baseline_tree(position), path)
        except IndexError:
            node = None
        if not isinstance(node, bod.BodObject) or node.cls.label() != class_label:
            raise EditError(
                "Ese ejemplo ya no está donde lo registró el índice (el objeto cambió al guardar). "
                "Vuelve a abrir el archivo para actualizar el índice."
            )
        copy = bod.clone(node)
        assert isinstance(copy, bod.BodObject)
        return copy

    def fill_null(self, position: int, path: tuple, value: object) -> EditGroup:
        """Pone ``value`` (un objeto ya copiado o una referencia) donde ahora hay un nulo."""
        node = self.node_at(position, path)
        if not isinstance(node, bod.Null):
            raise EditError("Ahí no hay un nulo")
        if not isinstance(value, (bod.BodObject, bod.ExternalRef)):
            raise EditError("Un nulo solo se rellena con un objeto o una referencia")
        if isinstance(value, bod.ExternalRef) and value.identity not in self._by_identity:
            raise EditError(f"No existe ningún objeto {identity_text(*value.identity)} en este archivo")
        operation = ReplaceValue(position, path, node, value)
        return self._push(EditGroup((operation,), f"Rellenar {self.full_label(position, path)}"))

    # --- Deshacer ----------------------------------------------------------------------------

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

    def run_operations(self, description: str, build: Callable[[Callable[[object], None]], None]) -> EditGroup | None:
        """Aplica operaciones una a una, cada una sobre el árbol que dejó la anterior.

        ``build`` recibe ``do(operación)``, que la aplica en el acto, y puede leer el árbol
        entre una y otra. Si ``build`` lanza, se deshacen las ya aplicadas y el documento
        queda como estaba. Todo junto es un único paso de deshacer.
        """
        applied: list[object] = []

        def do(operation: object) -> None:
            self._apply_one(operation, forward=True)
            applied.append(operation)

        try:
            build(do)
        except BaseException:
            for operation in reversed(applied):
                self._apply_one(operation, forward=False)
            self.version += 1
            raise
        self.version += 1
        if not applied:
            return None
        group = EditGroup(tuple(applied), description)
        self._undo.append(group)
        self._redo.clear()
        return group

    def _push(self, group: EditGroup) -> EditGroup:
        self._apply(group, forward=True)
        self._undo.append(group)
        self._redo.clear()
        return group

    def _apply(self, group: EditGroup, *, forward: bool) -> None:
        operations = group.edits if forward else tuple(reversed(group.edits))
        for operation in operations:
            self._apply_one(operation, forward=forward)
        self.version += 1

    def _apply_one(self, operation: object, *, forward: bool) -> None:
        position = operation.position  # type: ignore[attr-defined]
        if isinstance(operation, ReplaceTree):
            self._bod_cache[position] = operation.after if forward else operation.before
        elif forward:
            operation.apply(self.bod(position))  # type: ignore[attr-defined]
        else:
            operation.revert(self.bod(position))  # type: ignore[attr-defined]
        self._touched.add(position)
        self._encoded.pop(position, None)

    # --- Decodificación ----------------------------------------------------------------------

    def _decode(self, position: int) -> bod.BodDocument:
        """Árbol nuevo a partir de los bytes de partida (de presentación si es un script)."""
        blob = self.obsp.blob(position)
        if self.objects[position].is_script:
            return script.present(script.parse(blob))
        return bod.decode(blob)

    def bod(self, position: int) -> bod.BodDocument:
        """Árbol del objeto (BOD o, en los scripts, de presentación), decodificado una sola vez.

        Se puede llamar desde un hilo de trabajo: si dos hilos decodifican a la vez
        el mismo objeto, ``setdefault`` garantiza que todos reciben el mismo árbol,
        que es el único que se edita.
        """
        cached = self._bod_cache.get(position)
        if cached is None:
            cached = self._bod_cache.setdefault(position, self._decode(position))
        return cached

    def script(self, position: int) -> script.Script:
        """El script entero (modelo editable detrás del árbol de presentación)."""
        tree = self.bod(position)
        if not isinstance(tree, script.ScriptTree):
            raise EditError("Este objeto no es un script compilado")
        return tree.script

    def cached_bod(self, position: int) -> bod.BodDocument | None:
        """El árbol si ya se decodificó; nunca decodifica."""
        return self._bod_cache.get(position)

    def script_header(self, position: int) -> script.ScriptHeader:
        cached = self._script_cache.get(position)
        if cached is None:
            cached = script.parse_header(self.obsp.blob(position))
            self._script_cache[position] = cached
        return cached
