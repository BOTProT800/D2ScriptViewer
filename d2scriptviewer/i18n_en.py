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
