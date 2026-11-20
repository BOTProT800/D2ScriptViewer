# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Parches ``.d2svpatch.json`` (fase 8): las diferencias con el original, sin datos del juego.

Un parche lista, por objeto, las operaciones que convierten su árbol original en el
actual. Cada objeto se identifica por su ruta, su identidad (grupo, id) y el SHA-256
de su blob original y del resultado, así que un parche se aplica sobre el original
de Steam y sobre cualquier archivo donde solo difieran otros objetos.

Las operaciones se aplican en orden, cada una sobre el árbol que dejó la anterior:

========== ===============================================================
``valor``  cambia una hoja (ruta, etiqueta, valor anterior y nuevo)
``quitar`` quita un elemento de una lista o un mapa
``mover``  mueve un elemento dentro de su lista o mapa
``insertar`` inserta una copia de otro elemento (del mismo árbol o del original)
``nulo``   pone a nulo un objeto o una referencia
``copiar`` sustituye un hueco por la copia de un objeto del original
``referencia`` sustituye un hueco por una referencia
========== ===============================================================

Las estructurales solo copian contenido que ya está en el archivo original: el parche
nunca lleva objetos del juego, solo valores y rutas. Las huellas (SHA-256 recortado de
la huella canónica de un subárbol) comprueban al aplicar que se copia, quita o anula
lo mismo que al crear el parche.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from pathlib import Path

from . import __version__, diffing, edits, vocabulary
from .document import Document
from .edits import EditGroup, InsertItem, MoveItem, RemoveItem, ReplaceValue, ValueEdit
from .errors import D2ScriptViewerError, EditError, FormatError
from .formats import bod
from .formats.bod import Name
from .formats.hashes import name_hash
from .formats.obsp import STEAM_ORIGINAL_SHA256, identity_text
from .i18n import N_, Deferred, _, ngettext, term

PATCH_FORMAT = "d2svpatch"
PATCH_VERSION = 1
PATCH_SUFFIX = ".d2svpatch.json"

#: Las operaciones de un parche: identificadores del JSON, que el resumen muestra traducidos.
OPERATIONS = (
    N_("valor", "operación"), N_("quitar", "operación"), N_("mover", "operación"), N_("insertar", "operación"),
    N_("nulo", "operación"), N_("copiar", "operación"), N_("referencia", "operación"),
)

_LEAVES = (bod.Int32, bod.Float32, bod.Bool, bod.RawString, bod.HashedString, bod.ExternalRef)
_TYPE_NAMES = {
    bod.Int32: "int32", bod.Float32: "float32", bod.Bool: "bool", bod.RawString: "cadena",
    bod.HashedString: "nombre", bod.ExternalRef: "referencia",
}


