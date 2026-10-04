# Plan maestro: D2ScriptViewer — visor y editor de `scripts.obsp` (Darksiders II Deathinitive Edition, PC)

> Fase 2 cerrada (2026-10-03), pendiente del visto bueno del usuario (punto de control 1):
> visor de solo lectura en `gui/` (`app.py`, `object_tree.py`, `property_view.py`, `details.py`,
> `script_view.py`, más `search_view.py` y `theme.py`) sobre el núcleo nuevo `references.py`
> (índice "apunta a" / "usado por" y diccionario de hashes en una sola pasada) y `search.py`
> (búsqueda por ruta, nombre, carpeta, clase, valores, símbolos de script y, opcionalmente,
> nombres de campo, con prefiltro sobre los bytes crudos). Se abre con `python -m
> d2scriptviewer` o `D2ScriptViewer.pyw`. Abrir lee el archivo entero y lo cierra; indexar,
> buscar y decodificar objetos de más de 48 KB van en hilos con `queue`; los grupos del árbol
> de objetos y los hijos de las propiedades se cargan al abrirlos (listas de más de 500
> elementos, en tramos). Medido con el archivo real: abrir 0,38 s, índice listo en 1,8 s
> (3 406 referencias, 70 182 cadenas), **los 7 862 objetos mostrados uno a uno en 7,2 s: el peor
> 0,22 s y la media 0,9 ms**; búsqueda de metadatos 0,02 s y de valores 0,2–0,7 s. Ni el
> archivo ni su carpeta cambian (tamaño, fecha, SHA y listado comprobados por test). 74 tests.
> **Desviaciones:** los objetos se agrupan por carpeta del editor (o tipo) **y después por el
> directorio de la ruta**, porque 2 358 objetos no tienen carpeta y 4 075 cuelgan de `oc`;
> la hoja muestra el último tramo de la ruta. Las preferencias (archivo, geometría,
> agrupación) se guardan al cerrar en `%APPDATA%\D2ScriptViewer\config.json`, nunca junto al
> `.obsp`. Doble clic sobre un `FC` navega a su destino; Alt+←/→ recorre el historial.
>
> Fase 1 cerrada (2026-10-03): núcleo en `binary.py`, `formats/obsp.py` (lector y escritor que
> regenera tabla, índice y cabecera), `formats/bod.py` (árbol tipado, decodificador y codificador
> canónico), `formats/script.py` (cabecera y símbolos), `formats/hashes.py` (diccionario global),
> `document.py` (abrir y decodificar bajo demanda) y `verification.py`. CLI: `info`, `list`
> (`--tipo --clase --filtro`), `show <ruta|nombre>` (`--profundidad`), `roundtrip` (`--salida`) y
> `verify`; todas aceptan `--archivo`. Con el archivo real: reconstrucción con SHA `B46DD3DA…`
> (también recodificando los 4 172 BOD), 4 172 / 4 172 BOD idénticos, 3 690 / 3 690 cabeceras de
> script coherentes, 70 182 pares hash↔cadena sin conflictos, tablas de tipos y tags del apéndice
> exactas y 3 406 `FC` con destino. Tiempos (Python 3.12): leer y parsear el índice 30 ms,
> decodificar todos los BOD 1,75 s, codificarlos 0,55 s, `verify` completo 2,8 s. 53 tests
> (9 de oro con el archivo real; los sintéticos cubren los 11 tags, los modos 0/1 de lista, el
> modo 1 de mapa, clases nativas y de script, nombres nuevos y por referencia, nulos y `FC`).
> **Desviaciones:** los `idObjeto` se muestran en hexadecimal (`grupo:ID`); el módulo de
> comprobaciones se llama `verification.py` (no estaba en la sección 5); el decodificador
> rechaza modos de lista o mapa que no aparecen en el juego en lugar de suponer su significado.
> Hipótesis nueva, en `research/FORMATO.md`: `idObjeto` = hash del nombre en minúsculas
> (4 835 casos comprobables, ninguno en contra).
>
> Fase 0 cerrada (2026-10-03): repositorio git (rama `main`), paquete `d2scriptviewer` con
> `python -m d2scriptviewer --version` (0.1.0), `pyproject.toml` sin dependencias, LICENSE MIT,
> cabeceras SPDX, `CREDITS.md`, `README.md`, `CHANGELOG.md`, `.gitignore` con `*.obsp`,
> `build/` y `dist/`, CI en `.github/workflows/tests.yml` y apoyo para el archivo real en
> `tests/support.py` (`D2SV_OBSP` o ruta del juego; si falta, se omite). 5 tests en verde.
> **Desviación:** la CI no se ha ejecutado en GitHub porque no hay remoto ni push. Se reprodujo
> en local con Python 3.12.5 (el único instalado) y un test que parsea todo el código con
> `feature_version=(3, 10)` y comprueba que solo se importa la biblioteca estándar.
> Decisiones de la sección 12 confirmadas por el usuario el mismo día.
>
> Estado verificado localmente: 3 de octubre de 2026. Todavía no hay código en el
> proyecto. Los hallazgos de formato salen de un prototipo desechable ejecutado
> fuera del repositorio; todo lo que no está demostrado va marcado como
> **hipótesis**.

