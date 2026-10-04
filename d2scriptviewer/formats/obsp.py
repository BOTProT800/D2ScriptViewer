# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Contenedor OBSP: cabecera, tabla de cadenas, índice y blobs (apéndice A.1 del plan).

El lector conserva el archivo entero en memoria. El escritor regenera la tabla
de cadenas, los offsets del índice y la cabecera a partir de las entradas y los
blobs; con las partes sin tocar reproduce el archivo byte a byte.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, replace
from typing import Mapping, Sequence

from ..binary import TEXT_ENCODING, ByteReader
from ..errors import FormatError

MAGIC = b"OBSP"
HEADER = struct.Struct("<4sBIIIIII")
INDEX_ENTRY = struct.Struct("<QQIIHBQQQ")
STRING_HEAD = struct.Struct("<QI")

#: Categoría del blob según el byte ``tipo`` del índice.
KIND_NAMES = {
    0: "Script",
    1: "Instancia",
    2: "CharacterMoveStateList",
    3: "SoundList",
    4: "AnimationList",
    5: "CharacterConditionalList",
    6: "InputWindowList",
    7: "HitInfoList",
    8: "Desc",
    9: "ModuleSystem",
    14: "TerrainMaterialDesc",
    15: "FloatTable",
}
SCRIPT_KIND = 0

#: Huella del ``scripts.obsp`` que instala Steam (18 334 463 bytes).
STEAM_ORIGINAL_SHA256 = "B46DD3DA7F17A0ED016E30AF523BFBA86D358C9920DFFA866C69D4A0F4F67C7C"
STEAM_ORIGINAL_SIZE = 18_334_463


def kind_name(kind: int) -> str:
    return KIND_NAMES.get(kind, f"Tipo {kind}")


def identity_text(group: int, object_id: int) -> str:
    """Identidad legible de un objeto: ``grupo:idObjeto`` con el id en hexadecimal."""
    return f"{group}:{object_id:016X}"


@dataclass(frozen=True)
class ObspHeader:
    version: int
    unknown: int
    object_count: int
    strings_end: int
    string_count: int
    max_string_length: int
    pad: int = 0


@dataclass(frozen=True)
class IndexEntry:
    """Una entrada del índice. ``offset`` y ``size`` los recalcula el escritor."""

    path_hash: int
    object_id: int
    offset: int
    size: int
    group: int
    kind: int
    name_hash: int
    folder_hash: int
    class_hash: int

    @property
    def identity(self) -> tuple[int, int]:
        """Identidad del objeto: la que usan las referencias ``FC``."""
        return (self.group, self.object_id)

    @property
    def is_script(self) -> bool:
        return self.kind == SCRIPT_KIND