class PatchError(D2ScriptViewerError):
    """El parche no se puede crear o no encaja con el archivo."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def print_of(node: object) -> str:
    """Huella corta de un subárbol, esté donde esté."""
    return hashlib.sha256(bod.fingerprint(node)).hexdigest()[:16].upper()


def _identity_json(document: Document, position: int) -> dict[str, object]:
    info = document.objects[position]
    return {"ruta": info.path, "grupo": info.entry.group, "id": f"{info.entry.object_id:016X}"}


# --- Estados de una hoja ----------------------------------------------------------------------


def state_json(node: object, state: object) -> dict[str, object]:
    text = edits.state_text(node, state)
    if isinstance(node, (bod.Int32, bod.Float32)):
        return {"hex": state.hex().upper(), "texto": text}  # type: ignore[union-attr]
    if isinstance(node, bod.Bool):
        return {"byte": state, "texto": text}
    if isinstance(node, bod.RawString):
        return {"texto": state}
    if isinstance(node, bod.HashedString):
        return {"texto": state.text}  # type: ignore[union-attr]
    if isinstance(node, bod.ExternalRef):
        group, object_id = state  # type: ignore[misc]
        return {"grupo": group, "id": f"{object_id:016X}"}
    raise PatchError(_("Un {kind} no es una hoja editable").format(kind=type(node).__name__))


def state_from_json(node: object, data: object) -> object:
    if not isinstance(data, dict):
        raise PatchError(_("Valor mal formado en el parche"))
    try:
        if isinstance(node, (bod.Int32, bod.Float32)):
            raw = bytes.fromhex(str(data["hex"]))
            if len(raw) != 4:
                raise PatchError(_("Un número ocupa 4 bytes"))
            return raw
        if isinstance(node, bod.Bool):
            value = int(data["byte"])
            if not 0 <= value <= 0xFF:
                raise PatchError(_("Un bool ocupa un byte"))
            return value
        if isinstance(node, bod.RawString):
            return edits.parse_raw_string(str(data["texto"]))
        if isinstance(node, bod.HashedString):
            text = edits.parse_raw_string(str(data["texto"]))
            return Name(name_hash(text), text)
        if isinstance(node, bod.ExternalRef):
            return (int(data["grupo"]), int(str(data["id"]), 16))
    except (KeyError, ValueError, TypeError, EditError) as error:
        raise PatchError(_("Valor mal formado en el parche: {error}").format(error=error)) from None
    raise PatchError(_("Un {kind} no es una hoja editable").format(kind=type(node).__name__))


# --- Crear ------------------------------------------------------------------------------------


class _SourceFinder:
    """Busca en el original un objeto igual al pedido (o, si no, de la misma clase y campos)."""

    def __init__(self, base: Document) -> None:
        self.base = base
        self._by_class: dict[bod.ClassRef, list[tuple[int, tuple]]] | None = None

    def _index(self) -> dict[bod.ClassRef, list[tuple[int, tuple]]]:
        if self._by_class is None:
            index: dict[bod.ClassRef, list[tuple[int, tuple]]] = {}
            for info in self.base.objects:
                if info.is_script:
                    continue
                tree = bod.decode(self.base.obsp.blob(info.position))
                for path, node in bod.walk(tree.root):
                    if path and isinstance(node, bod.BodObject):
                        index.setdefault(node.cls, []).append((info.position, path))
            self._by_class = index
        return self._by_class

    def find(self, node: object) -> tuple[int, tuple, bod.BodObject] | None:
        if not isinstance(node, bod.BodObject):
            return None
        wanted = bod.fingerprint(node)
        names = [item.name for item in node.fields]
        fallback = None
        for position, path in self._index().get(node.cls, ()):
            found = bod.resolve(self.base.baseline_tree(position), path)
            assert isinstance(found, bod.BodObject)
            if bod.fingerprint(found) == wanted:
                return position, path, found
            if fallback is None and [item.name for item in found.fields] == names:
                fallback = (position, path, found)
        return fallback


def _same_kind(old: object, new: object) -> bool:
    if type(old) is not type(new):
        return False
    if isinstance(old, bod.BodObject):
        return old.cls == new.cls and [f.name for f in old.fields] == [f.name for f in new.fields]  # type: ignore[attr-defined]
    if isinstance(old, (bod.BodList, bod.BodMap)):
        return old.mode == new.mode  # type: ignore[attr-defined]
    if isinstance(old, bod.BodTuple):
        return len(old.items) == len(new.items)  # type: ignore[attr-defined]
    return True


class _Deriver:
    def __init__(self, current: bod.BodDocument, finder: _SourceFinder, base: Document, label: str) -> None:
        self.current = current
        self.finder = finder
        self.base = base
        self.label = label
        self.operations: list[dict[str, object]] = []
        self.sources: set[int] = set()

    def fail(self, path: tuple, reason: str) -> PatchError:
        return PatchError(f"{self.label} · {vocabulary.path_label(self.current, path)}: {reason}")

    def external(self, node: object, path: tuple) -> tuple[dict[str, object], object]:
        found = self.finder.find(node)
        if found is None:
            raise self.fail(path, _("no hay en el original ningún {value} del que copiar").format(value=diffing.describe(node)))
        position, source_path, source = found
        self.sources.add(position)
        origin = {"objeto": _identity_json(self.base, position), "ruta": list(source_path)}
        return origin, source

    def reconcile(self, old: object, new: object, path: tuple) -> None:
        if not _same_kind(old, new):
            self.replace(old, new, path)
            return
        if isinstance(old, _LEAVES):
            before, after = edits.get_state(old), edits.get_state(new)
            if before != after:
                self.operations.append({
                    "op": "valor", "ruta": list(path), "etiqueta": bod.path_label(self.current, path),
                    "tipo": _TYPE_NAMES[type(old)], "antes": state_json(old, before), "despues": state_json(new, after),
                })
            return
        if isinstance(old, bod.BodObject):
            for index, (before, after) in enumerate(zip(old.fields, new.fields)):  # type: ignore[attr-defined]
                self.reconcile(before.value, after.value, path + (index,))
        elif isinstance(old, bod.Pair):
            self.reconcile(old.key, new.key, path + (0,))  # type: ignore[attr-defined]
            self.reconcile(old.value, new.value, path + (1,))  # type: ignore[attr-defined]
        elif isinstance(old, bod.BodTuple):
            for index, (before, after) in enumerate(zip(old.items, new.items)):  # type: ignore[attr-defined]
                self.reconcile(before, after, path + (index,))
        elif isinstance(old, (bod.BodList, bod.BodMap)):
            self.sequence(old.items, new.items, path)  # type: ignore[attr-defined]

    def replace(self, old: object, new: object, path: tuple) -> None:
        if not path:
            raise self.fail(path, _("cambió la clase del objeto raíz"))
        if isinstance(new, bod.Null) and isinstance(old, (bod.BodObject, bod.ExternalRef)):
            self.operations.append({"op": "nulo", "ruta": list(path), "huella": print_of(old)})
        elif isinstance(new, bod.ExternalRef):
            self.operations.append({
                "op": "referencia", "ruta": list(path), "huella_antes": print_of(old),
                "grupo": new.group, "id": f"{new.object_id:016X}",
            })
        elif isinstance(new, bod.BodObject):
            origin, source = self.external(new, path)
            self.operations.append({
                "op": "copiar", "ruta": list(path), "huella_antes": print_of(old),
                "copia_de": origin, "huella": print_of(source),
            })
            self.reconcile(source, new, path)
        else:
            raise self.fail(path, _("no se puede expresar el cambio de {old} a {new}").format(
                old=diffing.describe(old), new=diffing.describe(new)))

    def attempt(self, old: object, new: object, path: tuple) -> "_Deriver | None":
        """Las operaciones que convierten ``old`` en ``new`` en ``path``, o ``None`` si no se puede."""
        child = _Deriver(self.current, self.finder, self.base, self.label)
        try:
            child.reconcile(old, new, path)
        except PatchError:
            return None
        return child

    def sequence(self, old_items: list, new_items: list, path: tuple) -> None:
        alignment = diffing.align(old_items, new_items)
        if alignment is not None:
            source_of = {new: old for old, new in alignment.equal + alignment.moved}
            candidates = alignment.modified
        elif len(old_items) == len(new_items):
            source_of, candidates = {}, [(index, index) for index in range(len(new_items))]
        else:
            raise self.fail(path, _("la lista cambió demasiado para describirla elemento a elemento"))
        nested: dict[int, _Deriver] = {}
        for old_index, new_index in candidates:
            child = self.attempt(old_items[old_index], new_items[new_index], path + (new_index,))
            if child is not None:
                source_of[new_index] = old_index
                nested[new_index] = child
        # Primero se colocan los elementos en su sitio (moviendo originales e insertando copias)
        # y al final se quitan los originales que sobran: así todos sirven de origen de una copia.
        work: list[tuple] = [("original", index) for index in range(len(old_items))]
        for target, item in enumerate(new_items):
            if target in source_of:
                tag = ("original", source_of[target])
                where = work.index(tag)
                if where != target:
                    self.operations.append({"op": "mover", "contenedor": list(path), "desde": where, "hasta": target})
                    work.insert(target, work.pop(where))
                continue
            origin, source, child = self.copy_source(old_items, work, item, path, target)
            self.operations.append({
                "op": "insertar", "contenedor": list(path), "indice": target, "copia_de": origin,
                "huella": print_of(source),
            })
            work.insert(target, ("copia", target))
            nested[target] = child
        for index in range(len(work) - 1, len(new_items) - 1, -1):
            tag = work[index]
            self.operations.append({
                "op": "quitar", "contenedor": list(path), "indice": index, "huella": print_of(old_items[tag[1]]),
            })
            del work[index]
        for target in range(len(new_items)):
            child = nested.get(target)
            if child is None:  # igual que su original: no hay nada que hacer dentro
                continue
            self.operations.extend(child.operations)
            self.sources |= child.sources

    def copy_source(
        self, old_items: list, work: list[tuple], item: object, path: tuple, target: int
    ) -> tuple[dict[str, object], object, "_Deriver"]:
        """De dónde copiar un elemento añadido: un original igual, de la misma forma o al menos
        sustituible (objeto o referencia); si no, un objeto igual o de la misma clase del original."""
        originals = [tag[1] for tag in work if tag[0] == "original"]
        wanted = bod.fingerprint(item)
        replaceable = (bod.BodObject, bod.ExternalRef, bod.Null)
        ordered = (
            [index for index in originals if bod.fingerprint(old_items[index]) == wanted]
            + [index for index in originals if diffing._same_shape(old_items[index], item)]
            + [index for index in originals
               if isinstance(old_items[index], replaceable[:2]) and isinstance(item, replaceable)]
        )
        tried: set[int] = set()
        for index in ordered:
            if index in tried:
                continue
            tried.add(index)
            child = self.attempt(old_items[index], item, path + (target,))
            if child is not None:
                return {"ruta": list(path + (work.index(("original", index)),))}, old_items[index], child
        found = self.finder.find(item)
        if found is not None:
            position, source_path, source = found
            child = self.attempt(source, item, path + (target,))
            if child is not None:
                self.sources.add(position)
                return {"objeto": _identity_json(self.base, position), "ruta": list(source_path)}, source, child
        raise self.fail(path + (target,), _("no hay en el original nada de lo que copiar {value}").format(
            value=diffing.describe(item)))


def create_patch(base_data: bytes, document: Document) -> dict[str, object]:
    """Parche que convierte ``base_data`` en el estado actual de ``document``.

    Antes de devolverlo lo reaplica sobre la base y comprueba que da exactamente el
    mismo archivo; si no, lanza :class:`PatchError` (nunca se escribe un parche que no
    reproduce el archivo).
    """
    base = Document.from_bytes(base_data)
    if [entry.identity for entry in base.obsp.entries] != [entry.identity for entry in document.obsp.entries]:
        raise PatchError(_("La base no tiene los mismos objetos, en el mismo orden, que el archivo actual"))
    finder = _SourceFinder(base)
    objects = []
    sources: set[int] = set()
    for info in document.objects:
        position = info.position
        current_blob = document.blob(position)
        original_blob = base.obsp.blob(position)
        if current_blob == original_blob:
            continue
        deriver = _Deriver(document.bod(position), finder, base, info.label())
        deriver.reconcile(base.baseline_tree(position).root, document.bod(position).root, ())
        if info.is_script and any(operation["op"] != "valor" for operation in deriver.operations):
            raise PatchError(_("{object}: en un script solo puede haber cambios de valor").format(object=info.label()))
        sources |= deriver.sources
        entry = _identity_json(base, position)
        entry.update({
            "nombre": info.name,
            "sha256_original": sha256(original_blob),
            "sha256_resultado": sha256(current_blob),
            "operaciones": deriver.operations,
        })
        objects.append(entry)
    target = document.current_data()
    patch: dict[str, object] = {
        "formato": PATCH_FORMAT,
        "version": PATCH_VERSION,
        "herramienta": f"D2ScriptViewer {__version__}",
        "creado": _dt.datetime.now().replace(microsecond=0).isoformat(),
        "base": {"sha256": sha256(base_data), "tamaño": len(base_data),
                 "original_de_steam": sha256(base_data) == STEAM_ORIGINAL_SHA256},
        "resultado": {"sha256": sha256(target), "tamaño": len(target)},
        "fuentes": [
            dict(_identity_json(base, position), sha256_original=sha256(base.obsp.blob(position)))
            for position in sorted(sources)
        ],
        "objetos": objects,
    }
    check = Document.from_bytes(base_data)
    apply_patch(check, patch)
    if check.current_data() != target:
        raise PatchError(_("El parche no reproduce el archivo actual al reaplicarlo sobre la base; no se escribe"))
    return patch


# --- Aplicar ----------------------------------------------------------------------------------


def _locate(document: Document, data: object, source: bool = False) -> int:
    """La posición del objeto (o, con ``source``, del objeto de origen) que nombra el parche."""
    kind = _("objeto de origen") if source else _("objeto")
    if not isinstance(data, dict):
        raise PatchError(_("Un {kind} del parche está mal formado").format(kind=kind))
    try:
        identity = (int(data["grupo"]), int(str(data["id"]), 16))
        path = str(data["ruta"])
    except (KeyError, ValueError, TypeError):
        raise PatchError(_("Un {kind} del parche está mal formado").format(kind=kind)) from None
    info = document.object_by_identity(identity)
    if info is None:
        raise PatchError(_("El {kind} {path} ({identity}) no existe en este archivo").format(
            kind=kind, path=path, identity=identity_text(*identity)))
    if info.path != path:
        raise PatchError(_("El {kind} {identity} se llama {actual}, no {path}").format(
            kind=kind, identity=identity_text(*identity), actual=info.path, path=path))
    return info.position


def _path(value: object) -> tuple:
    if not isinstance(value, list) or not all(isinstance(step, int) and step >= 0 for step in value):
        raise PatchError(_("Ruta mal formada en el parche"))
    return tuple(value)


def _resolve(tree: bod.BodDocument, path: tuple, label: str) -> object:
    try:
        return bod.resolve(tree, path)
    except (IndexError, FormatError):
        raise PatchError(_("{where}: la ruta {path} no existe").format(where=label, path=list(path))) from None


def apply_patch(document: Document, patch: dict[str, object], name: str = "parche") -> EditGroup | None:
    """Aplica el parche como un único paso de deshacer; si algo no encaja, no cambia nada."""
    if not isinstance(patch, dict) or patch.get("formato") != PATCH_FORMAT:
        raise PatchError(_("No es un parche de D2ScriptViewer"))
    if patch.get("version") != PATCH_VERSION:
        raise PatchError(_("Versión de parche {version} no admitida (se admite la {supported})").format(
            version=patch.get("version"), supported=PATCH_VERSION))
    objects = patch.get("objetos")
    sources = patch.get("fuentes", [])
    if not isinstance(objects, list) or not isinstance(sources, list):
        raise PatchError(_("El parche no tiene la lista de objetos"))
    source_positions: dict[tuple[int, int], int] = {}
    for item in sources:
        position = _locate(document, item, source=True)
        if sha256(document.original_blob(position)) != item.get("sha256_original"):
            raise PatchError(_("{object}: el original no coincide con el del parche").format(
                object=document.objects[position].label()))
        source_positions[document.objects[position].identity] = position
    plan = []
    for item in objects:
        position = _locate(document, item)
        info = document.objects[position]
        if document.is_modified(position):
            raise PatchError(_("{object} tiene cambios sin guardar: deshazlos o guárdalos antes de aplicar el parche").format(
                object=info.label()))
        if sha256(document.blob(position)) != item.get("sha256_original"):
            raise PatchError(_("{object} no es el que espera el parche (su contenido es otro)").format(object=info.label()))
        operations = item.get("operaciones")
        if not isinstance(operations, list):
            raise PatchError(_("{object}: faltan las operaciones").format(object=info.label()))
        plan.append((position, item, operations))

    def source_node(position: int, tree: bod.BodDocument, origin: object, label: str) -> object:
        if not isinstance(origin, dict):
            raise PatchError(_("{where}: origen de copia mal formado").format(where=label))
        path = _path(origin.get("ruta"))
        if "objeto" in origin:
            other = _locate(document, origin["objeto"], source=True)
            if document.objects[other].identity not in source_positions:
                raise PatchError(_("{where}: el objeto de origen no está entre las fuentes del parche").format(where=label))
            return _resolve(document.baseline_tree(other), path, label)
        return _resolve(tree, path, label)

    def build(do) -> None:  # type: ignore[no-untyped-def]
        for position, item, operations in plan:
            info = document.objects[position]
            label = info.label()
            for operation in operations:
                if not isinstance(operation, dict):
                    raise PatchError(_("{where}: operación mal formada").format(where=label))
                kind = operation.get("op")
                if info.is_script and kind != "valor":
                    raise PatchError(_("{where}: en un script solo se aplican cambios de valor").format(where=label))
                tree = document.bod(position)
                if kind == "valor":
                    path = _path(operation.get("ruta"))
                    where = f"{label} · {operation.get('etiqueta')}"
                    _resolve(tree, path, where)
                    try:
                        node = document.node_at(position, path)
                    except EditError as error:
                        raise PatchError(f"{where}: {error}") from None
                    # La etiqueta del parche es canónica: se compara con la canónica, nunca con la que se ve.
                    if bod.path_label(tree, path) != operation.get("etiqueta"):
                        raise PatchError(_("{where}: en esa ruta está {label}").format(
                            where=where, label=vocabulary.path_label(tree, path)))
                    if _TYPE_NAMES.get(type(node)) != operation.get("tipo"):
                        raise PatchError(_("{where}: el valor es de tipo {type}").format(
                            where=where, type=vocabulary.type_text(node)))
                    before = edits.get_state(node)
                    if before != state_from_json(node, operation.get("antes")):
                        raise PatchError(_("{where}: el valor actual ({value}) no es el que espera el parche").format(
                            where=where, value=edits.state_text(node, before)))
                    after = state_from_json(node, operation.get("despues"))
                    if isinstance(node, bod.ExternalRef) and document.object_by_identity(after) is None:  # type: ignore[arg-type]
                        raise PatchError(_("{where}: la referencia {identity} no existe").format(
                            where=where, identity=identity_text(*after)))  # type: ignore[misc]
                    do(ValueEdit(position, path, before, after))
                elif kind in ("quitar", "mover", "insertar"):
                    container_path = _path(operation.get("contenedor"))
                    container = _resolve(tree, container_path, label)
                    if not isinstance(container, (bod.BodList, bod.BodMap)):
                        raise PatchError(_("{where}: {path} no es una lista ni un mapa").format(
                            where=label, path=list(container_path)))
                    items = container.items
                    where = f"{label} · {vocabulary.path_label(tree, container_path)}"
                    if kind == "quitar":
                        index = operation.get("indice")
                        if not isinstance(index, int) or not 0 <= index < len(items):
                            raise PatchError(_("{where}: no hay elemento {index}").format(where=where, index=index))
                        if print_of(items[index]) != operation.get("huella"):
                            raise PatchError(_("{where}[{index}] no es el elemento que el parche quita").format(
                                where=where, index=index))
                        do(RemoveItem(position, container_path, index, items[index]))
                    elif kind == "mover":
                        source, target = operation.get("desde"), operation.get("hasta")
                        if not all(isinstance(value, int) and 0 <= value < len(items) for value in (source, target)):
                            raise PatchError(_("{where}: movimiento fuera de la lista").format(where=where))
                        do(MoveItem(position, container_path, source, target))  # type: ignore[arg-type]
                    else:
                        index = operation.get("indice")
                        if not isinstance(index, int) or not 0 <= index <= len(items):
                            raise PatchError(_("{where}: no se puede insertar en {index}").format(where=where, index=index))
                        node = source_node(position, tree, operation.get("copia_de"), where)
                        if print_of(node) != operation.get("huella"):
                            raise PatchError(_("{where}: lo que se copia no es lo que espera el parche").format(where=where))
                        do(InsertItem(position, container_path, index, bod.clone(node)))
                elif kind in ("nulo", "copiar", "referencia"):
                    path = _path(operation.get("ruta"))
                    if not path:
                        raise PatchError(_("{where}: no se sustituye la raíz").format(where=label))
                    node = _resolve(tree, path, label)
                    where = f"{label} · {vocabulary.path_label(tree, path)}"
                    expected = operation.get("huella" if kind == "nulo" else "huella_antes")
                    if print_of(node) != expected:
                        raise PatchError(_("{where}: ahí no está lo que espera el parche").format(where=where))
                    if kind == "nulo":
                        if not edits.can_null(tree, path):
                            raise PatchError(_("{where}: solo un objeto o una referencia pueden pasar a nulo").format(
                                where=where))
                        value: object = bod.Null()
                    elif kind == "copiar":
                        source = source_node(position, tree, operation.get("copia_de"), where)
                        if print_of(source) != operation.get("huella"):
                            raise PatchError(_("{where}: lo que se copia no es lo que espera el parche").format(where=where))
                        value = bod.clone(source)
                    else:
                        try:
                            identity = (int(operation["grupo"]), int(str(operation["id"]), 16))
                        except (KeyError, ValueError, TypeError):
                            raise PatchError(_("{where}: referencia mal formada").format(where=where)) from None
                        if document.object_by_identity(identity) is None:
                            raise PatchError(_("{where}: la referencia {identity} no existe").format(
                                where=where, identity=identity_text(*identity)))
                        value = bod.ExternalRef(*identity)
                    do(ReplaceValue(position, path, node, value))
                else:
                    raise PatchError(_("{where}: operación desconocida {kind!r}").format(where=label, kind=kind))
            if sha256(document.blob(position)) != item.get("sha256_resultado"):
                raise PatchError(_("{where}: el resultado no es el que espera el parche").format(where=label))

    return document.run_operations(Deferred("Aplicar {name}", name=name), build)


# --- Archivo ----------------------------------------------------------------------------------


def patch_summary(patch: dict[str, object]) -> str:
    objects = patch.get("objetos", [])
    total = sum(len(item.get("operaciones", [])) for item in objects) if isinstance(objects, list) else 0
    kinds: dict[str, int] = {}
    for item in objects if isinstance(objects, list) else []:
        for operation in item.get("operaciones", []):
            kinds[operation.get("op", "?")] = kinds.get(operation.get("op", "?"), 0) + 1
    if not total:
        return _("sin cambios")
    detail = ", ".join(f"{count} {term(str(kind), 'operación')}" for kind, count in sorted(kinds.items()))
    count = len(objects)
    return _("{objects}, {operations} ({detail})").format(
        objects=ngettext("{count:,} objeto", "{count:,} objetos", count).format(count=count),
        operations=ngettext("{count:,} operación", "{count:,} operaciones", total).format(count=total),
        detail=detail,
    )


_INT_LIST = re.compile(r"\[\s*(-?\d+(?:,\s*-?\d+)*)\s*\]")


def dumps(patch: dict[str, object]) -> str:
    """JSON legible, con las rutas de índices en una sola línea."""
    text = json.dumps(patch, ensure_ascii=False, indent=1)
    return _INT_LIST.sub(lambda match: "[" + ", ".join(match.group(1).replace(",", " ").split()) + "]", text)


def save_patch(patch: dict[str, object], path: Path) -> None:
    path.write_text(dumps(patch), encoding="utf-8")


def load_patch(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PatchError(_("No se pudo leer {path}: {error}").format(path=path, error=error.strerror or error)) from None
    except ValueError as error:
        raise PatchError(_("{name} no es un JSON válido: {error}").format(name=path.name, error=error)) from None
    if not isinstance(data, dict) or data.get("formato") != PATCH_FORMAT:
        raise PatchError(_("{name} no es un parche de D2ScriptViewer").format(name=path.name))
    return data


def base_for(document: Document) -> tuple[bytes, str]:
    """La base de un parche: la copia del original junto al archivo o, si no hay, el archivo abierto."""
    from .saving import original_copy_path

    if document.path is not None:
        copy = original_copy_path(document.path)
        if copy.is_file():
            return copy.read_bytes(), str(copy)
    return document.obsp.data, str(document.path) if document.path is not None else _("archivo abierto")
