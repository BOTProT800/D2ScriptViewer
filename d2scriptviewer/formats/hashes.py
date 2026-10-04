# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Función de hash de 64 bits y diccionario global hash ↔ cadena.

La función (fase 6) es un CRC-64 reflejado con un polinomio propio del juego,
deducido de los 70 182 pares del archivo (apéndice A.4 del plan). Es la misma en
el contenedor, los BOD y los scripts, distingue mayúsculas y da 0 para la cadena
vacía. La identidad de un objeto (``idObjeto``) es el hash de su nombre en minúsculas.
"""

from __future__ import annotations

from typing import Iterable, Iterator

from ..binary import TEXT_ENCODING
from . import bod
from .bod import BodDocument, Name

#: Polinomio del CRC-64 en forma normal (sin el término x⁶⁴) y en forma reflejada.
CRC64_POLY = 0x0060034000F0D50B
CRC64_POLY_REFLECTED = 0xD0AB0F0002C00600
#: Valor inicial y XOR final.
CRC64_INIT = CRC64_XOROUT = 0xFFFFFFFFFFFFFFFF
#: Valor de control habitual de un CRC: el hash de ``"123456789"``.
CRC64_CHECK = 0x9AFB180E4C211BB4


def _crc_table() -> tuple[int, ...]:
    table = []
    for byte in range(256):
        crc = byte
        for _ in range(8):
            crc = (crc >> 1) ^ (CRC64_POLY_REFLECTED if crc & 1 else 0)
        table.append(crc)
    return tuple(table)


_TABLE = _crc_table()


def name_hash(text: str) -> int:
    """Hash de 64 bits del juego para ``text`` (distingue mayúsculas; ``""`` da 0)."""
    crc = CRC64_INIT
    table = _TABLE
    for byte in text.encode(TEXT_ENCODING):
        crc = (crc >> 8) ^ table[(crc ^ byte) & 0xFF]
    return crc ^ CRC64_XOROUT


def object_id(name: str) -> int:
    """``idObjeto`` que corresponde a un objeto llamado ``name``: el hash del nombre en minúsculas."""
    return name_hash(name.lower())


def make_name(text: str) -> Name:
    """Un nombre con su hash calculado."""
    return Name(name_hash(text), text)


def first_wrong_name(names: Iterable[Name]) -> Name | None:
    """El primer nombre cuyo hash no es el de su texto, o ``None``."""
    seen: set[Name] = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            if name_hash(name.text) != name.hash:
                return name
    return None


class HashDictionary:
    def __init__(self) -> None:
        self._texts: dict[int, str] = {}
        self._hashes: dict[str, int] | None = None
        self._sorted: list[str] | None = None
        self._folded: dict[str, list[str]] | None = None
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
            self._sorted = None
            self._folded = None
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
        """Todas las cadenas conocidas, en orden alfabético sin distinguir mayúsculas (en caché)."""
        if self._sorted is None:
            self._sorted = sorted(self._texts.values(), key=str.casefold)
        return self._sorted

    def case_variants(self, text: str) -> list[str]:
        """Cadenas conocidas que solo difieren de ``text`` en mayúsculas (sin incluir ``text``)."""
        if self._folded is None:
            self._folded = {}
            for value in self._texts.values():
                self._folded.setdefault(value.lower(), []).append(value)
        return sorted(value for value in self._folded.get(text.lower(), ()) if value != text)

    def pairs(self) -> Iterator[tuple[int, str]]:
        return iter(self._texts.items())

    def mismatches(self) -> list[tuple[int, str]]:
        """Pares cuyo hash no es el de su texto, también los que chocan con otro texto."""
        seen = list(self._texts.items()) + [(value_hash, text) for value_hash, _known, text in self.conflicts]
        return [(value_hash, text) for value_hash, text in seen if name_hash(text) != value_hash]

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
