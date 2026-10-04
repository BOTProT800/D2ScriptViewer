# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Scripts compilados (tipo 0): cabecera y tabla de símbolos (apéndice A.3 del plan).

Solo se interpreta la cabecera verificada. El cuerpo (bytecode y tablas de
miembros y funciones) se trata como bytes opacos de solo lectura hasta la fase 7.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from ..binary import ByteReader
from ..errors import FormatError
from .obsp import IndexEntry

HEADER = struct.Struct("<III")
SYMBOL_HEAD = struct.Struct("<QI")
TRAILER = struct.Struct("<QI")

SCRIPT_VERSION = 1


@dataclass(frozen=True)
class Symbol:
    hash: int
    text: str


@dataclass(frozen=True)
class ScriptHeader:
    version: int
    declared_max_symbol_length: int
    symbols: tuple[Symbol, ...]
    path_hash: int
    group: int
    body_offset: int
    """Offset, dentro del blob, del primer byte que sigue a la cabecera."""

    @property
    def max_symbol_length(self) -> int:
        return max((len(symbol.text) for symbol in self.symbols), default=0)


def parse_header(data: bytes) -> ScriptHeader:
    reader = ByteReader(data, label="cabecera de script")
    version, count, max_length = reader.unpack(HEADER)
    if count > len(data) // SYMBOL_HEAD.size:
        raise FormatError(f"Número de símbolos imposible: {count}")
    symbols = []
    for _ in range(count):
        value_hash, length = reader.unpack(SYMBOL_HEAD)
        symbols.append(Symbol(value_hash, reader.text(length)))
    path_hash, group = reader.unpack(TRAILER)
    return ScriptHeader(version, max_length, tuple(symbols), path_hash, group, reader.pos)


def header_problems(header: ScriptHeader, entry: IndexEntry) -> list[str]:
    """Incoherencias entre la cabecera y su entrada del índice (vacío si todo cuadra)."""
    problems = []
    if header.version != SCRIPT_VERSION:
        problems.append(f"versión {header.version}, se esperaba {SCRIPT_VERSION}")
    if header.declared_max_symbol_length != header.max_symbol_length:
        problems.append(
            f"longitud máxima declarada {header.declared_max_symbol_length}, "
            f"real {header.max_symbol_length}"
        )
    if header.path_hash != entry.path_hash:
        problems.append("el hash de ruta no coincide con el del índice")
    if header.group != entry.group:
        problems.append(f"grupo {header.group}, el índice dice {entry.group}")
    return problems
