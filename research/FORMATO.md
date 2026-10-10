# Notas de formato

Hallazgos sobre `scripts.obsp` que complementan el apéndice A de `PLAN_MAESTRO.md`. Todo se
midió sobre la copia de Steam (SHA-256 `B46DD3DA…`), sin incorporar datos del juego al
repositorio.

## 2026-10-03 — Fase 1

### Verificado con el núcleo del proyecto

Lo mismo que el prototipo, ahora reproducido por `python -m d2scriptviewer verify` y por
`tests/test_golden.py`:

- La reconstrucción del contenedor da el SHA original, también recodificando los 4 172 BOD.
- Los 4 172 BOD salen idénticos; sus contadores de cabecera (número de nombres y longitud
  máxima en bytes) coinciden con los recalculados.
- Las 3 690 cabeceras de script son coherentes (versión 1, longitud máxima de símbolo real,
  hash de ruta y grupo iguales a los del índice).
- 70 182 pares hash↔cadena sin conflictos en ningún sentido; ninguna cadena no ASCII,
  incluidas las `05`.
- Las tablas de tipos (A.1) y de tags (A.2) coinciden exactamente. El recuento de `07`
  (146 328) no incluye los 4 172 objetos raíz, que no llevan tag.
- Los 3 406 `FC` apuntan a objetos que existen en el propio archivo.
- Bools: 27 062 valen 1 y 7 935 valen 0; ninguno tiene otro byte.
- Profundidad máxima del árbol BOD: 11 niveles.
- Las listas `09` usan el modo 0 (37 039) y el 1 (7); los mapas `0A`, solo el 1 (39). El
  decodificador rechaza cualquier otro modo en lugar de suponer su significado.

### Hipótesis: `idObjeto` = hash del nombre en minúsculas

**Confirmada en los 7 862 objetos el 2026-10-04** con la función de hash (ver abajo).

En 4 835 de los 7 862 objetos, `idObjeto` es exactamente el hash de `nombre.lower()` (por
ejemplo, `death/death`, nombre `Death`, tiene id `8C882C7C958E9802` = hash de `death`). En los
3 027 restantes la cadena en minúsculas no aparece en el archivo, así que no se puede
comprobar, pero ninguno la contradice. Consecuencia: renombrar un objeto exigiría la función
de hash (fase 6); hasta entonces el nombre y la identidad no se editan.

## 2026-10-04 — Fase 6: la función de hash

Es un **CRC-64 reflejado** con polinomio `0x0060034000F0D50B` (forma reflejada
`0xD0AB0F0002C00600`) y valor inicial y XOR final `0xFFFFFFFFFFFFFFFF`. Se dedujo solo con los
70 182 pares hash↔cadena del archivo, sin código ajeno ni análisis del ejecutable:

1. **Las cadenas de un carácter** delatan una estructura lineal sobre GF(2): el XOR de los hashes
   de `'0'` y `'1'`, `'0'` y `'2'`, `'0'` y `'3'`… se combina como el XOR de los caracteres. Cambiar
   el bit k del carácter hace siempre XOR con `0x01A1561E0005800C << k`.
2. **El prefijo no importa**: en todas las cadenas, cambiar el bit k del último carácter produce
   ese mismo XOR (por ejemplo, `'10'` frente a `'11'`). Es lo que hace un CRC por tablas: el
   último byte entra como `T[byte]`, y `T` es lineal.
3. **El penúltimo carácter** se propaga como en un CRC reflejado:
   `crc = (crc >> 8) ^ T[(crc ^ byte) & 0xFF]`. Con `T[0x80]` = polinomio reflejado sale
   `0xD0AB0F0002C00600`, y `T[1] = 0x01A1561E0005800C` cuadra con el paso 1.
4. **El resto depende solo de la longitud**: para cada longitud (89 distintas), el XOR del hash
   con el CRC «en bruto» (valor inicial 0, sin XOR final) es constante. Esas 89 constantes cuadran
   con valor inicial y XOR final `~0`. La cadena vacía da 0, como en el archivo.

Comprobado: los 70 182 pares, y `hashRuta`, `hashNombre`, `hashCarpeta`, `hashClase` e `idObjeto`
de los 7 862 objetos. El polinomio no es ninguno de los CRC-64 habituales (ECMA-182, ISO, Jones),
y por eso no apareció en las pruebas anteriores (sección 2.4 del plan). Lo comprueban
`python -m d2scriptviewer verify` y `tests/test_golden.py`; los tests sintéticos contrastan la
implementación por tablas con una bit a bit en forma normal.

