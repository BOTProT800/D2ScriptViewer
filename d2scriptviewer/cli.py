# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from collections import Counter
from pathlib import Path

from . import __version__
from .document import Document, ObjectInfo
from .errors import D2ScriptViewerError
from .formats import bod
from .formats.obsp import KIND_NAMES, STEAM_ORIGINAL_SHA256, identity_text, kind_name, rebuild
from .settings import OBSP_ENV, find_default_obsp
from .verification import verify_data
from .wording import count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="d2scriptviewer",
        description="Visor y editor de scripts.obsp de Darksiders II Deathinitive Edition. "
        "Sin subcomando abre la interfaz gráfica.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    def add_command(name: str, help_text: str) -> argparse.ArgumentParser:
        command = subparsers.add_parser(name, help=help_text, description=help_text)
        command.add_argument(
            "--archivo",
            type=Path,
            help=f"scripts.obsp que se lee (por defecto, ${OBSP_ENV} o el del juego)",
        )
        return command

    add_command("info", "resumen del archivo: huella, cabecera y objetos por tipo")

    listing = add_command("list", "listar objetos del índice")
    listing.add_argument("--tipo", help="número o nombre del tipo (p. ej. 8 o Desc)")
    listing.add_argument("--clase", help="texto contenido en la clase")
    listing.add_argument("--filtro", help="texto contenido en la ruta, el nombre o la carpeta")

    show = add_command("show", "mostrar un objeto como árbol de texto")
    show.add_argument("objeto", help="ruta (p. ej. death/death_desc) o nombre (p. ej. Death_Desc)")
    show.add_argument("--profundidad", type=int, default=0, help="profundidad máxima (0 = sin límite)")

    roundtrip = add_command("roundtrip", "recodificar todos los BOD, reconstruir y comparar")
    roundtrip.add_argument("--salida", type=Path, help="escribir aquí el archivo reconstruido")

    add_command("verify", "comprobar el archivo entero (apéndice A del plan)")
    return parser


def _resolve_path(value: Path | None) -> Path:
    path = value or find_default_obsp()
    if path is None:
        raise D2ScriptViewerError(
            f"No se encontró scripts.obsp: usa --archivo o define {OBSP_ENV}"
        )
    if not path.is_file():
        raise D2ScriptViewerError(f"No existe el archivo {path}")
    return path


def _status_text(sha256: str) -> str:
    return "original de Steam" if sha256 == STEAM_ORIGINAL_SHA256 else "modificado o desconocido"


def _parse_kind(value: str) -> int:
    if value.isdigit():
        return int(value)
    for kind, name in KIND_NAMES.items():
        if name.casefold() == value.casefold():
            return kind
    raise D2ScriptViewerError(
        f"Tipo desconocido '{value}'. Tipos: " + ", ".join(f"{k}={n}" for k, n in KIND_NAMES.items())
    )


def command_info(document: Document, path: Path) -> int:
    obsp = document.obsp
    header = obsp.header
    sha = obsp.sha256()
    print(f"Archivo:   {path}")
    print(f"Tamaño:    {len(obsp.data):,} bytes")
    print(f"SHA-256:   {sha}")
    print(f"Estado:    {_status_text(sha)}")
    print(f"Versión:   {header.version}   campo desconocido: {header.unknown}")
    print(f"Objetos:   {header.object_count:,}   cadenas: {header.string_count:,}   "
          f"longitud máxima: {header.max_string_length}")
    print()
    counts = Counter(entry.kind for entry in obsp.entries)
    sizes = Counter()
    for entry in obsp.entries:
        sizes[entry.kind] += entry.size
    print(f"{'Tipo':>4}  {'Contenido':26} {'Objetos':>8} {'Bytes':>12}")
    for kind in sorted(counts):
        print(f"{kind:>4}  {kind_name(kind):26} {counts[kind]:>8,} {sizes[kind]:>12,}")
    return 0


def command_list(document: Document, args: argparse.Namespace) -> int:
    kind = _parse_kind(args.tipo) if args.tipo else None
    class_filter = (args.clase or "").casefold()
    text_filter = (args.filtro or "").replace("\\", "/").casefold()
    shown = 0
    for info in document.objects:
        if kind is not None and info.entry.kind != kind:
            continue
        if class_filter and class_filter not in info.class_name.casefold():
            continue
        if text_filter and not any(
            text_filter in value.replace("\\", "/").casefold() for value in (info.path, info.name, info.folder)
        ):
            continue
        shown += 1
        identity = identity_text(info.entry.group, info.entry.object_id)
        print(
            f"{identity:22}  {info.kind_label:24} {info.entry.size:>8,}  {info.path}  "
            f"[{info.class_name or '-'}] {info.folder}"
        )
    print(count(shown, "objeto"), file=sys.stderr)
    return 0


