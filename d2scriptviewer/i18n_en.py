# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Catálogo inglés de la interfaz (fase 12).

``MESSAGES`` va del texto español del código a su traducción; un término del vocabulario
lleva su contexto, ``(contexto, texto)``. ``PLURALS`` va de ``(singular, plural)`` en
español a ``(singular, plural)`` en inglés. ``tests/test_i18n.py`` comprueba que cada texto
marcado en el código tiene su entrada con los mismos marcadores, y que no sobra ninguna.
"""

from __future__ import annotations

MESSAGES: dict[object, str] = {
    # --- Vocabulario: etiquetas de las rutas («ruta») ---------------------------------------
    ("ruta", "(raíz)"): "(root)",
    ("ruta", "clave"): "key",
    ("ruta", "valor"): "value",
    ("ruta", "Versión"): "Version",
    ("ruta", "Símbolos"): "Symbols",
    ("ruta", "Hash de ruta"): "Path hash",
    ("ruta", "Grupo"): "Group",
    ("ruta", "Nombre"): "Name",
    ("ruta", "Clase base"): "Base class",
    ("ruta", "Miembros"): "Members",
    ("ruta", "Valores iniciales"): "Initial values",
    ("ruta", "Funciones"): "Functions",
    ("ruta", "Estados"): "States",
    ("ruta", "Parámetros"): "Parameters",
    # --- Vocabulario: la columna Tipo («tipo») ----------------------------------------------
    ("tipo", "cadena"): "string",
    ("tipo", "nombre"): "name",
    ("tipo", "referencia"): "reference",
    ("tipo", "nulo"): "null",
    ("tipo", "objeto"): "object",
    ("tipo", "lista"): "list",
    ("tipo", "pares"): "pairs",
    ("tipo", "mapa"): "map",
    ("tipo", "tupla"): "tuple",
    ("tipo", "par"): "pair",
    ("tipo", "tramo"): "range",
    ("tipo", "función"): "function",
    ("tipo", "parámetro"): "param",
    ("tipo", "fin"): "end",
    ("tipo", "método"): "method",
    ("tipo", "llamada"): "call",
    ("tipo", "línea"): "line",
    ("tipo", "tipo {number}"): "type {number}",
    # --- Vocabulario: la categoría de un objeto («categoría») -------------------------------
    ("categoría", "Instancia"): "Instance",
    ("categoría", "Tipo {kind}"): "Type {kind}",
    # --- Filas del panel de propiedades -----------------------------------------------------
    "{name} (script, grupo {group})": "{name} (script, group {group})",
    "sin código": "no code",
    "función · {params} · {size:,} bytes": "function · {params} · {size:,} bytes",
    "sin valor por defecto · banderas 0x{flags:02X}": "no default value · flags 0x{flags:02X}",
    "{count:,} (ver pestaña Script)": "{count:,} (see the Script tab)",
    "la raíz": "the root",
    # --- Búsqueda en el objeto y lista de objetos -------------------------------------------
    "(cualquiera)": "(any)",
    "Todos los tipos": "All types",
    ("agrupar", "Carpeta"): "Folder",
    ("agrupar", "Ruta"): "Path",
    ("agrupar", "Tipo"): "Type",
    # --- Ventana principal ------------------------------------------------------------------
    "Sin archivo": "No file",
    "Abre un scripts.obsp con Archivo → Abrir (Ctrl+O)": "Open a scripts.obsp with File → Open (Ctrl+O)",
    "Visor y editor de scripts.obsp — Darksiders II Deathinitive Edition":
        "scripts.obsp viewer and editor — Darksiders II Deathinitive Edition",
    "{dirty}{name}{app} {version} — scripts.obsp de Darksiders II Deathinitive Edition":
        "{dirty}{name}{app} {version} — Darksiders II Deathinitive Edition scripts.obsp",
    "{app} {version}\n\nVisor y editor de scripts.obsp de Darksiders II Deathinitive Edition.\n\nLicencia MIT · BOTProT800":
        "{app} {version}\n\nViewer and editor for the Darksiders II Deathinitive Edition scripts.obsp."
        "\n\nMIT License · BOTProT800",
    "Selecciona un objeto en el panel de la izquierda.": "Select an object in the left panel.",
    "Indexando referencias y cadenas en segundo plano…": "Indexing references and strings in the background…",
    "Espera a que termine la operación en curso para cambiar el idioma":
        "Wait for the current operation to finish before changing the language",
    "Idioma de la interfaz: {language}": "Interface language: {language}",
    # --- Menús ------------------------------------------------------------------------------
    "Archivo": "File",
    "Abrir…": "Open…",
    "Guardar": "Save",
    "Guardar como…": "Save As…",
    "Ctrl+Mayús+S": "Ctrl+Shift+S",
    "Restaurar original…": "Restore Original…",
    "Exportar a JSON y CSV…": "Export to JSON and CSV…",
    "Exportar parche…": "Export Patch…",
    "Aplicar parche…": "Apply Patch…",
    "Copia rotativa de la versión anterior (últimas {count})": "Rotating backup of the previous version (last {count})",
    "Salir": "Exit",
    "Editar": "Edit",
    "Deshacer": "Undo",
    "Rehacer": "Redo",
    "Deshacer: {action}": "Undo: {action}",
    "Rehacer: {action}": "Redo: {action}",
    "Editar valor": "Edit Value",
    "Revertir objeto": "Revert Object",
    "Estructura": "Structure",
    "Duplicar elemento": "Duplicate Item",
    "Eliminar elemento": "Delete Item",
    "Supr": "Del",
    "Subir": "Move Up",
    "Bajar": "Move Down",
    "Poner a nulo": "Set to Null",
    "Rellenar nulo con un objeto…": "Fill Null with an Object…",
    "Cambios pendientes…": "Pending Changes…",
    "Buscar": "Search",
    "Buscar en el objeto": "Find in Object",
    "Buscar en todo el archivo…": "Find in Whole File…",
    "Ctrl+Mayús+F": "Ctrl+Shift+F",
    "Ir": "Go",
    "Atrás": "Back",
    "Adelante": "Forward",
    "Alt+Izquierda": "Alt+Left",
    "Alt+Derecha": "Alt+Right",
    "Ir a la ruta…": "Go to Path…",
    "Ayuda": "Help",
    "Acerca de": "About",
    # --- Deshacer y rehacer -----------------------------------------------------------------
    "Editar {label}": "Edit {label}",
    "Revertir {label}": "Revert {label}",
    "Duplicar {label}": "Duplicate {label}",
    "Eliminar {label}": "Delete {label}",
    "Subir {label}": "Move up {label}",
    "Bajar {label}": "Move down {label}",
    "Poner a nulo {label}": "Set to null {label}",
    "Rellenar {label}": "Fill {label}",
    "Aplicar {name}": "Apply {name}",
    "Deshecho: {description}": "Undone: {description}",
    "Rehecho: {description}": "Redone: {description}",
    # --- Guardar ----------------------------------------------------------------------------
    "Espera a que termine el guardado": "Wait for the save to finish",
    "(«No» los descarta.)": "(“No” discards them.)",
    "¿Guardarlos antes de abrir otro archivo?": "Save them before opening another file?",
    "¿Guardarlos antes de salir?": "Save them before exiting?",
    "{copy} ya existe y no se tocará.": "{copy} already exists and will not be touched.",
    "Antes se creará {copy}: copia exacta del archivo actual, verificada y de solo lectura.":
        "{copy} will be created first: an exact copy of the current file, verified and read-only.",
    "Vas a sobrescribir {target} en la instalación del juego.\n\n• {copy_note}\n• Darksiders II debe estar cerrado.\n"
    "• «Verificar integridad» de Steam devolverá el original.\n\n¿Guardar?":
        "You are about to overwrite {target} in the game installation.\n\n• {copy_note}\n"
        "• Darksiders II must be closed.\n• Steam’s “Verify integrity” will bring back the original.\n\nSave?",
    "… y {count:,} más": "… and {count:,} more",
    "Avisos antes de guardar:\n{warnings}\n\n¿Guardar de todos modos?":
        "Warnings before saving:\n{warnings}\n\nSave anyway?",
    "Guardando {name}…": "Saving {name}…",
    "No se guardó el archivo.\n\n{message}": "The file was not saved.\n\n{message}",
    "No se pudo abrir el archivo.\n\n{message}": "The file could not be opened.\n\n{message}",
    "Los archivos *.original.obsp son copias del original y nunca se sobrescriben. Elige otro nombre.":
        "*.original.obsp files are original backups and are never overwritten. Choose another name.",
    "Copia del original (original de Steam): solo «Guardar como»": "Original backup (Steam original): “Save As” only",
    "Copia del original: solo «Guardar como»": "Original backup: “Save As” only",
    "Original de Steam": "Steam original",
    "Modificado (copia del original en {copy})": "Modified (original backup in {copy})",
    "No es el original de Steam y no hay copia del original": "Not the Steam original, and there is no original backup",
    "{name} está abierto por otro programa. Cierra Darksiders II y vuelve a intentarlo.":
        "{name} is open in another program. Close Darksiders II and try again.",
    "Guardado {name}: {size:,} bytes, SHA-256 {sha}…": "Saved {name}: {size:,} bytes, SHA-256 {sha}…",
    "Copia del original creada: {copy} (original de Steam), verificada y de solo lectura.":
        "Original backup created: {copy} (Steam original), verified and read-only.",
    "Copia del original creada: {copy} (archivo previo, que ya venía modificado), verificada y de solo lectura.":
        "Original backup created: {copy} (the previous file, which was already modified), verified and read-only.",
    "La copia del original ({copy}) ya existía y no se ha tocado.":
        "The original backup ({copy}) already existed and was not touched.",
    "Versión anterior guardada en {folder}\\{name}.": "Previous version saved in {folder}\\{name}.",
}

PLURALS: dict[tuple[str, str], tuple[str, str]] = {
    ("{count:,} objeto  •  {size}  •  SHA-256 {sha}…", "{count:,} objetos  •  {size}  •  SHA-256 {sha}…"):
        ("{count:,} object  •  {size}  •  SHA-256 {sha}…", "{count:,} objects  •  {size}  •  SHA-256 {sha}…"),
    ("Hay {count:,} cambio sin guardar.", "Hay {count:,} cambios sin guardar."):
        ("There is {count:,} unsaved change.", "There are {count:,} unsaved changes."),
    ("{count:,} elemento", "{count:,} elementos"): ("{count:,} item", "{count:,} items"),
    ("{count:,} parámetro", "{count:,} parámetros"): ("{count:,} parameter", "{count:,} parameters"),
    ("{count} función", "{count} funciones"): ("{count} function", "{count} functions"),
    ("{count} miembro", "{count} miembros"): ("{count} member", "{count} members"),
    ("{count} valor", "{count} valores"): ("{count} value", "{count} values"),
    ("{count} estado", "{count} estados"): ("{count} state", "{count} states"),
}


def _merge(target: dict, section: dict) -> None:
    """Añade una sección a ``target``; la misma clave con otra traducción es un error."""
    for key, value in section.items():
        if target.get(key, value) != value:
            raise ValueError(f"Dos traducciones distintas para {key!r}")
        target[key] = value


# --- Secciones por módulo -------------------------------------------------------------------

# edits.py: validación y avisos
_merge(MESSAGES, {
    "Los valores de tipo {type} no se pueden editar todavía": "Values of type {type} cannot be edited yet",
    "Escribe un número entero": "Type an integer",
    "{text} no cabe en un int32": "{text} does not fit in an int32",
    "{text} ocupa más de 32 bits": "{text} takes more than 32 bits",
    "«{text}» no es un número entero (usa dígitos o 0x seguido de hexadecimal)":
        "“{text}” is not an integer (use digits, or 0x followed by hexadecimal)",
    "{number} está fuera del rango de int32 ({minimum} … {maximum})": "{number} is out of the int32 range ({minimum} … {maximum})",
    "Escribe un número": "Type a number",
    "No se admiten NaN ni infinitos": "NaN and infinities are not allowed",
    "«{text}» no es un número": "“{text}” is not a number",
    "{text} no cabe en un float32 (máximo ±{maximum:.7g})": "{text} does not fit in a float32 (maximum ±{maximum:.7g})",
    "Escribe true o false": "Type true or false",
    "Solo se admiten caracteres ASCII": "Only ASCII characters are allowed",
    "La cadena no puede contener el carácter nulo": "The string cannot contain the null character",
    "La cadena supera los {count:,} caracteres": "The string is longer than {count:,} characters",
    "Aún se está construyendo el diccionario de cadenas; espera unos segundos":
        "The string dictionary is still being built; wait a few seconds",
    "«{text}» tiene el mismo hash ({hash:016X}) que «{other}», que ya está en el archivo: el juego no podría distinguirlas":
        "“{text}” has the same hash ({hash:016X}) as “{other}”, which is already in the file: the game could not tell them apart",
    "«{text}» no aparece en el archivo: es una cadena nueva (hash {hash:016X}). El juego solo la reconocerá si existe algo con ese nombre, como un recurso o una animación.":
        "“{text}” does not appear in the file: it is a new string (hash {hash:016X}). The game will only recognize it if "
        "something with that name exists, such as a resource or an animation.",
    "«{name}»": "“{name}”",
    "Ojo: en el archivo está {names}, que solo difiere en mayúsculas, y el hash las distingue.":
        "Careful: the file has {names}, which differs only in case, and the hash tells them apart.",
    "Los valores de tipo {type} no se editan escribiendo": "Values of type {type} are not edited by typing",
    "Se guardará como float32 {value} · hex {raw}": "Will be saved as float32 {value} · hex {raw}",
    "Se guardará como float32 {value} (exacto {exact}) · hex {raw}": "Will be saved as float32 {value} (exactly {exact}) · hex {raw}",
    "Cadena conocida · hash {hash:016X}": "Known string · hash {hash:016X}",
    "Cadena nueva, no aparece en el archivo · hash {hash:016X} · ojo: existe «{other}»":
        "New string, not in the file · hash {hash:016X} · careful: “{other}” exists",
    "Cadena nueva, no aparece en el archivo · hash {hash:016X}": "New string, not in the file · hash {hash:016X}",
    "el campo se llama «{field}»": "the field is called “{field}”",
    "el valor actual ({value}, 0x{raw:08X}) parece un hash": "the current value ({value}, 0x{raw:08X}) looks like a hash",
    "{first} y {second}": "{first} and {second}",
    "Esta propiedad parece un identificador: {reasons}. Cambiarla puede romper enlaces que el juego resuelve por ese valor.":
        "This property looks like an identifier: {reasons}. Changing it can break links that the game resolves by that value.",
    "Solo las listas y los mapas admiten añadir, quitar o mover elementos": "Only lists and maps allow adding, removing or moving items",
})
_merge(PLURALS, {
    ("{count:,} carácter ASCII (antes {before:,})", "{count:,} caracteres ASCII (antes {before:,})"):
        ("{count:,} ASCII character (was {before:,})", "{count:,} ASCII characters (was {before:,})"),
})

# document.py: rutas y operaciones
_merge(MESSAGES, {
    "Una ruta ocupa una sola línea": "A path takes a single line",
    "La ruta lleva un carácter invisible (U+{code:04X}): bórralo": "The path contains an invisible character (U+{code:04X}): delete it",
    "El archivo guardado no tiene los mismos objetos que el documento": "The saved file does not have the same objects as the document",
    "En los scripts compilados solo se editan, sin cambiar tamaños, los literales int, float y bool y los valores por defecto e iniciales de esos tipos":
        "In compiled scripts, only int, float and bool literals and the default and initial values of those types "
        "can be edited, without changing sizes",
    "Escribe una ruta, como MoveStates[44].JumpImpulse, o el objeto delante: death/playercommon_movestates · MoveStates[44].JumpImpulse":
        "Type a path, such as MoveStates[44].JumpImpulse, or put the object first: "
        "death/playercommon_movestates · MoveStates[44].JumpImpulse",
    "Falta el objeto antes de «{separator}»": "The object is missing before “{separator}”",
    "Para ir a una propiedad de otro objeto, sepáralos con « · »: {location}":
        "To go to a property of another object, separate them with “ · ”: {location}",
    "No hay ningún objeto «{name}». Parecidos: {similar}": "There is no object “{name}”. Similar: {similar}",
    "No hay ningún objeto «{name}»": "There is no object “{name}”",
    "No existe ningún objeto {identity} en este archivo": "There is no object {identity} in this file",
    "Los scripts compilados son de solo lectura": "Compiled scripts are read-only",
    "Solo los elementos de una lista o las entradas de un mapa se pueden duplicar, quitar o mover (las tuplas tienen tamaño fijo)":
        "Only list items and map entries can be duplicated, removed or moved (tuples have a fixed size)",
    "Solo un objeto o una referencia (fuera de tuplas y de claves) puede pasar a nulo":
        "Only an object or a reference (outside tuples and keys) can be set to null",
    "Ese ejemplo ya no está donde lo registró el índice (el objeto cambió al guardar). Vuelve a abrir el archivo para actualizar el índice.":
        "That example is no longer where the index recorded it (the object changed when saving). "
        "Reopen the file to update the index.",
    "Ahí no hay un nulo": "There is no null there",
    "Un nulo solo se rellena con un objeto o una referencia": "A null can only be filled with an object or a reference",
    "Este objeto no es un script compilado": "This object is not a compiled script",
})

# formats/bod.py: errores de formato y Ctrl+G
_merge(MESSAGES, {
    "Referencia a un nombre no definido ({index}) en 0x{pos:x}": "Reference to an undefined name ({index}) at 0x{pos:x}",
    "Marca de nombre desconocida 0x{marker:02X} en 0x{pos:x}": "Unknown name marker 0x{marker:02X} at 0x{pos:x}",
    "Tipo de clase desconocido 0x{kind:02X} en 0x{pos:x}": "Unknown class type 0x{kind:02X} at 0x{pos:x}",
    "Modo {mode} desconocido en la secuencia 0x{tag:02X} de 0x{pos:x}": "Unknown mode {mode} in the 0x{tag:02X} sequence at 0x{pos:x}",
    "Cadena 05 sin la marca 0xFF en 0x{pos:x}": "05 string without the 0xFF marker at 0x{pos:x}",
    "Tag desconocido 0x{tag:02X} en 0x{pos:x}": "Unknown tag 0x{tag:02X} at 0x{pos:x}",
    "No es un blob BOD: falta la firma 'BOD\\xFD'": "Not a BOD blob: the 'BOD\\xFD' signature is missing",
    "El blob BOD está truncado": "The BOD blob is truncated",
    "El blob BOD tiene {count} bytes de más o de menos": "The BOD blob has {count} bytes too many or too few",
    "Nombre demasiado largo ({count} bytes)": "Name too long ({count} bytes)",
    "Tipo de clase desconocido 0x{kind:02X}": "Unknown class type 0x{kind:02X}",
    "Un número BOD ocupa exactamente 4 bytes": "A BOD number takes exactly 4 bytes",
    "Modo {mode} desconocido en la secuencia 0x{tag:02X}": "Unknown mode {mode} in the 0x{tag:02X} sequence",
    "Cadena demasiado larga ({count} bytes)": "String too long ({count} bytes)",
    "Valor BOD desconocido: {kind}": "Unknown BOD value: {kind}",
    "No se puede copiar un {kind}": "A {kind} cannot be copied",
    "Un {kind} no tiene hijos": "A {kind} has no children",
    "Falta el «]» que cierra el índice": "The “]” that closes the index is missing",
    "Falta el número entre los corchetes, como [0]": "The number between the brackets is missing, as in [0]",
    "Entre corchetes va un número, como [0], y «{text}» no lo es (los índices por nombre no están disponibles)":
        "Brackets take a number, as in [0], and “{text}” is not one (indices by name are not available)",
    "Ese índice es demasiado grande para cualquier lista": "That index is too large for any list",
    "Sobra un «]» sin su «[»": "There is a “]” without its “[”",
    "Falta un nombre de campo tras el «.»": "A field name is missing after the “.”",
    "Una ruta empieza por un nombre de campo, no por «{char}»": "A path starts with a field name, not with “{char}”",
    "Se esperaba «.» o «[» antes de «{char}»": "Expected “.” or “[” before “{char}”",
    "un mapa": "a map",
    "una tupla": "a tuple",
    "una lista de pares": "a list of pairs",
    "una lista": "a list",
    "{names} o {last}": "{names} or {last}",
    "«{name}» puede ser {spellings} en {where}: escríbelo con sus mayúsculas":
        "“{name}” can be {spellings} in {where}: type it with its capitals",
    "«{name}» no es el comienzo de ninguna instrucción de {where}: la anterior es {previous}":
        "“{name}” is not the start of any instruction in {where}: the previous one is {previous}",
    "«{name}» no es el comienzo de ninguna instrucción de {where}": "“{name}” is not the start of any instruction in {where}",
    "«{name}» no es un campo de {where}. Parecidos: {similar}": "“{name}” is not a field of {where}. Similar: {similar}",
    "«{name}» no es un campo de {where}": "“{name}” is not a field of {where}",
    "Hay {count} campos «{name}» en {where}: se eligió el primero": "There are {count} “{name}” fields in {where}: the first one was chosen",
    "«{step}» no vale aquí: {where} es un objeto y sus campos van por nombre":
        "“{step}” does not work here: {where} is an object and its fields go by name",
    "«{step}» no vale aquí: {where} es {container} y se esperaba un índice, como [0]":
        "“{step}” does not work here: {where} is {container} and an index was expected, as in [0]",
    "«{step}» no existe: {where} no tiene elementos": "“{step}” does not exist: {where} has no items",
    "«{step}» no vale aquí: {where} es un par y solo tiene .{key} y .{value}":
        "“{step}” does not work here: {where} is a pair and only has .{key} and .{value}",
    "«{step}» no vale aquí: {where} es un valor ({type}) y no tiene hijos":
        "“{step}” does not work here: {where} is a value ({type}) and has no children",
})
_merge(PLURALS, {
    ("«{step}» no existe: {where} tiene {count:,} elemento, de [0] a [{last}]",
     "«{step}» no existe: {where} tiene {count:,} elementos, de [0] a [{last}]"):
        ("“{step}” does not exist: {where} has {count:,} item, from [0] to [{last}]",
         "“{step}” does not exist: {where} has {count:,} items, from [0] to [{last}]"),
})

# formats/script.py, bytecode.py, obsp.py y binary.py: errores de formato
_merge(MESSAGES, {
    "cabecera de script": "script header",
    "Número de símbolos imposible: {count}": "Impossible number of symbols: {count}",
    "versión {version}, se esperaba {expected}": "version {version}, expected {expected}",
    "longitud máxima declarada {declared}, real {real}": "declared maximum length {declared}, actual {real}",
    "el hash de ruta no coincide con el del índice": "the path hash does not match the index",
    "grupo {group}, el índice dice {expected}": "group {group}, the index says {expected}",
    "El hash {hash:016X} no está en la tabla de símbolos del script": "Hash {hash:016X} is not in the script's symbol table",
    "Un valor del script define un nombre nuevo en 0x{pos:X}": "A script value defines a new name at 0x{pos:X}",
    "El código de una función se sale del blob": "A function's code goes past the end of the blob",
    "El script está truncado": "The script is truncated",
    "El script tiene {count} bytes de más": "The script has {count} extra bytes",
    "«{name}» no está en la tabla de símbolos del script": "“{name}” is not in the script's symbol table",
    "El miembro {name} no concuerda con sus banderas": "Member {name} does not match its flags",
    "Una función vacía no tiene código que desensamblar": "An empty function has no code to disassemble",
    "Opcode desconocido 0x{opcode:02X} en 0x{pos:X}": "Unknown opcode 0x{opcode:02X} at 0x{pos:X}",
    "Nombre sin NUL final en 0x{pos:X}": "Name without a trailing NUL at 0x{pos:X}",
    "Instrucción truncada en 0x{pos:X}": "Truncated instruction at 0x{pos:X}",
    "Código truncado": "Truncated code",
    "Opcode desconocido 0x{opcode:02X}": "Unknown opcode 0x{opcode:02X}",
    "Nombre en línea demasiado largo ({count} bytes)": "Inline name too long ({count} bytes)",
    "Un literal numérico ocupa 4 bytes": "A numeric literal takes 4 bytes",
    "El archivo es demasiado corto para ser un OBSP": "The file is too short to be an OBSP",
    "No es un archivo OBSP: falta la firma 'OBSP'": "Not an OBSP file: the 'OBSP' signature is missing",
    "La cabecera OBSP apunta fuera del archivo": "The OBSP header points outside the file",
    "tabla de cadenas": "string table",
    "La tabla de cadenas no termina donde dice la cabecera": "The string table does not end where the header says",
    "El blob del objeto {identity} sale del archivo": "The blob of object {identity} goes past the end of the file",
    "objeto {position}: offset 0x{offset:x}, se esperaba 0x{expected:x}": "object {position}: offset 0x{offset:x}, expected 0x{expected:x}",
    "el último blob acaba en 0x{end:x} y el archivo en 0x{size:x}": "the last blob ends at 0x{end:x} and the file at 0x{size:x}",
    "Hay distinto número de entradas que de blobs": "The number of entries and blobs differ",
    "Falta la cadena del hash 0x{hash:016X}": "The string for hash 0x{hash:016X} is missing",
    "El archivo resultante supera los 4 GiB que admite el índice": "The resulting file is larger than the 4 GiB the index allows",
    "Rango inválido en {label}": "Invalid range in {label}",
    "Lectura fuera de rango en {label}: 0x{start:x} + {count} > 0x{end:x}": "Read out of range in {label}: 0x{start:x} + {count} > 0x{end:x}",
})

# binary.py
_merge(MESSAGES, {
    "datos": "data",
})

# diffing.py y validation.py: cambios pendientes y comprobaciones al guardar
_merge(MESSAGES, {
    ("cambio", "valor"): "value",
    ("cambio", "reemplazado"): "replaced",
    ("cambio", "añadido"): "added",
    ("cambio", "eliminado"): "deleted",
    ("cambio", "movido"): "moved",
    ("cambio", "lista"): "list",
    "objeto {name}": "object {name}",
    "{type} de {value}": "{type} of {value}",
    "posición [{index}]": "position [{index}]",
    "{container}[{index}] (posición original)": "{container}[{index}] (original position)",
    "{location}: la referencia {identity} no apunta a ningún objeto del archivo":
        "{location}: reference {identity} does not point to any object in the file",
    "{location}: claves repetidas ({keys}). Cambia la clave de la entrada duplicada antes de guardar.":
        "{location}: repeated keys ({keys}). Change the key of the duplicated entry before saving.",
    "{location}: el campo {name} se repite ({values}) y antes no se repetía":
        "{location}: field {name} repeats ({values}) and did not repeat before",
})

# search.py: búsqueda global
_merge(MESSAGES, {
    ("coincidencia", "ruta"): "path",
    ("coincidencia", "nombre"): "name",
    ("coincidencia", "carpeta"): "folder",
    ("coincidencia", "clase"): "class",
    ("coincidencia", "símbolo"): "symbol",
    ("coincidencia", "valor"): "value",
    ("coincidencia", "campo"): "field",
})

# saving.py: guardar y restaurar
_merge(MESSAGES, {
    "No se puede guardar todavía:\n{problems}": "It cannot be saved yet:\n{problems}",
    "No se pudo construir el archivo: {error}": "The file could not be built: {error}",
    "El archivo construido no se puede volver a leer: {error}": "The built file cannot be read back: {error}",
    "El archivo construido no tiene el mismo número de objetos": "The built file does not have the same number of objects",
    "El archivo construido no tiene los blobs contiguos: {problems}": "The built file does not have contiguous blobs: {problems}",
    "La cabecera del archivo construido no conserva versión y campo desconocido":
        "The header of the built file does not keep the version and the unknown field",
    "El objeto {position} cambió de identidad al construir el archivo": "Object {position} changed identity when building the file",
    "El objeto {position} no se editó y sus bytes cambiaron": "Object {position} was not edited and its bytes changed",
    "El objeto {position} no contiene el árbol editado": "Object {position} does not contain the edited tree",
    "El objeto editado {position} no se recodifica igual": "Edited object {position} does not re-encode the same",
    "El objeto editado {position} no decodifica: {error}": "Edited object {position} does not decode: {error}",
    "El objeto editado {position} tiene la cadena «{text}» con un hash que no le corresponde ({hash:016X}; debería ser {expected:016X})":
        "Edited object {position} has the string “{text}” with a hash that does not match it ({hash:016X}; it should be {expected:016X})",
    "La tabla de cadenas cambió al construir el archivo": "The string table changed when building the file",
    "La tabla de cadenas tiene «{text}» con un hash que no le corresponde ({hash:016X})":
        "The string table has “{text}” with a hash that does not match it ({hash:016X})",
    "El script editado {position} no se recodifica igual": "Edited script {position} does not re-encode the same",
    "En el script editado {position} cambió algo más que literales y valores":
        "Something other than literals and values changed in edited script {position}",
    "El script editado {position} no se puede volver a leer: {error}": "Edited script {position} cannot be read back: {error}",
    "{name} es de solo lectura. Quítale ese atributo o usa «Guardar como».": "{name} is read-only. Remove that attribute or use “Save As”.",
    "No hay permiso para escribir en {folder}. Si el juego sigue abierto, ciérralo; si no, ejecuta la herramienta con permisos suficientes o guarda en otra carpeta.":
        "There is no permission to write in {folder}. If the game is still open, close it; otherwise, run the tool "
        "with enough permissions or save in another folder.",
    "No queda espacio en el disco de {folder}.": "There is no space left on the disk of {folder}.",
    "No se pudo escribir {path}: {error}": "{path} could not be written: {error}",
    "{path} es una carpeta": "{path} is a folder",
    "No existe la carpeta {folder}": "The folder {folder} does not exist",
    "{name} apareció mientras se creaba; no se sobrescribe": "{name} appeared while it was being created; it is not overwritten",
    "La copia {copy} no coincide con el archivo copiado; no se guarda nada": "The copy {copy} does not match the copied file; nothing is saved",
    "No se pudo marcar {copy} como solo lectura: {error}": "{copy} could not be marked read-only: {error}",
    "Aviso: {name} ya venía modificado (no es el original de Steam); la copia lo conserva tal cual.":
        "Warning: {name} was already modified (it is not the Steam original); the backup keeps it as it was.",
    "No se guarda nunca encima de {name}: es la copia del original. Usa «Guardar como».":
        "Nothing is ever saved over {name}: it is the original backup. Use “Save As”.",
    "No se pudo guardar la copia rotativa: {error}": "The rotating backup could not be saved: {error}",
    "Se escribió {name} pero no se pudo releer: {error}": "{name} was written but could not be read back: {error}",
    "{name} no coincide con lo que se quería escribir. Restaura el original desde Archivo → Restaurar original.":
        "{name} does not match what was meant to be written. Restore the original from File → Restore Original.",
    "Ese archivo ya es la copia del original": "That file is already the original backup",
    "No existe {copy} junto a {name}: no hay copia del original que restaurar":
        "There is no {copy} next to {name}: there is no original backup to restore",
    "No se pudo leer {copy}: {error}": "{copy} could not be read: {error}",
    "{copy} no es un OBSP válido: {error}": "{copy} is not a valid OBSP: {error}",
    "{name} no quedó idéntico a {copy} tras restaurar": "{name} was not identical to {copy} after restoring",
    "El documento no tiene ruta: indica dónde guardarlo": "The document has no path: choose where to save it",
})

# patches.py: crear y aplicar parches
_merge(MESSAGES, {
    ("operación", "valor"): "value",
    ("operación", "quitar"): "remove",
    ("operación", "mover"): "move",
    ("operación", "insertar"): "insert",
    ("operación", "nulo"): "null",
    ("operación", "copiar"): "copy",
    ("operación", "referencia"): "reference",
    "Un {kind} no es una hoja editable": "A {kind} is not an editable leaf",
    "Valor mal formado en el parche": "Malformed value in the patch",
    "Un número ocupa 4 bytes": "A number takes 4 bytes",
    "Un bool ocupa un byte": "A bool takes one byte",
    "Valor mal formado en el parche: {error}": "Malformed value in the patch: {error}",
    "no hay en el original ningún {value} del que copiar": "the original has no {value} to copy from",
    "cambió la clase del objeto raíz": "the class of the root object changed",
    "no se puede expresar el cambio de {old} a {new}": "the change from {old} to {new} cannot be expressed",
    "no hay en el original nada de lo que copiar {value}": "the original has nothing to copy {value} from",
    "La base no tiene los mismos objetos, en el mismo orden, que el archivo actual":
        "The base does not have the same objects, in the same order, as the current file",
    "{object}: en un script solo puede haber cambios de valor": "{object}: a script can only have value changes",
    "El parche no reproduce el archivo actual al reaplicarlo sobre la base; no se escribe":
        "The patch does not reproduce the current file when reapplied to the base; it is not written",
    "objeto de origen": "source object",
    "objeto": "object",
    "Un {kind} del parche está mal formado": "A {kind} in the patch is malformed",
    "El {kind} {path} ({identity}) no existe en este archivo": "The {kind} {path} ({identity}) does not exist in this file",
    "El {kind} {identity} se llama {actual}, no {path}": "The {kind} {identity} is called {actual}, not {path}",
    "Ruta mal formada en el parche": "Malformed path in the patch",
    "{where}: la ruta {path} no existe": "{where}: path {path} does not exist",
    "No es un parche de D2ScriptViewer": "It is not a D2ScriptViewer patch",
    "Versión de parche {version} no admitida (se admite la {supported})": "Patch version {version} is not supported (version {supported} is)",
    "El parche no tiene la lista de objetos": "The patch does not have the list of objects",
    "{object}: el original no coincide con el del parche": "{object}: the original does not match the patch",
    "{object} tiene cambios sin guardar: deshazlos o guárdalos antes de aplicar el parche":
        "{object} has unsaved changes: undo or save them before applying the patch",
    "{object} no es el que espera el parche (su contenido es otro)": "{object} is not the one the patch expects (its content is different)",
    "{object}: faltan las operaciones": "{object}: the operations are missing",
    "{where}: origen de copia mal formado": "{where}: malformed copy source",
    "{where}: el objeto de origen no está entre las fuentes del parche": "{where}: the source object is not among the patch sources",
    "{where}: operación mal formada": "{where}: malformed operation",
    "{where}: en un script solo se aplican cambios de valor": "{where}: only value changes apply to a script",
    "{where}: en esa ruta está {label}": "{where}: that path holds {label}",
    "{where}: el valor es de tipo {type}": "{where}: the value is of type {type}",
    "{where}: el valor actual ({value}) no es el que espera el parche": "{where}: the current value ({value}) is not the one the patch expects",
    "{where}: la referencia {identity} no existe": "{where}: reference {identity} does not exist",
    "{where}: {path} no es una lista ni un mapa": "{where}: {path} is neither a list nor a map",
    "{where}: no hay elemento {index}": "{where}: there is no item {index}",
    "{where}[{index}] no es el elemento que el parche quita": "{where}[{index}] is not the item the patch removes",
    "{where}: movimiento fuera de la lista": "{where}: move outside the list",
    "{where}: no se puede insertar en {index}": "{where}: cannot insert at {index}",
    "{where}: lo que se copia no es lo que espera el parche": "{where}: what is copied is not what the patch expects",
    "{where}: no se sustituye la raíz": "{where}: the root is not replaced",
    "{where}: ahí no está lo que espera el parche": "{where}: what the patch expects is not there",
    "{where}: solo un objeto o una referencia pueden pasar a nulo": "{where}: only an object or a reference can be set to null",
    "{where}: referencia mal formada": "{where}: malformed reference",
    "{where}: operación desconocida {kind!r}": "{where}: unknown operation {kind!r}",
    "{where}: el resultado no es el que espera el parche": "{where}: the result is not the one the patch expects",
    "sin cambios": "no changes",
    "{objects}, {operations} ({detail})": "{objects}, {operations} ({detail})",
    "No se pudo leer {path}: {error}": "{path} could not be read: {error}",
    "{name} no es un JSON válido: {error}": "{name} is not valid JSON: {error}",
    "{name} no es un parche de D2ScriptViewer": "{name} is not a D2ScriptViewer patch",
})
_merge(PLURALS, {
    ("{count:,} objeto", "{count:,} objetos"): ("{count:,} object", "{count:,} objects"),
    ("{count:,} operación", "{count:,} operaciones"): ("{count:,} operation", "{count:,} operations"),
})

# export.py: exportación JSON y CSV
_merge(MESSAGES, {
    "No se sabe exportar un {kind}": "A {kind} cannot be exported",
    "{path} no tiene la forma de una FloatTable": "{path} does not have the shape of a FloatTable",
    "No se exporta dentro de la carpeta del juego: elige otra carpeta": "Nothing is exported inside the game folder: choose another folder",
    "{folder} no es una carpeta": "{folder} is not a folder",
    "{folder} no está vacía ni contiene una exportación anterior de D2ScriptViewer: elige una carpeta vacía":
        "{folder} is not empty and does not hold an earlier D2ScriptViewer export: choose an empty folder",
    "Exportados {objects} y {tables} en {folder} ({size:.1f} MB)": "Exported {objects} and {tables} to {folder} ({size:.1f} MB)",
    "Exportación cancelada": "Export cancelled",
})
_merge(PLURALS, {
    ("{count:,} tabla CSV", "{count:,} tablas CSV"): ("{count:,} CSV table", "{count:,} CSV tables"),
})

# gui/app.py: ventana principal
_merge(MESSAGES, {
    "Este archivo es la copia del original: guarda los cambios con «Guardar como».":
        "This file is the original backup: save the changes with “Save As”.",
    "Abrir scripts.obsp": "Open scripts.obsp",
    "Scripts de Darksiders II": "Darksiders II scripts",
    "Todos los archivos": "All files",
    "Abriendo {name}…": "Opening {name}…",
    "No se pudo abrir el archivo": "The file could not be opened",
    "Se borró {name}, resto de un guardado interrumpido": "{name}, left over from an interrupted save, was deleted",
    "No se pudo indexar: {error}": "Indexing failed: {error}",
    "Índice listo: {references:,} referencias, {strings:,} cadenas conocidas":
        "Index ready: {references:,} references, {strings:,} known strings",
    "(no existe) {identity}": "(does not exist) {identity}",
    "La referencia {identity} no apunta a ningún objeto de este archivo":
        "Reference {identity} does not point to any object in this file",
    "Decodificando {size}…": "Decoding {size}…",
    "No se pudo decodificar: {error}": "Could not decode: {error}",
    "Este objeto no se pudo decodificar: no tiene propiedades a las que ir":
        "This object could not be decoded: it has no properties to go to",
    "Este objeto no se pudo decodificar: {error}": "This object could not be decoded: {error}",
    "Script": "Script",
    "Editables": "Editable",
    "BOD": "BOD",
    "versión {version}, campo desconocido {flags}": "version {version}, unknown field {flags}",
    "Nombres internos": "Interned names",
    "{count:,} al abrir (máx. {length} caracteres)": "{count:,} when opened (max. {length} characters)",
    "Estado": "Status",
    "sin cambios": "no changes",
    "No hay ningún objeto seleccionado": "No object is selected",
    "¿Aplicar el cambio de todos modos?": "Apply the change anyway?",
    "Ese objeto no tiene cambios": "That object has no changes",
    "Selecciona antes una propiedad en el panel central": "Select a property in the center panel first",
    "Esa operación no se puede hacer sobre la propiedad seleccionada": "That operation cannot be done on the selected property",
    "El elemento ya está en ese extremo de la lista": "The item is already at that end of the list",
    "La copia repite la clave de la entrada original: cámbiala antes de guardar (una clave repetida impide guardar).":
        "The copy repeats the key of the original entry: change it before saving (a repeated key prevents saving).",
    "Espera a que termine el índice del archivo para rellenar nulos": "Wait for the file index to finish before filling nulls",
    "En el archivo no aparece ningún objeto ni referencia en el hueco {slot}, así que no hay de dónde copiar uno con seguridad.":
        "No object or reference appears in slot {slot} anywhere in the file, so there is nowhere to safely copy one from.",
    "{changes} sin guardar en {objects}": "{changes} unsaved in {objects}",
    "Sin cambios": "No changes",
    "{name} es la copia del original y nunca se sobrescribe.\n\nUsa «Guardar como» para guardar los cambios en otro archivo.":
        "{name} is the original backup and is never overwritten.\n\nUse “Save As” to save the changes to another file.",
    "No hay cambios que guardar": "There are no changes to save",
    "Guardar como": "Save As",
    "No se guardó": "Not saved",
    "¿Restaurar ahora la copia del original?": "Restore the original backup now?",
    "Este archivo ya es la copia del original.": "This file is already the original backup.",
    "No existe {copy} junto a {name}.\n\nLa copia se crea la primera vez que se guarda encima del archivo.":
        "There is no {copy} next to {name}.\n\nThe backup is created the first time you save over the file.",
    "Se copiará {copy} encima de {name} y se verificará.\n• {copy} se conserva.\n• La versión actual irá a {folder} si las copias rotativas están activas.{lost}\n\n¿Restaurar?":
        "{copy} will be copied over {name} and verified.\n• {copy} is kept.\n"
        "• The current version will go to {folder} if rotating backups are on.{lost}\n\nRestore?",
    "Restaurando {name}…": "Restoring {name}…",
    "No se restauró": "Not restored",
    "No se restauró el original.\n\n{message}": "The original was not restored.\n\n{message}",
    "{name} vuelve a ser el original de Steam.\nSHA-256 {sha}": "{name} is the Steam original again.\nSHA-256 {sha}",
    "{name} vuelve a ser la copia del original.\nSHA-256 {sha}": "{name} is the original backup again.\nSHA-256 {sha}",
    "Exportar a JSON y CSV (carpeta vacía)": "Export to JSON and CSV (empty folder)",
    "Exportando a {folder}…": "Exporting to {folder}…",
    "No se exportó": "Not exported",
    "No se exportó.\n\n{message}": "Nothing was exported.\n\n{message}",
    "No se pudo leer el original: {error}": "The original could not be read: {error}",
    "No hay diferencias con la base ({base}): no hay nada que poner en un parche.":
        "There are no differences from the base ({base}): there is nothing to put in a patch.",
    "Exportar parche": "Export Patch",
    "Parches de D2ScriptViewer": "D2ScriptViewer patches",
    "Creando el parche y comprobándolo sobre la base…": "Creating the patch and checking it against the base…",
    "No se creó el parche": "The patch was not created",
    "No se creó el parche.\n\n{message}": "The patch was not created.\n\n{message}",
    "original de Steam": "Steam original",
    "no es el original de Steam": "not the Steam original",
    "Parche guardado en {name}": "Patch saved in {name}",
    "Parche guardado en {path}.\n\n• {summary}.\n• Base: {base} ({steam}).\n• Comprobado: reaplicado sobre la base da exactamente el archivo actual.":
        "Patch saved in {path}.\n\n• {summary}.\n• Base: {base} ({steam}).\n"
        "• Checked: reapplied to the base, it gives exactly the current file.",
    "Aplicar parche": "Apply Patch",
    "No se aplicó el parche.\n\n{message}": "The patch was not applied.\n\n{message}",
    "El parche no tiene cambios.": "The patch has no changes.",
    "Parche aplicado: {summary}.\n\nSon cambios pendientes: revísalos con Ctrl+P, deshazlos todos con Ctrl+Z o guárdalos con Ctrl+S.":
        "Patch applied: {summary}.\n\nThese are pending changes: review them with Ctrl+P, undo them all with Ctrl+Z "
        "or save them with Ctrl+S.",
    "Abre antes un scripts.obsp con Archivo → Abrir (Ctrl+O)": "Open a scripts.obsp first with File → Open (Ctrl+O)",
    "Selecciona antes un objeto, o escribe el objeto delante: objeto · propiedad":
        "Select an object first, or put the object in front: object · property",
})
_merge(PLURALS, {
    ("{count:,} objeto no decodifica", "{count:,} objetos no decodifican"):
        ("{count:,} object does not decode", "{count:,} objects do not decode"),
    ("{count:,} miembro", "{count:,} miembros"): ("{count:,} member", "{count:,} members"),
    ("{count:,} valor inicial", "{count:,} valores iniciales"): ("{count:,} initial value", "{count:,} initial values"),
    ("{count:,} función", "{count:,} funciones"): ("{count:,} function", "{count:,} functions"),
    ("{count:,} estado", "{count:,} estados"): ("{count:,} state", "{count:,} states"),
    ("{count:,} literal o valor", "{count:,} literales o valores"): ("{count:,} literal or value", "{count:,} literals or values"),
    ("modificado: {count:,} propiedad, {size:,} bytes al guardar", "modificado: {count:,} propiedades, {size:,} bytes al guardar"):
        ("modified: {count:,} property, {size:,} bytes when saved", "modified: {count:,} properties, {size:,} bytes when saved"),
    ("{count:,} cambio", "{count:,} cambios"): ("{count:,} change", "{count:,} changes"),
    ("• Se perderá {count:,} cambio sin guardar.", "• Se perderán {count:,} cambios sin guardar."):
        ("• {count:,} unsaved change will be lost.", "• {count:,} unsaved changes will be lost."),
})

# gui/details.py, script_view.py y pending_view.py
_merge(MESSAGES, {
    "DETALLES": "DETAILS",
    "Detalles": "Details",
    "Hex": "Hex",
    "Apunta a": "Points to",
    "Usado por": "Used by",
    "Propiedad": "Property",
    "Objeto": "Object",
    "Referencias": "References",
    "Ruta": "Path",
    "Nombre": "Name",
    "Clase": "Class",
    "Carpeta": "Folder",
    "Identidad": "Identity",
    "Grupo": "Group",
    "Tipo": "Type",
    "Offset": "Offset",
    "0x{offset:X} ({offset:,})": "0x{offset:X} ({offset:,})",
    "Tamaño": "Size",
    "{size:,} bytes": "{size:,} bytes",
    "Posición en el índice": "Index position",
    "{position:,}": "{position:,}",
    "No se pudo leer la cabecera: {error}": "The header could not be read: {error}",
    "Este objeto no es un script compilado.": "This object is not a compiled script.",
    "{size:,} bytes · offsets absolutos en el archivo · versión editada (aún sin guardar)":
        "{size:,} bytes · absolute offsets in the file · edited version (not saved yet)",
    "{size:,} bytes · offsets absolutos en el archivo": "{size:,} bytes · absolute offsets in the file",
    "{title} (indexando…)": "{title} (indexing…)",
    "Apunta a ({count:,})": "Points to ({count:,})",
    "Usado por ({count:,})": "Used by ({count:,})",
    "Selecciona un script (tipo 0).": "Select a script (type 0).",
    "Hash": "Hash",
    "Símbolo": "Symbol",
    "Versión {version} · {symbols:,} símbolos · cuerpo de {size:,} bytes a partir de 0x{offset:X}. Los miembros y el código desensamblado están en el panel central.":
        "Version {version} · {symbols:,} symbols · {size:,}-byte body from 0x{offset:X}. The members and the "
        "disassembled code are in the center panel.",
    "Cambios pendientes — D2ScriptViewer": "Pending Changes — D2ScriptViewer",
    "Cambio": "Change",
    "Antes": "Before",
    "Después": "After",
    "Cerrar": "Close",
    "Ir": "Go",
    "{changes} en {objects}": "{changes} in {objects}",
    "No hay cambios pendientes.": "There are no pending changes.",
})

# gui/editors.py y search_view.py: diálogos y búsqueda global
_merge(MESSAGES, {
    "Cambiar referencia — D2ScriptViewer": "Change Reference — D2ScriptViewer",
    "Ahora es nulo: elige el objeto al que apuntará la referencia nueva.":
        "It is null now: choose the object the new reference will point to.",
    "(no existe)": "(does not exist)",
    "Ahora apunta a: {target}  [{identity}]": "It points to: {target}  [{identity}]",
    "Filtrar": "Filter",
    "Cancelar": "Cancel",
    "Aceptar": "OK",
    "(se muestran {limit:,}; afina el filtro)": "({limit:,} shown; narrow the filter)",
    "Rellenar nulo — D2ScriptViewer": "Fill Null — D2ScriptViewer",
    "valor del campo": "value of the field",
    "elemento de la lista": "list item",
    "valor de un par": "value of a pair",
    "Hueco: {slot} ({role}). Se copia un objeto de una clase que ya aparece en este mismo hueco en el archivo; elige un ejemplo y se insertará una copia exacta.":
        "Slot: {slot} ({role}). An object of a class that already appears in this same slot in the file is copied; "
        "choose an example and an exact copy will be inserted.",
    "Clase / ejemplo": "Class / example",
    "{name}  ({count:,} en el archivo)": "{name}  ({count:,} in the file)",
    "En el archivo no hay objetos en este hueco.": "There are no objects in this slot in the file.",
    "Copiar este objeto": "Copy This Object",
    "Referencia a un objeto…": "Reference to an Object…",
    "Buscar — D2ScriptViewer": "Search — D2ScriptViewer",
    "Escribe un texto o un número y pulsa Intro.": "Type a text or a number and press Enter.",
    "Rutas, nombres, carpetas y clases": "Paths, names, folders and classes",
    "Valores y símbolos": "Values and symbols",
    "Nombres de campo": "Field names",
    "Dónde": "Where",
    "Coincidencia": "Match",
    "Buscando «{text}»…": "Searching for “{text}”…",
    "(búsqueda cancelada)": "(search cancelled)",
    "(límite alcanzado; afina la búsqueda)": "(limit reached; narrow the search)",
    "{results}. Doble clic para ir al objeto.": "{results}. Double-click to go to the object.",
    "Error: {error}": "Error: {error}",
})
_merge(PLURALS, {
    ("En este hueco hay {count:,} referencia en el archivo.", "En este hueco hay {count:,} referencias en el archivo."):
        ("There is {count:,} reference in this slot in the file.", "There are {count:,} references in this slot in the file."),
    ("{count:,} resultado…", "{count:,} resultados…"): ("{count:,} result…", "{count:,} results…"),
    ("{count:,} resultado", "{count:,} resultados"): ("{count:,} result", "{count:,} results"),
})

# gui/object_tree.py y property_view.py
_merge(MESSAGES, {
    "OBJETOS": "OBJECTS",
    "Agrupar": "Group by",
    "(raíz)": "(root)",
    "(sin carpeta)": "(no folder)",
    "{visible:,} de {total:,}": "{visible:,} of {total:,}",
    "PROPIEDADES": "PROPERTIES",
    "Valor": "Value",
    "Ir a": "Go to",
    "Script compilado: doble clic o F2 edita los literales int, float y bool y los valores de esos tipos; lo demás es de solo lectura":
        "Compiled script: double-click or F2 edits the int, float and bool literals and values of those types; "
        "the rest is read-only",
    "Doble clic o F2 para editar un valor · clic derecho para más opciones": "Double-click or F2 to edit a value · right-click for more options",
    "Sin resultados": "No results",
    "{rank:,} de {total:,}": "{rank:,} of {total:,}",
    "Ctrl+D duplica, Supr elimina, Alt+↑/↓ mueve": "Ctrl+D duplicates, Del deletes, Alt+↑/↓ moves",
    "clic derecho: poner a nulo": "right-click: set to null",
    "clic derecho: rellenar con un objeto": "right-click: fill with an object",
    "Doble clic o Intro para ir al destino · F2 para cambiar la referencia":
        "Double-click or Enter to go to the target · F2 to change the reference",
    "F2 o doble clic para cambiar la cadena: sugiere las del archivo y admite nuevas (distingue mayúsculas)":
        "F2 or double-click to change the string: it suggests the file's strings and accepts new ones (case-sensitive)",
    "Solo lectura: en los scripts solo se editan los literales int, float y bool y los valores de esos tipos, sin cambiar tamaños":
        "Read-only: in scripts only the int, float and bool literals and values of those types are edited, "
        "without changing sizes",
    "Doble clic o F2 para editar": "Double-click or F2 to edit",
    "Las tuplas tienen tamaño fijo en el juego: solo se editan sus valores": "Tuples have a fixed size in the game: only their values are edited",
    "Este valor no se edita escribiendo: usa el clic derecho para las operaciones de estructura":
        "This value is not edited by typing: right-click for the structure operations",
    "Ir al destino": "Go to Target",
    "Cambiar referencia…": "Change Reference…",
    "Revertir esta propiedad": "Revert This Property",
    "Copiar valor": "Copy Value",
    "Copiar ruta de la propiedad": "Copy Property Path",
    "Copiar ruta completa": "Copy Full Path",
    "Rellenar con un objeto…": "Fill with an Object…",
})

# patches.py (cont.)
_merge(MESSAGES, {
    "la lista cambió demasiado para describirla elemento a elemento": "the list changed too much to describe it item by item",
})

# patches.py (base)
_merge(MESSAGES, {
    "archivo abierto": "open file",
})

# gui/app.py (nombre del parche)
_merge(MESSAGES, {
    "cambios": "changes",
})
