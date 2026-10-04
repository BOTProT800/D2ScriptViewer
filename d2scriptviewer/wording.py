# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Pequeñas ayudas de redacción para los textos de la interfaz y de la CLI."""

from __future__ import annotations


def count(number: int, singular: str, plural: str | None = None) -> str:
    """``1 objeto``, ``2 objetos``; con separador de miles."""
    word = singular if number == 1 else (plural or singular + "s")
    return f"{number:,} {word}"
