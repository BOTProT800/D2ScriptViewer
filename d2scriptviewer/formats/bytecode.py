# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Bytecode de los scripts compilados (fase 7): tabla de opcodes, desensamblador y ensamblador.

El código de una función empieza por un byte con su número de parámetros y sigue
con instrucciones de longitud variable: un opcode y, según el opcode, un operando.
La tabla se dedujo estadísticamente sobre las 9 721 funciones del juego (apéndice
A.3 del plan): con ella todas se decodifican de forma lineal justo hasta su tamaño
y todos los nombres en línea llevan el hash de su texto.

Solo tienen nombre los opcodes cuyo significado se comprobó con los datos; el
resto se muestra como ``op_XX`` con su operando.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from ..binary import TEXT_ENCODING, U32
from ..errors import FormatError
from . import bod
from .bod import Name

#: Clases de operando.
NONE = "none"
INT32 = "int32"  # literal entero (4 bytes)
FLOAT32 = "float32"  # literal float (4 bytes)
BOOL = "bool"  # literal booleano (1 byte, 0 o 1)
LINE = "line"  # número de línea (u32)
JUMP = "jump"  # destino absoluto dentro del código de la función (u32)
WORD = "word"  # u32 de significado desconocido
NAME = "name"  # u8 longitud + u64 hash + texto + NUL

NAME_HEAD = struct.Struct("<BQ")


@dataclass(frozen=True)
class Opcode:
    code: int
    operand: str
    mnemonic: str
    count: int
    """Apariciones en las 9 721 funciones del juego (documentación)."""


def _op(code: int, operand: str, count: int, mnemonic: str | None = None) -> Opcode:
    return Opcode(code, operand, mnemonic or f"op_{code:02X}", count)


#: Los 57 opcodes del juego. Nombres solo para lo comprobado:
#: línea (siempre crece dentro de una función), literales (int, float, bool 0/1,
#: cadena con su hash), parámetro (hay tantos como indica el primer byte),
#: llamadas (siempre precedidas por el número de argumentos) y fin (último byte).
OPCODES: dict[int, Opcode] = {
    op.code: op
    for op in (
        _op(0x00, NONE, 545), _op(0x01, NONE, 434), _op(0x02, NONE, 551), _op(0x03, NONE, 76),
        _op(0x04, NONE, 5), _op(0x05, NONE, 421), _op(0x06, NONE, 2), _op(0x07, NONE, 21),
        _op(0x08, NONE, 292), _op(0x09, NONE, 46), _op(0x0A, NONE, 3), _op(0x0C, NONE, 6),
        _op(0x0D, NONE, 484), _op(0x0E, NONE, 190), _op(0x0F, NONE, 750),
        _op(0x10, JUMP, 6751), _op(0x12, JUMP, 2415),
        _op(0x13, NONE, 313), _op(0x14, NONE, 346), _op(0x15, NONE, 2418), _op(0x16, NONE, 1699),
        _op(0x17, NONE, 187), _op(0x18, NONE, 165), _op(0x19, NONE, 541), _op(0x1A, NONE, 26),
        _op(0x1B, NONE, 1135), _op(0x1E, NONE, 314), _op(0x1F, NONE, 314), _op(0x20, NAME, 314),
        _op(0x21, NONE, 1989), _op(0x22, FLOAT32, 1113, "float"), _op(0x23, INT32, 32353, "int"),
        _op(0x24, NAME, 12391, "cadena"), _op(0x25, BOOL, 5039, "bool"), _op(0x26, NAME, 42),
        _op(0x27, NAME, 3308), _op(0x28, NAME, 3702, "parámetro"), _op(0x29, NONE, 7736),
        _op(0x2A, NONE, 5026), _op(0x2B, NONE, 5026), _op(0x2C, NAME, 47470), _op(0x2D, WORD, 9091),
        _op(0x2E, NONE, 1129), _op(0x2F, NONE, 9709, "fin"), _op(0x30, NONE, 2270),
        _op(0x31, NONE, 19), _op(0x32, NONE, 23799), _op(0x34, NONE, 1033), _op(0x35, NONE, 23644),
        _op(0x36, NAME, 5), _op(0x38, NAME, 18756, "método"), _op(0x39, NAME, 6329, "llamada"),
        _op(0x3A, NAME, 19286), _op(0x3B, LINE, 64366, "línea"), _op(0x3D, NONE, 268),
        _op(0x3E, NONE, 24), _op(0x43, NONE, 2),
    )
}

OP_INT = 0x23
OP_FLOAT = 0x22
OP_BOOL = 0x25
OP_METHOD = 0x38
OP_CALL = 0x39
OP_CALL_36 = 0x36
OP_VARIABLE = 0x2C
OP_END = 0x2F

_SIZES = {NONE: 0, INT32: 4, FLOAT32: 4, BOOL: 1, LINE: 4, JUMP: 4, WORD: 4}


