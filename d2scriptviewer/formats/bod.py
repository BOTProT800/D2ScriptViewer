# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Blobs BOD: árbol tipado, decodificador y codificador canónico (apéndice A.2 del plan).

Cada blob lleva su propia tabla de nombres internada: ``01`` define un nombre
nuevo con su hash y ``00`` remite a uno ya definido. La comparten los nombres de
campo, los de clase y las cadenas ``0F``.

El codificador es canónico: interna por (hash, texto) en un recorrido en
profundidad (la clase antes que los campos, el nombre antes que el valor),
numera los objetos ``07`` en ese mismo orden y recalcula los dos contadores de
la cabecera. Con eso reproduce byte a byte los blobs del juego.

Los int32 y float32 guardan sus 4 bytes crudos y el bool su byte crudo: un valor
sin editar nunca cambia por redondeo ni por normalización.
"""

from __future__ import annotations

import difflib
import functools
import math
from decimal import Decimal
import re
import struct
import unicodedata
from typing import Callable, Iterator, NamedTuple, Union

from ..binary import F32, I32, TEXT_ENCODING, U16, U32
from ..errors import FormatError, PathError
from ..wording import count

MAGIC = b"BOD\xfd"
HEADER = struct.Struct("<4sHHII")
NAME_HEAD = struct.Struct("<QH")
EXTERNAL_REF = struct.Struct("<IQ")
SEQUENCE_HEAD = struct.Struct("<IB")

TAG_INT32 = 0x02
TAG_FLOAT32 = 0x03
TAG_BOOL = 0x04
TAG_RAW_STRING = 0x05
TAG_OBJECT = 0x07
TAG_LIST = 0x09
TAG_MAP = 0x0A
TAG_TUPLE = 0x0B
TAG_NAME = 0x0F
TAG_EXTERNAL_REF = 0xFC
TAG_NULL = 0xFE

NAME_REFERENCE = 0x00
NAME_DEFINITION = 0x01

CLASS_NATIVE = 0x01
CLASS_SCRIPT = 0x04

#: Byte fijo que precede a la longitud de una cadena ``05``.
RAW_STRING_MARKER = 0xFF

MODE_VALUES = 0
MODE_PAIRS = 1

MAX_TEXT_LENGTH = 0xFFFF


class Name(NamedTuple):
    """Un nombre internado: su hash de 64 bits y su texto."""

    hash: int
    text: str


class ClassRef(NamedTuple):
    """Clase de un objeto: nativa (``01``) o de script (``04``, con su grupo)."""

    kind: int
    group: int | None
    name: Name

    @property
    def is_script(self) -> bool:
        return self.kind == CLASS_SCRIPT

    def label(self) -> str:
        if self.is_script:
            return f"{self.name.text} (script, grupo {self.group})"
        return self.name.text


class Value:
    """Base de todos los valores. ``tag`` es el byte que lo precede en el blob."""

    __slots__ = ()
    tag = -1
    type_label = "?"


class Int32(Value):
    __slots__ = ("raw",)
    tag = TAG_INT32
    type_label = "int32"

    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    @classmethod
    def of(cls, value: int) -> "Int32":
        return cls(I32.pack(value))

    @property
    def value(self) -> int:
        return I32.unpack(self.raw)[0]


class Float32(Value):
    __slots__ = ("raw",)
    tag = TAG_FLOAT32
    type_label = "float32"

    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    @classmethod
    def of(cls, value: float) -> "Float32":
        return cls(F32.pack(value))

    @property
    def value(self) -> float:
        return F32.unpack(self.raw)[0]


class Bool(Value):
    __slots__ = ("raw",)
    tag = TAG_BOOL
    type_label = "bool"

    def __init__(self, raw: int) -> None:
        self.raw = raw

    @property
    def value(self) -> bool:
        return self.raw != 0


class RawString(Value):
    """Cadena sin hash (``05``): se puede escribir texto libre ASCII."""

    __slots__ = ("text",)
    tag = TAG_RAW_STRING
    type_label = "cadena"

    def __init__(self, text: str) -> None:
        self.text = text


class HashedString(Value):
    """Cadena con hash (``0F``): un nombre de la tabla internada."""

    __slots__ = ("name",)
    tag = TAG_NAME
    type_label = "nombre"

    def __init__(self, name: Name) -> None:
        self.name = name


class ExternalRef(Value):
    """Referencia a otro objeto del contenedor por su identidad (grupo, idObjeto)."""

    __slots__ = ("group", "object_id")
    tag = TAG_EXTERNAL_REF
    type_label = "referencia"

    def __init__(self, group: int, object_id: int) -> None:
        self.group = group
        self.object_id = object_id

    @property
    def identity(self) -> tuple[int, int]:
        return (self.group, self.object_id)


class Null(Value):
    __slots__ = ()
    tag = TAG_NULL
    type_label = "nulo"


class Note(Value):
    """Fila de presentación de solo lectura (scripts compilados): nunca se codifica como BOD."""

    __slots__ = ("text", "type_label")

    def __init__(self, text: str, type_label: str = "") -> None:
        self.text = text
        self.type_label = type_label  # type: ignore[misc]


class Field:
    __slots__ = ("name", "value")

    def __init__(self, name: Name, value: Value) -> None:
        self.name = name
        self.value = value


class Pair:
    __slots__ = ("key", "value")

    def __init__(self, key: Value, value: Value) -> None:
        self.key = key
        self.value = value


class BodObject(Value):
    """Objeto (``07``). ``index`` es el número leído; el codificador lo recalcula."""

    __slots__ = ("index", "cls", "fields")
    tag = TAG_OBJECT
    type_label = "objeto"

    def __init__(self, index: int | None, cls: ClassRef, fields: list[Field]) -> None:
        self.index = index
        self.cls = cls
        self.fields = fields


class BodList(Value):
    """Lista (``09``): en modo 0 contiene valores; en modo 1, pares clave/valor."""

    __slots__ = ("mode", "items")
    tag = TAG_LIST

    def __init__(self, mode: int, items: list) -> None:
        self.mode = mode
        self.items = items

    @property
    def type_label(self) -> str:  # type: ignore[override]
        return "pares" if self.mode == MODE_PAIRS else "lista"


class BodMap(Value):
    """Mapa (``0A``): pares clave/valor. En el juego el modo es siempre 1."""

    __slots__ = ("mode", "items")
    tag = TAG_MAP
    type_label = "mapa"

    def __init__(self, mode: int, items: list[Pair]) -> None:
        self.mode = mode
        self.items = items


class BodTuple(Value):
    __slots__ = ("items",)
    tag = TAG_TUPLE
    type_label = "tupla"

    def __init__(self, items: list[Value]) -> None:
        self.items = items


Container = Union[BodObject, BodList, BodMap, BodTuple]


class BodDocument:
    """Un blob BOD decodificado.

    ``version`` y ``flags`` (el ``u16 = 1`` de significado desconocido) se
    conservan tal cual. Los contadores declarados solo sirven para comprobar que
    el blob de origen era canónico; el codificador los recalcula.
    """

    __slots__ = ("version", "flags", "root", "declared_name_count", "declared_max_name_length")

    def __init__(
        self,
        version: int,
        flags: int,
        root: BodObject,
        declared_name_count: int = 0,
        declared_max_name_length: int = 0,
    ) -> None:
        self.version = version
        self.flags = flags
        self.root = root
        self.declared_name_count = declared_name_count
        self.declared_max_name_length = declared_max_name_length


# --- Decodificación ---------------------------------------------------------------------------


class _Decoder:
    __slots__ = ("data", "pos", "names")

    def __init__(self, data: bytes, pos: int) -> None:
        self.data = data
        self.pos = pos
        self.names: list[Name] = []

    def name(self) -> Name:
        data = self.data
        pos = self.pos
        marker = data[pos]
        if marker == NAME_REFERENCE:
            index = U32.unpack_from(data, pos + 1)[0]
            self.pos = pos + 5
            if index >= len(self.names):
                raise FormatError(f"Referencia a un nombre no definido ({index}) en 0x{pos:x}")
            return self.names[index]
        if marker == NAME_DEFINITION:
            value_hash, length = NAME_HEAD.unpack_from(data, pos + 1)
            start = pos + 11
            self.pos = start + length
            name = Name(value_hash, data[start:start + length].decode(TEXT_ENCODING))
            self.names.append(name)
            return name
        raise FormatError(f"Marca de nombre desconocida 0x{marker:02X} en 0x{pos:x}")

    def class_ref(self) -> ClassRef:
        data = self.data
        pos = self.pos
        kind = data[pos]
        if kind == CLASS_NATIVE:
            self.pos = pos + 1
            return ClassRef(kind, None, self.name())
        if kind == CLASS_SCRIPT:
            group = U32.unpack_from(data, pos + 1)[0]
            self.pos = pos + 5
            return ClassRef(kind, group, self.name())
        raise FormatError(f"Tipo de clase desconocido 0x{kind:02X} en 0x{pos:x}")

    def fields(self) -> list[Field]:
        count = U32.unpack_from(self.data, self.pos)[0]
        self.pos += 4
        name = self.name
        value = self.value
        result = []
        append = result.append
        for _ in range(count):
            field_name = name()
            append(Field(field_name, value()))
        return result

    def pairs(self, count: int) -> list[Pair]:
        value = self.value
        result = []
        append = result.append
        for _ in range(count):
            key = value()
            append(Pair(key, value()))
        return result

    def value(self) -> Value:
        data = self.data
        pos = self.pos
        tag = data[pos]
        pos += 1
        if tag == TAG_INT32:
            self.pos = pos + 4
            return Int32(data[pos:pos + 4])
        if tag == TAG_NAME:
            self.pos = pos
            return HashedString(self.name())
        if tag == TAG_FLOAT32:
            self.pos = pos + 4
            return Float32(data[pos:pos + 4])
        if tag == TAG_OBJECT:
            index = U32.unpack_from(data, pos)[0]
            self.pos = pos + 4
            cls = self.class_ref()
            return BodObject(index, cls, self.fields())
        if tag == TAG_BOOL:
            self.pos = pos + 1
            return Bool(data[pos])
        if tag == TAG_LIST or tag == TAG_MAP:
            count, mode = SEQUENCE_HEAD.unpack_from(data, pos)
            self.pos = pos + 5
            if mode == MODE_PAIRS:
                items: list = self.pairs(count)
            elif mode == MODE_VALUES and tag == TAG_LIST:
                value = self.value
                items = [value() for _ in range(count)]
            else:
                raise FormatError(f"Modo {mode} desconocido en la secuencia 0x{tag:02X} de 0x{pos - 1:x}")
            return BodList(mode, items) if tag == TAG_LIST else BodMap(mode, items)
        if tag == TAG_TUPLE:
            count = U32.unpack_from(data, pos)[0]
            self.pos = pos + 4
            value = self.value
            return BodTuple([value() for _ in range(count)])
        if tag == TAG_EXTERNAL_REF:
            group, object_id = EXTERNAL_REF.unpack_from(data, pos)
            self.pos = pos + 12
            return ExternalRef(group, object_id)
        if tag == TAG_RAW_STRING:
            marker = data[pos]
            if marker != RAW_STRING_MARKER:
                raise FormatError(f"Cadena 05 sin la marca 0xFF en 0x{pos:x}")
            length = U16.unpack_from(data, pos + 1)[0]
            start = pos + 3
            self.pos = start + length
            return RawString(data[start:start + length].decode(TEXT_ENCODING))
        if tag == TAG_NULL:
            self.pos = pos
            return Null()
        raise FormatError(f"Tag desconocido 0x{tag:02X} en 0x{pos - 1:x}")


def decode(data: bytes) -> BodDocument:
    """Decodifica un blob BOD completo; falla si sobran o faltan bytes."""
    if len(data) < HEADER.size or data[:4] != MAGIC:
        raise FormatError("No es un blob BOD: falta la firma 'BOD\\xFD'")
    _magic, version, flags, name_count, max_name_length = HEADER.unpack_from(data, 0)
    decoder = _Decoder(data, HEADER.size)
    try:
        cls = decoder.class_ref()
        root = BodObject(None, cls, decoder.fields())
    except (IndexError, struct.error):
        raise FormatError("El blob BOD está truncado") from None
    if decoder.pos != len(data):
        raise FormatError(f"El blob BOD tiene {len(data) - decoder.pos} bytes de más o de menos")
    return BodDocument(version, flags, root, name_count, max_name_length)


def is_bod(data: bytes) -> bool:
    return data[:4] == MAGIC


# --- Codificación canónica --------------------------------------------------------------------


class _Encoder:
    __slots__ = ("out", "names", "max_length", "next_index")

    def __init__(self) -> None:
        self.out = bytearray()
        self.names: dict[Name, int] = {}
        self.max_length = 0
        self.next_index = 0

    def name(self, name: Name) -> None:
        out = self.out
        index = self.names.get(name)
        if index is not None:
            out.append(NAME_REFERENCE)
            out += U32.pack(index)
            return
        raw = name.text.encode(TEXT_ENCODING)
        if len(raw) > MAX_TEXT_LENGTH:
            raise FormatError(f"Nombre demasiado largo ({len(raw)} bytes)")
        self.names[name] = len(self.names)
        if len(raw) > self.max_length:
            self.max_length = len(raw)
        out.append(NAME_DEFINITION)
        out += NAME_HEAD.pack(name.hash, len(raw))
        out += raw

    def class_ref(self, cls: ClassRef) -> None:
        if cls.kind == CLASS_SCRIPT:
            self.out.append(CLASS_SCRIPT)
            self.out += U32.pack(cls.group or 0)
        elif cls.kind == CLASS_NATIVE:
            self.out.append(CLASS_NATIVE)
        else:
            raise FormatError(f"Tipo de clase desconocido 0x{cls.kind:02X}")
        self.name(cls.name)

    def fields(self, fields: list[Field]) -> None:
        self.out += U32.pack(len(fields))
        name = self.name
        value = self.value
        for field in fields:
            name(field.name)
            value(field.value)

    def value(self, value: Value) -> None:
        out = self.out
        kind = type(value)
        if kind is Int32 or kind is Float32:
            if len(value.raw) != 4:  # type: ignore[attr-defined]
                raise FormatError("Un número BOD ocupa exactamente 4 bytes")
            out.append(value.tag)
            out += value.raw  # type: ignore[attr-defined]
        elif kind is HashedString:
            out.append(TAG_NAME)
            self.name(value.name)  # type: ignore[attr-defined]
        elif kind is BodObject:
            out.append(TAG_OBJECT)
            out += U32.pack(self.next_index)
            self.next_index += 1
            self.class_ref(value.cls)  # type: ignore[attr-defined]
            self.fields(value.fields)  # type: ignore[attr-defined]
        elif kind is Bool:
            out.append(TAG_BOOL)
            out.append(value.raw)  # type: ignore[attr-defined]
        elif kind is BodList or kind is BodMap:
            items = value.items  # type: ignore[attr-defined]
            mode = value.mode  # type: ignore[attr-defined]
            out.append(value.tag)
            out += SEQUENCE_HEAD.pack(len(items), mode)
            if mode == MODE_PAIRS:
                for pair in items:
                    self.value(pair.key)
                    self.value(pair.value)
            elif mode == MODE_VALUES and kind is BodList:
                for item in items:
                    self.value(item)
            else:
                raise FormatError(f"Modo {mode} desconocido en la secuencia 0x{value.tag:02X}")
        elif kind is BodTuple:
            items = value.items  # type: ignore[attr-defined]
            out.append(TAG_TUPLE)
            out += U32.pack(len(items))
            for item in items:
                self.value(item)
        elif kind is ExternalRef:
            out.append(TAG_EXTERNAL_REF)
            out += EXTERNAL_REF.pack(value.group, value.object_id)  # type: ignore[attr-defined]
        elif kind is RawString:
            raw = value.text.encode(TEXT_ENCODING)  # type: ignore[attr-defined]
            if len(raw) > MAX_TEXT_LENGTH:
                raise FormatError(f"Cadena demasiado larga ({len(raw)} bytes)")
            out.append(TAG_RAW_STRING)
            out.append(RAW_STRING_MARKER)
            out += U16.pack(len(raw))
            out += raw
        elif kind is Null:
            out.append(TAG_NULL)
        else:
            raise FormatError(f"Valor BOD desconocido: {kind.__name__}")


def encode(document: BodDocument) -> bytes:
    """Codifica de forma canónica; un blob del juego sin editar sale idéntico."""
    encoder = _Encoder()
    encoder.class_ref(document.root.cls)
    encoder.fields(document.root.fields)
    header = HEADER.pack(MAGIC, document.version, document.flags, len(encoder.names), encoder.max_length)
    return header + bytes(encoder.out)


class _FingerprintEncoder(_Encoder):
    """Serializa un subárbol sin depender de su contexto: sin internado ni numeración."""

    __slots__ = ()

    def name(self, name: Name) -> None:
        raw = name.text.encode(TEXT_ENCODING)
        self.out += NAME_HEAD.pack(name.hash, len(raw))
        self.out += raw

    def value(self, value: Value) -> None:
        if type(value) is Note:
            raw = f"{value.type_label}\0{value.text}".encode(TEXT_ENCODING, "replace")  # type: ignore[attr-defined]
            self.out.append(0xEE)
            self.out += U32.pack(len(raw))
            self.out += raw
            return
        if type(value) is BodObject:
            # El índice depende de la posición en el blob; para comparar no cuenta.
            self.out.append(TAG_OBJECT)
            self.class_ref(value.cls)
            self.fields(value.fields)
            return
        super().value(value)


def fingerprint(node: object) -> bytes:
    """Bytes que identifican el contenido de un subárbol, esté donde esté.

    Dos subárboles con la misma huella se codifican igual en cualquier posición.
    """
    encoder = _FingerprintEncoder()
    if isinstance(node, Pair):
        encoder.value(node.key)
        encoder.value(node.value)
    else:
        encoder.value(node)  # type: ignore[arg-type]
    return bytes(encoder.out)


def clone(node: object) -> object:
    """Copia profunda de un valor o de un par. Los nombres y los bytes crudos son inmutables."""
    kind = type(node)
    if kind is Int32 or kind is Float32 or kind is Bool:
        return kind(node.raw)  # type: ignore[attr-defined]
    if kind is RawString:
        return RawString(node.text)  # type: ignore[attr-defined]
    if kind is HashedString:
        return HashedString(node.name)  # type: ignore[attr-defined]
    if kind is ExternalRef:
        return ExternalRef(node.group, node.object_id)  # type: ignore[attr-defined]
    if kind is Null:
        return Null()
    if kind is BodObject:
        return BodObject(
            node.index,  # type: ignore[attr-defined]
            node.cls,  # type: ignore[attr-defined]
            [Field(field.name, clone(field.value)) for field in node.fields],  # type: ignore[attr-defined]
        )
    if kind is BodList or kind is BodMap:
        return kind(node.mode, [clone(item) for item in node.items])  # type: ignore[attr-defined]
    if kind is BodTuple:
        return BodTuple([clone(item) for item in node.items])  # type: ignore[attr-defined]
    if kind is Pair:
        return Pair(clone(node.key), clone(node.value))  # type: ignore[attr-defined]
    raise FormatError(f"No se puede copiar un {kind.__name__}")


def clone_document(document: BodDocument) -> BodDocument:
    root = clone(document.root)
    assert isinstance(root, BodObject)
    return BodDocument(
        document.version, document.flags, root, document.declared_name_count, document.declared_max_name_length
    )


def get_slot(parent: object, key: int) -> object:
    """El hijo ``key`` de ``parent`` (mismo criterio que :func:`children`)."""
    return child(parent, key)[1]


def set_slot(parent: object, key: int, value: object) -> None:
    """Sustituye el hijo ``key`` de ``parent`` por ``value``."""
    if isinstance(parent, BodObject):
        parent.fields[key].value = value  # type: ignore[assignment]
    elif isinstance(parent, (BodList, BodMap, BodTuple)):
        parent.items[key] = value
    elif isinstance(parent, Pair):
        if key == 0:
            parent.key = value  # type: ignore[assignment]
        elif key == 1:
            parent.value = value  # type: ignore[assignment]
        else:
            raise IndexError(key)
    else:
        raise FormatError(f"Un {type(parent).__name__} no tiene hijos")


# --- Recorrido y presentación -----------------------------------------------------------------

#: Un paso de ruta: índice de campo, de elemento o, dentro de un par, 0 (clave) / 1 (valor).
Path = tuple


def children(node: object) -> list[tuple[str, object]]:
    """Hijos directos de un nodo, con la etiqueta que se muestra al usuario."""
    if isinstance(node, BodObject):
        return [(field.name.text, field.value) for field in node.fields]
    if isinstance(node, (BodList, BodMap)):
        if node.mode == MODE_PAIRS:
            return [(f"[{index}]", pair) for index, pair in enumerate(node.items)]
        return [(f"[{index}]", item) for index, item in enumerate(node.items)]
    if isinstance(node, BodTuple):
        return [(f"[{index}]", item) for index, item in enumerate(node.items)]
    if isinstance(node, Pair):
        return [("clave", node.key), ("valor", node.value)]
    return []


def child(node: object, step: int) -> tuple[str, object]:
    """``children(node)[step]`` sin construir la lista entera de hijos.

    En una lista de miles de elementos es la diferencia entre microsegundos y milisegundos por paso.
    """
    if isinstance(node, BodObject):
        field = node.fields[step]
        return field.name.text, field.value
    if isinstance(node, (BodList, BodMap, BodTuple)):
        item = node.items[step]
        return f"[{step % len(node.items)}]", item
    if isinstance(node, Pair):
        return (("clave", node.key), ("valor", node.value))[step]
    raise IndexError(step)


def has_children(node: object) -> bool:
    if isinstance(node, BodObject):
        return bool(node.fields)
    if isinstance(node, (BodList, BodMap, BodTuple)):
        return bool(node.items)
    return isinstance(node, Pair)


def resolve(document: BodDocument, path: Path) -> object:
    """Devuelve el nodo al que lleva ``path`` desde la raíz."""
    node: object = document.root
    for step in path:
        node = child(node, step)[1]
    return node


def walk(node: object, path: Path = ()) -> Iterator[tuple[Path, object]]:
    """Recorrido en profundidad: (ruta, nodo) para el nodo y todos sus descendientes."""
    stack = [(path, node)]
    while stack:
        current_path, current = stack.pop()
        yield current_path, current
        kids = children(current)
        for index in range(len(kids) - 1, -1, -1):
            stack.append((current_path + (index,), kids[index][1]))


def path_label(document: BodDocument, path: Path) -> str:
    """Ruta legible, p. ej. ``Stats.Damage[3].valor``."""
    node: object = document.root
    parts: list[str] = []
    for step in path:
        label, node = child(node, step)
        if label.startswith("["):
            parts.append(label)
        elif parts:
            parts.append("." + label)
        else:
            parts.append(label)
    return "".join(parts) or ROOT_LABEL


# --- Rutas legibles: la inversa de path_label (fase 11) ---------------------------------------

ROOT_LABEL = "(raíz)"
#: Las etiquetas de los dos hijos de un par, en su orden.
PAIR_LABELS = ("clave", "valor")
#: Cuántos nombres parecidos se sugieren cuando un tramo no existe.
SUGGESTIONS = 3
#: Un índice con más cifras no cabe en ninguna lista (y ``int()`` limita las cifras que convierte).
MAX_INDEX_DIGITS = 18
_OFFSET = re.compile(r"0[xX]([0-9A-Fa-f]{1,8})")
_DIGITS = re.compile(r"[0-9]+")
_SPACES = re.compile(r"\s*")
#: Un nombre llega hasta un separador de la ruta, uno de los que preceden a la propiedad (``·`` o
#: ``::``) o un carácter de control. Ninguna etiqueta del juego contiene ``:`` ni ``·``.
_NAME = re.compile(r"[^.\[\]·:\x00-\x1f\x7f-\x9f]*")
_ROOT_TEXTS = ("", ROOT_LABEL, "(raiz)")


class PathStep(NamedTuple):
    """Un tramo de una ruta legible: un nombre (``.Campo``) o un índice (``[3]``).

    ``start`` y ``end`` delimitan el tramo en el texto, para señalarlo si no lleva a ninguna parte.
    """

    name: str | None
    index: int | None
    start: int
    end: int

    @property
    def text(self) -> str:
        return self.name if self.name is not None else f"[{self.index}]"


class PathMatch(NamedTuple):
    """Hasta dónde llega una ruta en un árbol.

    ``path`` es el nodo válido más profundo. Si un tramo no se pudo seguir, ``failed`` es ese
    tramo y ``message`` explica por qué; si se llegó, ``message`` puede llevar un aviso (un
    nombre de campo repetido).
    """

    path: Path
    failed: PathStep | None
    message: str

    @property
    def complete(self) -> bool:
        return self.failed is None


def fold(text: str) -> str:
    """Texto para comparar sin distinguir mayúsculas ni tildes (``Parámetros`` = ``parametros``)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _skip_spaces(text: str, position: int, end: int) -> int:
    return _SPACES.match(text, position, end).end()  # type: ignore[union-attr]