## 1. Objetivo

Construir una herramienta de escritorio que abra `scripts.obsp`, muestre su
contenido de forma legible, permita modificarlo y lo guarde en el mismo formato
`.obsp`, listo para que el juego lo cargue.

Prioridades, en este orden:

1. **Visualizar**: navegar los 7 862 objetos del archivo y ver sus datos.
2. **Modificar**: editar valores con validación, deshacer y lista de cambios pendientes.
3. **Guardar como `.obsp`**: reescribir el archivo con el formato original.
4. **Copia del original**: al guardar encima de `scripts.obsp`, crear antes una copia
   sin cambios del archivo original, verificada y que nunca se sobrescribe.

Objetivos secundarios, después del primer hito:

- Exportar a JSON (y CSV para las tablas).
- Desensamblar, y más adelante descompilar, los scripts compilados.

### Fuera del alcance del primer hito

- Editar bytecode de scripts (más adelante: solo parches de literales del mismo tamaño).
- Crear cadenas nuevas que necesiten hash, hasta identificar la función (fase 6).
- Recompilar scripts desde código fuente.
- Cargar el archivo como mod a través de Darksiders2DLL (ver apéndice B).
- Modificar `.upak`, `worlds.bin` u otros archivos del juego.

## 2. Estado local confirmado

### 2.1 Rutas

- Proyecto: `C:\Users\vicen\Documents\Proyectos\Software\D2ScriptViewer` (solo este plan y `CLAUDE.md`).
- Juego: `C:\Program Files (x86)\Steam\steamapps\common\Darksiders II Deathinitive Edition`.
- Archivo instalado: `media\scripts.obsp`, suelto (no está dentro de los `.upak`).
- Copias extraídas, idénticas al instalado (MD5 `063C0AE1D9696F2E13098569D441F460`):
  `C:\Users\vicen\Documents\Extractions\Darksiders\scripts.obsp`, `misc\scripts.obsp` y
  `misc\scripts_1.obsp`.
- Darksiders2DLL (`...\Software\Darksiders2DLL`): proxy `dinput8.dll` en C++. Ya redirige
  `mods/<mod>/media/scripts.obsp` en el modo `scripts=inventory`.
- Darkstractor (`...\Software\Darkstractor`): extractor en Python (solo biblioteca estándar)
  con tkinter. Trata `scripts.obsp` como copia exacta, sin interpretarlo.

### 2.2 Huellas

- `scripts.obsp`: 18 334 463 bytes, SHA-256
  `B46DD3DA7F17A0ED016E30AF523BFBA86D358C9920DFFA866C69D4A0F4F67C7C`
  (coincide con el registrado en Darksiders2DLL).
- `Darksiders2.exe`: SHA-256 `5580738EF70BC5BBCC72D7DC4A9C319956CD14DBFEF6F9DBEC54C1B5D97799FB`.

### 2.3 Lo que el prototipo ya demostró

| Prueba | Resultado |
|---|---|
| Reconstruir el `.obsp` completo desde sus partes (cabecera, cadenas, índice, datos) | Idéntico byte a byte, mismo SHA-256 |
| Decodificar los 4 172 objetos BOD a árbol y recodificarlos con un codificador canónico | 4 172 / 4 172 idénticos |
| Recalcular los contadores de la cabecera BOD (nº de nombres, longitud máxima) | 4 172 / 4 172 coinciden |
| Cabecera de los 3 690 scripts compilados (versión, símbolos, hash de ruta, grupo) | 3 690 / 3 690 coherentes |
| Misma cadena → mismo hash en contenedor, BOD y scripts | 70 182 pares, 0 conflictos |
| Cadenas no ASCII en todo el archivo | Ninguna |
| Rendimiento en Python 3.12 | Índice 15 ms · decodificar todo BOD 1,5 s · codificar 0,6 s |

Consecuencia: guardar en `.obsp` con ediciones de valores, e incluso con cambios
estructurales en BOD, es viable desde el principio. Lo único bloqueado es crear
cadenas **nuevas** (falta la función de hash).

### 2.4 Lo que todavía no se conoce

- **Función de hash de 64 bits.** Distingue mayúsculas de minúsculas. Ya descartados:
  - FNV-1 y FNV-1a 64, también en minúsculas, con NUL y en UTF-16.
  - CRC-64 ECMA, ISO y Jones (reflejados o no, con init/xorout 0 o ~0).
  - Multiplicativos comunes (31, 33, 65599…).
  - Mitades de 32 bits con CRC32, FNV-32, djb2 o sdbm.

  El FNV-1 64 que contiene el ejecutable pasa la cadena a minúsculas antes de hashear, así que no es este.
