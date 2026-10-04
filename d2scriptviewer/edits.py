# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Ediciones de valores: validación del texto del usuario y comandos reversibles.

Una edición cambia el *estado* de una hoja del árbol BOD sin cambiar su tipo:

========== ============================== ==============================
Tag        Nodo                           Estado
========== ============================== ==============================
``02``     :class:`~.bod.Int32`           4 bytes crudos
``03``     :class:`~.bod.Float32`         4 bytes crudos
``04``     :class:`~.bod.Bool`            byte crudo
``05``     :class:`~.bod.RawString`       texto ASCII
``0F``     :class:`~.bod.HashedString`    :class:`~.bod.Name` ya conocido
``FC``     :class:`~.bod.ExternalRef`     identidad (grupo, idObjeto)
========== ============================== ==============================

Las cadenas con hash solo admiten textos que ya aparecen en el archivo: la
función de hash es desconocida (fase 6). Cambiar el tipo de un valor, poner
nulos o tocar contenedores es la fase 5.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable

from .binary import F32, I32, U32
from .errors import EditError
from .formats import bod
from .formats.bod import Name
from .formats.hashes import HashDictionary
from .formats.obsp import identity_text

EDITABLE_TYPES = (bod.Int32, bod.Float32, bod.Bool, bod.RawString, bod.HashedString, bod.ExternalRef)
INT32_MIN = -(2 ** 31)
INT32_MAX = 2 ** 31 - 1
FLOAT32_MAX = 3.4028234663852886e38
MAX_STRING_LENGTH = bod.MAX_TEXT_LENGTH
#: A partir de aquí un entero tiene más pinta de hash o de identificador que de cantidad.
HASH_LIKE_THRESHOLD = 1_000_000

State = object


def is_editable(node: object) -> bool:
    return isinstance(node, EDITABLE_TYPES)


def get_state(node: object) -> State:
    if isinstance(node, (bod.Int32, bod.Float32, bod.Bool)):
        return node.raw
    if isinstance(node, bod.RawString):
        return node.text
    if isinstance(node, bod.HashedString):
        return node.name
    if isinstance(node, bod.ExternalRef):
        return node.identity
    raise EditError(f"Los valores de tipo {bod.type_text(node)} no se pueden editar todavía")


def set_state(node: object, state: State) -> None:
    if isinstance(node, (bod.Int32, bod.Float32)):
        assert isinstance(state, bytes) and len(state) == 4
        node.raw = state
    elif isinstance(node, bod.Bool):
        assert isinstance(state, int) and 0 <= state <= 0xFF
        node.raw = state
    elif isinstance(node, bod.RawString):
        assert isinstance(state, str)
        node.text = state
    elif isinstance(node, bod.HashedString):
        assert isinstance(state, Name)
        node.name = state
    elif isinstance(node, bod.ExternalRef):
        group, object_id = state  # type: ignore[misc]
        node.group = group
        node.object_id = object_id
    else:
        raise EditError(f"Los valores de tipo {bod.type_text(node)} no se pueden editar todavía")


def state_text(node: object, state: State, ref_label: Callable[[tuple[int, int]], str] | None = None) -> str:
    """El estado como lo vería el usuario en la columna «Valor»."""
    if isinstance(node, bod.ExternalRef):
        identity = state  # type: ignore[assignment]
        return ref_label(identity) if ref_label else identity_text(*identity)  # type: ignore[misc]
    probe = type(node).__new__(type(node))
    set_state(probe, state)
    return bod.value_text(probe)


# --- Validación del texto del usuario ---------------------------------------------------------


