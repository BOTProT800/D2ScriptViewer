# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Lectura binaria little-endian acotada sobre datos en memoria."""

from __future__ import annotations

import struct

from .errors import FormatError

U8 = struct.Struct("<B")
U16 = struct.Struct("<H")
U32 = struct.Struct("<I")
I32 = struct.Struct("<i")
U64 = struct.Struct("<Q")
F32 = struct.Struct("<f")

#: Las cadenas del archivo se leen como latin-1: es biyectivo con los bytes, así
#: que nada se pierde al reescribir. La validación de las ediciones exige ASCII.
TEXT_ENCODING = "latin-1"


class ByteReader:
    """Cursor sobre ``bytes`` que nunca lee fuera de ``[start, end)``."""

    __slots__ = ("data", "pos", "end", "label")

    def __init__(self, data: bytes, pos: int = 0, end: int | None = None, *, label: str = "datos") -> None:
        self.data = data
        self.pos = pos
        self.end = len(data) if end is None else end
        self.label = label
        if not 0 <= pos <= self.end <= len(data):
            raise FormatError(f"Rango inválido en {label}")

    def remaining(self) -> int:
        return self.end - self.pos

    def _take(self, count: int) -> int:
        start = self.pos
        if count < 0 or start + count > self.end:
            raise FormatError(
                f"Lectura fuera de rango en {self.label}: 0x{start:x} + {count} > 0x{self.end:x}"
            )
        self.pos = start + count
        return start

    def read(self, count: int) -> bytes:
        start = self._take(count)
        return self.data[start:start + count]

    def unpack(self, layout: struct.Struct) -> tuple:
        return layout.unpack_from(self.data, self._take(layout.size))

    def u8(self) -> int:
        return U8.unpack_from(self.data, self._take(1))[0]

    def u16(self) -> int:
        return U16.unpack_from(self.data, self._take(2))[0]

    def u32(self) -> int:
        return U32.unpack_from(self.data, self._take(4))[0]

    def u64(self) -> int:
        return U64.unpack_from(self.data, self._take(8))[0]

    def text(self, length: int) -> str:
        return self.read(length).decode(TEXT_ENCODING)
