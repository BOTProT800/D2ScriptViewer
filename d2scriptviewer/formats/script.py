# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Scripts compilados (tipo 0): cabecera, cuerpo, serializador y presentación (apéndice A.3).

Un script es la cabecera verificada en la fase 1 (versión, símbolos, hash de ruta y
grupo) seguida del cuerpo, formalizado en la fase 7 sobre los 3 690 scripts del juego:

- hash del nombre corto y hash de la clase base;
- miembros: hash, banderas, tipo y, si las banderas llevan ``0x08``, un valor por
  defecto codificado como en los BOD (los nombres son índices a los símbolos);
- valores iniciales: hash y valor;
- funciones: hash, tamaño y código (:mod:`.bytecode`);
- estados: hash y sus funciones.

Todos los nombres del cuerpo están en la tabla de símbolos del propio script.

Solo se editan, sin cambiar tamaños, los literales int, float y bool del código que
no son número de argumentos, y los int, float y bool de los valores por defecto e
iniciales. :func:`present` construye un árbol con la forma de un BOD cuyas hojas
editables son esos mismos nodos; el resto son :class:`~.bod.Note` de solo lectura.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from ..binary import ByteReader, U32
from ..errors import FormatError
from ..wording import count
from . import bod, bytecode
from .bod import BodDocument, BodObject, ClassRef, Field, Name, Note
from .bytecode import Instruction
from .obsp import IndexEntry

HEADER = struct.Struct("<III")
SYMBOL_HEAD = struct.Struct("<QI")
TRAILER = struct.Struct("<QI")
CLASS_HASHES = struct.Struct("<QQ")
MEMBER_HEAD = struct.Struct("<QBB")
FUNCTION_HEAD = struct.Struct("<QI")
HASH = struct.Struct("<Q")

SCRIPT_VERSION = 1
#: Bit de las banderas de un miembro que indica que lleva valor por defecto.
MEMBER_HAS_DEFAULT = 0x08

#: Nombre del tipo declarado de un miembro (son los tags BOD; el 1 no se conoce).
MEMBER_TYPES = {
    0x02: "int32", 0x03: "float32", 0x04: "bool", 0x05: "cadena", 0x07: "objeto",
    0x09: "lista", 0x0A: "mapa", 0x0B: "tupla",
}

EDITABLE_VALUES = (bod.Int32, bod.Float32, bod.Bool)


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


# --- Cuerpo -----------------------------------------------------------------------------------


@dataclass
class Member:
    name: Name
    flags: int
    type: int
    default: bod.Value | None

    @property
    def type_label(self) -> str:
        return MEMBER_TYPES.get(self.type, f"tipo {self.type}")


@dataclass
class InitialValue:
    name: Name
    value: bod.Value


@dataclass
class Function:
    name: Name
    params: int | None
    """Número de parámetros; ``None`` en una función sin código (tamaño 0)."""
    instructions: list[Instruction] = field(default_factory=list)

    @property
    def code(self) -> bytes:
        if self.params is None:
            return b""
        return bytecode.assemble(self.params, self.instructions)


@dataclass
class State:
    name: Name
    functions: list[Function]


@dataclass
class Script:
    header: ScriptHeader
    header_bytes: bytes
    name: Name
    base: Name
    members: list[Member]
    initial_values: list[InitialValue]
    functions: list[Function]
    states: list[State]

    def all_functions(self) -> list[tuple[State | None, Function]]:
        return [(None, function) for function in self.functions] + [
            (state, function) for state in self.states for function in state.functions
        ]


