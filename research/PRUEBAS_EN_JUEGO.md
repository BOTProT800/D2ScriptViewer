# Pruebas en el juego

Protocolo de la fase 4 de `PLAN_MAESTRO.md`: comprobar que Darksiders II carga un
`scripts.obsp` guardado por D2ScriptViewer, que refleja la edición y que acepta offsets
recalculados. Las pruebas las hace el usuario con la propia herramienta sobre el archivo
instalado; aquí se registran los resultados.

- **Juego:** Darksiders II Deathinitive Edition (Steam), `Darksiders2.exe` con SHA-256
  `5580738EF70BC5BBCC72D7DC4A9C319956CD14DBFEF6F9DBEC54C1B5D97799FB`.
- **Archivo de partida:** `media\scripts.obsp`, 18 334 463 bytes, SHA-256
  `B46DD3DA7F17A0ED016E30AF523BFBA86D358C9920DFFA866C69D4A0F4F67C7C` (original de Steam).
- **Herramienta:** D2ScriptViewer 0.1.0, rama `main`.

## Ediciones elegidas (2026-10-04)

Se eligieron con el visor y se ensayaron sobre una copia en una carpeta temporal: guardar,
verificar con `verify`, releer y restaurar dieron los resultados esperados.

### Prueba 1 — mismo tamaño: impulso del salto de Death

- **Objeto:** `death/playercommon_movestates` (`CharacterMoveStateList`, posición 3 113 del
  índice). `death/death_desc` lo enlaza en `MoveStateListArray.MoveStateLists[0]`.
- **Propiedad:** `MoveStates[44].JumpImpulse` (float32). El estado 44 es un `PlayerJumpDesc` con
  `Name` = `Jump`.
- **Cambio:** 350 → 700. Mismo tamaño de blob y de archivo (18 334 463 bytes); en el ensayo el
  SHA resultante empezaba por `48BF85EE6C7B9E6E`.
- **Efecto esperado:** el salto normal de Death (el primero, no el doble salto) es claramente más
  alto. Si el impulso es una velocidad inicial, la altura puede llegar a ser unas cuatro veces
  la original. **Hipótesis:** que `JumpImpulse` sea esa velocidad es una lectura del nombre del
  campo, no algo comprobado.

### Prueba 2 — cambio de tamaño: cadena `05` más larga

- **Objeto:** `base/quest_test_dialog` (`DialogSet`, posición 48 del índice): un diálogo de
  pruebas con flags de depuración.
- **Propiedad:** `Dialogs[0].Actions[1].FlagID` (cadena sin hash, tag `05`).
- **Cambio:** `flag_quest_debug_question_asked` → `flag_quest_debug_question_asked_d2sv`
  (5 caracteres más). Se guarda **junto con** la prueba 1.
- **Efecto esperado:** el archivo pasa a 18 334 468 bytes y los offsets de los 7 813 objetos
  posteriores se desplazan 5 bytes; en el ensayo, `death/playercommon_movestates` pasó de
  `0x776203` a `0x776208`. El juego debe arrancar, cargar la partida y funcionar con normalidad,
  y el salto alto de la prueba 1 debe seguir ahí, lo que demuestra que leyó bien un objeto
  desplazado. El diálogo de pruebas en sí no debería verse nunca. **Hipótesis:** que ese diálogo
  no se use en una partida normal se deduce de su nombre.

### Prueba 3 — restaurar

- **Acción:** Archivo → Restaurar original… copia `scripts.original.obsp` encima de
  `scripts.obsp`, verifica el resultado y vuelve a abrir el archivo.
- **Esperado:** «Original de Steam» en la barra de estado y SHA `B46DD3DA…`.

## Resultados (2026-10-04)

El usuario hizo las pruebas con la herramienta sobre el archivo instalado e informó de que «las
tres funcionan». No dio más detalles (por ejemplo, la altura del salto), así que no se registran.

