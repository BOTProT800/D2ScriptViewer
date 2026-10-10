# Guía del modder

Atajos de teclado de D2ScriptViewer y qué se suele modificar en `scripts.obsp`. El
[README](README.md) explica la instalación, el guardado y los parches; esta guía es para
trabajar con la herramienta día a día.

**Leyenda de la segunda parte:**

- **Probado:** se cambió con la herramienta, se jugó y el efecto fue el esperado
  ([research/PRUEBAS_EN_JUEGO.md](research/PRUEBAS_EN_JUEGO.md)).
- **Por explorar:** el tipo de objeto existe en el archivo, pero nadie ha comprobado qué hace
  cada campo; lo que se dice de él se deduce de los nombres.
- **No probado en el juego:** se sabe dónde está el dato y la herramienta lo puede cambiar, pero
  nadie ha comprobado en el juego qué pasa al cambiarlo.

## Parte 1 — Atajos de teclado

### En toda la ventana

| Tecla | Acción |
|---|---|
| Ctrl+O | Abrir otro `.obsp` |
| Ctrl+S | Guardar (con una celda abierta, primero confirma su valor; si no es válido, no guarda) |
| Ctrl+Mayús+S | Guardar como… |
| Ctrl+Z | Deshacer |
| Ctrl+Y | Rehacer |
| Ctrl+P | Cambios pendientes (antes → después de cada propiedad) |
| Ctrl+F | Buscar en el objeto abierto: lleva a la barra sobre las propiedades |
| Ctrl+Mayús+F | Buscar en todo el archivo |
| Ctrl+G | Ir a una ruta: abre la barra «Ir a» sobre las propiedades (también en Ir → Ir a la ruta…) |
| Alt+← | Atrás en el historial de navegación |
| Alt+→ | Adelante en el historial de navegación |

Ctrl+Z, Ctrl+Y y Ctrl+P no actúan mientras escribes en un campo de texto (un filtro, la barra
de búsqueda, la barra «Ir a», la celda que editas…): ahí las teclas son del propio campo. Sal del
campo para deshacer cambios del archivo.

Los menús no tienen letras subrayadas. Las acciones sin atajo están en ellos: Archivo →
Restaurar original…, Exportar a JSON y CSV…, Exportar parche…, Aplicar parche…, y Editar →
Revertir objeto.

### Lista de objetos (izquierda)

| Tecla | Acción |
|---|---|
| ↑ / ↓ | Seleccionar el objeto anterior o siguiente; se abre en el centro al seleccionarlo |
| → | Desplegar el grupo |
| ← | Plegar el grupo o subir al grupo que lo contiene |
| Intro o Espacio | Desplegar o plegar el grupo |
| RePág / AvPág | Desplazar la lista una página |
| Tab | Pasar entre los filtros (agrupar, tipo, clase, texto) y la lista |

Los filtros se aplican mientras escribes. Agrupar por **Carpeta** usa las carpetas del editor del
juego (`oc\Body\slayer`…); por **Ruta**, el prefijo de la ruta (`death/…`); por **Tipo**, la
categoría del objeto.

### Propiedades (centro)

| Tecla | Acción |
|---|---|
| ↑ / ↓, → / ← | Moverse, desplegar y plegar, como en la lista de objetos |
| Intro | En un valor: editarlo. En una referencia (`→ …`): ir a su destino. En un contenedor: desplegar o plegar |
| F2 | Editar el valor. En una referencia: abrir el selector para cambiar su destino |
| Doble clic | Igual que Intro |
| Clic derecho | Menú: ir al destino, editar, revertir la propiedad, estructura, copiar valor, copiar la ruta de la propiedad y copiar la ruta completa |
| Ctrl+D | Duplicar el elemento de lista o la entrada de mapa (la copia queda justo detrás) |
| Supr | Eliminar el elemento o la entrada |
| Alt+↑ / Alt+↓ | Subir o bajar el elemento dentro de su lista |
| F3 / Mayús+F3 | Resultado siguiente o anterior de la búsqueda en el objeto |