@dataclass
class Instruction:
    offset: int
    """Dentro del código de la función (el byte 0 es el número de parámetros)."""
    opcode: int
    operand: object = None
    """``None``; ``int`` (línea, salto o palabra); :class:`~.bod.Name`; o, en los literales,
    un nodo :class:`~.bod.Int32`, :class:`~.bod.Float32` o :class:`~.bod.Bool` (editable)."""
    argc: bool = False
    """Es el número de argumentos de una llamada: no se puede parchear."""

    @property
    def info(self) -> Opcode:
        return OPCODES[self.opcode]

    @property
    def is_literal(self) -> bool:
        """Literal de tamaño fijo que se puede parchear (int, float o bool que no es argc)."""
        return self.info.operand in (INT32, FLOAT32, BOOL) and not self.argc

    @property
    def size(self) -> int:
        operand = self.info.operand
        if operand == NAME:
            assert isinstance(self.operand, Name)
            return 1 + NAME_HEAD.size + len(self.operand.text.encode(TEXT_ENCODING)) + 1
        return 1 + _SIZES[operand]


def disassemble(code: bytes) -> tuple[int, list[Instruction]]:
    """(número de parámetros, instrucciones). Falla si un opcode es desconocido o el
    código no acaba justo al final de una instrucción."""
    if not code:
        raise FormatError("Una función vacía no tiene código que desensamblar")
    instructions: list[Instruction] = []
    end = len(code)
    pos = 1
    try:
        while pos < end:
            start = pos
            opcode = code[pos]
            info = OPCODES.get(opcode)
            if info is None:
                raise FormatError(f"Opcode desconocido 0x{opcode:02X} en 0x{start:X}")
            pos += 1
            kind = info.operand
            operand: object = None
            if kind == NAME:
                length, value_hash = NAME_HEAD.unpack_from(code, pos)
                text_start = pos + NAME_HEAD.size
                text_end = text_start + length
                if code[text_end] != 0:
                    raise FormatError(f"Nombre sin NUL final en 0x{start:X}")
                operand = Name(value_hash, code[text_start:text_end].decode(TEXT_ENCODING))
                pos = text_end + 1
            elif kind == INT32:
                operand = bod.Int32(code[pos:pos + 4])
                pos += 4
            elif kind == FLOAT32:
                operand = bod.Float32(code[pos:pos + 4])
                pos += 4
            elif kind == BOOL:
                operand = bod.Bool(code[pos])
                pos += 1
            elif kind != NONE:
                operand = U32.unpack_from(code, pos)[0]
                pos += 4
            if pos > end:
                raise FormatError(f"Instrucción truncada en 0x{start:X}")
            instructions.append(Instruction(start, opcode, operand))
    except (IndexError, struct.error):
        raise FormatError("Código truncado") from None
    _mark_argument_counts(instructions)
    return code[0], instructions


def _mark_argument_counts(instructions: list[Instruction]) -> None:
    """Las llamadas van precedidas del número de argumentos: ``int n`` + llamada, o
    ``int n`` + variable + método. Ese literal no es un valor del usuario."""
    for index, instruction in enumerate(instructions):
        opcode = instruction.opcode
        if opcode in (OP_CALL, OP_CALL_36):
            candidate = index - 1
        elif opcode == OP_METHOD and index >= 2 and instructions[index - 1].opcode == OP_VARIABLE:
            candidate = index - 2
        else:
            continue
        if candidate >= 0 and instructions[candidate].opcode == OP_INT:
            instructions[candidate].argc = True


def assemble(params: int, instructions: list[Instruction]) -> bytes:
    """Inverso de :func:`disassemble`."""
    out = bytearray([params])
    for instruction in instructions:
        info = OPCODES.get(instruction.opcode)
        if info is None:
            raise FormatError(f"Opcode desconocido 0x{instruction.opcode:02X}")
        out.append(instruction.opcode)
        operand = instruction.operand
        kind = info.operand
        if kind == NAME:
            assert isinstance(operand, Name)
            raw = operand.text.encode(TEXT_ENCODING)
            if len(raw) > 0xFF:
                raise FormatError(f"Nombre en línea demasiado largo ({len(raw)} bytes)")
            out += NAME_HEAD.pack(len(raw), operand.hash)
            out += raw
            out.append(0)
        elif kind in (INT32, FLOAT32):
            raw = operand.raw  # type: ignore[union-attr]
            if len(raw) != 4:
                raise FormatError("Un literal numérico ocupa 4 bytes")
            out += raw
        elif kind == BOOL:
            out.append(operand.raw)  # type: ignore[union-attr]
        elif kind != NONE:
            out += U32.pack(operand)  # type: ignore[arg-type]
    return bytes(out)


def operand_text(instruction: Instruction) -> str:
    """El operando como se muestra en el desensamblado."""
    operand = instruction.operand
    kind = instruction.info.operand
    if kind == NAME:
        assert isinstance(operand, Name)
        return repr(operand.text) if instruction.opcode == 0x24 else operand.text
    if kind == JUMP:
        return f"→ 0x{operand:04X}"
    if kind == WORD:
        return f"0x{operand:08X} ({operand})"
    if kind == LINE:
        return str(operand)
    if kind in (INT32, FLOAT32, BOOL):
        return bod.value_text(operand)
    return ""


def mnemonic(instruction: Instruction) -> str:
    return "args" if instruction.argc else instruction.info.mnemonic


def instruction_text(instruction: Instruction) -> str:
    """Una línea de desensamblado, p. ej. ``0x002B  int 21``."""
    operand = operand_text(instruction)
    return f"0x{instruction.offset:04X}  {mnemonic(instruction)}" + (f" {operand}" if operand else "")
