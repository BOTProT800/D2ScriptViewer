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

## Fase 7 — parche de un literal de script (2026-10-04)

Comprueba que el juego carga un script compilado con un literal parcheado (mismo tamaño) y que
el cambio tiene efecto. La edición se eligió con el desensamblador entre los literales con efecto
visible que no se guardan en la partida.

### Edición elegida

- **Objeto:** `ui_core/pausemenu` (script, 15 771 bytes): el menú de pausa.
- **Código:** en `onInit`, la línea 38 del fuente es `Game.setPaused(true)`: `bool true` en
  `0x004E`, `args 1`, `op_2C Game` y `método setPaused`. Al cerrarse, `onDeInit` llama a
  `Game.setPaused(false)` (línea 88).
- **Cambio:** `Funciones.onInit.0x004E` `true` → `false`.
- **En el ensayo**, sobre una copia en una carpeta temporal: cambia un solo byte del blob
  (`0x668`: 1 → 0); el archivo sigue midiendo 18 334 463 bytes; el SHA del archivo guardado
  empieza por `69A486B63E9A66AB`; `verify` da correcto; releer muestra `false`; restaurar devuelve
  `B46DD3DA…`.
- **Efecto esperado:** al abrir el menú de pausa, el juego no se detiene detrás: el mundo, los
  enemigos y las animaciones de Death siguen moviéndose. Al cerrarlo, todo sigue con normalidad.
  **Hipótesis:**
  - que el argumento de `setPaused` decida si se pausa se deduce de su nombre;
  - justo después, `NPC.onPause()` (línea 39) se sigue llamando, así que los NPC podrían
    detenerse aunque el resto no;
  - si el motor pausa también por otra vía, puede que no se note nada, y ese resultado también
    vale.
- **Estado de la instalación antes de la prueba** (leído en solo lectura): `scripts.obsp`
  original de Steam (`B46DD3DA…`, 16:41:24), `scripts.original.obsp` intacto (03:42:21) y 5
  copias rotativas, la última de las 16:41:24.

### Resultado (2026-10-04)

El usuario hizo la prueba con la herramienta sobre el archivo instalado e informó de que
«funcionó»:

- con el menú de pausa abierto, el juego sigue corriendo en tiempo real detrás;
- al intentar moverse entre las opciones del menú, se mueve el personaje y no la selección del
  menú. **Hipótesis:** la pausa también desvía la entrada del mando o el teclado hacia la
  interfaz; sin ella, la entrada sigue llegando al juego.

**Evidencia en la instalación**, leída después del informe y solo para leer:

- **17:31:53, guardado.** La copia rotativa `scripts.20261004-173153-100425.obsp` es el original
  de Steam (`B46DD3DA…`), la versión previa.
- **17:33:22, restauración** (hecha por el usuario). La copia rotativa
  `scripts.20261004-173322-960549.obsp` (18 334 463 bytes, SHA `69A486B63E9A66AB…`) es la versión
  que se jugó y coincide byte a byte con el ensayo: un solo byte cambiado, el literal de
  `Game.setPaused`.
- **Archivo instalado:** 18 334 463 bytes, SHA `B46DD3DA…`, original de Steam.
- **`scripts.original.obsp`:** sin cambios desde su creación (03:42:21, `B46DD3DA…`).
- **Copias rotativas:** quedan las últimas 5; la poda borró las de las 03:55:46 y 15:17:54.

### Conclusión

El juego carga un script compilado con un literal parcheado por la herramienta (mismo tamaño,
estructura intacta) y ejecuta el valor nuevo: la interpretación del bytecode de la fase 7 es
correcta al menos para ese literal y su llamada. Parchear literales de scripts sin cambiar
tamaños es viable.

## Fase 8 — reaplicar un parche tras restaurar (2026-10-04)

Comprueba el uso previsto del parche: recuperar los cambios después de que Steam (o Restaurar
original) devuelva el archivo de partida. Las ediciones son las ya probadas en el juego en las
fases 5 y 6, así que lo que se prueba es que el parche reproduce el archivo guardado a mano.