### Lo que no explica: enteros de 32 bits con aspecto de hash

De los 18 660 enteros `02` distintos del archivo, 15 467 tienen pinta de hash (|valor| ≥ 1 000 000)
y aparecen 67 453 veces (`OnStateOne = 0x4DFA84A3`, `MeshID`…). Comparados con las mitades alta y
baja del CRC-64, y con el CRC-32 de zlib, de las 70 182 cadenas conocidas y sus minúsculas, solo
coinciden 3, 1 y 0 valores, lo que cabe esperar del azar. Usan otra función, o hashean textos que
no están en el archivo; no se ha investigado más.

**Actualización 2026-10-09:** en su mayoría no son hashes, sino marcas de tiempo Unix que ponía
el editor (sección «Audio» más abajo).

## 2026-10-04 — Fase 7: cuerpo y bytecode de los scripts

Formalizados solo con los 3 690 scripts del archivo, sin analizar el ejecutable (decisión de la
fase). La especificación está en el apéndice A.3 del plan; aquí, cómo se llegó a ella.

### Estructura del cuerpo

1. Los dos primeros u64 del cuerpo son el hash del símbolo 1 (el último tramo de la ruta) y el
   del símbolo 2 (la clase base) en los 3 690.
2. **Miembros.** Un ejemplo (`base/equipweaponmodule`) mostraba entradas `hash, 0A, 05, 05 FF
   len "(Equip Weapon)"`: hash, banderas, tipo y un valor con la codificación de los BOD. El valor
   aparece si y solo si las banderas llevan `0x08`. Los objetos `07` dentro de los valores usan
   fichas `00` + índice a la tabla de símbolos (`ItemDesc` = símbolo 4), así que el decodificador
   de los BOD sirve sembrando su tabla de nombres con los símbolos.
3. **Segunda tabla:** hash + valor (p. ej. `WeaponID = 0`), los valores iniciales.
4. **Funciones:** hash, u32 tamaño y código. Con eso se leían enteros 3 406 cuerpos, que acababan
   en un u32 a 0.
5. **Estados:** los 275 restantes tenían esa tabla final llena: hash del estado, u32 con su
   número de funciones y las funciones (`sh_plinth/plinth`: `DeActivate`, `Active`…). Los 9 que
   fallaban tenían funciones de tamaño 0.
6. Resultado: los 3 690 cuerpos se consumen exactamente y vuelven a serializarse idénticos; todos
   los hashes están en la tabla de símbolos de su script.

### Bytecode

- **Desensamblado lineal con validación:** se fue ampliando una tabla de opcodes y formatos de
  operando, y cada pasada exigía que todos los nombres en línea llevaran el hash de su texto
  (CRC-64 de la fase 6) y que la decodificación acabara justo al final de la función. Las
  funciones decodificadas enteras pasaron de 2 320 a 5 653, 7 445, 8 740, 9 591, 9 715 y 9 721 en
  siete pasadas, sin ningún hash erróneo por el camino.
- **Comprobaciones independientes de la tabla:**
  - los destinos de `0x10` y `0x12` son offsets absolutos en la función y caen al principio de
    una instrucción (9 165 de 9 166; la excepción es un dato del original, ver abajo);
  - las líneas `0x3B` siempre crecen;
  - los booleanos `0x25` solo valen 0 o 1, y los floats `0x22` son valores redondos;
  - el byte 0 coincide con el número de `0x28` (parámetros) en las 9 709 funciones con código;
  - toda llamada `0x39` va precedida de `int n` y todo `0x38` de `int n` + `0x2C` variable. Ese n
    vale de 0 a 7 y es el mismo para cada destino en 2 063 de 2 102, así que es el número de
    argumentos: 25 090 de los 32 353 literales `int` no son valores del usuario.
- **Dato raro del original:** en `maker_male/maker_youngin_emote_component`, un `0x10` apunta a
  6503 en una función de 336 bytes. No impide decodificar; se muestra tal cual.
