# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Comprobaciones completas de un ``.obsp``: las del apéndice A, sobre cualquier archivo.

Las usa ``python -m d2scriptviewer verify`` y sirven también para comprobar que un
archivo guardado por la herramienta sigue siendo un OBSP coherente.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from .errors import FormatError
from .formats import bod, script
from .formats.hashes import HashDictionary, document_names
from .formats.obsp import STEAM_ORIGINAL_SHA256, ObspFile, identity_text, rebuild, string_table_order

Progress = Callable[[int, int], None]


@dataclass
class Check:
    label: str
    ok: bool
    detail: str


@dataclass
class VerifyReport:
    size: int
    sha256: str
    checks: list[Check] = field(default_factory=list)
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def is_steam_original(self) -> bool:
        return self.sha256 == STEAM_ORIGINAL_SHA256

    def add(self, label: str, ok: bool, detail: str) -> None:
        self.checks.append(Check(label, ok, detail))


def verify_data(data: bytes, progress: Progress | None = None) -> VerifyReport:
    started = time.perf_counter()
    try:
        obsp = ObspFile.parse(data)
    except FormatError as error:
        report = VerifyReport(len(data), "")
        report.add("Contenedor OBSP", False, str(error))
        return report
    report = VerifyReport(len(data), obsp.sha256())
    entries = obsp.entries
    report.add(
        "Contenedor OBSP",
        True,
        f"{len(entries):,} objetos, {len(obsp.strings):,} cadenas, versión {obsp.header.version}",
    )
    problems = obsp.layout_problems()
    report.add("Blobs contiguos hasta el EOF", not problems, "; ".join(problems) or "sí")
    report.add(
        "Tabla de cadenas en orden de primera aparición",
        list(obsp.strings) == string_table_order(entries),
        f"{len(obsp.strings):,} cadenas",
    )
    identities = Counter(entry.identity for entry in entries)
    duplicated = sum(1 for count in identities.values() if count > 1)
    report.add("Identidades (grupo, id) únicas", duplicated == 0, f"{duplicated} repetidas")

    dictionary = HashDictionary()
    dictionary.update(obsp.strings.items())
    non_ascii = sum(1 for text in obsp.strings.values() if not text.isascii())
    recoded: dict[int, bytes] = {}
    bod_total = bod_same = bod_failed = 0
    script_total = script_bad = 0
    references: list[tuple[int, int]] = []
    first_failures: list[str] = []
    total = len(entries)
    for position, entry in enumerate(entries):
        blob = obsp.blob(position)
        label = obsp.text(entry.path_hash) or identity_text(entry.group, entry.object_id)
        if entry.is_script:
            script_total += 1
            try:
                header = script.parse_header(blob)
            except FormatError as error:
                script_bad += 1
                first_failures.append(f"{label}: {error}")
                continue
            header_problems = script.header_problems(header, entry)
            if header_problems:
                script_bad += 1
                first_failures.append(f"{label}: " + "; ".join(header_problems))
            for symbol in header.symbols:
                dictionary.add(symbol.hash, symbol.text)
                non_ascii += not symbol.text.isascii()
        else:
            bod_total += 1
            try:
                document = bod.decode(blob)
            except FormatError as error:
                bod_failed += 1
                first_failures.append(f"{label}: {error}")
                continue
            encoded = bod.encode(document)
            recoded[position] = encoded
            if encoded == blob:
                bod_same += 1
            else:
                first_failures.append(f"{label}: el BOD recodificado difiere")
            for name in document_names(document):
                dictionary.add(name.hash, name.text)
                non_ascii += not name.text.isascii()
            for _path, node in bod.walk(document.root):
                if isinstance(node, bod.RawString):
                    non_ascii += not node.text.isascii()
                elif isinstance(node, bod.ExternalRef):
                    references.append(node.identity)
        if progress and position % 256 == 0:
            progress(position, total)

    report.add(
        "BOD: decodificar y recodificar idéntico",
        bod_same == bod_total and not bod_failed,
        f"{bod_same:,} / {bod_total:,} idénticos" + (f", {bod_failed} no decodifican" if bod_failed else ""),
    )
    report.add(
        "Scripts: cabeceras coherentes",
        script_bad == 0,
        f"{script_total - script_bad:,} / {script_total:,} coherentes",
    )
    rebuilt = rebuild(obsp, recoded)
    report.add(
        "Reconstrucción completa (BOD recodificados)",
        rebuilt == data,
        "idéntica al archivo" if rebuilt == data else "difiere del archivo",
    )
    conflicts = len(dictionary.conflicts) + len(dictionary.reverse_conflicts())
    report.add(
        "Misma cadena, mismo hash",
        conflicts == 0,
        f"{len(dictionary):,} pares hash↔cadena, {conflicts} conflictos",
    )
    report.add("Cadenas solo ASCII", non_ascii == 0, f"{non_ascii} no ASCII")
    dangling = sum(1 for identity in references if identity not in identities)
    report.add(
        "Referencias FC",
        True,
        f"{len(references):,} referencias, {dangling} sin objeto de destino en este archivo",
    )
    if first_failures:
        report.add("Primeros fallos", False, " | ".join(first_failures[:5]))
    if progress:
        progress(total, total)
    report.seconds = time.perf_counter() - started
    return report
