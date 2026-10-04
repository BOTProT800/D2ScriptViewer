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

### Resultado

Pendiente: lo registrará el usuario tras jugar.