def parse_int32(text: str) -> bytes:
    """Entero con signo de 32 bits. ``0x…`` se lee como patrón de bits (0 … 0xFFFFFFFF)."""
    value = text.strip().replace("_", "")
    if not value:
        raise EditError("Escribe un número entero")
    if re.fullmatch(r"[+-]?0[xX][0-9a-fA-F]+", value):
        negative = value.startswith("-")
        number = int(value.lstrip("+-"), 16)
        if negative:
            number = -number
            if number < INT32_MIN:
                raise EditError(f"{text.strip()} no cabe en un int32")
            return I32.pack(number)
        if number > 0xFFFFFFFF:
            raise EditError(f"{text.strip()} ocupa más de 32 bits")
        return U32.pack(number)
    if not re.fullmatch(r"[+-]?\d+", value):
        raise EditError(f"«{text.strip()}» no es un número entero (usa dígitos o 0x seguido de hexadecimal)")
    number = int(value)
    if not INT32_MIN <= number <= INT32_MAX:
        raise EditError(f"{number} está fuera del rango de int32 ({INT32_MIN} … {INT32_MAX})")
    return I32.pack(number)


def parse_float32(text: str) -> bytes:
    """Número decimal; admite coma decimal. Rechaza NaN, infinitos y desbordamientos."""
    value = text.strip().replace("_", "")
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    if not value:
        raise EditError("Escribe un número")
    if re.search(r"(nan|inf)", value, re.IGNORECASE):
        raise EditError("No se admiten NaN ni infinitos")
    try:
        number = float(value)
    except ValueError:
        raise EditError(f"«{text.strip()}» no es un número") from None
    if math.isnan(number) or math.isinf(number) or abs(number) > FLOAT32_MAX:
        raise EditError(f"{text.strip()} no cabe en un float32 (máximo ±{FLOAT32_MAX:.7g})")
    return F32.pack(number)


TRUE_WORDS = {"true", "1", "sí", "si", "verdadero", "yes", "on"}
FALSE_WORDS = {"false", "0", "no", "falso", "off"}


def parse_bool(text: str) -> int:
    value = text.strip().casefold()
    if value in TRUE_WORDS:
        return 1
    if value in FALSE_WORDS:
        return 0
    raise EditError("Escribe true o false")


def parse_raw_string(text: str) -> str:
    if not text.isascii():
        raise EditError("Solo se admiten caracteres ASCII")
    if "\x00" in text:
        raise EditError("La cadena no puede contener el carácter nulo")
    if len(text) > MAX_STRING_LENGTH:
        raise EditError(f"La cadena supera los {MAX_STRING_LENGTH:,} caracteres")
    return text


def parse_known_name(text: str, dictionary: HashDictionary | None) -> Name:
    if dictionary is None:
        raise EditError("Aún se está construyendo el diccionario de cadenas; espera unos segundos")
    name = dictionary.name_for(text)
    if name is None:
        close = [known for known in suggestions(dictionary, text, limit=1)]
        hint = f" ¿Querías decir «{close[0]}»?" if close else ""
        raise EditError(
            f"«{text}» no aparece en el archivo, así que no se conoce su hash (distingue mayúsculas).{hint}"
        )
    return name


def parse_state(node: object, text: str, dictionary: HashDictionary | None = None) -> State:
    """Convierte el texto del usuario en el nuevo estado de ``node``; lanza :class:`EditError`."""
    if isinstance(node, bod.Int32):
        return parse_int32(text)
    if isinstance(node, bod.Float32):
        return parse_float32(text)
    if isinstance(node, bod.Bool):
        return parse_bool(text)
    if isinstance(node, bod.RawString):
        return parse_raw_string(text)
    if isinstance(node, bod.HashedString):
        return parse_known_name(text, dictionary)
    raise EditError(f"Los valores de tipo {bod.type_text(node)} no se editan escribiendo")


def editable_text(node: object) -> str:
    """Texto inicial del editor: el valor sin comillas ni adornos."""
    if isinstance(node, bod.RawString):
        return node.text
    if isinstance(node, bod.HashedString):
        return node.name.text
    if isinstance(node, bod.Bool):
        return "true" if node.value else "false"
    return bod.value_text(node)