class ObspFile:
    """Un ``.obsp`` leído entero en memoria."""

    def __init__(self, data: bytes, header: ObspHeader, strings: dict[int, str], entries: list[IndexEntry]) -> None:
        self.data = data
        self.header = header
        self.strings = strings
        self.entries = entries
        self._sha256: str | None = None

    @classmethod
    def parse(cls, data: bytes) -> "ObspFile":
        if len(data) < HEADER.size:
            raise FormatError("El archivo es demasiado corto para ser un OBSP")
        magic, pad, version, unknown, count, strings_end, string_count, max_len = HEADER.unpack_from(data, 0)
        if magic != MAGIC:
            raise FormatError("No es un archivo OBSP: falta la firma 'OBSP'")
        header = ObspHeader(version, unknown, count, strings_end, string_count, max_len, pad)
        index_end = strings_end + count * INDEX_ENTRY.size
        if not HEADER.size <= strings_end <= index_end <= len(data):
            raise FormatError("La cabecera OBSP apunta fuera del archivo")

        reader = ByteReader(data, HEADER.size, strings_end, label="tabla de cadenas")
        strings: dict[int, str] = {}
        for _ in range(string_count):
            value_hash, length = reader.unpack(STRING_HEAD)
            strings[value_hash] = reader.text(length)
        if reader.remaining():
            raise FormatError("La tabla de cadenas no termina donde dice la cabecera")

        entries = []
        size = len(data)
        for values in INDEX_ENTRY.iter_unpack(data[strings_end:index_end]):
            entry = IndexEntry(*values)
            if entry.offset < index_end or entry.offset + entry.size > size:
                raise FormatError(
                    f"El blob del objeto {identity_text(entry.group, entry.object_id)} sale del archivo"
                )
            entries.append(entry)
        return cls(data, header, strings, entries)

    @property
    def index_end(self) -> int:
        return self.header.strings_end + len(self.entries) * INDEX_ENTRY.size

    def blob(self, position: int) -> bytes:
        entry = self.entries[position]
        return self.data[entry.offset:entry.offset + entry.size]

    def blobs(self) -> list[bytes]:
        return [self.blob(position) for position in range(len(self.entries))]

    def text(self, value_hash: int) -> str | None:
        return self.strings.get(value_hash)

    def sha256(self) -> str:
        if self._sha256 is None:
            self._sha256 = hashlib.sha256(self.data).hexdigest().upper()
        return self._sha256

    def layout_problems(self) -> list[str]:
        """Diferencias con la disposición que produce el escritor (contigua, sin relleno)."""
        problems = []
        cursor = self.index_end
        for position, entry in enumerate(self.entries):
            if entry.offset != cursor:
                problems.append(f"objeto {position}: offset 0x{entry.offset:x}, se esperaba 0x{cursor:x}")
                break
            cursor += entry.size
        if not problems and cursor != len(self.data):
            problems.append(f"el último blob acaba en 0x{cursor:x} y el archivo en 0x{len(self.data):x}")
        return problems


def string_table_order(entries: Sequence[IndexEntry]) -> list[int]:
    """Hashes de la tabla de cadenas, sin repetir y en orden de primera aparición."""
    seen: dict[int, None] = {}
    for entry in entries:
        for value_hash in (entry.path_hash, entry.name_hash, entry.folder_hash, entry.class_hash):
            if value_hash not in seen:
                seen[value_hash] = None
    return list(seen)


def build_obsp(
    header: ObspHeader,
    entries: Sequence[IndexEntry],
    blobs: Sequence[bytes],
    strings: Mapping[int, str],
) -> bytes:
    """Escribe un OBSP completo.

    De ``header`` solo se conservan ``version``, ``unknown`` y ``pad``; el resto se
    recalcula. De cada entrada se ignoran ``offset`` y ``size``.
    """
    if len(entries) != len(blobs):
        raise FormatError("Hay distinto número de entradas que de blobs")
    table = bytearray()
    max_length = 0
    order = string_table_order(entries)
    for value_hash in order:
        try:
            raw = strings[value_hash].encode(TEXT_ENCODING)
        except KeyError:
            raise FormatError(f"Falta la cadena del hash 0x{value_hash:016X}") from None
        table += STRING_HEAD.pack(value_hash, len(raw))
        table += raw
        max_length = max(max_length, len(raw))

    strings_end = HEADER.size + len(table)
    cursor = strings_end + len(entries) * INDEX_ENTRY.size
    index = bytearray()
    for entry, blob in zip(entries, blobs):
        placed = replace(entry, offset=cursor, size=len(blob))
        index += INDEX_ENTRY.pack(
            placed.path_hash,
            placed.object_id,
            placed.offset,
            placed.size,
            placed.group,
            placed.kind,
            placed.name_hash,
            placed.folder_hash,
            placed.class_hash,
        )
        cursor += len(blob)
    if cursor > 0xFFFFFFFF:
        raise FormatError("El archivo resultante supera los 4 GiB que admite el índice")

    head = HEADER.pack(
        MAGIC,
        header.pad,
        header.version,
        header.unknown,
        len(entries),
        strings_end,
        len(order),
        max_length,
    )
    return b"".join([head, bytes(table), bytes(index), *blobs])


def rebuild(obsp: ObspFile, replacements: Mapping[int, bytes] | None = None) -> bytes:
    """Reconstruye ``obsp`` sustituyendo los blobs indicados por posición."""
    replacements = replacements or {}
    blobs = [
        replacements[position] if position in replacements else obsp.blob(position)
        for position in range(len(obsp.entries))
    ]
    return build_obsp(obsp.header, obsp.entries, blobs, obsp.strings)