- Las teclas de estructura solo actúan sobre elementos de listas y entradas de mapas, y nunca
  en los scripts compilados. **Poner a nulo** y **Rellenar nulo con un objeto…** no tienen
  atajo: clic derecho o Editar → Estructura.
- La línea bajo el árbol explica por qué una fila no se puede editar y, mientras escribes, avisa
  de errores y muestra cómo quedará el valor.
- **Copiar ruta de la propiedad** (clic derecho) da algo como `MoveStates[44].JumpImpulse`: es
  la forma más cómoda de anotar qué cambiaste. **Copiar ruta completa** pone el objeto delante:
  `death/playercommon_movestates · MoveStates[44].JumpImpulse`. Las dos se pegan en Ctrl+G para
  volver a esa fila.

### Búsqueda en el objeto (barra sobre las propiedades)

Tres campos, uno por columna del árbol: **Nombre**, **Tipo** y **Valor**. Buscan en todo el
objeto abierto, también dentro de los nodos y tramos que no has desplegado.

- **Nombre** y **Valor** buscan el texto que contienen, tal como se ve en la columna y sin
  distinguir mayúsculas. En una referencia, el valor es `→` y el destino: `death_desc` encuentra
  las referencias a `death/death_desc`.
- **Tipo** es exacto (`int32`, `float32`, `nombre`, `referencia`, `op_3A`…). La lista (↓ o la
  flecha) trae los tipos del objeto abierto; «(cualquiera)» no filtra.
- Un campo vacío no filtra, y los que tienen texto se combinan con «y».
- El contador dice «3 de 7» sobre un resultado, «7 resultados» si la fila seleccionada no es
  uno, y «Sin resultados» si no hay ninguno.
- Los campos se conservan al cambiar de objeto, y los resultados se recalculan tras editar,
  deshacer o cambiar la estructura.

| Tecla | Acción |
|---|---|
| Ctrl+F | Ir a la barra, al último campo usado y con su texto seleccionado (cancela la celda que editabas) |
| Escribir | Tras una pausa breve, va al primer resultado a partir de la fila seleccionada |
| Intro o F3 | Resultado siguiente; tras el último vuelve al primero |
| Mayús+Intro o Mayús+F3 | Resultado anterior |
| ‹ / › | Lo mismo con el ratón |
| F2 | Editar la fila seleccionada, como en el árbol |
| Escape | Volver al árbol (las flechas se mueven desde el resultado) |

### Ir a una ruta (barra «Ir a» sobre las propiedades)

Ctrl+G abre una barra entre la de búsqueda y el árbol. Escribe o pega una ruta y pulsa Intro: el
árbol se abre hasta esa fila y la selecciona, también dentro de los tramos de las listas largas
(`[1000…1499]`).

- **Formatos:**
  - `MoveStates[44].JumpImpulse`: una fila del objeto abierto, como la da «Copiar ruta de la
    propiedad». En los scripts, `Funciones.onInit.0x004E`.
  - `death/playercommon_movestates · MoveStates[44].JumpImpulse`: salta a ese objeto y a esa
    fila. Si tu teclado no tiene `·`, vale `::` (`death/playercommon_movestates::MoveStates[44].JumpImpulse`).
    Alt+← vuelve al objeto anterior.
  - `death/death`: abre el objeto.
- **Al abrir la barra**, si el portapapeles contiene algo que parece una ruta, ya aparece escrito
  y seleccionado. Si no, queda la última ruta que usaste.
- **Mayúsculas y tildes:** primero se busca el nombre exacto. Si no está, se acepta sin distinguir
  mayúsculas ni tildes (`movestates[44].jumpimpulse`, `Parametros`), siempre que solo haya una
  posibilidad. En los scripts, `0x4e` vale como `0x004E`.