def input_hint(node: object, text: str, dictionary: HashDictionary | None = None) -> tuple[bool, str]:
    """(válido, mensaje) para mostrar mientras se escribe."""
    try:
        state = parse_state(node, text, dictionary)
    except EditError as error:
        return False, str(error)
    if isinstance(node, bod.Int32):
        value = I32.unpack(state)[0]  # type: ignore[arg-type]
        return True, f"int32 {value} · hex 0x{U32.unpack(state)[0]:08X}"  # type: ignore[arg-type]
    if isinstance(node, bod.Float32):
        stored = F32.unpack(state)[0]  # type: ignore[arg-type]
        shown = bod.format_float(stored)
        exact = f"{stored:.9g}"
        note = "" if shown == exact else f" (exacto {exact})"
        return True, f"Se guardará como float32 {shown}{note} · hex {state.hex(' ')}"  # type: ignore[union-attr]
    if isinstance(node, bod.RawString):
        return True, f"{len(state):,} caracteres ASCII (antes {len(node.text):,})"  # type: ignore[arg-type]
    if isinstance(node, bod.HashedString):
        return True, f"Cadena conocida · hash {state.hash:016X}"  # type: ignore[union-attr]
    return True, ""


def suggestions(dictionary: HashDictionary, text: str, limit: int = 60) -> list[str]:
    """Cadenas conocidas que empiezan por ``text`` y, después, las que lo contienen."""
    needle = text.casefold()
    texts = dictionary.texts()
    if not needle:
        return texts[:limit]
    prefix = [value for value in texts if value.casefold().startswith(needle)]
    if len(prefix) >= limit:
        return prefix[:limit]
    contained = [value for value in texts if needle in value.casefold() and not value.casefold().startswith(needle)]
    return (prefix + contained)[:limit]


def identifier_warning(field: str, node: object) -> str | None:
    """Aviso si la propiedad parece un identificador o un hash (cambiarla puede romper enlaces)."""
    reasons = []
    if field == "ID" or field.endswith("ID") or field.endswith("Id") or "Hash" in field:
        reasons.append(f"el campo se llama «{field}»")
    if isinstance(node, bod.Int32) and abs(node.value) >= HASH_LIKE_THRESHOLD:
        reasons.append(f"el valor actual ({node.value}, 0x{U32.unpack(node.raw)[0]:08X}) parece un hash")
    if not reasons:
        return None
    return (
        "Esta propiedad parece un identificador: " + " y ".join(reasons)
        + ". Cambiarla puede romper enlaces que el juego resuelve por ese valor."
    )


def field_name(document: bod.BodDocument, path: tuple) -> str:
    """Nombre del campo más cercano a ``path`` (para los avisos), p. ej. ``ItemID`` en ``Items[3].ItemID``."""
    label = bod.path_label(document, path)
    for part in reversed(re.split(r"[.\[]", label)):
        if part and not part[0].isdigit() and not part.endswith("]") and part not in ("clave", "valor"):
            return part
    return label


# --- Comandos ---------------------------------------------------------------------------------
#
# Cada operación se aplica o se deshace sobre el árbol de su objeto. Las rutas son
# coherentes porque deshacer y rehacer siguen un orden estricto (LIFO): cuando una
# operación se deshace, el árbol está exactamente como quedó al aplicarla.
# ``focus`` es la ruta que conviene seleccionar después (``None``: ninguna).


@dataclass(frozen=True)
class ValueEdit:
    position: int
    path: tuple
    before: State
    after: State

    def apply(self, tree: bod.BodDocument) -> None:
        set_state(bod.resolve(tree, self.path), self.after)

    def revert(self, tree: bod.BodDocument) -> None:
        set_state(bod.resolve(tree, self.path), self.before)

    def focus(self, forward: bool) -> tuple | None:
        return self.path


def _items_of(tree: bod.BodDocument, container_path: tuple) -> list:
    container = bod.resolve(tree, container_path)
    if not isinstance(container, (bod.BodList, bod.BodMap)):
        raise EditError("Solo las listas y los mapas admiten añadir, quitar o mover elementos")
    return container.items