### Ediciones y pasos

1. **A mano**, sobre el original de Steam:
   - duplicar `MoveStates[0]` de `death/playercommon_movestates`;
   - `MoveStates[45].JumpImpulse` 350 → 700 (el estado «Jump», desplazado por la inserción);
   - `Animations[435].AnimationName` de `death/death_animations` (`PaperDoll_Idle`):
     `D_Idle` → `D_WScy_Combo04`.

   Guardar.
2. **Archivo → Exportar parche…**, fuera de la carpeta del juego. La base es
   `scripts.original.obsp`.
3. **Archivo → Restaurar original.**
4. **Archivo → Aplicar parche…** y guardar.
5. Jugar y, al terminar, restaurar.

### Ensayo sobre una copia

- Paso 1: 18 334 652 bytes, SHA `AF244850234B2FD80DC187FB7952EF47C0C7AC865329C4E6C76A28A01B5FFB6C`.
- Paso 2: parche de 1 834 bytes, «2 objetos, 3 operaciones (1 insertar, 2 valor)», base
  `scripts.original.obsp` (original de Steam).
- Paso 3: `B46DD3DA…`.
- Paso 4: el mismo SHA `AF244850…` que el paso 1, y `verify` correcto.
- **Efecto esperado en el juego:** el de las fases 5 y 6. Salto normal mucho más alto, y el
  muñeco del menú haciendo el combo de guadaña (y quieto en el último fotograma).
- **Estado de la instalación antes de la prueba** (leído en solo lectura): `scripts.obsp`
  original de Steam (`B46DD3DA…`, 17:33:22), `scripts.original.obsp` intacto (03:42:21) y 5
  copias rotativas, la última de las 17:33:22.

### Resultado (2026-10-04)

El usuario hizo los pasos con la herramienta sobre el archivo instalado e informó de que «todo
funcionó bien» salvo que el muñeco del menú no hizo el combo de guadaña; estaba quieto, en su
pose normal.

**Evidencia en la instalación**, leída después del informe y solo para leer:

- **18:30:17, guardado a mano.** La copia rotativa `scripts.20261004-183017-836720.obsp` es el
  original (`B46DD3DA…`), la versión previa.
- **18:48:56, restauración.** La copia rotativa `scripts.20261004-184856-352651.obsp` guarda la
  versión hecha a mano: 18 334 632 bytes, SHA `BC3F812B0F190511…`.
- **18:49:09, guardado tras aplicar el parche.** La copia rotativa de ese momento es el original
  (`B46DD3DA…`).
- **18:50:56, restauración.** La copia rotativa `scripts.20261004-185056-985591.obsp` guarda la
  versión reaplicada: **el mismo SHA `BC3F812B…` que la hecha a mano**.
- **Archivo instalado:** `B46DD3DA…`, original de Steam. `scripts.original.obsp` sigue intacto
  (03:42:21).
- **Copias rotativas:** quedan las últimas 5.

**Por qué no salió el combo:** comparar la versión jugada con el original da tres cambios:
duplicar `MoveStates[0]`, `MoveStates[45].JumpImpulse` 350 → 700 y
`Animations[435].Name` `PaperDoll_Idle` → `D_WScy_Combo04`. El último se hizo en `Name`, la fila
de encima de `AnimationName`, que era la prevista. Como los dos textos miden 14 caracteres, el
archivo no creció los 20 bytes del ensayo (18 334 632 en vez de 18 334 652). Con la entrada
renombrada, el juego no encuentra una animación llamada `PaperDoll_Idle` y el muñeco se queda en
su pose normal. **Hipótesis**, coherente con la fase 6 (donde cambiar `AnimationName` sí hizo
que el muñeco hiciera el combo): el muñeco del menú busca su animación por el `Name`
`PaperDoll_Idle` y, si no la encuentra, no se anima.

### Conclusión

