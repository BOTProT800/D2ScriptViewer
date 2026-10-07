# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Búsqueda global por ruta, nombre, carpeta, clase y valores, y búsqueda dentro de un objeto.

La global (:func:`search`) está pensada para correr en un hilo: comprueba
``cancel`` entre objetos y entrega los resultados por lotes con ``on_hits``. Para
no decodificar los 4 172 BOD en cada búsqueda, primero mira si el texto (o los 4
bytes del número) aparece en el blob crudo; solo decodifica los candidatos. Los
objetos ya decodificados (y quizá editados) se buscan directamente en su árbol.

La de dentro del objeto (:func:`find_in_tree`, fase 10) compara las columnas
Nombre, Tipo y Valor de las filas del panel de propiedades tal como se ven. El
objeto mayor se recorre en unas decenas de milisegundos, así que corre en el
hilo de la interfaz, sin índices.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from typing import Callable, Iterator

from .binary import F32, I32, TEXT_ENCODING
from .document import Document
from .errors import FormatError
from .formats import bod

DEFAULT_LIMIT = 2000
#: Valor del campo Tipo que no filtra (la primera opción del desplegable).
ANY_TYPE = "(cualquiera)"

RefLabel = Callable[[tuple[int, int]], str]


@dataclass(frozen=True)
class SearchHit:
    position: int
    path: tuple | None
    """Ruta de la propiedad; ``None`` si coincide un metadato del índice."""
    where: str
    text: str
    label: str = ""
    """Ruta legible de la propiedad (vacía en los metadatos)."""


@dataclass(frozen=True)
class SearchOptions:
    metadata: bool = True
    values: bool = True
    field_names: bool = False
    limit: int = DEFAULT_LIMIT


@dataclass(frozen=True)
class _Query:
    needle: str
    needle_bytes: bytes | None
    integer: int | None
    float_raw: bytes | None

    @classmethod
    def parse(cls, text: str) -> "_Query":
        needle = text.strip().casefold()
        try:
            needle_bytes: bytes | None = needle.encode(TEXT_ENCODING)
        except UnicodeEncodeError:
            needle_bytes = None
        integer = None
        float_raw = None
        try:
            integer = int(text.strip(), 0)
            if not -(2 ** 31) <= integer < 2 ** 31:
                integer = None
        except ValueError:
            pass
        try:
            number = float(text.strip())
            if not math.isnan(number) and abs(number) < 3.4e38:
                float_raw = F32.pack(number)
        except ValueError:
            pass
        return cls(needle, needle_bytes, integer, float_raw)

    def blob_may_match(self, lowered_blob: bytes, blob: bytes) -> bool:
        if self.needle_bytes and self.needle_bytes in lowered_blob:
            return True
        if self.integer is not None and I32.pack(self.integer) in blob:
            return True
        return self.float_raw is not None and self.float_raw in blob


def _match_value(query: _Query, node: object) -> str | None:
    kind = type(node)
    if kind is bod.RawString:
        if query.needle in node.text.casefold():  # type: ignore[attr-defined]
            return bod.value_text(node)
    elif kind is bod.HashedString:
        if query.needle in node.name.text.casefold():  # type: ignore[attr-defined]
            return node.name.text  # type: ignore[attr-defined]
    elif kind is bod.Int32:
        if query.integer is not None and node.value == query.integer:  # type: ignore[attr-defined]
            return bod.value_text(node)
    elif kind is bod.Float32:
        if query.float_raw is not None and node.raw == query.float_raw:  # type: ignore[attr-defined]
            return bod.value_text(node)
    elif kind is bod.BodObject and node.index is not None:  # type: ignore[attr-defined]
        # La clase de la raíz ya la cubre el metadato «clase» del índice.
        if query.needle in node.cls.name.text.casefold():  # type: ignore[attr-defined]
            return node.cls.label()  # type: ignore[attr-defined]
    return None


