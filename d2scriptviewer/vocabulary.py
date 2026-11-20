# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""El vocabulario de la herramienta en el idioma de la interfaz (fase 12).

El núcleo nombra en español canónico lo que no es del juego: las etiquetas de las
rutas (``clave``, ``valor``, los campos fijos de los scripts), los tipos y los
mnemónicos. Esos nombres forman parte de lo que se guarda, se exporta o se escribe en
un parche, y de las huellas que comparan subárboles, así que nunca cambian. La
interfaz los muestra traducidos con estas funciones, que comparten el panel de
propiedades, la búsqueda en el objeto, «Copiar ruta» y Ctrl+G.

Los nombres del juego (objetos, campos, clases y cadenas) nunca se traducen. Solo son
vocabulario los hijos de un par y, en el árbol de presentación de un script, los
campos de la raíz y ``Parámetros``: ahí los nombres son fijos y ninguno coincide con
uno del juego.
"""

from __future__ import annotations

import functools
from typing import Callable

from . import i18n
from .formats import bod, script
from .formats.obsp import kind_name
from .i18n import N_, _, ngettext, term

#: Contextos de :func:`.i18n.pgettext` del vocabulario.
PATH = "ruta"
TYPE = "tipo"
KIND = "categoría"

#: El tipo de una fila de tramo (``[1000…1499]``) en el panel de propiedades.
CHUNK = N_("tramo", "tipo")

RefLabel = Callable[[tuple[int, int]], str]


def shown_term(label: str, context: str) -> str:
    """Un término canónico (o un :class:`.i18n.Deferred`) en el idioma activo."""
    if isinstance(label, i18n.Deferred):
        return label.shown()
    return term(label, context)


# --- Filas del panel ------------------------------------------------------------------------


def is_term(document: bod.BodDocument, parent_path: bod.Path, parent: object, label: str) -> bool:
    """Si la etiqueta del hijo ``label`` de ``parent`` es vocabulario de la herramienta."""
    if isinstance(parent, bod.Pair):
        return True
    if isinstance(document, script.ScriptTree):
        return label == script.PARAMETERS or (not parent_path and label in script.ROOT_FIELDS)
    return False


def row_label(document: bod.BodDocument, parent_path: bod.Path, parent: object, label: str) -> str:
    """La columna Nombre: la etiqueta del hijo ``label`` de ``parent`` (en ``parent_path``)."""
    return term(label, PATH) if is_term(document, parent_path, parent, label) else label


def type_text(node: object) -> str:
    """La columna Tipo."""
    label = bod.type_text(node)
    return shown_term(label, TYPE) if label else label


def canonical_type(shown: str) -> str:
    """El tipo canónico (o «(cualquiera)») que se ve como ``shown``: la búsqueda sobrevive al cambio de idioma."""
    found = i18n.canonical(shown, TYPE)
    return found if found != shown else i18n.canonical(shown)


def shown_type(canonical: str) -> str:
    """La inversa de :func:`canonical_type`."""
    found = term(canonical, TYPE)
    return found if found != canonical else term(canonical)


def class_text(cls: bod.ClassRef) -> str:
    """La clase como ``str`` canónico (``cls.label()``) que se muestra traducido (índices en un hilo)."""
    if cls.is_script:
        return i18n.Deferred("{name} (script, grupo {group})", name=cls.name.text, group=cls.group)
    return cls.name.text


def class_label(cls: bod.ClassRef) -> str:
    if cls.is_script:
        return _("{name} (script, grupo {group})").format(name=cls.name.text, group=cls.group)
    return i18n.text(cls.name.text)


def value_text(node: object, ref_label: RefLabel | None = None) -> str:
    """La columna Valor; en una referencia, ``→`` y el destino."""
    if ref_label is not None and isinstance(node, bod.ExternalRef):
        return f"→ {ref_label(node.identity)}"
    if isinstance(node, (bod.BodList, bod.BodMap, bod.BodTuple)):
        size = len(node.items)
        return ngettext("{count:,} elemento", "{count:,} elementos", size).format(count=size)
    if isinstance(node, bod.BodObject):
        return class_label(node.cls)
    if isinstance(node, bod.Pair):
        return f"{value_text(node.key)} → {value_text(node.value)}"
    if isinstance(node, bod.Note):
        return i18n.text(node.text)
    return bod.value_text(node)


def kind_label(kind: int) -> str:
    """La categoría de un objeto del índice (``Instancia``, ``Desc``…)."""
    return shown_term(kind_name(kind), KIND)


# --- Rutas ----------------------------------------------------------------------------------


class PathText(str):
    """Una ruta canónica (la de los parches) que se muestra con el vocabulario del idioma activo.

    Es un ``str`` con la etiqueta de siempre (:func:`.formats.bod.path_label`), así que
    sirve donde antes. ``pieces`` dice qué tramos son vocabulario; con eso :meth:`shown`
    la traduce aunque el árbol haya cambiado después (las descripciones de deshacer).
    """

    def __new__(cls, pieces: tuple[tuple[str, bool], ...]) -> "PathText":
        self = super().__new__(cls, "".join(piece for piece, _vocabulary in pieces))
        self.pieces = pieces
        return self

    def shown(self) -> str:
        return "".join(term(piece, PATH) if is_vocabulary else piece for piece, is_vocabulary in self.pieces)


def path_text(document: bod.BodDocument, path: bod.Path, prefix: str = "") -> PathText:
    """La ruta de ``path`` como :class:`PathText`, con ``prefix`` delante (el objeto y « · »)."""
    pieces: list[tuple[str, bool]] = [(prefix, False)] if prefix else []
    node: object = document.root
    first = True
    for depth, step in enumerate(path):
        label, child = bod.child(node, step)
        translated = is_term(document, path[:depth], node, label)
        if not label.startswith("[") and not first:
            pieces.append((".", False))
        pieces.append((label, translated))
        first = False
        node = child
    if first:
        pieces.append((bod.ROOT_LABEL, True))
    return PathText(tuple(pieces))


def path_label(document: bod.BodDocument, path: bod.Path) -> str:
    """La ruta que se ve en la interfaz y que copia «Copiar ruta de la propiedad»."""
    return path_text(document, path).shown()


class ShownNames(bod.PathNames):
    """Ctrl+G con el vocabulario de la interfaz: los mensajes en su idioma, y los dos idiomas valen."""

    def describe(self, document: bod.BodDocument, path: bod.Path) -> str:
        return path_label(document, path) if path else _("la raíz")

    def field(self, document: bod.BodDocument, parent_path: bod.Path, parent: object, label: str) -> str:
        return row_label(document, parent_path, parent, label)

    def type(self, node: object) -> str:
        return type_text(node)

    def alias(self, document: bod.BodDocument, parent_path: bod.Path, parent: object, name: str) -> str | None:
        """La etiqueta canónica que ``name`` nombra en algún idioma (``Functions`` → ``Funciones``)."""
        if isinstance(parent, bod.Pair):
            candidates: tuple[str, ...] = bod.PAIR_LABELS
        elif isinstance(document, script.ScriptTree):
            candidates = script.ROOT_FIELDS if not parent_path else (script.PARAMETERS,)
        else:
            return None
        return _aliases(candidates).get(bod.fold(name))


@functools.lru_cache(maxsize=None)
def _aliases(candidates: tuple[str, ...]) -> dict[str, str]:
    """Cada forma de los términos ``candidates`` en cualquier idioma, sin mayúsculas ni tildes → la canónica."""
    table: dict[str, str] = {}
    for canonical in candidates:
        for variant in i18n.variants(canonical, PATH):
            table.setdefault(bod.fold(variant), canonical)
    return table


NAMES = ShownNames()
