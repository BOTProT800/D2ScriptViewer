# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Índice de referencias ``FC`` ("apunta a" / "usado por") y diccionario global de hashes.

Construirlo exige decodificar todos los BOD (unos 2-3 s), así que la interfaz lo
hace en un hilo aparte con :func:`build_indexes`. Después se mantiene al día
objeto a objeto con :meth:`ReferenceIndex.set_object`.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from .errors import FormatError
from .formats import bod, script
from .formats.hashes import HashDictionary, document_names
from .formats.obsp import ObspFile

Progress = Callable[[int, int], None]


class Cancelled(Exception):
    """El usuario canceló o cerró el archivo mientras se indexaba."""


@dataclass(frozen=True)
class Reference:
    source: int
    """Posición del objeto que contiene el ``FC``."""
    path: tuple
    """Ruta de la propiedad dentro del árbol del objeto de origen."""
    target: tuple[int, int]
    """Identidad (grupo, idObjeto) del objeto apuntado."""
    label: str
    """Ruta legible de la propiedad, p. ej. ``Weapons[2].Projectile``."""


def references_in(position: int, document: bod.BodDocument) -> list[Reference]:
    return [
        Reference(position, path, node.identity, bod.path_label(document, path))
        for path, node in bod.walk(document.root)
        if isinstance(node, bod.ExternalRef)
    ]


class ReferenceIndex:
    def __init__(self) -> None:
        self._outgoing: dict[int, list[Reference]] = {}
        self._incoming: dict[tuple[int, int], list[Reference]] = defaultdict(list)

    def __len__(self) -> int:
        return sum(len(references) for references in self._outgoing.values())

    def set_object(self, position: int, references: list[Reference]) -> None:
        """Sustituye las referencias que salen de ``position`` (tras una edición)."""
        for old in self._outgoing.pop(position, []):
            incoming = self._incoming.get(old.target)
            if incoming is not None:
                incoming[:] = [reference for reference in incoming if reference.source != position]
        if references:
            self._outgoing[position] = list(references)
            for reference in references:
                self._incoming[reference.target].append(reference)

    def references_from(self, position: int) -> list[Reference]:
        return list(self._outgoing.get(position, ()))

    def references_to(self, identity: tuple[int, int]) -> list[Reference]:
        return list(self._incoming.get(identity, ()))


#: Un hueco: (clase del objeto dueño, campo, papel). El papel es ``campo`` (valor del campo),
#: ``elemento`` (de una lista) o ``par`` (valor de un par de un mapa o lista de pares).
SlotKey = tuple


def slot_key(tree: bod.BodDocument, path: tuple) -> SlotKey:
    """El hueco que ocupa el valor de ``path``."""
    node: object = tree.root
    owner = tree.root.cls.name.text
    field = ""
    role = "campo"
    for step in path:
        if isinstance(node, bod.BodObject):
            owner = node.cls.name.text
            field = node.fields[step].name.text
            role = "campo"
            node = node.fields[step].value
        elif isinstance(node, (bod.BodList, bod.BodMap)):
            role = "par" if node.mode == bod.MODE_PAIRS else "elemento"
            node = node.items[step]
        elif isinstance(node, bod.Pair):
            role = "par" if step == 1 else "clave"
            node = node.value if step == 1 else node.key
        elif isinstance(node, bod.BodTuple):
            role = "tupla"
            node = node.items[step]
        else:
            raise IndexError(step)
    return (owner, field, role)


def slot_occurrences(tree: bod.BodDocument) -> list[tuple[SlotKey, tuple, object]]:
    """Cada objeto, referencia o nulo del árbol con su hueco (sin tuplas ni claves de pares)."""
    found: list[tuple[SlotKey, tuple, object]] = []

    def visit(node: object, path: tuple, owner: str, field: str, role: str) -> None:
        kind = type(node)
        if kind is bod.BodObject or kind is bod.ExternalRef or kind is bod.Null:
            found.append(((owner, field, role), path, node))
        if kind is bod.BodObject:
            name = node.cls.name.text  # type: ignore[attr-defined]
            for index, child in enumerate(node.fields):  # type: ignore[attr-defined]
                visit(child.value, path + (index,), name, child.name.text, "campo")
        elif kind is bod.BodList or kind is bod.BodMap:
            if node.mode == bod.MODE_PAIRS:  # type: ignore[attr-defined]
                for index, pair in enumerate(node.items):  # type: ignore[attr-defined]
                    visit(pair.value, path + (index, 1), owner, field, "par")
            else:
                for index, item in enumerate(node.items):  # type: ignore[attr-defined]
                    visit(item, path + (index,), owner, field, "elemento")

    root = tree.root
    for index, child in enumerate(root.fields):
        visit(child.value, (index,), root.cls.name.text, child.name.text, "campo")
    return found


class SlotIndex:
    """Qué clases de objeto (y si hay referencias) aparecen en cada hueco del archivo.

    Sirve para rellenar un nulo con la copia de un objeto de una clase que ya se usa
    en ese mismo hueco (decisión de la fase 5).
    """

    MAX_EXAMPLES = 12

    def __init__(self) -> None:
        self._classes: dict[SlotKey, dict[str, list]] = {}
        self._counts: dict[SlotKey, dict[str, int]] = {}
        self._references: dict[SlotKey, int] = {}

    def record(self, key: SlotKey, position: int, path: tuple, node: object) -> None:
        if isinstance(node, bod.BodObject):
            label = node.cls.label()
            counts = self._counts.setdefault(key, {})
            counts[label] = counts.get(label, 0) + 1
            examples = self._classes.setdefault(key, {}).setdefault(label, [])
            if len(examples) < self.MAX_EXAMPLES:
                examples.append((position, path))
        elif isinstance(node, bod.ExternalRef):
            self._references[key] = self._references.get(key, 0) + 1

    def classes(self, key: SlotKey) -> list[tuple[str, int, list]]:
        """(clase, apariciones, ejemplos (posición, ruta)) de más a menos usada."""
        counts = self._counts.get(key, {})
        return sorted(
            ((label, count, list(self._classes[key][label])) for label, count in counts.items()),
            key=lambda row: (-row[1], row[0]),
        )

    def references(self, key: SlotKey) -> int:
        return self._references.get(key, 0)


@dataclass
class FileIndexes:
    references: ReferenceIndex
    dictionary: HashDictionary
    failures: list[str]
    slots: SlotIndex


def build_indexes(
    obsp: ObspFile,
    progress: Progress | None = None,
    cancel: threading.Event | None = None,
) -> FileIndexes:
    """Decodifica cada objeto una vez (sin tocar la caché del documento)."""
    references = ReferenceIndex()
    dictionary = HashDictionary()
    dictionary.update(obsp.strings.items())
    slots = SlotIndex()
    failures: list[str] = []
    total = len(obsp.entries)
    for position, entry in enumerate(obsp.entries):
        if cancel is not None and cancel.is_set():
            raise Cancelled()
        blob = obsp.blob(position)
        try:
            if entry.is_script:
                for symbol in script.parse_header(blob).symbols:
                    dictionary.add(symbol.hash, symbol.text)
            else:
                document = bod.decode(blob)
                dictionary.update(document_names(document))
                references.set_object(position, references_in(position, document))
                for key, path, node in slot_occurrences(document):
                    slots.record(key, position, path, node)
        except FormatError as error:
            failures.append(f"{obsp.text(entry.path_hash)}: {error}")
        if progress is not None and position % 200 == 0:
            progress(position, total)
    if progress is not None:
        progress(total, total)
    return FileIndexes(references, dictionary, failures, slots)