Con el usuario se decidió cerrar la prueba con este resultado:

- lo que se probaba, que un parche reaplicado tras restaurar reproduce el archivo guardado a
  mano, se cumplió byte a byte (mismo SHA), y el juego lo cargó con su efecto (salto alto);
- la parte del muñeco no dependía del parche, sino de qué campo se editó, que fue el mismo en
  las dos versiones.

## Audio — evento y banco de un sonido de interfaz (2026-10-09)

Primeras pruebas de audio, a partir de las propuestas de `research/FORMATO.md` (sección
«Audio», 2026-10-09). Se hacen juntas, en un solo guardado:

- **Prueba 1, control:** cambiar el `Event` de un `SoundDesc` por otro del mismo banco. Comprueba
  que el juego reproduce el evento que nombra el obsp.
- **Prueba 2, carga por nombre:** apuntar otro `SoundDesc` a un evento de un banco de personaje
  que no tiene por qué estar cargado en ese momento. Comprueba si el juego carga un banco solo
  porque un `SoundDesc` lo nombra.

### Edición elegida

- **Objeto:** `ui_core/uisounds` (`SoundList`, posición 3 887). `ui_merchant/merchantmenu` y
  `ui_merchant/blackrootmenu` piden sus sonidos aquí por `Name` con
  `Sound.playUISoundByName`: `UI_MerchantOpen` en `onInit` y `UI_MerchantClose` al cerrar.
  `UI_MerchantBadBuy` suena en `onMerchantPurchaseErrorFunds` y `onMerchantPurchaseErrorLevel`.
- **Cambios** (ninguna cadena es nueva: no hay aviso):
  - `Sounds[180].Event` (`UI_MerchantOpen`, banco `UI`): `MerchantOpen` → `MerchantBadBuy`;
  - `Sounds[170].Bank` (`UI_MerchantClose`): `UI` → `SFX_Character_Archon`;
  - `Sounds[170].Event`: `MerchantClose` → `Voc_Archon_Corrupted_Scream`, un grito, para que no
    se confunda con un sonido de interfaz. Es uno de los 121 `SoundDesc` del banco, todos en
    `archon_common/sfx_character_archon`.
- **Base:** el archivo instalado, no el de Steam. Lleva un cambio del usuario del 6 de octubre:
  `death/death · Funciones.onInit.0x0783` 21 → 30, el literal del primer `NumSlots` de
  `GUIA_MODDER.md`. La prueba lo conserva; para deshacerla se vuelven a poner los tres valores,
  no se usa Restaurar original.
- **En el ensayo**, en memoria y sobre una copia en una carpeta temporal: `prepare_save` y
  `verify_plan` pasan sin avisos; solo cambia `ui_core/uisounds`; el archivo pasa de 18 334 463 a
  18 334 522 bytes (+59); el SHA del archivo guardado es
  `EF6E6DED1B2FFCF9A675D8DA23C5AD87481BB1E2D1E6158007E878B1D6FF0421`; `verify` da correcto, y
  deshacer los tres cambios devuelve `ADC2B872…`. Sobre el original de Steam darían el mismo
  tamaño y el SHA `43328BEA…`.
- **Efecto esperado** en cualquier comerciante:
  - al abrir la tienda suena el «no puedes comprarlo» (`MerchantBadBuy`) en lugar del sonido de
    apertura;
  - comprar sin dinero suficiente sigue sonando igual, porque `Sounds[168]` no se toca;
  - al cerrar la tienda, el grito del Archon si el juego carga el banco, y silencio (o el sonido
    de siempre) si no.
- **Hipótesis:**
  - que la entrada `Sounds[180]` sea la que suena se deduce de la llamada por nombre; si el
    juego buscara por `ID` (13) daría lo mismo, porque no cambia;
  - con Wwise, un evento de un banco sin cargar no suena y no da error. Si el cierre queda en
    silencio, el juego no carga bancos por el obsp; si suena el grito, sí, o el banco ya estaba
    cargado.