class _Body:
    """Lector del cuerpo: los nombres se resuelven con la tabla de símbolos."""

    def __init__(self, data: bytes, header: ScriptHeader) -> None:
        self.data = data
        self.pos = header.body_offset
        self.names = [Name(symbol.hash, symbol.text) for symbol in header.symbols]
        self.by_hash = {name.hash: name for name in self.names}

    def unpack(self, layout: struct.Struct) -> tuple:
        values = layout.unpack_from(self.data, self.pos)
        self.pos += layout.size
        return values

    def name(self, value_hash: int) -> Name:
        name = self.by_hash.get(value_hash)
        if name is None:
            raise FormatError(f"El hash {value_hash:016X} no está en la tabla de símbolos del script")
        return name

    def value(self) -> bod.Value:
        decoder = bod._Decoder(self.data, self.pos)
        decoder.names = list(self.names)
        value = decoder.value()
        if len(decoder.names) != len(self.names):
            raise FormatError(f"Un valor del script define un nombre nuevo en 0x{self.pos:X}")
        self.pos = decoder.pos
        return value

    def functions(self) -> list[Function]:
        (count,) = self.unpack(U32)
        result = []
        for _ in range(count):
            value_hash, size = self.unpack(FUNCTION_HEAD)
            code = self.data[self.pos:self.pos + size]
            if len(code) != size:
                raise FormatError("El código de una función se sale del blob")
            self.pos += size
            if size == 0:
                result.append(Function(self.name(value_hash), None))
                continue
            params, instructions = bytecode.disassemble(code)
            result.append(Function(self.name(value_hash), params, instructions))
        return result


def parse(data: bytes) -> Script:
    """Interpreta el script entero; falla si sobran o faltan bytes."""
    header = parse_header(data)
    body = _Body(data, header)
    try:
        name_hash, base_hash = body.unpack(CLASS_HASHES)
        members = []
        for _ in range(body.unpack(U32)[0]):
            value_hash, flags, kind = body.unpack(MEMBER_HEAD)
            default = body.value() if flags & MEMBER_HAS_DEFAULT else None
            members.append(Member(body.name(value_hash), flags, kind, default))
        initial_values = []
        for _ in range(body.unpack(U32)[0]):
            (value_hash,) = body.unpack(HASH)
            initial_values.append(InitialValue(body.name(value_hash), body.value()))
        functions = body.functions()
        states = []
        for _ in range(body.unpack(U32)[0]):
            (value_hash,) = body.unpack(HASH)
            states.append(State(body.name(value_hash), body.functions()))
        script = Script(
            header, data[:header.body_offset], body.name(name_hash), body.name(base_hash),
            members, initial_values, functions, states,
        )
    except (IndexError, struct.error):
        raise FormatError("El script está truncado") from None
    if body.pos != len(data):
        raise FormatError(f"El script tiene {len(data) - body.pos} bytes de más")
    return script


class _ValueEncoder(bod._Encoder):
    """Codifica valores con los nombres como índices a los símbolos del script."""

    __slots__ = ("symbols",)

    def __init__(self, symbols: dict[Name, int]) -> None:
        super().__init__()
        self.symbols = symbols

    def name(self, name: Name) -> None:
        index = self.symbols.get(name)
        if index is None:
            raise FormatError(f"«{name.text}» no está en la tabla de símbolos del script")
        self.out.append(bod.NAME_REFERENCE)
        self.out += U32.pack(index)


