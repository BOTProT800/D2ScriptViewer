# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Diferencias entre el árbol original de un objeto y el actual, en términos legibles.

No depende del historial de deshacer: compara los dos árboles. En las listas y
los mapas alinea los elementos por su huella (:func:`~.formats.bod.fingerprint`)
con la subsecuencia común más larga, así que distingue elementos añadidos,
eliminados, movidos y modificados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import edits
from .formats import bod
from .formats.obsp import identity_text

#: Por encima de este producto de longitudes, una lista cambiada se resume en una sola línea.
LCS_LIMIT = 250_000

RefLabel = Callable[[tuple[int, int]], str]


@dataclass(frozen=True)
class Change:
    kind: str
    """``valor``, ``reemplazado``, ``añadido``, ``eliminado``, ``movido`` o ``lista``."""
    path: tuple
    """Ruta en el árbol actual (para ``eliminado`` y ``lista``, la del contenedor)."""
    label: str
    before: str
    after: str
    original_state: object = None
    """Estado original de una hoja (solo en ``valor``): permite revertir esa propiedad."""


def describe(node: object, ref_label: RefLabel | None = None) -> str:
    if isinstance(node, bod.BodObject):
        return f"objeto {node.cls.label()}"
    if isinstance(node, bod.ExternalRef):
        target = ref_label(node.identity) if ref_label else identity_text(*node.identity)
        return f"→ {target}"
    if isinstance(node, bod.Pair):
        return f"{describe(node.key, ref_label)} → {describe(node.value, ref_label)}"
    if isinstance(node, (bod.BodList, bod.BodMap, bod.BodTuple)):
        return f"{bod.type_text(node)} de {bod.value_text(node)}"
    return bod.value_text(node)


_LEAVES = (bod.Int32, bod.Float32, bod.Bool, bod.RawString, bod.HashedString, bod.ExternalRef)


class _Differ:
    def __init__(self, current: bod.BodDocument, ref_label: RefLabel | None) -> None:
        self.current = current
        self.ref_label = ref_label
        self.changes: list[Change] = []
        #: Ruta actual → ruta original de cada lista o mapa comparado con su pareja.
        self.mapping: dict[tuple, tuple] = {}

    def label(self, path: tuple) -> str:
        return bod.path_label(self.current, path)

    def add(self, kind: str, path: tuple, before: str, after: str, label: str | None = None,
            original_state: object = None) -> None:
        self.changes.append(Change(kind, path, label or self.label(path), before, after, original_state))

    def replaced(self, old: object, new: object, path: tuple) -> None:
        self.add("reemplazado", path, describe(old, self.ref_label), describe(new, self.ref_label))

    def compare(self, old: object, new: object, path: tuple, old_path: tuple) -> None:
        if type(old) is not type(new):
            self.replaced(old, new, path)
            return
        if isinstance(old, _LEAVES):
            before, after = edits.get_state(old), edits.get_state(new)
            if before != after:
                self.add("valor", path, describe(old, self.ref_label), describe(new, self.ref_label),
                         original_state=before)
            return
        if isinstance(old, bod.BodObject):
            assert isinstance(new, bod.BodObject)
            if old.cls != new.cls or [f.name for f in old.fields] != [f.name for f in new.fields]:
                self.replaced(old, new, path)
                return
            for index, (before_field, after_field) in enumerate(zip(old.fields, new.fields)):
                self.compare(before_field.value, after_field.value, path + (index,), old_path + (index,))
            return
        if isinstance(old, bod.Pair):
            assert isinstance(new, bod.Pair)
            self.compare(old.key, new.key, path + (0,), old_path + (0,))
            self.compare(old.value, new.value, path + (1,), old_path + (1,))
            return
        if isinstance(old, bod.BodTuple):
            assert isinstance(new, bod.BodTuple)
            if len(old.items) != len(new.items):
                self.replaced(old, new, path)
                return
            for index, (before_item, after_item) in enumerate(zip(old.items, new.items)):
                self.compare(before_item, after_item, path + (index,), old_path + (index,))
            return
        if isinstance(old, (bod.BodList, bod.BodMap)):
            assert isinstance(new, (bod.BodList, bod.BodMap))
            if old.mode != new.mode:
                self.replaced(old, new, path)
                return
            self.mapping[path] = old_path
            self.sequence(old.items, new.items, path, old_path)

    def sequence(self, old_items: list, new_items: list, path: tuple, old_path: tuple) -> None:
        old_prints = [bod.fingerprint(item) for item in old_items]
        new_prints = [bod.fingerprint(item) for item in new_items]
        if old_prints == new_prints:
            return
        start = 0
        while start < len(old_prints) and start < len(new_prints) and old_prints[start] == new_prints[start]:
            start += 1
        old_end, new_end = len(old_prints), len(new_prints)
        while old_end > start and new_end > start and old_prints[old_end - 1] == new_prints[new_end - 1]:
            old_end -= 1
            new_end -= 1
        old_middle = list(range(start, old_end))
        new_middle = list(range(start, new_end))
        if len(old_middle) * len(new_middle) > LCS_LIMIT:
            self.add("lista", path, f"{len(old_items)} elementos", f"{len(new_items)} elementos")
            return
        matched_old, matched_new = _lcs(
            [old_prints[i] for i in old_middle], [new_prints[j] for j in new_middle]
        )
        free_old = [old_middle[i] for i in range(len(old_middle)) if i not in matched_old]
        free_new = [new_middle[j] for j in range(len(new_middle)) if j not in matched_new]
        # Mismo contenido en otra posición: se movió.
        waiting: dict[bytes, list[int]] = {}
        for index in free_old:
            waiting.setdefault(old_prints[index], []).append(index)
        still_new = []
        for index in free_new:
            queue = waiting.get(new_prints[index])
            if queue:
                source = queue.pop(0)
                free_old.remove(source)
                self.add("movido", path + (index,), f"posición [{source}]", f"posición [{index}]")
            else:
                still_new.append(index)
        # Lo que queda se empareja en orden si es del mismo tipo: elemento modificado.
        remaining_old = list(free_old)
        for index in list(still_new):
            if not remaining_old:
                break
            source = remaining_old[0]
            if _same_shape(old_items[source], new_items[index]):
                remaining_old.pop(0)
                still_new.remove(index)
                self.compare(old_items[source], new_items[index], path + (index,), old_path + (source,))
        for index in still_new:
            self.add("añadido", path + (index,), "—", describe(new_items[index], self.ref_label))
        container = self.label(path)
        for index in remaining_old:
            self.add("eliminado", path, describe(old_items[index], self.ref_label), "—",
                     label=f"{container}[{index}] (posición original)")


