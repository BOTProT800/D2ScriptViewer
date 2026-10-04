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


@dataclass
class FileIndexes:
    references: ReferenceIndex
    dictionary: HashDictionary
    failures: list[str]


def build_indexes(
    obsp: ObspFile,
    progress: Progress | None = None,
    cancel: threading.Event | None = None,
) -> FileIndexes:
    """Decodifica cada objeto una vez (sin tocar la caché del documento)."""
    references = ReferenceIndex()
    dictionary = HashDictionary()
    dictionary.update(obsp.strings.items())
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
        except FormatError as error:
            failures.append(f"{obsp.text(entry.path_hash)}: {error}")
        if progress is not None and position % 200 == 0:
            progress(position, total)
    if progress is not None:
        progress(total, total)
    return FileIndexes(references, dictionary, failures)