- **Estado de la instalación antes de la prueba** (leído en solo lectura):
  - `scripts.obsp`: 18 334 463 bytes, SHA `ADC2B872767005440BD41E8A20F964DA1EE280CC5BD5167C9FB783EEE8E60020`
    (20:49:27 del 6 de octubre), el original con el cambio de `NumSlots`;
  - `scripts.original.obsp` intacto (`B46DD3DA…`, 03:42:21 del 4 de octubre);
  - 5 copias rotativas, la última de las 20:49:27 del 6 de octubre (`B46DD3DA…`);
  - `Darksiders2.exe` con el SHA de siempre.

### Resultado (2026-10-10): no concluyente

El usuario informó de que no notó nada y propuso probar con otras acciones. Al preguntarle por
el cierre de la tienda, no se había fijado.

**Evidencia en la instalación**, leída después del informe y solo para leer:

- **23:49:12 del 9 de octubre, guardado.** La copia rotativa `scripts.20261009-234912-942105.obsp`
  es la versión previa, `ADC2B872…` (con `NumSlots`).
- **00:08:12, Restaurar original.** La copia rotativa `scripts.20261010-000812-646880.obsp`
  guarda la versión jugada: 18 334 522 bytes, como en el ensayo, pero con SHA `6A805E6B71F6BAFA…`
  en lugar de `EF6E6DED…`. Comparada con `ADC2B872…`, solo lleva los dos cambios de
  `Sounds[170]` (banco y evento del cierre). `Sounds[180].Event` siguió en `MerchantOpen`, y por
  eso no cambia el tamaño: `MerchantBadBuy` ya estaba en la tabla del BOD.
- **Archivo instalado:** el original de Steam (`B46DD3DA…`). Restaurar quitó también el cambio
  de `NumSlots`. Se guardó como parche, fuera del repositorio y de la carpeta del juego, en
  `Extractions\Darksiders\numslots_21_a_30.d2svpatch.json`; aplicado sobre el original da
  `ADC2B872…`.

**Conclusión:** la prueba 1 no se hizo, porque faltó el cambio de la apertura. De la 2 no hay
observación. Los sonidos de la tienda son cortos y se oyen poco, así que se pasa a acciones de
Death que se repiten mucho.

## Audio — salto y esquiva de Death (2026-10-10)

Las mismas dos preguntas que en la prueba de la tienda, con sonidos que se oyen a menudo. Las
animaciones disparan sus sonidos por `SoundTrigger.SoundID`, que es un `SoundDesc.ID` de
`death/death_sounds` (`SoundList`, posición 3 059).

### Edición elegida

- **Prueba 1, control:** `Sounds[47]` (`death_whoosh_jump`, ID 60200, banco
  `SFX_Character_Death`). Lo disparan 98 animaciones: `Jump` y `Jump_Double` de Death, las de
  cornisas y las de montar en el constructo. El salto lleva además la voz `Voc_Death_Jump`
  (`Sounds[131]`, sin tocar).
  - `Sounds[47].Event`: `Jump_Whoosh` → `Voc_Death_Death`, el grito de muerte de Death, del mismo
    banco (`Sounds[130]`, que solo disparan `Death_Start` y `KillRegion_Start`).
- **Prueba 2, carga por nombre:** `Sounds[42]` (`death_whoosh_flip`), el silbido al empezar las
  cuatro esquivas (`Evade_F`, `Evade_B`, `Evade_L`, `Evade_R`). La esquiva lleva además la voz
  `Voc_Death_Jump` y, al terminar, `Evade_Whoosh_End` (`Sounds[41]`), los dos sin tocar.
  - `Sounds[42].Bank`: `SFX_Character_Death` → `SFX_Character_Archon`;
  - `Sounds[42].Event`: `Flip_Whoosh` → `Voc_Archon_Corrupted_Scream`.
- **Ninguna cadena es nueva** en el archivo, así que no hay aviso. Las dos del Archon sí son
  nuevas en la tabla de nombres de ese BOD.