- El campo de la cabecera OBSP que vale `1` y el `u16 = 1` de la cabecera BOD.
- La semántica de muchos enteros: algunos son IDs o hashes de 32 bits (p. ej. `OnStateOne = 0x4DFA84A3`).
- El juego de opcodes completo del bytecode.

### 2.5 Pista importante para los scripts

El ejecutable incluye el compilador del lenguaje de scripts, un parser flex/bison:

- Tokens: `WHILE`, `BREAK`, `CONTINUE`, `RETURN`, `FUNCTION`, `NULLOBJECT`, `RAND_RANGE`,
  `CONTAINS`, `REMOVE`, `INT_CAST`, `ADD_ASSIGN`…
- Reglas: `if_statement`, `while_statement`, `iterator_statement`, `method_chain`,
  `property_chain`…
- Mensajes de error en tiempo de ejecución.

Con eso se puede reconstruir la gramática del lenguaje para un descompilador futuro.
Además, Darksiders2DLL ya documentó un patrón real del bytecode: `NumSlots\0`, `0x23`
+ int32 y luego `0x29 0x32` (`research/INVENTORY_SCRIPT.md`).

## 3. Decisiones de diseño

### 3.1 Tecnología: Python ≥ 3.10, solo biblioteca estándar, tkinter/ttk

Mismo stack y convenciones que Darkstractor:

- Cabeceras SPDX MIT y `CREDITS.md`. Las reglas para agentes que Darkstractor tiene en
  `AGENTS.md` aquí viven en `CLAUDE.md`.
- Tests con `unittest` y CI en Windows con Python 3.10–3.13.
- Ejecutable con PyInstaller.
- Interfaz en español con el mismo tema oscuro.

