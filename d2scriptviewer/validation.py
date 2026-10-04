# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Validación de los objetos modificados antes de guardar (decisiones de la fase 5).

Bloquean el guardado:

- una clave repetida en un mapa ``0A`` o en una lista de pares (ninguna de las
  1 322 del juego tiene claves repetidas);
- una referencia ``FC`` que no apunta a ningún objeto del archivo.

Solo avisa un campo ``*ID`` que pasa a repetirse en una lista de objetos donde en el
original no se repetía: en el juego solo el 72 % de esas listas tiene los ``*ID``
únicos, así que no es una regla, pero un duplicado nuevo suele venir de duplicar un
elemento y olvidar cambiarle el identificador.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from . import diffing, edits
from .document import Document
from .formats import bod
from .formats.obsp import identity_text

ID_FIELD = re.compile(r"ID|.*ID|.*Id")


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _duplicated_ids(items: list) -> dict[str, set]:
    """Campo ``*ID`` → valores repetidos entre los objetos de una lista."""
    values: dict[str, Counter] = {}
    for item in items:
        if not isinstance(item, bod.BodObject):
            continue
        for child in item.fields:
            if ID_FIELD.fullmatch(child.name.text) and edits.is_editable(child.value):
                values.setdefault(child.name.text, Counter())[_state_key(child.value)] += 1
    return {name: {value for value, count in counter.items() if count > 1} for name, counter in values.items()}


def _state_key(node: object) -> object:
    return (type(node).__name__, edits.get_state(node))


def _show(key: object) -> str:
    kind, state = key  # type: ignore[misc]
    probe = getattr(bod, kind).__new__(getattr(bod, kind))
    edits.set_state(probe, state)
    return bod.value_text(probe)


def _id_lists(tree: bod.BodDocument) -> list[tuple[tuple, bod.BodList]]:
    return [
        (path, node)
        for path, node in bod.walk(tree.root)
        if isinstance(node, bod.BodList) and node.mode == bod.MODE_VALUES and len(node.items) > 1
    ]


def validate(document: Document) -> ValidationReport:
    report = ValidationReport()
    for position in sorted(document.modified_positions):
        tree = document.bod(position)
        original = document.baseline_tree(position)
        owner = document.objects[position].label()
        # Una lista idéntica a alguna del original no puede tener repetidos nuevos; las demás
        # se comparan con su pareja según el alineamiento del diff, no por ruta: insertar o
        # quitar un elemento desplaza las rutas de todo lo que viene detrás.
        _changes, mapping = diffing.diff_with_mapping(original, tree)
        original_lists: set[bytes] | None = None
        for path, node in bod.walk(tree.root):
            if isinstance(node, bod.ExternalRef) and document.object_by_identity(node.identity) is None:
                report.errors.append(
                    f"{owner} · {bod.path_label(tree, path)}: la referencia {identity_text(*node.identity)} "
                    "no apunta a ningún objeto del archivo"
                )
            elif isinstance(node, (bod.BodMap, bod.BodList)) and node.mode == bod.MODE_PAIRS:
                keys = Counter(bod.fingerprint(pair.key) for pair in node.items)
                repeated = [pair.key for pair in node.items if keys[bod.fingerprint(pair.key)] > 1]
                if repeated:
                    shown = ", ".join(sorted({bod.value_text(key) for key in repeated}))
                    report.errors.append(
                        f"{owner} · {bod.path_label(tree, path)}: claves repetidas ({shown}). "
                        "Cambia la clave de la entrada duplicada antes de guardar."
                    )
            elif isinstance(node, bod.BodList) and node.mode == bod.MODE_VALUES and len(node.items) > 1:
                now = _duplicated_ids(node.items)
                if not any(now.values()):
                    continue
                if original_lists is None:
                    original_lists = {bod.fingerprint(item) for _p, item in _id_lists(original)}
                if bod.fingerprint(node) in original_lists:
                    continue
                before_node = bod.resolve(original, mapping[path]) if path in mapping else None
                before = _duplicated_ids(before_node.items) if isinstance(before_node, bod.BodList) else {}
                for name, values in now.items():
                    new = values - before.get(name, set())
                    if new:
                        shown = ", ".join(sorted(_show(value) for value in new))
                        report.warnings.append(
                            f"{owner} · {bod.path_label(tree, path)}: el campo {name} se repite ({shown}) "
                            "y antes no se repetía"
                        )
    return report
