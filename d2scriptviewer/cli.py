# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="d2scriptviewer",
        description="Visor y editor de scripts.obsp de Darksiders II Deathinitive Edition",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_subparsers(dest="command")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return 0