- **Si la ruta falla a mitad**, el árbol se queda en la última fila válida, la barra sigue abierta
  con el tramo que falló seleccionado y la línea bajo el árbol dice por qué: los nombres parecidos
  («`JumpImpuls` no es un campo de MoveStates[44]. Parecidos: `JumpImpulse`»), cuántos elementos
  tiene la lista o qué se esperaba. Si el objeto no existe, no se mueve nada y se sugieren los
  objetos de nombre parecido.
- Los índices son números: `MoveStates[Jump]` (por el `Name` del elemento) no está disponible.

| Tecla | Acción |
|---|---|
| Ctrl+G | Abrir la barra o volver a ella (cancela la celda que editabas) |
| Intro | Ir a la ruta. Si llega, la barra se cierra y el foco pasa al árbol: F2 edita la fila |
| Escape | Cerrar la barra y volver al árbol; si el objeto aún se estaba abriendo, ya no salta a la fila |

### Editor en la celda

| Tecla | Acción |
|---|---|
| Intro (también la del teclado numérico) | Confirmar |
| Escape | Cancelar |
| Clic fuera de la celda o girar la rueda del ratón | Cancelar |
| ↓ | En nombres (cadenas con hash) y bools: abrir la lista de opciones |

En un bool, elegir una opción de la lista confirma. En un nombre, la lista sugiere los que ya
existen en el archivo y se filtra con lo que escribes; elegir uno lo copia en la celda y hay que
confirmar con Intro.

### Detalles (derecha)

En la pestaña **Referencias**, Intro o doble clic sobre una fila de «Apunta a» o «Usado por»
abre ese objeto. Alt+← vuelve al anterior.

### Ventanas

| Ventana | Tecla | Acción |
|---|---|---|
| Buscar en todo el archivo (Ctrl+Mayús+F) | Intro en el campo de texto | Buscar |
| Buscar en todo el archivo | Intro o doble clic en un resultado | Ir al objeto y a la propiedad |
| Cambios pendientes | Intro o doble clic | Ir a la propiedad cambiada |
| Cambios pendientes | Escape | Cerrar |
| Cambiar referencia | Escribir | Filtrar por ruta o nombre (el filtro tiene el foco al abrir) |
| Cambiar referencia | Intro o doble clic en la lista | Aceptar el objeto elegido |
| Cambiar referencia | Escape | Cancelar |
| Rellenar nulo | Doble clic | Copiar el ejemplo elegido |
| Rellenar nulo | Escape | Cancelar |

En **Cambiar referencia**, Intro solo acepta cuando el foco está en la lista: pasa a ella con un
clic o con Tab.

### Cómo se escriben los valores

| Tipo | Se acepta | Ejemplos |
|---|---|---|
| Entero (int32) | Decimal, o `0x…` como patrón de 32 bits; `_` como separador | `700`, `-1`, `0xFFFFFFFF`, `1_000` |
| Float (float32) | Punto o coma decimal; sin NaN ni infinitos | `700`, `0.5`, `0,5`, `1e-3` |
| Bool | `true`, `1`, `sí`, `verdadero`, `yes`, `on` / `false`, `0`, `no`, `falso`, `off` | `true` |
| Cadena sin hash (`'…'`) | Texto ASCII | `flag_mi_mod` |
| Nombre (cadena con hash) | Un nombre del archivo o uno nuevo en ASCII (pide confirmación) | `D_WScy_Combo04` |

Los nombres distinguen mayúsculas: `D_Jump` y `d_jump` son nombres distintos para el juego.

## Parte 2 — Qué se suele modificar

### Antes de empezar: copia tus partidas

**Haz una copia de tus partidas guardadas antes de probar cambios**, y sobre todo antes de
probar límites (valores extremos, listas duplicadas o vaciadas, scripts parcheados). Si el juego
guarda la partida mientras un cambio lo tiene en mal estado, esa partida puede quedar dañada.