def _read_name(text: str, position: int, end: int) -> tuple[str, int, int]:
    """El nombre que empieza en ``position``: (nombre sin espacios al final, su fin, dónde sigue)."""
    stop = _NAME.match(text, position, end).end()  # type: ignore[union-attr]
    name = text[position:stop].rstrip()
    return name, position + len(name), stop


def parse_path_label(text: str, start: int = 0, end: int | None = None) -> list[PathStep]:
    """Los tramos de una ruta escrita como la da :func:`path_label` (``Stats.Damage[3].valor``).

    Analiza ``text[start:end]``. Tolera espacios entre tramos y dentro de los corchetes, y
    ceros a la izquierda en los índices. El texto vacío o ``(raíz)`` es la raíz. Lanza
    :class:`PathError` con el tramo culpable si la sintaxis no es la de una ruta.
    """
    end = len(text) if end is None else end
    position = _skip_spaces(text, start, end)
    if text[position:end].rstrip().casefold() in _ROOT_TEXTS:
        return []
    steps: list[PathStep] = []
    while position < end:
        char = text[position]
        if char == "[":
            close = text.find("]", position + 1, end)
            if close < 0:
                raise PathError("Falta el «]» que cierra el índice", position, end)
            inside = text[position + 1:close].strip()
            if not inside:
                raise PathError("Falta el número entre los corchetes, como [0]", position, close + 1)
            if not _DIGITS.fullmatch(inside):
                raise PathError(
                    f"Entre corchetes va un número, como [0], y «{inside}» no lo es (los índices por nombre "
                    "no están disponibles)", position, close + 1,
                )
            if len(inside.lstrip("0")) > MAX_INDEX_DIGITS:
                raise PathError("Ese índice es demasiado grande para cualquier lista", position, close + 1)
            steps.append(PathStep(None, int(inside), position, close + 1))
            position = close + 1
        elif char == "]":
            raise PathError("Sobra un «]» sin su «[»", position, position + 1)
        elif char == "." or not steps:
            dot = position if char == "." else None
            name_start = position if dot is None else _skip_spaces(text, position + 1, end)
            name, name_end, position = _read_name(text, name_start, end)
            if not name:
                if dot is not None:
                    raise PathError("Falta un nombre de campo tras el «.»", dot, dot + 1)
                raise PathError(f"Una ruta empieza por un nombre de campo, no por «{char}»", name_start, name_start + 1)
            steps.append(PathStep(name, None, name_start, name_end))
        else:
            raise PathError(f"Se esperaba «.» o «[» antes de «{char}»", position, position + 1)
        position = _skip_spaces(text, position, end)
    return steps


