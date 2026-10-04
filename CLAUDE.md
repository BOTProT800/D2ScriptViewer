# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

D2ScriptViewer es un visor/editor de escritorio para `media\scripts.obsp` de Darksiders II
Deathinitive Edition (PC). El usuario fijó este orden de prioridades:

1. Visualizar.
2. Modificar.
3. Guardar en el mismo formato `.obsp`, creando antes una copia intacta del original.

Exportar a JSON es secundario.

`PLAN_MAESTRO.md` es la fuente de verdad: fases, decisiones, pruebas y riesgos. Su
**apéndice A** contiene la especificación verificada del formato. Léelo antes de implementar.
Cuando se cierre una fase o cambie una decisión, actualízalo con una nota fechada al
principio, como hace el plan de Darksiders2DLL.

Estado al 3 de octubre de 2026: fase 0 cerrada (base del repositorio); en curso el primer
hito (fases 0 a 4). Las decisiones de la sección 12 del plan están confirmadas: Python ≥ 3.10
con tkinter/ttk, copia llamada `scripts.original.obsp` junto al archivo, copias rotativas (las
últimas 5, en `.d2sv_backups\`) y licencia MIT a nombre de BOTProT800.

El usuario escribe en español. La interfaz, los comentarios y la documentación van en
español; los identificadores, en inglés (estilo de Darkstractor).

## Comandos

Ya existen:

```powershell
python -m d2scriptviewer --version
python -m unittest discover -s tests -v                     # todos los tests
python -m unittest tests.<modulo>.<Clase>.<test>            # un solo test
$env:D2SV_OBSP = 'C:\ruta\a\scripts.obsp'                   # activa los tests con el archivo real
```

Previstos (aún no existen):

```powershell
python -m d2scriptviewer                                    # GUI
python -m d2scriptviewer info|list|show|roundtrip|verify    # CLI de la fase 1
```

Solo biblioteca estándar, sin dependencias externas. La CI (Windows, Python 3.10–3.13)
lo comprueba importando los módulos sin instalar nada. Los tests que necesitan el
archivo real buscan `D2SV_OBSP` o la ruta por defecto del juego, y se omiten si no lo
encuentran.

## Arquitectura

### Formato (detalle en el apéndice A del plan)

- **Contenedor OBSP**, en este orden:
  1. Cabecera de 29 bytes.
  2. Tabla de cadenas `{u64 hash, u32 len, chars}`: sin repetidos, en orden de primera
     aparición de (ruta, nombre, carpeta, clase) al recorrer el índice.
  3. Índice de 51 bytes por objeto (`<QQIIHBQQQ`): hashRuta, idObjeto, offset, tamaño,
     grupo, tipo, hashNombre, hashCarpeta, hashClase.
  4. Blobs contiguos y sin relleno hasta el EOF.

  Al escribir se regeneran la tabla, los offsets y la cabecera.
- **Identidad de un objeto**: el par (grupo, idObjeto). Las referencias entre objetos
  (tag `FC`) usan ese par, nunca offsets.
- **Blobs BOD** (todos los tipos salvo el 0): un árbol que se describe a sí mismo, con una
  tabla de nombres internada propia de cada blob:
  - `01` = nombre nuevo con su hash; `00` = índice a un nombre ya definido.
  - Comparten esa tabla los nombres de campo, los de clase y las cadenas `0F`.

  Tags: `02` int32 · `03` float32 · `04` bool · `05` cadena sin hash · `07` objeto ·
  `09` lista (modo 0) o pares (modo 1) · `0A` mapa · `0B` tupla · `0F` cadena con hash ·
  `FC` referencia externa · `FE` nulo.
- **Codificador canónico**, que reproduce byte a byte los 4 172 blobs:
  - interna por (hash, texto) en un recorrido en profundidad: la clase antes que los
    campos y el nombre antes que el valor;
  - numera los objetos `07` en ese mismo orden;
  - recalcula los dos contadores de la cabecera.
- **Scripts compilados (tipo 0)**: una tabla de símbolos propia, el hash de ruta, el grupo y
  después un bytecode de pila con los nombres y los números de línea en línea. La estructura
  del cuerpo está sin formalizar, así que se tratan como bytes opacos de solo lectura hasta
  la fase 7.
- **Hash de 64 bits**: la función es desconocida. Distingue mayúsculas de minúsculas y es la
  misma en el contenedor, los BOD y los scripts. Lo ya descartado está en la sección 2.4 del plan.

### Flujo de la aplicación (sección 5 del plan)

- **Abrir** solo lee cabecera, cadenas e índice. Cada objeto se decodifica al seleccionarlo
  y se guarda en caché.
- **Editar**: cada edición es un comando reversible sobre el árbol y marca su objeto como modificado.
- **Guardar**:
  1. Construir en memoria: los blobs intactos se copian tal cual y los modificados se recodifican.
  2. Volver a parsear el resultado y verificarlo.
  3. Crear la copia del original.
  4. Escribir un `.tmp`, hacer `fsync` y sustituir con `os.replace`.
  5. Releer el archivo y comparar su SHA-256 con el de memoria.

## Invariantes que no se pueden romper

- **Sin pérdidas.** Un objeto no editado conserva sus bytes exactos, y editar y revertir
  devuelve el archivo idéntico. El original mide 18 334 463 bytes y su SHA-256 es
  `B46DD3DA7F17A0ED016E30AF523BFBA86D358C9920DFFA866C69D4A0F4F67C7C`; reconstruirlo sin
  cambios debe dar ese mismo SHA.
- Los int32 y float32 guardan sus 4 bytes crudos. Un float solo se reempaqueta si se edita.
- **Copia del original.** Al guardar encima de `X.obsp` se crea `X.original.obsp` una sola vez:
  es la copia del archivo tal como estaba, verificada por SHA-256 y en solo lectura. Nunca se
  sobrescribe ni se borra, y no se permite guardar encima de un `*.original.obsp`.
- **No crear cadenas nuevas con hash** hasta resolver la función (fase 6). Solo se admiten
  cadenas ya presentes en el archivo (hay 70 182 pares hash↔cadena) o cadenas sin hash (tag `05`).
- Las cadenas son solo ASCII (el original no tiene ninguna que no lo sea) y su longitud cabe en u16.
- No se escribe en la instalación del juego fuera del guardado explícito. Los experimentos
  se hacen sobre copias.
- **Ningún dato del juego entra en el repositorio** (`*.obsp`, volcados, extractos). Los tests
  usan fixtures sintéticos generados con el propio codificador.

## Convenciones heredadas de Darkstractor

- Todo `.py` y `.pyw` empieza con estas dos líneas, antes de `from __future__ import annotations`:

  ```python
  # SPDX-FileCopyrightText: 2026 BOTProT800
  # SPDX-License-Identifier: MIT
  ```

- **Licencia MIT y créditos.** Todo material de procedencia externa se registra en
  `CREDITS.md` **en el mismo cambio** en que entra. Cuenta como externo: código, herramientas,
  formatos documentados por terceros y notas de ingeniería inversa ajenas.
  - El formato de cada entrada y las secciones son los de `..\Darkstractor\AGENTS.md`.
  - Las entradas nunca se borran: se mueven a `## History`.
  - Si falta el autor o la licencia, pregunta antes de cerrar la entrada.
  - Nada con copyleft (GPL, LGPL, AGPL, MPL) sin consultar antes.
  - Al terminar, informa en una línea qué entrada añadiste o cambiaste.
- La versión vive solo en `d2scriptviewer/__init__.py`.
- La GUI usa tkinter/ttk con el tema oscuro de `..\Darkstractor\darkstractor\gui.py`. El
  trabajo pesado va en hilos que se comunican con la GUI mediante `queue`. Los ajustes se
  guardan en `%APPDATA%\D2ScriptViewer\config.json`.
- Los hallazgos de investigación y los resultados de las pruebas en el juego van en `research/*.md`.

## Entorno y proyectos relacionados

- **Juego**: `C:\Program Files (x86)\Steam\steamapps\common\Darksiders II Deathinitive Edition`.
  `media\scripts.obsp` está suelto, no dentro de los `.upak`. El SHA-256 de
  `Darksiders2.exe` es `5580738EF70BC5BBCC72D7DC4A9C319956CD14DBFEF6F9DBEC54C1B5D97799FB`.
- **Copia para experimentos**: `C:\Users\vicen\Documents\Extractions\Darksiders\scripts.obsp`,
  idéntica al original.
- **`..\Darksiders2DLL`** (C++, proxy `dinput8.dll`):
  - Mientras el juego corre fija `scripts.obsp` con `FILE_SHARE_READ`, así que guardar fallará.
  - Su modo `scripts=inventory` exige que el `scripts.obsp` instalado sea el original (por SHA).
  - `research/INVENTORY_SCRIPT.md` documenta el único patrón de bytecode confirmado:
    `NumSlots\0`, `0x23` + int32 y luego `0x29 0x32`, con offsets en `death/death`.
- **`..\Darkstractor`** (Python stdlib + tkinter): referencia de estilo, estructura del
  repositorio, CI y tests.
- **Para la fase 7**: `Darksiders2.exe` contiene el compilador del lenguaje de scripts, con
  las cadenas flex/bison de sus tokens y reglas de gramática.