- **Lo que sigue sin saberse:** qué hacen la mayoría de los opcodes sin operando, `0x2D` (u32) y
  los que llevan nombre sin llamada (`0x2C`, `0x3A`, `0x27`…). Las hipótesis por posición están
  en el apéndice A.3.

## 2026-10-09 — Audio: bancos, sonidos e identificadores

Pregunta de partida: si se modifica un banco de sonido o se añade uno nuevo, ¿se puede tocar
`scripts.obsp` para que el juego lo incluya? Medido sobre la copia de Steam con scripts fuera del
repositorio. Nada de esto se ha probado todavía en el juego (pruebas propuestas al final).

**Actualización 2026-10-10:** las pruebas 1 y 2 se hicieron en el juego, con sonidos de Death en
lugar de los de la tienda (resultados al final y en `research/PRUEBAS_EN_JUEGO.md`). El juego
reproduce el `Event` que nombra el obsp, también el de un banco de otro personaje.

### Cómo nombra el obsp el audio

- **`SoundDesc`** es la ficha de un sonido: `ID` (int32), `Name`, `Bank` y `Event` (cadenas `0F`), y
  a veces `Loop`, `FadeOut`, `FadeCurve` o `RefNode`. Hay 12 655 en los BOD: 7 264 en los
  `SoundList` (tipo 3), 5 357 en listas incrustadas en Desc (`SoundsArray.SoundsLists[i].Sounds[j]`)
  y 34 en una Instancia. Otros 9 están en valores por defecto de 3 scripts `chest_weapon_rack`, donde
  solo se pueden parchear literales del mismo tamaño.
- **El campo `Bank`** aparece 12 447 veces en los BOD: en 12 423 `SoundDesc` (232 no lo llevan) y en
  24 `SoundModule`, nodos de los scripts visuales de `base/volcanic rumbles` y
  `base/z1_ld_rm08_roomcrumble`, que reproducen por `Bank` + `Event` sin `ID`. Son 243 nombres
  distintos; 242 sin distinguir mayúsculas, porque están `MIX_States` y `Mix_States`. El más usado
  es `SFX_Impact_FX`. Hay bancos de personaje, de zona, de DLC y globales (`UI`, `VO`,
  `MIX_States`, `MUS_Ambient`, `MUS_Boss`, `MUS_Stingers`).
- **No hay ninguna lista de bancos.** Ninguna clase, campo ni símbolo de script declara, precarga o
  carga bancos, y `.bnk`, `.pck`, `wwise`, `audiokinetic` y `fmod` no aparecen en el archivo. El
  nombre de un banco solo está como valor de `Bank` (y como nombre de 15 `SoundList` que se llaman
  igual).
  - La API de audio de los scripts solo reproduce, para y ajusta el volumen:
    - por nombre: `Sound.playUISoundByName`, `Sound.getUISoundDesc` + `Sound.playSound(desc, bool)` y `playMusic`;
    - por ID: `playSoundId` y `stopSoundId`;
    - y además `stopMenuMusic` y `setMasterVolume`.
  - Las listas de carga que hay nombran paquetes, nunca bancos: los 6 `ResourcePackageNames`
    (`base/game_packages`, `base/preload_scripts`…), `AIEnemy.Package` y otras.

### Cómo llega el juego a un sonido

- **Animaciones:** `SoundTrigger.SoundID` es un `SoundDesc.ID`. De 26 377 `SoundTrigger` con
  `SoundID` (contando los `AnimationList` incrustados en Desc), 25 988 coinciden con algún
  `SoundDesc.ID`. El disparador no tiene campo de banco ni de nombre.
- **Los ID no son globales.** 1 190 ID están en más de un contenedor y 609 de ellos con distinto
  `Name`, `Bank` o `Event`. Por ejemplo, el 122 es `Combat_Level1` en `base/ambient` y
  `Footstep_Creature_Small_Metal_Thin_Land` en `impact_fx/materials`. Los datos encajan con una
  búsqueda en las listas del propio actor (`SoundsArray.SoundsLists` de su Desc). Es una
  inferencia, no se ha comprobado el orden cuando un ID está en dos listas del mismo actor.
- **Scripts de interfaz:** piden el sonido por `Name` en `ui_core/uisounds`. Por ejemplo,
  `ui_merchant/merchantmenu` llama a `Sound.playUISoundByName('UI_MerchantOpen')`, y esa entrada
  (`Sounds[180]`) es `ID 13, Bank UI, Event MerchantOpen`.