- **Base:** el instalado, que es el original de Steam (`B46DD3DA…`, 00:08:12).
- **En el ensayo**, en memoria y sobre una copia en una carpeta temporal: `prepare_save` y
  `verify_plan` pasan sin avisos; solo cambia `death/death_sounds`; el archivo pasa de 18 334 463
  a 18 334 488 bytes (+25); el SHA del archivo guardado es
  `CE512D177DC344145870DA5A97A71E180A466356C14EEA93618BF57AF6C36C63`; `verify` da correcto, y
  deshacer los tres cambios devuelve `B46DD3DA…`. Sobre la versión con `NumSlots` darían
  `48AD7F79…`, del mismo tamaño.
- **Efecto esperado:**
  - al saltar y en el doble salto, el grito de muerte de Death en lugar del silbido;
  - al esquivar, el grito del Archon si el juego carga el banco. Si no lo carga, la esquiva
    pierde el silbido del principio, pero conserva la voz y el silbido final.
- **Hipótesis:**
  - que `SoundTrigger.SoundID` busque en las listas del propio actor (`research/FORMATO.md`);
    el ID 60200 solo está en `death/death_sounds`, así que no hay otra entrada que pueda ganar;
  - con Wwise, un evento de un banco sin cargar no suena y no da error.
- **Estado de la instalación antes de la prueba** (leído en solo lectura): `scripts.obsp`
  original de Steam (`B46DD3DA…`, 00:08:12 del 10 de octubre), `scripts.original.obsp` intacto
  (03:42:21 del 4 de octubre) y 5 copias rotativas, la última de las 00:08:12 (`6A805E6B…`, la
  prueba de la tienda).

### Resultado (2026-10-10)

El usuario informó de que todo fue bien y de que lo devolvió a los valores originales. Al
preguntarle, contestó:

- **Salto y doble salto:** el grito de muerte de Death en lugar del silbido. **La prueba 1 se
  cumple.**
- **Esquiva:** no está seguro de qué sonó al empezar. **La prueba 2 no es concluyente.** El
  silbido inicial es corto y se mezcla con el gruñido de Death y el silbido del final.
- **Lugar:** no sabe si estaba cerca de la zona del Archon. Según el obsp, es la zona 3
  (`base/quest_z3mq0_find_archon`, `zone03_archontower`).

**Evidencia en la instalación**, leída después del informe y solo para leer. El usuario guardó
tras cada cambio:

- **00:34:54:** `Sounds[47].Event` (18 334 446 bytes, `6662F03C…`). La copia rotativa de ese
  momento es el original (`B46DD3DA…`).
- **00:35:35:** además, `Sounds[42].Bank` (18 334 472 bytes, `231FC595…`).
- **00:35:42:** además, `Sounds[42].Event`. Es la versión jugada, guardada en la copia rotativa
  `scripts.20261010-004009-665418.obsp`: 18 334 488 bytes, SHA `CE512D177DC34414…`, **idéntica
  al ensayo**. Comparada con el original, lleva justo los tres cambios.
- **00:40:09, restauración:** `scripts.obsp` es el original de Steam (`B46DD3DA…`), y
  `scripts.original.obsp` sigue intacto.
- **Copias rotativas:** quedan las últimas 5. La poda borró la de `ADC2B872…` (con `NumSlots`),
  que sigue disponible como parche en `Extractions\Darksiders`.

**Conclusión:** el juego reproduce el `Event` que nombra el obsp. El camino es la animación,
luego `SoundTrigger.SoundID`, luego el `SoundDesc` con ese `ID` en `death/death_sounds`, y por
último su `Event`. Cambiar el evento de una entrada cambia el sonido en todas las animaciones que
la disparan. Falta saber si un evento de otro banco suena.

## Audio — grito del Archon en el salto (2026-10-10)

Repite la prueba 2 de la sección anterior en el disparador que ya se sabe que funciona, para que
el resultado no dependa de oír la falta de un silbido corto.

