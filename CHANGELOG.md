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
- Núcleo de formato: contenedor OBSP (lector y escritor que regenera tabla de cadenas, índice
  y cabecera), BOD (árbol tipado con los 11 tags, decodificador y codificador canónico que
  conserva los bytes crudos de int32, float32 y bool), cabecera y símbolos de los scripts de
  tipo 0 y diccionario global hash↔cadena.
- Línea de órdenes: `info`, `list` (`--tipo`, `--clase`, `--filtro`), `show <ruta|nombre>`,
  `roundtrip` (`--salida`) y `verify`, con `--archivo` o `D2SV_OBSP`.
- Tests de oro con el archivo real (SHA reconstruido, 4 172 BOD idénticos, 3 690 cabeceras de
  script coherentes, 70 182 pares hash↔cadena) y tests sintéticos sin datos del juego.