def encode(script: Script) -> bytes:
    """Inverso de :func:`parse`; un script del juego sin editar sale idéntico."""
    symbols = {Name(symbol.hash, symbol.text): index for index, symbol in enumerate(script.header.symbols)}

    def known(name: Name) -> int:
        if name not in symbols:
            raise FormatError(f"«{name.text}» no está en la tabla de símbolos del script")
        return name.hash

    def value(item: bod.Value) -> bytes:
        encoder = _ValueEncoder(symbols)
        encoder.value(item)
        return bytes(encoder.out)

    def functions(items: list[Function]) -> bytes:
        parts = [U32.pack(len(items))]
        for function in items:
            code = function.code
            parts.append(FUNCTION_HEAD.pack(known(function.name), len(code)))
            parts.append(code)
        return b"".join(parts)

    out = bytearray(script.header_bytes)
    out += CLASS_HASHES.pack(known(script.name), known(script.base))
    out += U32.pack(len(script.members))
    for member in script.members:
        out += MEMBER_HEAD.pack(known(member.name), member.flags, member.type)
        if (member.default is not None) != bool(member.flags & MEMBER_HAS_DEFAULT):
            raise FormatError(f"El miembro {member.name.text} no concuerda con sus banderas")
        if member.default is not None:
            out += value(member.default)
    out += U32.pack(len(script.initial_values))
    for initial in script.initial_values:
        out += HASH.pack(known(initial.name)) + value(initial.value)
    out += functions(script.functions)
    out += U32.pack(len(script.states))
    for state in script.states:
        out += HASH.pack(known(state.name)) + functions(state.functions)
    return bytes(out)


def all_names(script: Script) -> list[Name]:
    """Los nombres en línea del código (para comprobar sus hashes)."""
    return [
        instruction.operand
        for _state, function in script.all_functions()
        for instruction in function.instructions
        if isinstance(instruction.operand, Name)
    ]


def editable_leaves(script: Script) -> list[bod.Value]:
    """Los nodos que se pueden parchear, en un orden fijo (para comparar dos versiones)."""
    leaves: list[bod.Value] = []

    def collect(node: object, key: bool = False) -> None:
        if isinstance(node, EDITABLE_VALUES) and not key:
            leaves.append(node)  # type: ignore[arg-type]
        elif isinstance(node, bod.Pair):
            collect(node.key, key=True)
            collect(node.value)
        else:
            for _label, child in bod.children(node):
                collect(child)

    for member in script.members:
        if member.default is not None:
            collect(member.default)
    for initial in script.initial_values:
        collect(initial.value)
    for _state, function in script.all_functions():
        leaves.extend(instruction.operand for instruction in function.instructions  # type: ignore[misc]
                      if instruction.is_literal)
    return leaves


def only_literals_changed(original: bytes, patched: bytes) -> bool:
    """``patched`` es ``original`` con, como mucho, otros valores en las hojas editables."""
    if len(original) != len(patched):
        return False
    before, after = parse(original), parse(patched)
    old_leaves, new_leaves = editable_leaves(before), editable_leaves(after)
    if len(old_leaves) != len(new_leaves):
        return False
    for old, new in zip(old_leaves, new_leaves):
        if type(old) is not type(new):
            return False
        new.raw = old.raw  # type: ignore[attr-defined]
    return encode(after) == original


# --- Presentación -----------------------------------------------------------------------------


class ScriptTree(BodDocument):
    """Árbol de presentación de un script, con la forma de un BOD (para el panel de propiedades).

    Sus hojas editables son los mismos nodos del :class:`Script`, así que editar el
    árbol edita el script, que es lo que se recodifica al guardar.
    """

    def __init__(self, script: Script, root: BodObject) -> None:
        super().__init__(script.header.version, 0, root, len(script.header.symbols), script.header.max_symbol_length)
        self.script = script


def _object(label: str, fields: list[Field]) -> BodObject:
    return BodObject(None, ClassRef(bod.CLASS_NATIVE, None, Name(0, label)), fields)


def _field(label: str, value: bod.Value) -> Field:
    return Field(Name(0, label), value)


def _mirror(node: object) -> object:
    """Copia de presentación: contenedores nuevos, hojas editables compartidas y el resto, notas."""
    if isinstance(node, EDITABLE_VALUES):
        return node
    if isinstance(node, BodObject):
        return BodObject(node.index, node.cls, [Field(f.name, _mirror(f.value)) for f in node.fields])  # type: ignore[arg-type]
    if isinstance(node, bod.Pair):
        key = Note(bod.value_text(node.key), bod.type_text(node.key))
        return bod.Pair(key, _mirror(node.value))  # type: ignore[arg-type]
    if isinstance(node, bod.BodList):
        return bod.BodList(node.mode, [_mirror(item) for item in node.items])
    if isinstance(node, bod.BodMap):
        return bod.BodMap(node.mode, [_mirror(item) for item in node.items])  # type: ignore[misc]
    if isinstance(node, bod.BodTuple):
        return bod.BodTuple([_mirror(item) for item in node.items])  # type: ignore[misc]
    return Note(bod.value_text(node), bod.type_text(node))


