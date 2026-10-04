# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Rutas por defecto y preferencias del usuario, guardadas fuera del repositorio y del juego."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Darksiders II Deathinitive Edition")
DEFAULT_OBSP = DEFAULT_GAME / "media" / "scripts.obsp"

#: Variable de entorno que apunta a un scripts.obsp concreto (tests y CLI).
OBSP_ENV = "D2SV_OBSP"

#: Solo se conserva lo que el usuario elige a mano. Cualquier otra clave del
#: archivo se descarta al leer, para que una versión anterior o un fichero
#: manipulado no inyecten estado en la aplicación.
KNOWN_KEYS = frozenset({"last_file", "rotating_backups", "geometry", "group_by"})


def find_default_obsp() -> Path | None:
    """Devuelve el scripts.obsp de ``D2SV_OBSP`` o el del juego, si existe."""
    candidates = []
    value = os.environ.get(OBSP_ENV)
    if value:
        candidates.append(Path(value))
    candidates.append(DEFAULT_OBSP)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def config_path() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    return root / "D2ScriptViewer" / "config.json"


def load_settings(path: Path | None = None) -> dict[str, object]:
    """Lee las preferencias; si no hay o están corruptas, devuelve un dict vacío.

    Nunca lanza: que la configuración falle no puede impedir que la aplicación
    arranque.
    """
    try:
        data = json.loads((path or config_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {key: value for key, value in data.items() if key in KNOWN_KEYS}


def save_settings(values: dict[str, object], path: Path | None = None) -> None:
    """Guarda las preferencias. Un fallo de escritura se ignora en silencio."""
    destination = path or config_path()
    temporary = destination.with_name(destination.name + ".partial")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: value for key, value in values.items() if key in KNOWN_KEYS}
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, destination)
    except OSError:
        temporary.unlink(missing_ok=True)
