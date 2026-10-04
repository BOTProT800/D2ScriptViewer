# Changelog

Todos los cambios relevantes de D2ScriptViewer se registran aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto sigue
[Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Added

- Base del repositorio: paquete `d2scriptviewer` con `python -m d2scriptviewer --version`,
  `pyproject.toml` sin dependencias, licencia MIT, cabeceras SPDX, `CREDITS.md` y `README.md`.
- CI de tests en Windows con Python 3.10–3.13, que comprueba que no hacen falta dependencias.
- Apoyo para tests con el archivo real: `D2SV_OBSP` o la ruta por defecto del juego; si no
  existe, esos tests se omiten.
