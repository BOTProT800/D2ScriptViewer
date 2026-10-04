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

## Resultados

Pendientes: los registrará el usuario tras jugar.

| Prueba | Fecha | ¿Arranca y carga la partida? | ¿Efecto visible? | Incidencias |
|---|---|---|---|---|
| 1 — JumpImpulse 700 | | | | |
| 2 — FlagID +5 bytes | | | | |
| 3 — Restaurar | | | | |
