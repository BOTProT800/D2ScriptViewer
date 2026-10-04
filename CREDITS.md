# Créditos

D2ScriptViewer es obra original de **BOTProT800**, publicada con la Licencia MIT (ver
[LICENSE](LICENSE)). Este archivo registra todo lo de procedencia externa que haya influido en el
proyecto, según la política de [CLAUDE.md](CLAUDE.md), que hereda el formato de
`AGENTS.md` de Darkstractor.

## Estado de redistribución

**Este repositorio no redistribuye binarios ni código de terceros.** Comprobado el 2026-10-03:

- [pyproject.toml](pyproject.toml): `dependencies = []`. Todos los `import` del paquete se
  resuelven a la biblioteca estándar de Python; `tests/test_repository.py` lo comprueba.
- [.gitignore](.gitignore) excluye `*.obsp`: ningún dato del juego entra en el repositorio. Los
  tests usan fixtures sintéticos generados con el propio codificador.

## Procedencia propia (no externa)

Lo siguiente es trabajo del mismo autor y no requiere entrada, pero se deja constancia:

- **Formato OBSP, BOD y cabecera de scripts:** análisis local del 3 de octubre de 2026,
  documentado en el apéndice A de [PLAN_MAESTRO.md](PLAN_MAESTRO.md).
- **Patrón `NumSlots` del bytecode:** `Darksiders2DLL/research/INVENTORY_SCRIPT.md`.
- **Función de hash de 64 bits** (fase 6, 2026-10-04): un CRC-64 reflejado, algoritmo de manual
  implementado en `formats/hashes.py` sin copiar código de nadie. Sus parámetros (polinomio
  `0x0060034000F0D50B`, valor inicial y XOR final `~0`) se dedujeron analizando los pares
  hash↔cadena del propio archivo (`research/FORMATO.md`).
- **Tema oscuro, estructura del repositorio, CI y preferencias:** Darkstractor.

## Tools

Ninguna.

## Adapted code

Ninguno.

## References and documentation

Ninguna.

## History

Sin entradas.