| Prueba | ¿Arranca y carga la partida? | ¿Efecto visible? | Evidencia en disco |
|---|---|---|---|
| 1 — JumpImpulse 700 | Sí (informe del usuario) | Sí (informe del usuario) | Guardado a las 03:42:21 |
| 2 — FlagID +5 bytes | Sí (informe del usuario) | Sí: el juego funciona y el salto alto sigue (informe del usuario) | Guardado a las 03:49:17 |
| 3 — Restaurar | — | Sí: SHA `B46DD3DA…` (ver abajo) | Restaurado a las 03:55:46 |

### Evidencia leída en la instalación (solo lectura, tras el informe)

- `scripts.original.obsp` (03:42:21, solo lectura): 18 334 463 bytes, SHA `B46DD3DA…`. La copia
  del original se creó en el primer guardado y es idéntica al archivo previo.
- `.d2sv_backups\scripts.20261004-034221-256623.obsp`: SHA `B46DD3DA…`, la versión previa al
  primer guardado.
- `.d2sv_backups\scripts.20261004-034917-262165.obsp`: SHA `48BF85EE6C7B9E6E…`, la versión de la
  prueba 1; coincide con el ensayo.
- `scripts.obsp` (03:49:17): 18 334 468 bytes, SHA `D9B222B4…`, con `JumpImpulse = 700` y
  `FlagID = 'flag_quest_debug_question_asked_d2sv'`. Es el estado de la prueba 2: **no** está
  restaurado. Una restauración con las copias rotativas activadas (lo están en la
  configuración) habría dejado una copia de esta versión con una hora posterior, y no la hay.

### Restauración (prueba 3)

Con autorización del usuario, Claude restauró el archivo instalado con
`saving.restore_original`, el mismo código que ejecuta Archivo → Restaurar original:

1. **03:55:03.** Un guardado de la herramienta (no lo hizo Claude) guardó a un lado la versión de
   la prueba 2 en `.d2sv_backups\scripts.20261004-035503-077071.obsp` (SHA `D9B222B4…`) y dejó
   instalado el estado de la prueba 1 (SHA `48BF85EE…`). Es compatible con cerrar la ventana tras
   deshacer el `FlagID` y responder «Guardar».
2. **03:55:46.** La restauración guardó esa versión en
   `.d2sv_backups\scripts.20261004-035546-944941.obsp` (SHA `48BF85EE…`), copió
   `scripts.original.obsp` encima y releyó el resultado. `scripts.obsp` volvió a medir
   18 334 463 bytes con SHA `B46DD3DA7F17A0ED016E30AF523BFBA86D358C9920DFFA866C69D4A0F4F67C7C`, la
   barra de estado volvió a «Original de Steam» y `python -m d2scriptviewer verify` da todo correcto.
3. `scripts.original.obsp` conserva la fecha de su creación (03:42:21) y su SHA `B46DD3DA…`: ni
   los guardados de las 03:49:17 y 03:55:03 ni la restauración lo tocaron.

### Conclusión

- El juego carga un `scripts.obsp` guardado por D2ScriptViewer y refleja la edición.
- El juego acepta un archivo con otro tamaño y los offsets del índice recalculados: no hay
  checksum ni tamaño fijo que lo impida.
- La copia del original es idéntica al archivo previo, y restaurarla devuelve el SHA de Steam.

