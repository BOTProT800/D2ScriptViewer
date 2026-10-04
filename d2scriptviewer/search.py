# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Búsqueda global por ruta, nombre, carpeta, clase y valores.

Pensada para correr en un hilo: comprueba ``cancel`` entre objetos y entrega los
resultados por lotes con ``on_hits``. Para no decodificar los 4 172 BOD en cada
búsqueda, primero mira si el texto (o los 4 bytes del número) aparece en el
blob crudo; solo decodifica los candidatos. Los objetos ya decodificados (y
quizá editados) se buscan directamente en su árbol.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from typing import Callable

from .binary import F32, I32, TEXT_ENCODING
from .document import Document
from .errors import FormatError
from .formats import bod

DEFAULT_LIMIT = 2000


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