- **Voces de diálogo:** van por claves de localización (`LocalizationKey`, `playVO`), no por
  `SoundDesc`. Los gritos y emotes de NPC sí tienen `SoundDesc` en el banco `VO`.
- **Lo que viene de fuera:** 42 de los 275 `SoundList` no reciben ningún `FC` (búsqueda de bytes
  en todo el archivo). Entre ellos están `base/music`, `vo/vo_sounds`, `death/death_vo` y los
  `sfx_vfx_environmental_*`, así que los carga algo externo al obsp (código, niveles o paquetes).
  `base/music` solo tiene la zona 1. Samael llama a
  `visScriptCall('Z4_LD_08_Samael_BossFight_VSM', 'CombatMusic_TurnOFFAmbient')`, un script visual
  de nivel.
- **Música que sí está en el obsp:**
  - la de la pantalla de carga: `ui_core/storyboardloading` usa `UI_start_screen_music_N`, que en
    `ui_core/uisounds` llevan los eventos `MUS_Z1_Theme`…`MUS_Z4_Theme`;
  - la del menú y la de los créditos;
  - la de los jefes;
  - la intensidad de combate: `CombatMusicIntensity` en las oleadas de 6 scripts de encuentros, y
    `Music_Intensity_0x` → `Combat_Intensity_0x` en `sfx_global/global_sounds`.

### Middleware: probablemente Wwise, con nombres y no con ID de Wwise

- **Indicios de Wwise:** `RTPCName = 'Ball_Velocity'` en `rolleyball/rolleyball_anims`, el banco
  `MIX_States` con eventos de estado (`State_*`, `Combat_Intensity_*`) y los prefijos `Play_` y
  `Stop_`. La guía Darksiders2-Modding del autor sitúa el audio en `sounds_streamed/PC`
  (`core.pck`, `en.pck`, `es.pck`). No se ha comprobado con los archivos de audio.
- **El archivo no contiene ShortID de Wwise.** En Wwise, los ID de bancos, eventos y game syncs son
  el FNV-1 de 32 bits del nombre en minúsculas. Nuestra implementación da 1355168291 para `init`,
  el número con el que wwiser dice que aparece `init.bnk`. Comparando con todos los int32 grandes
  del archivo, FNV-1 y FNV-1a, con y sin minúsculas, sobre unas 107 000 cadenas del archivo, solo
  coinciden 2 valores, y sin relación con su fila; por azar cabían unos 0,4. Cada ID comparado con
  su propio `Name`, `Bank` o `Event` no coincide nunca.
- **Consecuencia (inferida):** el juego pasa a Wwise los nombres (`Bank`, `Event`, `RTPCName`) y
  los convierte en tiempo de ejecución, o con una tabla propia que no está en el obsp.

### Los enteros «con aspecto de hash» son, en su mayoría, marcas de tiempo

Los 15 467 int32 distintos con |valor| ≥ 1 000 000 de los BOD (67 453 apariciones) no se comportan
como hashes:

- 11 064 (71,5 %) son fechas Unix entre el 7 de enero de 2010 y el 22 de octubre de 2012;
- de esos, el 80,7 % cae entre las 9 y las 19 h de Austin (sede de Vigil Games) y el 93,2 %, de
  lunes a viernes;
- solo 6 de los 15 467 son negativos, cuando un hash de 32 bits daría la mitad.

En `SoundDesc.ID` pasa lo mismo: 4 745 valores grandes, el 67,1 % en ese intervalo y ninguno
negativo. Los ID pequeños (`1220`, `13`…) parecen secuenciales.

Son, por tanto, identificadores que el editor asignaba al crear cada entrada. Para referenciarlos
hace falta que coincidan, no calcular ningún hash. Un ID nuevo solo necesitaría no repetirse allí
donde se busca, aunque eso no se ha probado en el juego. Quedan excepciones sin estudiar, como
`ProjectileDesc.MeshID` o `InputWindow.ID` negativo.

### Qué implica para un banco modificado o nuevo

- **Mismo banco, mismos eventos:** el obsp no cambia, porque solo guarda los nombres. Si el audio
  pasa de bucle a sonido único o al revés, quizá haya que ajustar `Loop`, `FadeOut` o `FadeCurve`.