En la carpeta `media\` quedan `scripts.original.obsp` (copia permanente, de solo lectura) y
`.d2sv_backups\` con cuatro versiones (unos 73 MB), que se pueden borrar.

## Fase 5 — edición estructural (2026-10-04)

Comprueba el riesgo de la fase 5: al insertar o quitar objetos `07`, el codificador renumera sus
índices internos. Si el juego los usara para algo, un objeto posterior a la inserción se leería
mal.

### Edición elegida

Se eligió con el visor y se ensayó sobre una copia en una carpeta temporal: validar, guardar,
releer, `verify` y restaurar dieron lo esperado.

- **Objeto:** `death/playercommon_movestates` (`CharacterMoveStateList`, 108 estados, 961 objetos
  `07`). `death/death_desc` lo enlaza en `MoveStateListArray.MoveStateLists[0]`.
- **Cambio estructural:** duplicar `MoveStates[0]`, un `PlayerGenericStateDesc` con
  `Name` = `Death` e `ID` = 100000 y 3 objetos en su subárbol. La copia queda en
  `MoveStates[1]` y es idéntica al original.
- **Marca visible:** `MoveStates[45].JumpImpulse` 350 → 700. Es el estado «Jump», que estaba en
  `[44]` y la inserción desplaza a `[45]`.
- **En el ensayo:**
  - el blob pasa de 50 374 a 50 543 bytes y el archivo de 18 334 463 a 18 334 632 (+169);
  - los objetos pasan de 961 a 964, y el índice interno del estado «Jump» de 585 a 588;
  - la validación da un único aviso, «MoveStates: el campo ID se repite (100000)», que es
    esperado: se acepta;
  - el SHA del archivo guardado empieza por `FE50F6A4E22CE77E`.
- **Efecto esperado:** el juego arranca y carga la partida; Death se mueve, ataca y salta con
  normalidad, y el salto normal es mucho más alto. Si el juego usara los índices internos de los
  `07`, los estados posteriores a `[0]` (casi todos) quedarían desalineados y el movimiento
  fallaría o el juego se cerraría. **Hipótesis:** que un estado repetido e idéntico (mismo `Name`
  e `ID`) no cambie nada se deduce de que la copia es exacta; también es parte de lo que se prueba.

### Resultado (2026-10-04)

El usuario hizo la prueba con la herramienta sobre el archivo instalado e informó de que
«funciona»: el juego carga el archivo con la edición estructural y la refleja. No dio más
detalles y no se registran.

**Evidencia en la instalación**, leída después del informe y solo para leer:

- **15:17:54, guardado.** La copia rotativa `scripts.20261004-151754-697791.obsp` tiene SHA
  `B46DD3DA…`: es el original de Steam, la versión previa al guardado.
- **15:19:43, restauración.** La copia rotativa `scripts.20261004-151943-691961.obsp`
  (18 334 632 bytes, SHA `FE50F6A4E22CE77E…`) es la versión que se jugó. Coincide byte a byte
  con el ensayo, así que la edición fue exactamente la prevista: duplicar `MoveStates[0]` y
  `JumpImpulse` 700 en `MoveStates[45]`.
- **Archivo instalado:** 18 334 463 bytes, SHA `B46DD3DA…`, original de Steam. Restaurar
  funcionó.
- **`scripts.original.obsp`:** sin cambios desde su creación (03:42:21, SHA `B46DD3DA…`).
- **Copias rotativas:** con las dos nuevas había seis, y la poda borró la más antigua (03:42:21)
  dejando las últimas 5.

### Conclusión

El juego no usa los índices internos de los objetos `07` de un BOD, o al menos tolera que el
codificador los renumere: con 3 objetos insertados al principio de la lista de estados de
movimiento de Death, el estado «Jump» (índice 585 → 588) se lee bien y refleja su cambio.
También tolera un estado repetido idéntico, con el mismo `Name` e `ID`. Insertar, eliminar y
mover objetos dentro de un BOD es viable.

## Fase 6 — cadena con hash nueva (2026-10-04)

Comprueba que el juego acepta una cadena `0F` que no aparecía en `scripts.obsp`, con el hash que
calcula la herramienta (CRC-64, apéndice A.4 del plan), y que la usa. Para que se vea el efecto,
la cadena nombra un recurso que está fuera de `scripts.obsp`: una animación del paquete
`media/characters/death` de `media.upak`, listado en solo lectura con Darkstractor.

### Edición elegida

- **Recurso:** `D_WScy_Combo04.anm` (33 820 bytes), un combo de guadaña. Es una de las 44
  animaciones del paquete de Death cuyo nombre no aparece en ninguna de las 70 182 cadenas de
  `scripts.obsp`: el juego la trae pero ningún `AnimationDesc` la nombra.
- **Objeto:** `death/death_animations` (`AnimationList`, posición 3 107). En 912 de sus 968
  `AnimationName` (tag `0F`), el valor es el nombre de un `.anm` de ese paquete.
- **Cambios**, los tres con la misma cadena nueva `D_WScy_Combo04` (hash `01A97E58BABBD7A8`):
  - `Animations[339].AnimationName` (`Name` = `Jump`): `D_Jump` → `D_WScy_Combo04`;
  - `Animations[344].AnimationName` (`Name` = `JumpF`): `D_JumpF` → `D_WScy_Combo04`;
  - `Animations[435].AnimationName` (`Name` = `PaperDoll_Idle`): `D_Idle` → `D_WScy_Combo04`.
- **En el ensayo**, sobre una copia en una carpeta temporal: la herramienta avisa de que la
  cadena es nueva y pide confirmación; el archivo pasa de 18 334 463 a 18 334 483 bytes (+20, la
  definición de la cadena nueva en la tabla del BOD); `verify` da correcto; releer muestra los
  tres valores; el SHA del archivo guardado empieza por `D976CDED1A44DD32`; restaurar devuelve
  `B46DD3DA…`.
- **Efecto esperado:** el salto normal sin armas, parado (`Jump`) o corriendo (`JumpF`),
  reproduce el combo de guadaña en lugar de la animación de salto, y el muñeco de Death en la
  pantalla de personaje o inventario (`PaperDoll_Idle`) hace el combo en vez de estar quieto.
- **Hipótesis:**
  - que el controlador de animaciones elija `Jump` y `JumpF` para el salto sin armas, y
    `WScy_Jump` con la guadaña en la mano (sin tocar), se deduce de los nombres;
  - que `PaperDoll_Idle` sea el muñeco del menú, también;
  - que el juego cargue todas las animaciones del paquete, también las que nadie nombra, es parte
    de lo que se prueba.

  Si el salto o el muñeco se quedan congelados, en postura en T o sin animación, el juego no
  encontró el recurso.
- **Estado de la instalación antes de la prueba** (leído en solo lectura): `scripts.obsp`
  original de Steam (`B46DD3DA…`, 15:19:43), `scripts.original.obsp` intacto (03:42:21) y 5
  copias rotativas, la última de las 15:19:43.

### Resultado (2026-10-04)

El usuario hizo la prueba con la herramienta sobre el archivo instalado e informó de que «el
comportamiento fue el esperado», sin cierres ni congelaciones del juego:

- **Salto** (`Jump`, `JumpF`): reproduce el combo de guadaña en lugar del salto, como se esperaba.
- **Muñeco del menú** (`PaperDoll_Idle`): hace el combo de guadaña (el usuario lo confirmó al
  preguntarle) cada vez que se cambia de pantalla, y al terminar se queda congelado en el último
  fotograma. **Hipótesis:** el combo no es una animación en bucle y ocupa un hueco que espera un
  reposo en bucle, así que se detiene al acabar; no es un fallo de la herramienta.

**Evidencia en la instalación**, leída después del informe y solo para leer:

- **16:33:41, guardado.** `scripts.obsp` medía 18 334 483 bytes con SHA `D976CDED1A44DD32…`:
  coincide byte a byte con el ensayo, así que la edición fue exactamente la prevista. La copia
  rotativa `scripts.20261004-163341-909704.obsp` es el original de Steam (`B46DD3DA…`), la
  versión previa.
- **El archivo no estaba restaurado.** Con autorización del usuario, Claude ejecutó
  `saving.restore_original` (el código de Archivo → Restaurar original) a las 16:41:24. La copia
  rotativa `scripts.20261004-164124-148623.obsp` guarda la versión de la prueba (`D976CDED…`);
  `scripts.obsp` volvió a 18 334 463 bytes con SHA `B46DD3DA…`, y `verify` da correcto.
- **`scripts.original.obsp`:** sin cambios desde su creación (03:42:21, `B46DD3DA…`).
- **Copias rotativas:** quedan las últimas 5; la poda borró las de las 03:49:17 y 03:55:03.

### Conclusión

El juego acepta una cadena con hash que no estaba en `scripts.obsp`, con el hash que calcula la
herramienta, y la usa para encontrar un recurso de fuera del archivo: una animación que el juego
trae pero que nada nombraba. También carga las animaciones del paquete que ningún
`AnimationDesc` nombra. Esta prueba no distingue si el juego busca el recurso por el hash o por
el texto; la función ya estaba comprobada con los 70 182 pares.
