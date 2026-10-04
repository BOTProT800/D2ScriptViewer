# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Diccionario global hash ↔ cadena.

La función de hash de 64 bits sigue sin identificarse (fase 6), así que el único
modo de conocer el hash de una cadena es haberla visto ya en el archivo: en la
tabla del contenedor, en las tablas de nombres de los BOD o en los símbolos de
los scripts. Por eso no se pueden crear cadenas con hash nuevas.
"""

from __future__ import annotations

from typing import Iterable, Iterator

from . import bod
from .bod import BodDocument, Name


class HashDictionary:
    def __init__(self) -> None:
        self._texts: dict[int, str] = {}
        self._hashes: dict[str, int] | None = None
        #: (hash, texto ya conocido, texto nuevo) cuando un hash aparece con dos textos.
        self.conflicts: list[tuple[int, str, str]] = []

    def __len__(self) -> int:
        return len(self._texts)

    def __contains__(self, value_hash: object) -> bool:
        return value_hash in self._texts

    def add(self, value_hash: int, text: str) -> None:
        known = self._texts.get(value_hash)
        if known is None:
            self._texts[value_hash] = text
            self._hashes = None
        elif known != text:
            self.conflicts.append((value_hash, known, text))

    def update(self, pairs: Iterable[tuple[int, str]]) -> None:
        for value_hash, text in pairs:
            self.add(value_hash, text)

    def text(self, value_hash: int) -> str | None:
        return self._texts.get(value_hash)

    def hash_of(self, text: str) -> int | None:
        """Hash conocido de ``text`` (distingue mayúsculas), o ``None`` si nunca apareció."""
        if self._hashes is None:
            self._hashes = {}
            for value_hash, value in self._texts.items():
                self._hashes.setdefault(value, value_hash)
        return self._hashes.get(text)

    def name_for(self, text: str) -> Name | None:
        value_hash = self.hash_of(text)
        return None if value_hash is None else Name(value_hash, text)

    def texts(self) -> list[str]:
        return sorted(self._texts.values(), key=str.casefold)

    def pairs(self) -> Iterator[tuple[int, str]]:
        return iter(self._texts.items())

    def reverse_conflicts(self) -> list[tuple[str, list[int]]]:
        """Textos que aparecen con más de un hash (no debería haber ninguno)."""
        seen: dict[str, set[int]] = {}
        for value_hash, text in self._texts.items():
            seen.setdefault(text, set()).add(value_hash)
        return [(text, sorted(hashes)) for text, hashes in seen.items() if len(hashes) > 1]


def document_names(document: BodDocument) -> Iterator[Name]:
    """Todos los nombres de un BOD: clases, campos y cadenas ``0F``."""
    stack: list[object] = [document.root]
    while stack:
        node = stack.pop()
        kind = type(node)
        if kind is bod.BodObject:
            yield node.cls.name  # type: ignore[attr-defined]
            for field in node.fields:  # type: ignore[attr-defined]
                yield field.name
                stack.append(field.value)
        elif kind is bod.HashedString:
            yield node.name  # type: ignore[attr-defined]
        elif kind is bod.BodList or kind is bod.BodMap:
            if node.mode == bod.MODE_PAIRS:  # type: ignore[attr-defined]
                for pair in node.items:  # type: ignore[attr-defined]
                    stack.append(pair.key)
                    stack.append(pair.value)
            else:
                stack.extend(node.items)  # type: ignore[attr-defined]
        elif kind is bod.BodTuple:
            stack.extend(node.items)  # type: ignore[attr-defined]