def _same_shape(old: object, new: object) -> bool:
    if type(old) is not type(new):
        return False
    if isinstance(old, bod.BodObject):
        return old.cls == new.cls  # type: ignore[attr-defined]
    return True


def _lcs(old: list[bytes], new: list[bytes]) -> tuple[set[int], set[int]]:
    """Índices emparejados por la subsecuencia común más larga."""
    rows, columns = len(old), len(new)
    lengths = [[0] * (columns + 1) for _ in range(rows + 1)]
    for i in range(rows - 1, -1, -1):
        row, below = lengths[i], lengths[i + 1]
        for j in range(columns - 1, -1, -1):
            row[j] = below[j + 1] + 1 if old[i] == new[j] else max(below[j], row[j + 1])
    matched_old: set[int] = set()
    matched_new: set[int] = set()
    i = j = 0
    while i < rows and j < columns:
        if old[i] == new[j]:
            matched_old.add(i)
            matched_new.add(j)
            i += 1
            j += 1
        elif lengths[i + 1][j] >= lengths[i][j + 1]:
            i += 1
        else:
            j += 1
    return matched_old, matched_new


def diff_trees(original: bod.BodDocument, current: bod.BodDocument, ref_label: RefLabel | None = None) -> list[Change]:
    return diff_with_mapping(original, current, ref_label)[0]


def diff_with_mapping(
    original: bod.BodDocument, current: bod.BodDocument, ref_label: RefLabel | None = None
) -> tuple[list[Change], dict[tuple, tuple]]:
    """Los cambios y el alineamiento: ruta actual → ruta original de cada lista o mapa comparado.

    Las listas idénticas a la original no aparecen en el alineamiento (no hace falta
    compararlas); las que están dentro de un elemento añadido tampoco (no tienen pareja).
    """
    differ = _Differ(current, ref_label)
    differ.compare(original.root, current.root, (), ())
    return differ.changes, differ.mapping


def changed_paths(changes: list[Change]) -> set[tuple]:
    """Rutas del árbol actual que conviene resaltar (y sus contenedores en los eliminados)."""
    return {change.path for change in changes}