def _function_node(function: Function) -> bod.Value:
    if function.params is None:
        return Note("sin código", "función")
    fields = [_field("Parámetros", Note(str(function.params), "u8"))]
    for instruction in function.instructions:
        label = f"0x{instruction.offset:04X}"
        if instruction.is_literal:
            fields.append(_field(label, instruction.operand))  # type: ignore[arg-type]
        else:
            fields.append(_field(label, Note(bytecode.operand_text(instruction), bytecode.mnemonic(instruction))))
    size = len(function.code)
    return _object(f"función · {count(function.params, 'parámetro')} · {size:,} bytes", fields)


def _functions_node(functions: list[Function]) -> BodObject:
    return _object(f"{len(functions)} funciones", [_field(f.name.text, _function_node(f)) for f in functions])


def present(script: Script) -> ScriptTree:
    header = script.header
    members = []
    for member in script.members:
        if member.default is not None:
            members.append(_field(member.name.text, _mirror(member.default)))  # type: ignore[arg-type]
        else:
            members.append(
                _field(member.name.text, Note(f"sin valor por defecto · banderas 0x{member.flags:02X}", member.type_label))
            )
    root = _object(
        "script",
        [
            _field("Versión", Note(str(header.version), "u32")),
            _field("Símbolos", Note(f"{len(header.symbols):,} (ver pestaña Script)", "u32")),
            _field("Hash de ruta", Note(f"{header.path_hash:016X}", "u64")),
            _field("Grupo", Note(str(header.group), "u32")),
            _field("Nombre", Note(script.name.text, "nombre")),
            _field("Clase base", Note(script.base.text, "nombre")),
            _field("Miembros", _object(f"{len(script.members)} miembros", members)),
            _field(
                "Valores iniciales",
                _object(
                    f"{len(script.initial_values)} valores",
                    [_field(item.name.text, _mirror(item.value)) for item in script.initial_values],  # type: ignore[arg-type]
                ),
            ),
            _field("Funciones", _functions_node(script.functions)),
            _field(
                "Estados",
                _object(f"{len(script.states)} estados", [_field(s.name.text, _functions_node(s.functions)) for s in script.states]),
            ),
        ],
    )
    return ScriptTree(script, root)


def disassembly_lines(script: Script) -> list[str]:
    """El script entero como texto (CLI ``disasm``)."""
    header = script.header
    lines = [
        f"script {script.name.text}, clase base {script.base.text}, "
        f"{len(header.symbols)} símbolos, grupo {header.group}",
        f"miembros ({len(script.members)}):",
    ]
    for member in script.members:
        value = bod.value_text(member.default) if member.default is not None else "sin valor por defecto"
        lines.append(f"  {member.name.text}: {member.type_label}, banderas 0x{member.flags:02X} = {value}")
    lines.append(f"valores iniciales ({len(script.initial_values)}):")
    for item in script.initial_values:
        lines.append(f"  {item.name.text} = {bod.type_text(item.value)} {bod.value_text(item.value)}")
    for state, function in script.all_functions():
        owner = f"estado {state.name.text} · " if state is not None else ""
        if function.params is None:
            lines.append(f"{owner}función {function.name.text}: sin código")
            continue
        lines.append(f"{owner}función {function.name.text} ({count(function.params, 'parámetro')}, {len(function.code):,} bytes):")
        lines.extend(f"  {bytecode.instruction_text(instruction)}" for instruction in function.instructions)
    return lines