@dataclass(frozen=True)
class InsertItem:
    """Inserta ``item`` (un valor o, en listas de pares y mapas, un par) en ``index``."""

    position: int
    container_path: tuple
    index: int
    item: object

    def apply(self, tree: bod.BodDocument) -> None:
        _items_of(tree, self.container_path).insert(self.index, self.item)

    def revert(self, tree: bod.BodDocument) -> None:
        items = _items_of(tree, self.container_path)
        assert items[self.index] is self.item
        del items[self.index]

    def focus(self, forward: bool) -> tuple | None:
        return self.container_path + (self.index,) if forward else self.container_path


@dataclass(frozen=True)
class RemoveItem:
    position: int
    container_path: tuple
    index: int
    item: object

    def apply(self, tree: bod.BodDocument) -> None:
        items = _items_of(tree, self.container_path)
        assert items[self.index] is self.item
        del items[self.index]

    def revert(self, tree: bod.BodDocument) -> None:
        _items_of(tree, self.container_path).insert(self.index, self.item)

    def focus(self, forward: bool) -> tuple | None:
        return self.container_path if forward else self.container_path + (self.index,)


@dataclass(frozen=True)
class MoveItem:
    position: int
    container_path: tuple
    source: int
    target: int

    def apply(self, tree: bod.BodDocument) -> None:
        items = _items_of(tree, self.container_path)
        items.insert(self.target, items.pop(self.source))

    def revert(self, tree: bod.BodDocument) -> None:
        items = _items_of(tree, self.container_path)
        items.insert(self.source, items.pop(self.target))

    def focus(self, forward: bool) -> tuple | None:
        return self.container_path + ((self.target if forward else self.source),)


@dataclass(frozen=True)
class ReplaceValue:
    """Sustituye el valor de un hueco por otro de distinto tipo (objeto o referencia ↔ nulo)."""

    position: int
    path: tuple
    before: object
    after: object

    def _set(self, tree: bod.BodDocument, value: object) -> None:
        bod.set_slot(bod.resolve(tree, self.path[:-1]), self.path[-1], value)

    def apply(self, tree: bod.BodDocument) -> None:
        self._set(tree, self.after)

    def revert(self, tree: bod.BodDocument) -> None:
        self._set(tree, self.before)

    def focus(self, forward: bool) -> tuple | None:
        return self.path


@dataclass(frozen=True)
class ReplaceTree:
    """Cambia el árbol entero de un objeto (revertir). La aplica el documento, no el árbol."""

    position: int
    before: bod.BodDocument
    after: bod.BodDocument

    def focus(self, forward: bool) -> tuple | None:
        return None


@dataclass(frozen=True)
class EditGroup:
    """Lo que se deshace o rehace de una vez."""

    edits: tuple
    description: str

    @property
    def positions(self) -> list[int]:
        return sorted({edit.position for edit in self.edits})

    @property
    def structural(self) -> bool:
        return any(not isinstance(edit, ValueEdit) for edit in self.edits)


# --- Reglas de la edición estructural (decisiones de la fase 5) ------------------------------


def structural_parent(tree: bod.BodDocument, path: tuple) -> tuple[object, object] | None:
    """(contenedor, nodo) si ``path`` es un elemento de una lista o una entrada de un mapa."""
    if not path:
        return None
    container = bod.resolve(tree, path[:-1])
    if isinstance(container, (bod.BodList, bod.BodMap)):
        return container, bod.get_slot(container, path[-1])
    return None


def can_null(tree: bod.BodDocument, path: tuple) -> bool:
    """Solo un objeto ``07`` o una referencia ``FC`` pueden pasar a nulo, y nunca en una tupla ni la clave de un par."""
    if not path:
        return False
    node = bod.resolve(tree, path)
    if not isinstance(node, (bod.BodObject, bod.ExternalRef)):
        return False
    parent = bod.resolve(tree, path[:-1])
    if isinstance(parent, bod.BodTuple):
        return False
    return not (isinstance(parent, bod.Pair) and path[-1] == 0)
