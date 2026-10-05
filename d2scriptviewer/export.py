# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Exportación a JSON y CSV (fase 8): solo lectura del documento, nunca se reimporta.

Cada objeto se escribe en ``<carpeta>/<ruta>.json`` con su árbol tipado y las
referencias resueltas; los scripts, con sus miembros y su código desensamblado. Un
``manifest.json`` recoge la huella del archivo y el índice. Cada ``FloatTable`` se
escribe además como ``<ruta>.csv`` (nombres de fila y de columna, coma y punto
decimal). Se exporta el estado actual del documento, con sus cambios sin guardar.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import __version__
from .document import Document, ObjectInfo
from .errors import D2ScriptViewerError
from .formats import bod, bytecode, script
from .formats.obsp import STEAM_ORIGINAL_SHA256, kind_name
from .settings import DEFAULT_GAME

MANIFEST = "manifest.json"
EXPORT_FORMAT = "d2sv-export"
EXPORT_VERSION = 1
FLOAT_TABLE_KIND = 15

Progress = Callable[[int, int], None]
Cancelled = Callable[[], bool]


# --- Nodos ------------------------------------------------------------------------------------


class _Writer:
    def __init__(self, document: Document) -> None:
        self.document = document

    def reference(self, group: int, object_id: int) -> dict[str, object]:
        node: dict[str, object] = {"tipo": "referencia", "grupo": group, "id": f"{object_id:016X}"}
        target = self.document.object_by_identity((group, object_id))
        node["ruta"] = target.path if target else None
        node["nombre"] = target.name if target else None
        return node

    def value(self, value: object) -> dict[str, object]:
        if isinstance(value, bod.BodObject):
            node: dict[str, object] = {"tipo": "objeto", "clase": value.cls.name.text}
            if value.cls.kind == bod.CLASS_SCRIPT:
                node["grupo_clase"] = value.cls.group
            fields: dict[str, object] = {}
            for item in value.fields:
                key = item.name.text
                while key in fields:  # no ocurre en el juego, pero nunca se pierde un campo
                    key += "#"
                fields[key] = self.value(item.value)
            node["campos"] = fields
            return node
        if isinstance(value, bod.Int32):
            return {"tipo": "int32", "valor": value.value}
        if isinstance(value, bod.Float32):
            number = value.value
            if math.isnan(number) or math.isinf(number):
                return {"tipo": "float32", "hex": value.raw.hex().upper()}
            return {"tipo": "float32", "valor": float(bod.format_float(number))}
        if isinstance(value, bod.Bool):
            node = {"tipo": "bool", "valor": bool(value.value)}
            if value.raw not in (0, 1):
                node["byte"] = value.raw
            return node
        if isinstance(value, bod.RawString):
            return {"tipo": "cadena", "valor": value.text}
        if isinstance(value, bod.HashedString):
            return {"tipo": "nombre", "valor": value.name.text}
        if isinstance(value, bod.ExternalRef):
            return self.reference(value.group, value.object_id)
        if isinstance(value, bod.Null):
            return {"tipo": "nulo"}
        if isinstance(value, (bod.BodList, bod.BodMap)):
            kind = "mapa" if isinstance(value, bod.BodMap) else ("pares" if value.mode == bod.MODE_PAIRS else "lista")
            if value.mode == bod.MODE_PAIRS:
                items = [{"clave": self.value(pair.key), "valor": self.value(pair.value)} for pair in value.items]
            else:
                items = [self.value(item) for item in value.items]
            return {"tipo": kind, "elementos": items}
        if isinstance(value, bod.BodTuple):
            return {"tipo": "tupla", "elementos": [self.value(item) for item in value.items]}
        raise D2ScriptViewerError(f"No se sabe exportar un {type(value).__name__}")

    def function(self, function: script.Function) -> dict[str, object]:
        if function.params is None:
            return {"nombre": function.name.text, "codigo": None}
        return {
            "nombre": function.name.text,
            "parametros": function.params,
            "tamaño": len(function.code),
            "codigo": [
                {
                    "offset": instruction.offset,
                    "op": bytecode.mnemonic(instruction),
                    "operando": bytecode.operand_text(instruction) or None,
                    "editable": instruction.is_literal,
                }
                for instruction in function.instructions
            ],
        }

    def script(self, body: script.Script) -> dict[str, object]:
        header = body.header
        return {
            "version": header.version,
            "grupo": header.group,
            "nombre": body.name.text,
            "clase_base": body.base.text,
            "simbolos": [symbol.text for symbol in header.symbols],
            "miembros": [
                {
                    "nombre": member.name.text,
                    "banderas": member.flags,
                    "tipo": member.type_label,
                    "valor": self.value(member.default) if member.default is not None else None,
                }
                for member in body.members
            ],
            "valores_iniciales": [
                {"nombre": item.name.text, "valor": self.value(item.value)} for item in body.initial_values
            ],
            "funciones": [self.function(function) for function in body.functions],
            "estados": [
                {"nombre": state.name.text, "funciones": [self.function(function) for function in state.functions]}
                for state in body.states
            ],
        }


def _metadata(document: Document, info: ObjectInfo, modified: bool | None = None) -> dict[str, object]:
    entry = info.entry
    blob = document.blob(info.position)
    return {
        "ruta": info.path,
        "nombre": info.name,
        "carpeta": info.folder or None,
        "clase": info.class_name or None,
        "tipo": entry.kind,
        "tipo_nombre": kind_name(entry.kind),
        "grupo": entry.group,
        "id": f"{entry.object_id:016X}",
        "tamaño": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest().upper(),
        "modificado": document.is_modified(info.position) if modified is None else modified,
    }