def _describe(document: BodDocument, path: Path) -> str:
    return path_label(document, path) if path else "la raíz"


def _container_text(node: object) -> str:
    kind = type_text(node)
    return {"pares": "una lista de pares", "mapa": "un mapa", "tupla": "una tupla"}.get(kind, f"una {kind}")


def _quoted(names: list[str]) -> str:
    quoted = [f"«{name}»" for name in names]
    return quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + " o " + quoted[-1]


def _close_matches(name: str, candidates: list[str]) -> list[str]:
    """Hasta :data:`SUGGESTIONS` candidatos parecidos a ``name``, sin distinguir mayúsculas ni tildes."""
    folded: dict[str, str] = {}
    for candidate in candidates:
        folded.setdefault(fold(candidate), candidate)
    return [folded[key] for key in difflib.get_close_matches(fold(name), list(folded), n=SUGGESTIONS, cutoff=0.6)]


def _find_field(fields: list[Field], name: str, where: Callable[[], str]) -> tuple[int | None, str]:
    """(índice del campo o ``None``, mensaje).

    Sin campo, el mensaje explica por qué. Con campo, avisa si su nombre se repite.
    """
    found = [index for index, field in enumerate(fields) if field.name.text == name]
    labels = [field.name.text for field in fields] if not found or len(found) > 1 else []
    if not found:
        target = fold(name)
        found = [index for index, label in enumerate(labels) if fold(label) == target]
        variants = sorted({labels[index] for index in found})
        if len(variants) > 1:
            return None, f"«{name}» puede ser {_quoted(variants)} en {where()}: escríbelo con sus mayúsculas"
    if not found and (offset := _OFFSET.fullmatch(name)) is not None:
        value = int(offset.group(1), 16)
        starts = [
            (int(match.group(1), 16), index)
            for index, label in enumerate(labels)
            if (match := _OFFSET.fullmatch(label)) is not None
        ]
        found = [index for start, index in starts if start == value]
        if not found and starts:
            before = [labels[index] for start, index in starts if start < value]
            previous = f": la anterior es {before[-1]}" if before else ""
            return None, f"«{name}» no es el comienzo de ninguna instrucción de {where()}{previous}"
    if not found:
        similar = _close_matches(name, labels)
        hint = f". Parecidos: {', '.join(f'«{label}»' for label in similar)}" if similar else ""
        return None, f"«{name}» no es un campo de {where()}{hint}"
    if len(found) > 1:
        return found[0], f"Hay {len(found)} campos «{labels[found[0]]}» en {where()}: se eligió el primero"
    return found[0], ""


