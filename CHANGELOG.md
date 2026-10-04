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
- Visor de solo lectura (`python -m d2scriptviewer` o `D2ScriptViewer.pyw`): árbol de objetos
  por carpeta, ruta o tipo con filtros por tipo, clase y texto; propiedades con columnas
  Nombre, Tipo y Valor; detalles con metadatos, hexadecimal, referencias ("apunta a" / "usado
  por") y símbolos de los scripts; búsqueda global (Ctrl+F); doble clic en una referencia
  para ir a su destino e historial con Alt+←/→. El trabajo pesado corre en hilos y los árboles
  se cargan al abrirlos, así que ningún objeto tarda más de 0,25 s en mostrarse.
- Edición de valores en el visor: enteros, floats, bools, cadenas sin hash, cadenas ya
  presentes en el archivo (con autocompletado) y referencias (con un selector de objetos).
  Doble clic, F2 o Intro editan en la celda con validación y una pista en vivo (hexadecimal,
  redondeo a float32, hash de la cadena); deshacer y rehacer (Ctrl+Z / Ctrl+Y); revertir una
  propiedad o un objeto; ventana «Cambios pendientes» (Ctrl+P) con antes → después; marcas de
  modificado en el árbol, las propiedades, el título y la barra de estado; aviso y
  confirmación al editar campos con aspecto de identificador o de hash.