- La herramienta solo protege `scripts.obsp`: `scripts.original.obsp`, las copias de
  `.d2sv_backups\` y Restaurar original… devuelven el archivo de scripts, **no tus partidas**.
  Una partida dañada no se arregla restaurando el original.
- Copia la carpeta de partidas entera a otro sitio, y repite la copia cada vez que llegues a un
  punto que no quieras perder.
- Si tienes la nube de Steam activada para el juego, una partida dañada puede subirse y
  sustituir la que estaba en la nube. Mantén tu propia copia fuera de la carpeta del juego.
- Para probar, mejor una partida nueva o una que no te importe perder.

### Cómo trabajar

1. Copia tus partidas (ver arriba) y cierra el juego (con él abierto no se puede guardar).
2. Cambia **una sola cosa**, o unas pocas relacionadas.
3. Ctrl+P para revisar los cambios pendientes y Ctrl+S para guardar. La primera vez se crea
   `scripts.original.obsp`.
4. Prueba en el juego, en una partida de prueba. Si no ves efecto, prueba también con una
   partida nueva: es posible que la partida guarde algunos valores y conserve los antiguos
   (**hipótesis**, no comprobado).
5. Cuando funcione, Archivo → Exportar parche…, para no perderlo si Steam restaura el archivo.
6. Para volver al original: Archivo → Restaurar original… Si una partida quedó mal, sustitúyela
   por tu copia.

### Lo que ya está probado en el juego

| Qué cambia | Objeto | Propiedad | Ejemplo | Resultado |
|---|---|---|---|---|
| Altura del salto de Death | `death/playercommon_movestates` (`CharacterMoveStateList`) | `MoveStates[44].JumpImpulse` (float), el estado con `Name` = `Jump` | 350 → 700 | Salto normal mucho más alto |
| Animación que se reproduce | `death/death_animations` (`AnimationList`) | `Animations[n].AnimationName` (nombre con hash) | `D_Jump` → `D_WScy_Combo04` | El salto reproduce un combo de guadaña |
| Lógica de un script | `ui_core/pausemenu` (script) | `Funciones.onInit.0x004E`, el `true` de `Game.setPaused(true)` | `true` → `false` | El menú de pausa ya no detiene el juego |
| Estructura de una lista | `death/playercommon_movestates` | Duplicar `MoveStates[0]` (Ctrl+D) | — | El juego carga la lista más larga sin problemas |
| Texto sin hash más largo | `base/quest_test_dialog` (`DialogSet`) | `Dialogs[0].Actions[1].FlagID` | +5 caracteres | El archivo cambia de tamaño y el juego lo carga |
| Sonido de una acción | `death/death_sounds` (`SoundList`) | `Sounds[47].Event`, la entrada con `Name` = `death_whoosh_jump` | `Jump_Whoosh` → `Voc_Death_Death` | Saltar suena al grito de muerte de Death |
| Sonido de otro personaje | `death/death_sounds` | `Sounds[47].Bank` y `Sounds[47].Event` | `SFX_Character_Archon` y `Voc_Archon_Corrupted_Scream` | El doble salto suena al grito del Archon, también lejos de su zona |

Las rutas de la columna Propiedad se pueden pegar en Ctrl+G con el objeto abierto, o con el
objeto delante: `death/playercommon_movestates · MoveStates[44].JumpImpulse`,
`ui_core/pausemenu · Funciones.onInit.0x004E`, `base/quest_test_dialog · Dialogs[0].Actions[1].FlagID`
o `death/death_sounds · Sounds[47].Event`.
En `Animations[n].AnimationName`, cambia `n` por el índice de la animación.

Lo que enseñan esas pruebas:

- **Busca los elementos de una lista por su `Name`, no por su índice.** Duplicar `MoveStates[0]`
  desplazó el estado `Jump` de `[44]` a `[45]`. Los índices cambian; el `Name` no.
- **El `Name` de una entrada es la clave por la que el juego la busca: no lo cambies.** En la
  prueba de la fase 8 se cambió por error `Animations[435].Name` (`PaperDoll_Idle`) en lugar de
  `AnimationName`, la fila de debajo, y el muñeco del menú se quedó sin animar. Para cambiar una
  animación, edita `AnimationName`.
- **Un `AnimationName` nuevo** debe ser el nombre (sin `.anm`) de una animación que el juego trae
  en sus `.upak`. Si pones una animación que no es en bucle donde se espera un reposo (por ejemplo
  `PaperDoll_Idle`), se reproduce una vez y se queda congelada en el último fotograma.
- **En los scripts** solo se cambian literales `int`, `float` y `bool` sin alterar tamaños. El
  número de argumentos de una llamada (el `int n` antes de la llamada) es de solo lectura.
- **Para cambiar un sonido, edita `Event`** (y `Bank` si el evento es de otro banco), no `ID` ni
  `Name`. Cada animación dispara sus sonidos por número (`SoundID` en `Triggers`), que es el `ID`
  de una entrada de la lista de sonidos del personaje. Así, el cambio afecta a todas las
  animaciones que usan esa entrada: `death_whoosh_jump` suena en el salto, el doble salto, las
  cornisas y más. Los eventos que existen salen de los `Event` de otras entradas: busca uno con
  Ctrl+Mayús+F. Que el juego cargue un banco nuevo, que no venga con él, está sin probar.
- **Elige para probar un sonido que se repita y se oiga bien.** Un silbido corto que desaparece se
  nota poco; un grito donde había un silbido, sí.

### No probado en el juego: los huecos del inventario

Un ejemplo de cómo llegar a un dato con la búsqueda en el objeto. **No se ha probado en el
juego**: se sabe dónde está el número y que la herramienta lo puede cambiar, no qué pasa al
cambiarlo.

1. Abre el script `death/death` (el filtro de la lista de objetos ayuda a encontrarlo).
2. Ctrl+F. En **Tipo**, escribe o elige `op_3A`; en **Valor**, escribe `NumSlots`. El contador
   dice «1 de 7».
3. Son las siete filas `op_3A NumSlots` de `Funciones.onInit`, de `0x0770` a `0x0A4A`. Intro
   las recorre. También se llega a la primera con Ctrl+G y `death/death · Funciones.onInit.0x0770`.
4. El número está en la fila de debajo de cada una (Escape y ↓): un `int32` que vale 21, 21, 21,
   22, 22, 22 y 21. Es un literal del código, así que F2 lo cambia sin alterar el tamaño del
   script.

Por el nombre, cada uno sería el número de huecos de una parte del inventario. Qué parte es cada
uno, si el juego acepta otros valores y si la interfaz los muestra está por comprobar. Si lo
pruebas, copia antes tus partidas (ver arriba): lo que llevas en el inventario se guarda en la
partida.

### Por explorar: dónde suele estar cada cosa

Categorías del archivo (columna «Tipo» de la lista de objetos y filtro **Tipo**):

| Tipo | Objetos | Qué contiene | Interés para el modder |
|---|---|---|---|
| `Desc` | 1 668 | Descripciones de actores, personajes, proyectiles, ítems… (`death/death_desc` es Death) | Floats e ints de cada entidad. Es el primer sitio donde mirar estadísticas |
| `CharacterMoveStateList` | 275 | Estados de movimiento por personaje | Salto (probado), y por explorar el resto de estados |
| `AnimationList` | 1 071 | Qué animación usa cada acción | Cambiar animaciones (probado) |
| `FloatTable` | 65 | Tablas de floats con nombres de fila y de columna | Tablas numéricas: expórtalas a CSV para ver qué es cada una |
| `Instancia` | 757 | `ItemGeneratorTable`, `Quest`, `DialogSet` y otras clases de script | Generación de objetos, misiones y diálogos, a juzgar por los nombres |
| `Script` | 3 690 | Scripts compilados | Literales del código (probado) |
| `SoundList` | 275 | Sonidos por personaje (`ID`, `Name`, `Bank`, `Event`) | Cambiar sonidos (probado) |
| `HitInfoList` | 3 | Información de golpes | Por explorar |
| `InputWindowList` | 5 | Ventanas de entrada (combos, por el nombre) | Por explorar |
| `CharacterConditionalList` | 7 | Condiciones por personaje | Por explorar |
| `ModuleSystem` | 4 | Grafos de módulos | Por explorar |
| `TerrainMaterialDesc` | 42 | Materiales del terreno | Por explorar |

### Cómo encontrar lo que quieres cambiar

- **Por su ruta.** Si ya sabes la ruta (de tus notas, de esta guía o de un parche), Ctrl+G y
  pégala.
- **Por nombre de campo.** Ctrl+Mayús+F, marca «Nombres de campo» y escribe un término en inglés
  del concepto. `Jump` lleva a `JumpImpulse`; prueba otros que se te ocurran. Si no hay
  resultados, no hay ningún campo con ese texto.
- **Por el número que ves en el juego.** Ctrl+Mayús+F con un número (`350`) encuentra los
  enteros y los floats con ese valor exacto. Sirve para localizar un dato del que conoces el
  valor.
- **Dentro de un objeto grande.** Ctrl+F y los campos Nombre, Tipo y Valor de la barra, en lugar
  de desplegar el árbol a mano: Nombre `JumpImpulse` en `death/playercommon_movestates` recorre
  las filas con ese nombre sin abrir los estados uno a uno. La barra busca el texto contenido
  (Valor `350` también encuentra `3500`); para el valor exacto de un número, usa la búsqueda en
  todo el archivo.
- **Siguiendo referencias.** Desde el `Desc` de un personaje, las filas `→ …` llevan a sus listas
  de movimientos, animaciones, etc. (`death/death_desc` → `MoveStateListArray.MoveStateLists[0]`
  → `death/playercommon_movestates`). En Detalles → Referencias, «Usado por» dice quién apunta al
  objeto abierto. Alt+← vuelve atrás.
- **Por clase.** El filtro **Clase** de la izquierda lista todos los objetos de una clase
  (`PlayerJumpDesc`, `DialogSet`…).
- **Fuera de la herramienta.** Archivo → Exportar a JSON y CSV… vuelca todo a una carpeta donde
  puedes buscar con cualquier editor, y cada `FloatTable` a un CSV que se abre en una hoja de
  cálculo. Es solo para leer: los cambios se hacen en la herramienta.
- **Scripts.** El panel central muestra el código desensamblado de cada función; Detalles →
  Script, los símbolos. Ctrl+Mayús+F con «Valores y símbolos» encuentra los scripts que tienen el
  texto entre sus símbolos (sus miembros, funciones y estados). Los nombres que solo aparecen
  dentro del código, como el método `setPaused`, no salen en esa búsqueda. Con el script abierto,
  la barra sí los encuentra (Ctrl+F, Valor `setPaused`). Para buscarlos en todos los scripts a la
  vez, usa la exportación JSON, que incluye el código desensamblado, o
  `python -m d2scriptviewer disasm ruta`.

### Qué no tocar (o tocar con cuidado)

- **Identificadores.** Los campos `…ID`, `…Id`, los que contienen `Hash` y los enteros enormes
  (|valor| ≥ 1 000 000, casi siempre identificadores que el editor creó a partir de la fecha)
  enlazan con otras cosas del juego. Por ejemplo, el `SoundID` de un disparador de animación es el
  `ID` de un sonido de la lista del personaje. La herramienta pide confirmación antes de cambiarlos.
- **Los `Name` de las entradas de una lista**, por lo visto arriba.
- **Claves repetidas.** Tras Ctrl+D sobre una entrada de mapa, cambia la clave de la copia: con
  una clave repetida no se puede guardar.
- **Referencias sin destino.** Tampoco se puede guardar si una referencia apunta a un objeto que
  no existe.
- **Valores extremos.** Multiplicar un valor por 2 se nota y es fácil de deshacer; multiplicarlo
  por 1 000 puede romper la física o la partida. Pruébalos solo con tus partidas copiadas.
- **Cosas que la herramienta no permite** (y no hace falta intentar): renombrar o crear objetos,
  cambiar nombres de campo o de clase, o cambiar el tamaño del código de un script.