def find_path(document: BodDocument, steps: list[PathStep]) -> PathMatch:
    """Sigue ``steps`` (de :func:`parse_path_label`) desde la raíz de ``document``.

    Cada nombre se busca primero exacto y, si no hay ninguno, sin distinguir mayúsculas ni
    tildes, solo si todas las coincidencias son el mismo nombre. Un ``0x…`` sin coincidencia de
    texto se compara por valor (``0x4e`` es ``0x004E``). Un par tiene ``clave`` y ``valor``.
    """
    node: object = document.root
    path: Path = ()
    notes: list[str] = []
    for step in steps:
        where = functools.partial(_describe, document, path)
        index: int | None = None
        message = ""
        if isinstance(node, BodObject):
            if step.name is None:
                message = f"«{step.text}» no vale aquí: {where()} es un objeto y sus campos van por nombre"
            else:
                index, message = _find_field(node.fields, step.name, where)
        elif isinstance(node, (BodList, BodMap, BodTuple)):
            size = len(node.items)
            if step.index is None:
                message = f"«{step.text}» no vale aquí: {where()} es {_container_text(node)} y se esperaba un índice, como [0]"
            elif step.index < size:
                index = step.index
            elif size:
                message = f"«{step.text}» no existe: {where()} tiene {count(size, 'elemento')}, de [0] a [{size - 1}]"
            else:
                message = f"«{step.text}» no existe: {where()} no tiene elementos"
        elif isinstance(node, Pair):
            folded = fold(step.name) if step.name is not None else ""
            if folded in PAIR_LABELS:
                index = PAIR_LABELS.index(folded)
            else:
                message = f"«{step.text}» no vale aquí: {where()} es un par y solo tiene .clave y .valor"
        else:
            message = f"«{step.text}» no vale aquí: {where()} es un valor ({type_text(node)}) y no tiene hijos"
        if index is None:
            return PathMatch(path, step, message)
        if message:
            notes.append(message)
        path += (index,)
        node = child(node, index)[1]
    return PathMatch(path, None, " · ".join(notes))