- **Banco nuevo:** el obsp puede nombrarlo de dos formas.
  - Cambiar `Bank` y `Event` de un `SoundDesc` existente; la herramienta avisa de las cadenas
    nuevas y calcula su hash. Hay listas compartidas: `death/death_sounds` la usan 137 objetos.
  - Copiar un `SoundDesc` con un `ID` nuevo en una lista del actor y apuntarle un `SoundTrigger`.

  Comprobado en memoria sobre `ui_core/uisounds · Sounds[180]`, sin escribir en disco:

  | Cambio | Aviso de cadena nueva | `prepare_save` y `verify_plan` | Tamaño |
  |---|---|---|---|
  | `Event` → `MerchantBadBuy` | no | pasan | 18 334 463 |
  | `Bank` → `SFX_Character_Archon`, `Event` → `Archon_Air_Impact` | no | pasan | 18 334 512 |
  | `Bank` → `MOD_Test`, `Event` → `MOD_Test_Play` | sí | pasan | 18 334 496 |

  Lo que el obsp no puede hacer es que el juego cargue el banco. Tampoco se sabe si el juego carga
  un banco solo porque un `SoundDesc` lo nombra, ni dónde buscaría uno nuevo (suelto o dentro de
  `core.pck`).
- **Duda abierta:** 71 eventos aparecen con dos bancos distintos, por ejemplo los de Samael en
  `samael/samael_targethelperdesc` y en `samael_common_sounds`. Puede que el motor no exija que el
  evento esté en el banco que se nombra.

### Pruebas en el juego propuestas (2026-10-09; resultados en la sección siguiente)

Sobre `ui_core/uisounds · Sounds[180]`, que suena al abrir la tienda de un comerciante:

1. **Control:** `Event` → `MerchantBadBuy`. Debería oírse el sonido de compra fallida.
2. **Carga por nombre:** `Bank` → `SFX_Character_Archon`, `Event` → `Archon_Air_Impact`, lejos de
   donde aparece el Archon. Si suena, el juego carga el banco que nombra el obsp.
3. **Banco nuevo:** generar `MOD_Test` con el evento `MOD_Test_Play`, con la versión de Wwise del
   juego, colocarlo primero suelto y luego en el `.pck`, y poner esos nombres en la entrada.
4. **Disparador de un personaje:** copiar un `SoundDesc` en `death/death_sounds` con un ID nuevo y
   apuntarle un `SoundTrigger` de `death/death_animations`.

Sin abrir el juego, cargar `core.pck` en wwiser con la lista de bancos y eventos del obsp
confirmaría que es Wwise y que esos son los nombres reales. También daría la versión de Wwise
(cabecera `BKHD` de un banco).

### Resultados en el juego (2026-10-10)

Detalle y evidencia en `research/PRUEBAS_EN_JUEGO.md` (secciones «Audio»).

- **Tienda (pruebas 1 y 2 sobre `ui_core/uisounds`): sin resultado.** El cambio de la apertura no
  llegó a guardarse, y el cierre no se escuchó con atención. Los sonidos de la tienda son cortos y
  poco frecuentes; se pasó a acciones de Death.
- **Prueba 1, control: se cumple.** `death/death_sounds · Sounds[47].Event` (`death_whoosh_jump`,
  ID 60200, el que disparan el salto, el doble salto y 96 animaciones más): `Jump_Whoosh` →
  `Voc_Death_Death`. El salto suena al grito de muerte de Death.
- **Prueba 2, carga por nombre: se cumple.** En la misma entrada, `Bank` → `SFX_Character_Archon`
  y `Event` → `Voc_Archon_Corrupted_Scream`. El doble salto suena al grito del Archon en
  Tripetra, en las Tierras de la Forja. Según el obsp, el Archon es de la zona 3
  (`base/quest_z3mq0_find_archon`, `zone03_archontower`). En la esquiva (`Sounds[42]`) el
  resultado no fue concluyente: el silbido inicial es corto y se mezcla con otros.
- **Queda abierto:**
  - si el banco se carga por el `Bank` del `SoundDesc` o ya estaba cargado (todos al empezar,
    por ejemplo). Se distinguiría nombrando el banco de Death con un evento del Archon;
  - las pruebas 3 (banco nuevo) y 4 (`SoundDesc` nuevo con un `SoundTrigger`).
