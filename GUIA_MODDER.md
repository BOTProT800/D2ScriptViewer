# Guía del modder

Atajos de teclado de D2ScriptViewer y qué se suele modificar en `scripts.obsp`. El
[README](README.md) explica la instalación, el guardado y los parches; esta guía es para
trabajar con la herramienta día a día.

**Leyenda de la segunda parte:**

- **Probado:** se cambió con la herramienta, se jugó y el efecto fue el esperado
  ([research/PRUEBAS_EN_JUEGO.md](research/PRUEBAS_EN_JUEGO.md)).
- **Por explorar:** el tipo de objeto existe en el archivo, pero nadie ha comprobado qué hace
  cada campo; lo que se dice de él se deduce de los nombres.

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
| Ctrl+F | Buscar |
| Alt+← | Atrás en el historial de navegación |
| Alt+→ | Adelante en el historial de navegación |

Ctrl+Z, Ctrl+Y y Ctrl+P no actúan mientras escribes en un campo de texto (un filtro, la celda
que editas…): ahí las teclas son del propio campo. Sal del campo para deshacer cambios del
archivo.

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
| Clic derecho | Menú: ir al destino, editar, revertir la propiedad, estructura, copiar valor y copiar ruta |
| Ctrl+D | Duplicar el elemento de lista o la entrada de mapa (la copia queda justo detrás) |
| Supr | Eliminar el elemento o la entrada |
| Alt+↑ / Alt+↓ | Subir o bajar el elemento dentro de su lista |

- Las teclas de estructura solo actúan sobre elementos de listas y entradas de mapas, y nunca
  en los scripts compilados. **Poner a nulo** y **Rellenar nulo con un objeto…** no tienen
  atajo: clic derecho o Editar → Estructura.
- La línea bajo el árbol explica por qué una fila no se puede editar y, mientras escribes, avisa
  de errores y muestra cómo quedará el valor.
- **Copiar ruta de la propiedad** (clic derecho) da algo como `MoveStates[44].JumpImpulse`: es
  la forma más cómoda de anotar qué cambiaste.

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
| Buscar | Intro en el campo de texto | Buscar |
| Buscar | Intro o doble clic en un resultado | Ir al objeto y a la propiedad |
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
| `SoundList` | 275 | Sonidos por personaje | Por explorar |
| `HitInfoList` | 3 | Información de golpes | Por explorar |
| `InputWindowList` | 5 | Ventanas de entrada (combos, por el nombre) | Por explorar |
| `CharacterConditionalList` | 7 | Condiciones por personaje | Por explorar |
| `ModuleSystem` | 4 | Grafos de módulos | Por explorar |
| `TerrainMaterialDesc` | 42 | Materiales del terreno | Por explorar |

### Cómo encontrar lo que quieres cambiar

- **Por nombre de campo.** Ctrl+F, marca «Nombres de campo» y escribe un término en inglés del
  concepto. `Jump` lleva a `JumpImpulse`; prueba otros que se te ocurran. Si no hay resultados,
  no hay ningún campo con ese texto.
- **Por el número que ves en el juego.** Ctrl+F con un número (`350`) encuentra los enteros y los
  floats con ese valor exacto. Sirve para localizar un dato del que conoces el valor.
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
  Script, los símbolos. Ctrl+F con «Valores y símbolos» encuentra los scripts que tienen el texto
  entre sus símbolos (sus miembros, funciones y estados). Los nombres que solo aparecen dentro
  del código, como el método `setPaused`, no salen en esa búsqueda: búscalos en la exportación
  JSON, que incluye el código desensamblado, o con `python -m d2scriptviewer disasm ruta`.

### Qué no tocar (o tocar con cuidado)

- **Identificadores.** Los campos `…ID`, `…Id`, los que contienen `Hash` y los enteros enormes
  (|valor| ≥ 1 000 000, casi siempre hashes de 32 bits de función desconocida) enlazan con otras
  cosas del juego. La herramienta pide confirmación antes de cambiarlos.
- **Los `Name` de las entradas de una lista**, por lo visto arriba.
- **Claves repetidas.** Tras Ctrl+D sobre una entrada de mapa, cambia la clave de la copia: con
  una clave repetida no se puede guardar.
- **Referencias sin destino.** Tampoco se puede guardar si una referencia apunta a un objeto que
  no existe.
- **Valores extremos.** Multiplicar un valor por 2 se nota y es fácil de deshacer; multiplicarlo
  por 1 000 puede romper la física o la partida. Pruébalos solo con tus partidas copiadas.
- **Cosas que la herramienta no permite** (y no hace falta intentar): renombrar o crear objetos,
  cambiar nombres de campo o de clase, o cambiar el tamaño del código de un script.