def format_float(value: float) -> str:
    """El texto más corto que, empaquetado como float32, da el mismo valor.

    Se escribe en notación decimal (``200``, no ``2e+02``) salvo en magnitudes
    extremas, donde la científica es más legible.
    """
    if math.isnan(value) or math.isinf(value):
        return repr(value)
    packed = F32.pack(value)
    for precision in range(1, 10):
        text = f"{value:.{precision}g}"
        if F32.pack(float(text)) == packed:
            break
    else:
        text = repr(value)
    if "e" in text and -7 < int(text.rsplit("e", 1)[1]) < 16:
        text = format(Decimal(text), "f")
    return text


def value_text(value: object) -> str:
    """Valor de un nodo en una línea, para la columna «Valor»."""
    if isinstance(value, Int32):
        return str(value.value)
    if isinstance(value, Float32):
        return format_float(value.value)
    if isinstance(value, Bool):
        text = "true" if value.value else "false"
        return text if value.raw in (0, 1) else f"{text} (0x{value.raw:02X})"
    if isinstance(value, RawString):
        return repr(value.text)
    if isinstance(value, HashedString):
        return value.name.text
    if isinstance(value, ExternalRef):
        return f"→ {value.group}:{value.object_id:016X}"
    if isinstance(value, Null):
        return "null"
    if isinstance(value, BodObject):
        return value.cls.label()
    if isinstance(value, (BodList, BodMap, BodTuple)):
        return count(len(value.items), "elemento")
    if isinstance(value, Pair):
        return f"{value_text(value.key)} → {value_text(value.value)}"
    if isinstance(value, Note):
        return value.text
    return ""


def type_text(value: object) -> str:
    if isinstance(value, Pair):
        return "par"
    if isinstance(value, Value):
        return value.type_label
    return ""
