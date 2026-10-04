# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Un ``.obsp`` abierto: objetos, decodificación bajo demanda y caché.

Abrir solo lee cabecera, cadenas e índice. Cada objeto se decodifica la primera
vez que se pide y queda en caché. El archivo se lee entero y se cierra: abrirlo
no lo bloquea ni escribe nada.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .formats import bod, script
from .formats.obsp import STEAM_ORIGINAL_SHA256, IndexEntry, ObspFile, identity_text, kind_name


@dataclass(frozen=True)
class ObjectInfo:
    """Metadatos legibles de una entrada del índice."""

    position: int
    entry: IndexEntry
    path: str
    name: str
    folder: str
    class_name: str

    @property
    def identity(self) -> tuple[int, int]:
        return self.entry.identity

    @property
    def kind_label(self) -> str:
        return kind_name(self.entry.kind)

    @property
    def is_script(self) -> bool:
        return self.entry.is_script

    def label(self) -> str:
        return self.path or self.name or identity_text(self.entry.group, self.entry.object_id)


def _text(obsp: ObspFile, value_hash: int) -> str:
    text = obsp.text(value_hash)
    return text if text is not None else f"#{value_hash:016X}"


class Document:
    def __init__(self, obsp: ObspFile, path: Path | None = None) -> None:
        self.obsp = obsp
        self.path = path
        self.objects = [
            ObjectInfo(
                position,
                entry,
                _text(obsp, entry.path_hash),
                _text(obsp, entry.name_hash),
                _text(obsp, entry.folder_hash),
                _text(obsp, entry.class_hash),
            )
            for position, entry in enumerate(obsp.entries)
        ]
        self._by_identity = {info.identity: info for info in self.objects}
        self._bod_cache: dict[int, bod.BodDocument] = {}
        self._script_cache: dict[int, script.ScriptHeader] = {}

    @classmethod
    def open(cls, path: Path) -> "Document":
        # read_bytes abre, lee y cierra: el archivo no queda bloqueado.
        return cls(ObspFile.parse(path.read_bytes()), path)

    @classmethod
    def from_bytes(cls, data: bytes, path: Path | None = None) -> "Document":
        return cls(ObspFile.parse(data), path)

    @property
    def is_steam_original(self) -> bool:
        return self.obsp.sha256() == STEAM_ORIGINAL_SHA256

    def object_by_identity(self, identity: tuple[int, int]) -> ObjectInfo | None:
        return self._by_identity.get(identity)

    def find(self, query: str) -> list[ObjectInfo]:
        """Objetos cuya ruta o nombre coincide con ``query`` (sin distinguir mayúsculas).

        Primero se buscan coincidencias exactas; si no hay ninguna, las que lo contienen.
        """
        needle = query.strip().replace("\\", "/").casefold()
        exact = [info for info in self.objects if needle in (info.path.casefold(), info.name.casefold())]
        if exact:
            return exact
        return [info for info in self.objects if needle in info.path.casefold() or needle in info.name.casefold()]

    def original_blob(self, position: int) -> bytes:
        return self.obsp.blob(position)

    def bod(self, position: int) -> bod.BodDocument:
        """Árbol BOD del objeto, decodificado una sola vez."""
        cached = self._bod_cache.get(position)
        if cached is None:
            cached = bod.decode(self.obsp.blob(position))
            self._bod_cache[position] = cached
        return cached

    def script_header(self, position: int) -> script.ScriptHeader:
        cached = self._script_cache.get(position)
        if cached is None:
            cached = script.parse_header(self.obsp.blob(position))
            self._script_cache[position] = cached
        return cached