El rendimiento medido basta si se decodifica bajo demanda. Si se prefiere otro stack
(p. ej. C#/WPF), hay que decidirlo antes de la fase 0.

### 3.2 Principios

1. **Sin pérdidas.** Cada objeto conserva sus bytes originales y solo se recodifican los
   modificados. Guardar sin cambios produce exactamente el mismo archivo.
2. **Decodificar bajo demanda.** Abrir el archivo solo lee cabecera, cadenas e índice. Cada
   objeto se decodifica al seleccionarlo y queda en caché.
3. **Ediciones como comandos reversibles** (deshacer/rehacer). El documento sabe qué objetos
   están modificados.
4. **Validar antes de escribir.** Tipos, rangos (int32, float32), ASCII, longitudes (u16 en BOD)
   y existencia de las referencias.
5. **Verificar después de escribir.** El resultado se vuelve a parsear y comparar antes de darlo por bueno.
6. **Nunca tocar la copia del original.** Nunca se escribe en disco sin una acción explícita de guardar.
7. **Sin datos del juego en el repositorio.** Los tests usan fixtures sintéticos. Las pruebas con
   el archivo real solo se ejecutan si está presente.

## 4. Guardado y copia del original

### 4.1 Política de la copia

- Al guardar encima de `X.obsp`, si no existe `X.original.obsp` en la misma carpeta, se crea
  primero, copiando el archivo **tal como está en disco antes de guardar**.
- La copia se verifica (su SHA-256 debe ser igual al del archivo copiado) y se marca como solo lectura.
- Si ya existe, **no se toca nunca**: ni en guardados posteriores ni al restaurar.
- Si el SHA del archivo copiado es `B46DD3DA…`, la copia se etiqueta como "original de Steam".
  Si no, se avisa de que el archivo ya venía modificado, pero la copia se hace igualmente.
- La herramienta se niega a guardar encima de un `*.original.obsp`; para eso solo ofrece "Guardar como…".
- Opción activada por defecto: copia rotativa de la versión anterior en
  `.d2sv_backups\X.<fecha>.obsp`, conservando las últimas 5.

### 4.2 Secuencia de guardado

1. **Construir en memoria.** Los blobs sin cambios se copian tal cual y los modificados se
   recodifican. Se recalculan los offsets y tamaños del índice y se regeneran la tabla de cadenas y la cabecera.
2. **Autoverificar.** Se vuelve a parsear el resultado y se comprueba:
   - el mismo número de objetos e identidades (ruta, nombre, grupo, id, tipo);
   - que los blobs no modificados son idénticos;
   - que los modificados decodifican al árbol editado.
3. **Copia del original**, según la sección 4.1.
4. **Escribir.** Se escribe en `X.obsp.tmp` (misma carpeta), con `flush` + `fsync`, y se sustituye
   con `os.replace`, que es atómico en el mismo volumen. Un `.tmp` huérfano se limpia en el siguiente arranque.
5. **Comprobar.** Se relee el archivo final y su SHA-256 se compara con el de memoria.
6. **Fallos.** Si algo falla antes del paso 4, el archivo queda intacto. Si falla el paso 5, se
   informa y se ofrece restaurar desde la copia.

### 4.3 Casos especiales

- **Juego abierto.** El juego lee el archivo, y Darksiders2DLL lo fija con `FILE_SHARE_READ`
  mientras corre, así que la escritura fallará. Mensaje: "Cierra Darksiders II y vuelve a intentarlo".
- **Steam.** "Verificar integridad" o una actualización restauran el original. Al abrir, la
  herramienta muestra el estado del archivo: original de Steam, modificado o desconocido.
- **Darksiders2DLL con `scripts=inventory`.** Ese modo exige el `scripts.obsp` instalado original,
  comprobado por SHA. Con el instalado modificado se rechazará: hay que restaurar el original antes de usarlo.
- **Restaurar original.** Copia `X.original.obsp` encima de `X.obsp`, con verificación. La copia se conserva.

## 5. Arquitectura

```text
D2ScriptViewer/
├─ d2scriptviewer/
│  ├─ __init__.py          # __version__ (fuente única)
│  ├─ __main__.py          # python -m d2scriptviewer
│  ├─ binary.py            # lectura/escritura binaria little-endian
│  ├─ errors.py
│  ├─ formats/
│  │  ├─ obsp.py           # contenedor: cabecera, cadenas, índice, blobs; escritor
│  │  ├─ bod.py            # árbol BOD tipado; decodificador y codificador canónico
│  │  ├─ script.py         # tipo 0: cabecera y símbolos; luego desensamblador
│  │  └─ hashes.py         # diccionario hash↔cadena; función de hash (fase 6)
│  ├─ document.py          # archivo abierto: objetos, caché, modificados, undo/redo
│  ├─ edits.py             # comandos de edición y validación
│  ├─ references.py        # índice inverso de referencias FC ("usado por")
│  ├─ search.py            # búsqueda en segundo plano por ruta/nombre/clase/valor
│  ├─ saving.py            # pipeline de guardado, copia del original, restaurar
│  ├─ settings.py          # %APPDATA%\D2ScriptViewer\config.json
│  ├─ cli.py               # info, list, show, roundtrip, verify (export más adelante)
│  └─ gui/
│     ├─ app.py            # ventana, tema, menús, atajos, barra de estado
│     ├─ object_tree.py    # panel de objetos
│     ├─ property_view.py  # árbol de propiedades y editores
│     ├─ details.py        # metadatos, hex, referencias
│     └─ script_view.py    # símbolos y (más adelante) desensamblado
├─ tests/
├─ research/               # notas de formato y resultados de pruebas en el juego
├─ CLAUDE.md  CREDITS.md  LICENSE  README.md  CHANGELOG.md  pyproject.toml
└─ PLAN_MAESTRO.md
```

### 5.1 Modelo BOD

Nodos:

| Nodo | Tag |
|---|---|
| `Object(index, clase, campos)` | 07 |
| `Int32` | 02 |
| `Float32` | 03 |
| `Bool` | 04 |
| `RawString` | 05 |
| `Name` | 0F |
| `List` / `Pairs` | 09, modo 0 / 1 |
| `Map` | 0A |
| `Tuple` | 0B |
| `ExternalRef(grupo, id)` | FC |
| `Null` | FE |

Los números guardan sus 4 bytes originales. Un float solo se reempaqueta si se edita, así
que ningún valor sin tocar cambia por redondeo. El codificador:

- interna los nombres por (hash, texto) en orden de primera aparición;
- numera los objetos en orden de aparición;
- recalcula la cabecera.

Esas tres reglas reproducen los 4 172 blobs originales.

## 6. Interfaz

Tres zonas, con el estilo visual de Darkstractor:

- **Objetos (izquierda).** Árbol por carpeta del editor (`oc\Body\slayer`, `data\quests\Z1`…) o
  por ruta. Filtros por tipo (Desc, AnimationList, SoundList, script, FloatTable…) y por clase,
  y buscador. Los objetos modificados llevan una marca.
- **Propiedades (centro).** `ttk.Treeview` con columnas Nombre | Tipo | Valor, carga perezosa de
  hijos y edición en línea con doble clic.
- **Detalles (derecha/abajo).** Ruta, nombre, clase, carpeta, grupo, id, tipo, offset y tamaño.
  Pestañas: Hex | Referencias ("apunta a" / "usado por") | Script.
- **Barra de estado.** Estado del archivo (original / modificado), número de cambios pendientes y ruta.
- **Acciones.** Abrir (Ctrl+O), Guardar (Ctrl+S), Guardar como, Deshacer/Rehacer (Ctrl+Z / Ctrl+Y),
  Revertir objeto, Cambios pendientes, Restaurar original, Buscar (Ctrl+F) e Ir a referencia (doble clic).

Editores por tipo de valor:

| Tag | Editor | Fase |
|---|---|---|
| 02 int32 | Entrada con validación de rango y vista hexadecimal | 3 |
| 03 float32 | Entrada; muestra el valor ya redondeado a float32 | 3 |
| 04 bool | Casilla | 3 |
| 05 cadena sin hash | Texto libre ASCII (≤ 65 535) | 3 |
| 0F cadena con hash | Autocompletado entre las 70 182 cadenas conocidas; texto libre al resolver el hash | 3 / 6 |
| FC referencia | Selector de objetos del índice; navegable | 3 |
| 09 / 0A / 0B contenedores | Duplicar, eliminar y reordenar elementos | 5 |
| FE nulo / 07 objeto | Poner a nulo; crear duplicando un objeto existente de la misma clase | 5 |
| Scripts (tipo 0) | Solo lectura; luego parches de literales del mismo tamaño | 7 |

## 7. Fases

### Fase 0 — Base del repositorio

- `git init`, estructura del árbol, `pyproject.toml` sin dependencias, LICENSE MIT, cabeceras SPDX.
- `CLAUDE.md` (ya creado) con las reglas de Darkstractor (créditos, SPDX, licencias), `CREDITS.md`,
  `README.md` y `CHANGELOG.md`.
- `.gitignore` que excluya `*.obsp`, `build/` y `dist/`.
- CI de tests en Windows (3.10–3.13) que compruebe que no hacen falta dependencias externas.
- Apoyo para tests con el archivo real: variable `D2SV_OBSP` o ruta por defecto del juego. Si no existe, el test se omite.

**Hecho cuando** `python -m d2scriptviewer --version` funciona y la CI pasa.

### Fase 1 — Núcleo de formato (sin GUI)

- `obsp.py`: cabecera, tabla de cadenas, índice y acceso a blobs; escritor que regenera tabla, índice y cabecera.
- `bod.py`: decodificador a árbol y codificador canónico (11 tags).
- `script.py`: cabecera y tabla de símbolos de los scripts.
- `hashes.py`: diccionario global hash↔cadena.
- CLI: `info`, `list [--tipo --clase --filtro]`, `show <ruta|nombre>` (árbol en texto), `roundtrip` y `verify`.

**Hecho cuando**, con el archivo real:

- la reconstrucción da el SHA `B46DD3DA…`;
- los 4 172 BOD salen idénticos;
- las 3 690 cabeceras de script son coherentes;
- los tests sintéticos cubren todos los tags.

### Fase 2 — Visor (solo lectura)

- Ventana, árbol de objetos, filtros, propiedades, detalles con hex y símbolos de scripts.
- Índice de referencias FC con navegación "ir a" / "usado por".
- Búsqueda global en segundo plano: rutas, nombres, clases y valores.
- Abre el archivo leyéndolo entero y cerrándolo: no lo bloquea ni escribe nada.

**Hecho cuando** se navega todo el archivo, cualquier objeto se muestra en menos de 1 s y no
se escribe nada en disco.

### Fase 3 — Edición de valores

- Editores de la sección 6 para 02, 03, 04, 05, 0F (con cadenas conocidas) y FC.
- Deshacer/rehacer, revertir objeto, marca de modificado y panel "Cambios pendientes"
  (antes → después, por objeto).
- Aviso al editar campos con aspecto de identificador (`ID`, `*ID`, enteros que parecen hashes).

**Hecho cuando** editar y deshacer deja el blob idéntico y cada edición cambia solo su blob.

### Fase 4 — Guardado `.obsp` y copia del original (cierra el primer hito)

- Todo lo de la sección 4: Guardar, Guardar como, Restaurar original, copias rotativas, estado del
  archivo y mensajes para archivo bloqueado o sin permisos.
- Protocolo en el juego, con resultados en `research/PRUEBAS_EN_JUEGO.md`:
  1. Cambiar un valor de efecto evidente sin alterar el tamaño del blob y comprobar el efecto en
     el juego. Candidatos, a confirmar con el visor de la fase 2: una fila de `tables\Char_Death`
     o un float del `Desc` de Death.
  2. Hacer un cambio que altere el tamaño de un blob (p. ej. una cadena 05 más larga) para validar
     que el juego acepta los offsets recalculados.
  3. Restaurar el original y verificar el SHA `B46DD3DA…`.

**Hecho cuando** el juego carga un `scripts.obsp` guardado por la herramienta y refleja la
edición, y la copia del original es idéntica al archivo previo.

### Fase 5 — Edición estructural de BOD

- Duplicar, eliminar y reordenar elementos de listas y pares de mapas; poner a nulo; duplicar objetos.
- La renumeración de objetos y los contadores ya los resuelve el codificador.
- Validaciones: IDs únicos donde existan y referencias FC válidas.

### Fase 6 — Investigación: función de hash

- Banco de pruebas: los 70 182 pares conocidos sirven como vectores.
- Vías posibles:
  - **Offline:** más candidatos (CityHash, MurmurHash64A/3, xxHash64, SpookyHash, FarmHash, lookup3…).
    Cualquier implementación ajena se registra en `CREDITS.md`.
  - **Análisis estático** de `Darksiders2.exe` (Ghidra / x64dbg), partiendo del lector del OBSP
    (la cadena `scripts.obsp` está en el ejecutable) o del intérprete.
  - **Instrumentación** con Darksiders2DLL, registrando pares cadena → hash en tiempo de ejecución.
- Resultado: `hashes.py` con la función y sus tests. Habilita cadenas nuevas y renombrados.

### Fase 7 — Scripts compilados

1. Formalizar la estructura del cuerpo: tablas de miembros y funciones, rangos de código.
2. Desensamblador de solo lectura. La tabla de opcodes se deduce estadísticamente sobre los 3 690
   scripts y se contrasta con el intérprete del ejecutable. Vista por función con líneas y nombres.
3. Parches de literales del mismo tamaño, generalizando el parche `NumSlots` de Darksiders2DLL:
   editar operandos `0x23` (int) y equivalentes sin cambiar tamaños.
4. A largo plazo: descompilador a pseudocódigo usando la gramática del compilador incluido en el
   ejecutable. Las ediciones que cambien el tamaño solo serán posibles cuando se entiendan los saltos.

### Fase 8 — Exportación y parches (secundaria)

- **JSON por objeto**: árbol con tipos y valores, con las referencias resueltas a `"ruta/nombre"`
  además de grupo/id. Las carpetas reflejan la ruta, y un `manifest.json` recoge el índice.
- **CSV** para `FloatTable` y tablas similares.
- **Archivo de parche** (`.d2svpatch.json`) con la lista de ediciones (objeto + ruta de propiedad
  + valor). Sirve para reaplicar los cambios tras una restauración de Steam y para compartirlos
  sin distribuir el archivo del juego.
- Opcional: importar desde JSON, en un formato reversible.

### Fase 9 — Distribución

- Ejecutable con PyInstaller y workflow de release como el de Darkstractor.
- README con guía de uso y advertencias (copia del original, juego cerrado, Steam).

## 8. Estrategia de pruebas

### Unitarias (sin el juego, en CI)

- **Fixtures sintéticos** construidos con el propio codificador: un OBSP mínimo con varios tipos de
  objeto que cubra los 11 tags, listas en modo 0 y 1, clases nativas y de script, nombres nuevos y
  por referencia, nulos y referencias externas.
- **Invariantes**: decodificar y volver a codificar da lo mismo; la cabecera se recalcula; los
  offsets son contiguos; la tabla de cadenas queda en orden de primera aparición.
- **Ediciones**: cada tipo de valor y sus límites (int32, float32 NaN/inf, ASCII, longitud), deshacer/rehacer.
- **Guardado**:
  - la copia se crea una sola vez, verificada, y nunca se sobrescribe;
  - un fallo simulado a mitad deja el original intacto;
  - un archivo bloqueado (handle abierto sin compartir escritura) produce un error claro;
  - se rechaza guardar encima de `*.original.obsp`.

### Con el archivo real (se omiten si no está)

- Reconstrucción idéntica (SHA `B46DD3DA…`), 4 172 BOD idénticos y 3 690 scripts coherentes.
- Editar un valor cambia solo ese blob y los offsets posteriores del índice (diff estructural).
- Editar y revertir deja el archivo idéntico.

### GUI

- Prueba de humo: crear la ventana, cargar un fixture, seleccionar un objeto, editar un valor y cerrar.

### En el juego (manual)

- El protocolo de la fase 4, con resultados en `research/`.

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Función de hash desconocida | Editar solo cadenas ya conocidas o sin hash (tag 05) hasta la fase 6 |
| Semántica desconocida de algunos valores (IDs, hashes, enums) | Mostrar el dato crudo, avisar en campos tipo ID, hacer cambios pequeños y probarlos en el juego |
| El juego valida algo que no vemos | No hay checksum aparente en la cabecera; pasos 1 y 2 del protocolo de la fase 4 |
| Otro archivo depende de offsets del `.obsp` (improbable) | Paso 2 del protocolo (cambio de tamaño) |
| Corromper el archivo instalado | Copia del original, escritura atómica, verificación posterior y Restaurar original |
| Juego abierto o DLL que fija el archivo | Detectar el error y pedir que se cierre el juego |
| Steam restaura el archivo | Mostrar el estado al abrir; reaplicar con el archivo de parche (fase 8) |
| `scripts=inventory` de la DLL rechaza el archivo instalado modificado | Documentarlo; restaurar el original antes de usar ese modo |
| Redondeo de floats | Conservar los bytes crudos y reempaquetar solo los valores editados |
| Objetos grandes en tkinter (hasta 350 KB, `base/itemfoleytable`) | Hijos perezosos en el árbol y búsqueda en un hilo aparte |
| Contenido del juego en el repositorio | `.gitignore` con `*.obsp` y fixtures sintéticos |

## 10. Criterios de finalización del primer hito

- Abre el `scripts.obsp` del juego o una copia y permite navegar los 7 862 objetos.
- Muestra las propiedades de los objetos BOD y los metadatos y símbolos de los scripts.
- Edita int, float, bool, cadenas sin hash, cadenas conocidas y referencias, con deshacer.
- Guarda en `.obsp`. El primer guardado crea `scripts.original.obsp` idéntico al archivo previo
  (SHA verificado) y los siguientes no lo tocan.
- Los objetos no editados quedan idénticos byte a byte, y editar y revertir devuelve el archivo idéntico.
- El juego carga el archivo guardado y refleja un cambio comprobable. Restaurar original devuelve el SHA `B46DD3DA…`.

## 11. Orden inmediato recomendado

1. Confirmar las decisiones abiertas (sección 12).
2. Fases 0 y 1, portando el prototipo con sus tests.
3. Fase 2 (visor), luego fases 3 y 4 (edición y guardado).
4. Prueba en el juego.
5. Fases 5 a 9 según interés.

## 12. Decisiones

Confirmadas por el usuario el 3 de octubre de 2026:

| Decisión | Estado |
|---|---|
| Stack | **Decidido:** Python ≥ 3.10, solo biblioteca estándar, tkinter/ttk (el usuario tiene Python 3.12.5 con Tk 8.6) |
| Nombre de la copia | **Decidido:** `scripts.original.obsp`, junto al archivo que se guarda |
| Copias rotativas de la versión anterior | **Decidido:** activadas, las últimas 5, en `.d2sv_backups\` |
| Licencia y autoría | **Decidido:** MIT, BOTProT800 |
| Repositorio público | Abierta; el archivo del juego nunca se versiona |

## 13. Prompt de contexto para retomar el proyecto

> D2ScriptViewer es un visor/editor en Python (solo stdlib, tkinter) para
> `media\scripts.obsp` de Darksiders II Deathinitive Edition (18 334 463 bytes,
> SHA-256 `B46DD3DA…`). Prioridad: visualizar → editar → guardar al mismo
> formato `.obsp`, creando antes `scripts.original.obsp` (una sola vez,
> verificada, nunca sobrescrita). Exportar a JSON es secundario. El formato
> está en el apéndice A de `PLAN_MAESTRO.md`: el contenedor y los 4 172 objetos
> BOD se reconstruyen byte a byte; la función de hash de 64 bits sigue sin
> identificarse. Proyectos relacionados: Darksiders2DLL (C++, redirige
> `scripts.obsp` en `scripts=inventory`) y Darkstractor (Python, mismo estilo).
> Consulta la sección 7 para saber en qué fase está el proyecto.

## 14. Créditos y procedencia

El conocimiento del formato procede del análisis local del 3 de octubre de 2026 y de
`Darksiders2DLL/research/INVENTORY_SCRIPT.md` (trabajo propio: offsets y patrón de `NumSlots`).
No se ha usado código ni documentación de terceros. Si se incorpora cualquier implementación
externa (p. ej. de funciones de hash en la fase 6), se registrará en `CREDITS.md` según las reglas
de `CLAUDE.md`.

---

## Apéndice A — Especificación verificada

Todos los enteros son little-endian. Los "hash" son u64 de la función desconocida,
salvo el 0, que corresponde a la cadena vacía.

### A.1 Contenedor OBSP

| Offset | Tamaño | Campo | Valor en el original |
|---|---|---|---|
| 0x00 | 4 | Firma `OBSP` | |
| 0x04 | 1 | Byte `0x00` | 0 |
| 0x05 | 4 | Versión | 10 |
| 0x09 | 4 | Desconocido | 1 |
| 0x0D | 4 | Número de objetos | 7 862 |
| 0x11 | 4 | Fin de la tabla de cadenas (= inicio del índice) | 0x9C0E6 |
| 0x15 | 4 | Número de cadenas | 15 520 |
| 0x19 | 4 | Longitud máxima de cadena | 74 |
| 0x1D | … | Tabla de cadenas: `{ u64 hash; u32 len; char[len] }`, ASCII sin NUL | |
| 0x9C0E6 | 51 × n | Índice | |
| 0xFDF28 | … | Datos: blobs contiguos en el orden del índice, sin relleno; el último acaba en EOF | |

- La tabla de cadenas contiene, sin repetir y en orden de primera aparición, las cadenas
  (ruta, nombre, carpeta, clase) al recorrer el índice. Incluye la cadena vacía.
- Entrada del índice, 51 bytes, empaquetada (`<QQIIHBQQQ`):

```text
u64 hashRuta     ruta del objeto, p. ej. "sh_plinth/plinth_desc"
u64 idObjeto     identidad; junto con el grupo es lo que usan las referencias FC
u32 offset       absoluto en el archivo
u32 tamaño
u16 grupo        626 valores distintos (10000–11818)
u8  tipo         categoría del blob (tabla siguiente)
u64 hashNombre   p. ej. "Plinth_Desc"
u64 hashCarpeta  carpeta del editor, p. ej. "oc\Body\slayer" (160 distintas; 0 = ninguna)
u64 hashClase    clase nativa o ruta de clase de script; 0 en los tipos 0, 9 y 15
```

| Tipo | Contenido | Objetos | Bytes |
|---|---|---|---|
| 0 | Script compilado | 3 690 | 5 795 617 |
| 1 | Instancias de clases de script, `ItemGeneratorTable`, `Quest`, `DialogSet`… | 757 | 1 525 649 |
| 2 | `CharacterMoveStateList` | 275 | 1 945 850 |
| 3 | `SoundList` | 275 | 830 826 |
| 4 | `AnimationList` | 1 071 | 3 603 893 |
| 5 | `CharacterConditionalList` | 7 | 64 591 |
| 6 | `InputWindowList` | 5 | 53 506 |
| 7 | `HitInfoList` | 3 | 64 617 |
| 8 | `*Desc` (actores, personajes, proyectiles, ítems…) | 1 668 | 2 686 596 |
| 9 | `ModuleSystem` (grafos de módulos) | 4 | 47 565 |
| 14 | `TerrainMaterialDesc` | 42 | 25 559 |
| 15 | `FloatTable` | 65 | 650 026 |

### A.2 Blob BOD (todos los tipos salvo el 0)

Cabecera, 16 bytes:

```text
"BOD\xFD"   u16 versión = 4   u16 = 1 (desconocido)
u32 número de entradas de la tabla interna de nombres
u32 longitud máxima de nombre
```

Después vienen la **clase raíz** y sus **campos**.

- **Nombre** (token internado):
  - `01` + u64 hash + u16 len + char[len]: se añade a la tabla;
  - `00` + u32 índice: referencia a una entrada ya definida.

  Nombres de campo, nombres de clase y cadenas `0F` comparten la misma tabla.
- **Clase**:
  - `01` + nombre: clase nativa;
  - `04` + u32 grupo + nombre: clase de script.
- **Campos**: u32 n, seguido de n × { nombre, valor }.
- **Valor**: u8 tag + carga útil:

| Tag | Tipo | Carga útil | Apariciones |
|---|---|---|---|
| 02 | int32 con signo | 4 bytes | 196 222 |
| 03 | float32 | 4 bytes | 127 484 |
| 04 | bool | u8 | 34 997 |
| 05 | cadena sin hash | `FF` + u16 len + char[len] | 2 865 |
| 07 | objeto | u32 índice (secuencial desde 0, en orden de aparición) + clase + campos | 146 328 |
| 09 | lista | u32 n + u8 modo (0: n valores; 1: n pares clave/valor) | 37 046 |
| 0A | mapa | u32 n + u8 modo (siempre 1 aquí) + pares | 39 |
| 0B | tupla | u32 n + n valores | 1 716 |
| 0F | cadena con hash | nombre (token internado) | 151 488 |
| FC | referencia externa | u32 grupo + u64 idObjeto | 3 406 |
| FE | nulo | sin carga | 220 |

Reglas del codificador canónico, verificadas sobre los 4 172 blobs:

- se interna por (hash, texto) en el orden de un recorrido en profundidad: clase antes que
  campos, nombre del campo antes que su valor;
- los objetos se numeran en ese mismo orden;
- los dos contadores de la cabecera se recalculan.

### A.3 Script compilado (tipo 0)

Verificado en los 3 690 scripts:

```text
u32 versión = 1
u32 número de símbolos
u32 longitud máxima de símbolo
símbolos: { u64 hash; u32 len; char[len] }
u64 hashRuta   (= el del índice)
u32 grupo      (= el del índice)
```

**Hipótesis**, observadas en muestras y pendientes de formalizar en la fase 7:

- Detrás vienen el hash del nombre corto, el hash de la clase base y tablas de miembros y
  funciones; cada función lleva su hash, un u32 con el tamaño del código y el bytecode.
- El bytecode es de pila y lleva los nombres en línea:

| Opcode | Significado | Formato |
|---|---|---|
| `0x3B` | número de línea | u32 |
| `0x23` | literal int32 | i32 |
| `0x28` / `0x2C` | variable | u8 len + u64 hash + nombre\0 |
| `0x3A` | miembro o método | u8 len + u64 hash + nombre\0 |
| `0x39` | llamada por nombre | |
| `0x29` | ¿asignación? | |
| `0x32` | ¿fin de sentencia? | |
| `0x2F` | ¿fin de función? | |

## Apéndice B — Interacción con Darksiders2DLL

- El juego lee `media\scripts.obsp` directamente. Sobrescribirlo, con su copia del original, no
  necesita la DLL.
- La DLL 0.7.0 solo redirige `mods/<mod>/media/scripts.obsp` si:
  - el instalado es el original (SHA `B46DD3DA…`);
  - el mod cambia únicamente los siete enteros `NumSlots` de `death/death`.

  Cualquier otra edición se rechaza.
- Integración posible a futuro, fuera de este plan: una acción "Guardar como mod" en
  D2ScriptViewer más un modo general en la DLL que valide la estructura OBSP. La DLL podría
  reutilizar las comprobaciones de la sección 4.2. Así no habría que tocar el archivo instalado
  y se convivía con Steam.