def _print_tree(document: Document, label: str, node: object, depth: int, limit: int) -> None:
    indent = "  " * depth
    if isinstance(node, bod.ExternalRef):
        target = document.object_by_identity(node.identity)
        suffix = f"  ({target.label()})" if target else "  (sin destino)"
    else:
        suffix = ""
    print(f"{indent}{label}: {bod.type_text(node)} = {bod.value_text(node)}{suffix}")
    if limit and depth + 1 >= limit:
        return
    for child_label, child in bod.children(node):
        _print_tree(document, child_label, child, depth + 1, limit)


def _print_object(document: Document, info: ObjectInfo, limit: int) -> None:
    entry = info.entry
    print(f"# {info.path}  ({info.name})")
    print(f"# tipo {entry.kind} ({info.kind_label}), clase {info.class_name or '-'}, "
          f"carpeta {info.folder or '-'}, id {identity_text(entry.group, entry.object_id)}, "
          f"offset 0x{entry.offset:X}, {entry.size:,} bytes")
    if info.is_script:
        header = document.script_header(info.position)
        print(f"script versión {header.version}, {len(header.symbols)} símbolos, "
              f"cuerpo de {entry.size - header.body_offset:,} bytes (solo lectura)")
        for symbol in header.symbols:
            print(f"  {symbol.hash:016X}  {symbol.text}")
        return
    parsed = document.bod(info.position)
    print(f"BOD versión {parsed.version}, flags {parsed.flags}")
    _print_tree(document, "raíz", parsed.root, 0, limit)


def command_show(document: Document, args: argparse.Namespace) -> int:
    matches = document.find(args.objeto)
    if not matches:
        raise D2ScriptViewerError(f"Ningún objeto coincide con '{args.objeto}'")
    if len(matches) > 1:
        print(f"{len(matches)} objetos coinciden; sé más preciso:", file=sys.stderr)
        for info in matches[:50]:
            print(f"  {info.path}  ({info.name}, {info.kind_label})", file=sys.stderr)
        return 1
    _print_object(document, matches[0], args.profundidad)
    return 0


def command_roundtrip(document: Document, path: Path, output: Path | None) -> int:
    obsp = document.obsp
    started = time.perf_counter()
    recoded = {
        position: bod.encode(bod.decode(obsp.blob(position)))
        for position, entry in enumerate(obsp.entries)
        if not entry.is_script
    }
    data = rebuild(obsp, recoded)
    elapsed = time.perf_counter() - started
    sha = hashlib.sha256(data).hexdigest().upper()
    identical = data == obsp.data
    print(f"BOD recodificados: {len(recoded):,}")
    print(f"Original:      {obsp.sha256()}")
    print(f"Reconstruido:  {sha}")
    print(f"Resultado:     {'idéntico' if identical else 'DIFIERE'} ({elapsed:.2f} s)")
    if output is not None:
        if output.resolve() == path.resolve():
            raise D2ScriptViewerError("--salida no puede ser el propio archivo de entrada")
        if output.name.casefold().endswith(".original.obsp"):
            raise D2ScriptViewerError("No se escribe nunca encima de una copia *.original.obsp")
        if output.exists():
            raise D2ScriptViewerError(f"{output} ya existe; elige otra ruta")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        print(f"Escrito en {output}")
    return 0 if identical else 1


def command_verify(path: Path) -> int:
    data = path.read_bytes()
    report = verify_data(data)
    print(f"Archivo:  {path}")
    print(f"SHA-256:  {report.sha256}  ({_status_text(report.sha256)})")
    for check in report.checks:
        print(f"[{'OK' if check.ok else 'FALLO'}] {check.label}: {check.detail}")
    print(f"{'Todo correcto' if report.ok else 'HAY FALLOS'} ({report.seconds:.2f} s)")
    return 0 if report.ok else 1


def _tolerant_output() -> None:
    # En una tubería la consola de Windows usa cp1252, que no tiene «→» ni «↔».
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        from .gui.app import main as gui_main

        gui_main()
        return 0
    _tolerant_output()
    try:
        path = _resolve_path(args.archivo)
        if args.command == "verify":
            return command_verify(path)
        document = Document.open(path)
        if args.command == "info":
            return command_info(document, path)
        if args.command == "list":
            return command_list(document, args)
        if args.command == "show":
            return command_show(document, args)
        if args.command == "roundtrip":
            return command_roundtrip(document, path, args.salida)
        parser.error(f"subcomando desconocido: {args.command}")
    except D2ScriptViewerError as error:
        parser.exit(2, f"error: {error}\n")
    return 0