def search(
    document: Document,
    text: str,
    options: SearchOptions = SearchOptions(),
    *,
    cancel: threading.Event | None = None,
    on_hits: Callable[[list[SearchHit]], None] | None = None,
) -> tuple[list[SearchHit], bool]:
    """Devuelve (resultados, truncado). ``truncado`` indica que se alcanzó el límite."""
    query = _Query.parse(text)
    hits: list[SearchHit] = []
    if not query.needle:
        return hits, False
    batch: list[SearchHit] = []

    def emit(hit: SearchHit) -> bool:
        hits.append(hit)
        batch.append(hit)
        return len(hits) >= options.limit

    def flush() -> None:
        if on_hits is not None and batch:
            on_hits(list(batch))
        batch.clear()

    for info in document.objects:
        if cancel is not None and cancel.is_set():
            break
        if options.metadata:
            for where, value in (("ruta", info.path), ("nombre", info.name), ("carpeta", info.folder),
                                 ("clase", info.class_name)):
                if query.needle in value.casefold():
                    if emit(SearchHit(info.position, None, where, value)):
                        flush()
                        return hits, True
                    break
        if not options.values:
            continue
        if info.is_script:
            # Los scripts no tienen valores editables, pero sus símbolos son nombres.
            blob = document.original_blob(info.position)
            if query.needle_bytes and query.needle_bytes in blob.lower():
                try:
                    header = document.script_header(info.position)
                except FormatError:
                    continue
                for symbol in header.symbols:
                    if query.needle in symbol.text.casefold():
                        if emit(SearchHit(info.position, None, "símbolo", symbol.text)):
                            flush()
                            return hits, True
            continue
        tree = document.cached_bod(info.position)
        if tree is None:
            blob = document.original_blob(info.position)
            if not query.blob_may_match(blob.lower(), blob):
                continue
            try:
                tree = bod.decode(blob)
            except FormatError:
                continue
        for path, node in bod.walk(tree.root):
            matched = _match_value(query, node)
            if matched is not None:
                hit = SearchHit(info.position, path, "valor", matched, bod.path_label(tree, path))
                if emit(hit):
                    flush()
                    return hits, True
            if options.field_names and isinstance(node, bod.BodObject):
                for index, field in enumerate(node.fields):
                    if query.needle in field.name.text.casefold():
                        field_path = path + (index,)
                        hit = SearchHit(info.position, field_path, "campo", field.name.text,
                                        bod.path_label(tree, field_path))
                        if emit(hit):
                            flush()
                            return hits, True
        if len(batch) >= 100:
            flush()
    flush()
    return hits, False


# --- Búsqueda dentro del objeto (fase 10) ------------------------------------------------------


def row_value_text(node: object, ref_label: RefLabel | None = None) -> str:
    """Texto de la columna «Valor» del panel de propiedades; en una referencia, ``→`` y el destino."""
    if ref_label is not None and isinstance(node, bod.ExternalRef):
        return f"→ {ref_label(node.identity)}"
    return bod.value_text(node)


def _rows(root: object) -> Iterator[tuple[bod.Path, str, object]]:
    """(ruta, etiqueta, nodo) de cada fila, en el orden del árbol y sin la raíz (que no es una fila)."""
    stack: list[tuple[bod.Path, str, object]] = []

    def push(path: bod.Path, node: object) -> None:
        kids = bod.children(node)
        for index in range(len(kids) - 1, -1, -1):
            label, child = kids[index]
            stack.append((path + (index,), label, child))

    push((), root)
    while stack:
        path, label, node = stack.pop()
        yield path, label, node
        push(path, node)


def tree_types(document: bod.BodDocument) -> list[str]:
    """Los tipos de las filas del objeto (columna «Tipo»), sin repetir y en orden alfabético."""
    return sorted({bod.type_text(node) for _path, _label, node in _rows(document.root)} - {""}, key=str.casefold)


def is_empty_query(name: str, type_name: str, value: str) -> bool:
    """Con los tres campos vacíos (o Tipo en «(cualquiera)») no hay búsqueda."""
    kind = type_name.strip().casefold()
    return not name.strip() and not value.strip() and kind in ("", ANY_TYPE.casefold())


def find_in_tree(
    document: bod.BodDocument,
    name: str = "",
    type_name: str = "",
    value: str = "",
    ref_label: RefLabel | None = None,
) -> list[bod.Path]:
    """Rutas de las filas que cumplen todos los campos no vacíos, en el orden de las filas.

    Nombre y Valor buscan el texto contenido; Tipo, el tipo exacto. Ninguno
    distingue mayúsculas. El orden de las filas es el lexicográfico de sus rutas,
    así que el resultado sirve para buscar el siguiente con :mod:`bisect`.
    """
    if is_empty_query(name, type_name, value):
        return []
    name_needle = name.strip().casefold()
    kind = type_name.strip().casefold()
    if kind == ANY_TYPE.casefold():
        kind = ""
    value_needle = value.strip().casefold()
    found = []
    for path, label, node in _rows(document.root):
        if name_needle and name_needle not in label.casefold():
            continue
        if kind and bod.type_text(node).casefold() != kind:
            continue
        if value_needle and value_needle not in row_value_text(node, ref_label).casefold():
            continue
        found.append(path)
    return found