### Edición elegida

- **Objeto:** `death/death_sounds`, `Sounds[47]` (`death_whoosh_jump`, ID 60200):
  - `Bank`: `SFX_Character_Death` → `SFX_Character_Archon`;
  - `Event`: `Jump_Whoosh` → `Voc_Archon_Corrupted_Scream`.
- **Base:** el instalado, el original de Steam (`B46DD3DA…`, 00:40:09).
- **En el ensayo**, en memoria y sobre una copia en una carpeta temporal: `prepare_save` y
  `verify_plan` pasan sin avisos; solo cambia `death/death_sounds`; el archivo pasa de 18 334 463
  a 18 334 505 bytes (+42); el SHA del archivo guardado es
  `7F8B4AEEDB5B7D3365552D603AB680BADF15FBA75E5295424E4617754392BABE`; `verify` da correcto, y
  deshacer los dos cambios devuelve `B46DD3DA…`.
- **Efecto esperado:** el doble salto solo dispara `Sounds[47]`.
  - Si el juego carga el banco, suena el grito del Archon.
  - Si no lo carga, el doble salto queda en silencio, y el salto simple solo conserva el gruñido
    de Death (`Sounds[131]`).
- **Para interpretarlo hace falta el lugar:** si suena lejos de la zona 3 y antes de llegar al
  Archon en la historia, el banco no estaba cargado por la zona.

### Primer intento (2026-10-10): no vale

El usuario informó de que la hizo y la restauró. Al preguntarle, dijo que el doble salto sonó al
grito del Archon y que no recuerda el mensaje de guardado.

**Evidencia en la instalación**, leída a las 00:55 y solo para leer: no hubo ningún guardado.
`scripts.obsp` sigue siendo el original de Steam con fecha de las 00:40:09 (la restauración
anterior), no hay copias rotativas nuevas, y ningún `.obsp` de la carpeta del juego ni de la del
usuario cambió después de las 00:41. Así que el juego no pudo cargar el cambio de esta prueba, y
lo que se oyó no se puede atribuir a él. Se repite con un punto de control: tras guardar, Claude
comprueba el SHA instalado antes de abrir el juego.

### Resultado (2026-10-10)

- **02:53:37, guardado.** Antes de abrir el juego, Claude leyó la instalación en solo lectura:
  `scripts.obsp` medía 18 334 505 bytes con SHA `7F8B4AEE…`, idéntico al ensayo; la copia
  rotativa de ese momento era el original (`B46DD3DA…`), y el juego estaba cerrado.
- **En el juego**, en Tripetra (Tierras de la Forja, la primera zona), el usuario informó de que
  **el doble salto sonó al grito del Archon**. No dijo si ya había llegado al Archon en esa
  partida.
- **02:57:32, Restaurar original.** La copia rotativa `scripts.20261010-025732-511862.obsp` guarda
  la versión jugada (`7F8B4AEE…`). `scripts.obsp` volvió a 18 334 463 bytes y `B46DD3DA…`, y
  `scripts.original.obsp` sigue intacto. El juego estaba cerrado.

### Conclusión

Un `SoundDesc` de Death que nombra el banco de otro personaje (`SFX_Character_Archon`) y uno de
sus eventos suena en una zona donde ese personaje no aparece. Para un modder, cualquier sonido
puede tomar el evento de otro banco del juego cambiando `Bank` y `Event`.

Lo que esta prueba no distingue:

- **Cómo llega el banco a estar cargado.** Puede que el juego lo cargue al leer el `Bank` del
  `SoundDesc`, o que ya estuviera cargado (todos los bancos al empezar, o los de las listas de
  sonido que se cargan). Se distinguiría con un `SoundDesc` que nombre el banco de Death con un
  evento del Archon: si también suena, el campo `Bank` no decide qué se carga.
- **Si funciona con un banco nuevo**, que no venga con el juego (prueba 3 de
  `research/FORMATO.md`).