def object_json(document: Document, position: int, modified: bool | None = None) -> dict[str, object]:
    """El objeto entero como datos JSON (estado actual, con los cambios sin guardar)."""
    info = document.objects[position]
    writer = _Writer(document)
    data = _metadata(document, info, modified)
    if info.is_script:
        data["script"] = writer.script(document.script(position))
    else:
        tree = document.bod(position)
        data["bod"] = {"version": tree.version, "flags": tree.flags}
        data["raiz"] = writer.value(tree.root)
    return data


def float_table_csv(document: Document, position: int) -> str:
    """Una ``FloatTable`` como CSV: primera fila, nombres de columna; primera columna, de fila."""
    tree = document.bod(position)
    fields = {item.name.text: item.value for item in tree.root.fields}
    rows = fields.get("Data")
    columns = fields.get("ColumnNames")
    row_names = fields.get("RowNames")
    if not isinstance(rows, bod.BodList):
        raise D2ScriptViewerError(f"{document.objects[position].path} no tiene la forma de una FloatTable")
    column_names = [bod.value_text(item) for item in columns.items] if isinstance(columns, bod.BodList) else []
    names = [bod.value_text(item) for item in row_names.items] if isinstance(row_names, bod.BodList) else []
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([""] + column_names)
    for index, row in enumerate(rows.items):
        cells = row.fields[0].value.items if isinstance(row, bod.BodObject) and row.fields else []
        writer.writerow([names[index] if index < len(names) else str(index)] + [bod.value_text(cell) for cell in cells])
    return out.getvalue()


def is_float_table(info: ObjectInfo) -> bool:
    return info.entry.kind == FLOAT_TABLE_KIND


# --- Escritura --------------------------------------------------------------------------------


def check_destination(folder: Path) -> None:
    """Nunca dentro de la carpeta del juego; vacía o con una exportación anterior."""
    resolved = folder.resolve()
    game = DEFAULT_GAME.resolve()
    if resolved == game or game in resolved.parents:
        raise D2ScriptViewerError("No se exporta dentro de la carpeta del juego: elige otra carpeta")
    if resolved.exists() and not resolved.is_dir():
        raise D2ScriptViewerError(f"{folder} no es una carpeta")
    if resolved.is_dir() and any(resolved.iterdir()):
        manifest = resolved / MANIFEST
        try:
            previous = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = None
        if not isinstance(previous, dict) or previous.get("formato") != EXPORT_FORMAT:
            raise D2ScriptViewerError(
                f"{folder} no está vacía ni contiene una exportación anterior de D2ScriptViewer: elige una carpeta vacía"
            )


@dataclass
class ExportResult:
    folder: Path
    objects: int = 0
    csv_files: int = 0
    bytes_written: int = 0
    files: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Exportados {self.objects:,} objetos y {self.csv_files:,} tablas CSV en {self.folder} "
            f"({self.bytes_written / 1e6:,.1f} MB)"
        )


def _write(folder: Path, relative: str, text: str, result: ExportResult) -> None:
    target = folder / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = text.encode("utf-8")
    target.write_bytes(raw)
    result.bytes_written += len(raw)
    result.files.append(relative)


def export_document(
    document: Document,
    folder: Path,
    positions: list[int] | None = None,
    progress: Progress | None = None,
    cancelled: Cancelled | None = None,
    unsaved: set[int] | None = None,
    source: Path | None = None,
) -> ExportResult:
    """Escribe los JSON, los CSV y el manifiesto. Se puede llamar desde un hilo.

    La interfaz exporta una instantánea (``Document.from_bytes(current_data())``) para no
    competir con las ediciones; ``unsaved`` y ``source`` dicen entonces qué objetos tenían
    cambios sin guardar y de qué archivo venía.
    """
    check_destination(folder)
    folder.mkdir(parents=True, exist_ok=True)
    chosen = list(range(len(document.objects))) if positions is None else sorted(positions)
    result = ExportResult(folder)
    listed = []
    for count, position in enumerate(chosen):
        if cancelled is not None and cancelled():
            raise D2ScriptViewerError("Exportación cancelada")
        info = document.objects[position]
        data = object_json(document, position, None if unsaved is None else position in unsaved)
        relative = f"{info.path}.json"
        _write(folder, relative, json.dumps(data, ensure_ascii=False, indent=1), result)
        result.objects += 1
        entry = {key: data[key] for key in ("ruta", "nombre", "carpeta", "clase", "tipo", "grupo", "id", "tamaño", "sha256")}
        entry["json"] = relative
        if is_float_table(info):
            csv_relative = f"{info.path}.csv"
            _write(folder, csv_relative, float_table_csv(document, position), result)
            result.csv_files += 1
            entry["csv"] = csv_relative
        listed.append(entry)
        if progress is not None and count % 64 == 0:
            progress(count, len(chosen))
    data = document.current_data()
    sha = hashlib.sha256(data).hexdigest().upper()
    manifest = {
        "formato": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "herramienta": f"D2ScriptViewer {__version__}",
        "archivo": {
            "ruta": str(source or document.path) if (source or document.path) else None,
            "sha256": sha,
            "tamaño": len(data),
            "original_de_steam": sha == STEAM_ORIGINAL_SHA256,
            "cambios_sin_guardar": bool(document.modified_positions if unsaved is None else unsaved),
        },
        "objetos": listed,
    }
    _write(folder, MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=1), result)
    if progress is not None:
        progress(len(chosen), len(chosen))
    return result
