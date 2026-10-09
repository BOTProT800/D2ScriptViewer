# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

from __future__ import annotations


class D2ScriptViewerError(Exception):
    """Error esperado que puede mostrarse directamente al usuario."""


class FormatError(D2ScriptViewerError):
    """Los datos no coinciden con el formato esperado o están truncados."""


class EditError(D2ScriptViewerError):
    """Una edición no supera la validación y no se aplica."""


class SaveError(D2ScriptViewerError):
    """El guardado se detuvo; el archivo de destino no se ha tocado salvo que se diga."""


class PathError(D2ScriptViewerError):
    """Un texto que no lleva a ninguna parte (fase 11): ``start`` y ``end`` señalan el tramo culpable."""

    def __init__(self, message: str, start: int = 0, end: int = 0) -> None:
        super().__init__(message)
        self.start = start
        self.end = end
