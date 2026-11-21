# D2ScriptViewer

[Español](README.md) · **English**

Desktop viewer and editor for `media\scripts.obsp` in **Darksiders II Deathinitive Edition**
(PC). It is written in Python, using only the standard library and tkinter.

It shows the 7,862 objects in the file and edits their values and their structure. It can also
create new strings, show and patch the compiled scripts, and export to JSON and CSV. It saves in
the same `.obsp` format and keeps an untouched copy of the original. Everything has been tested
in the game. The project plan and its history are in [PLAN_MAESTRO.md](PLAN_MAESTRO.md) (in
Spanish).

The keyboard shortcuts and what people usually change are in the
[modder's guide](GUIA_MODDER.en.md).

## Before you start

- **The first time you save** over `scripts.obsp`, the tool creates `scripts.original.obsp`. It
  is an exact copy of the file as it was, verified and read-only. It is never overwritten, and
  **File → Restore Original…** puts it back.
- **Close Darksiders II before saving.** While the game is open, the file is in use and cannot be
  written.
- **Steam** (“Verify integrity of game files”, or an update) brings back the original file and
  wipes your changes. Save a patch first (**File → Export Patch…**) so you can reapply them.
- Make small changes and test them: many values in the game have no documented meaning.

## Download

Each release publishes `D2ScriptViewer.exe`, a single Windows executable that does not need
Python. It comes with the license texts of the third-party software it bundles (CPython, Tcl/Tk
and the PyInstaller bootloader); see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The command
line and the tests need the source code and Python.

## Requirements (from source)

Python 3.10 or later on Windows. No packages need to be installed.

## Usage

Graphical interface (or double-click `D2ScriptViewer.exe` or `D2ScriptViewer.pyw`):

```powershell
python -m d2scriptviewer
```

It opens the last file you used, the one in `D2SV_OBSP`, or the game's own file. Opening a file
neither locks nor changes it.

**Language:** the interface is available in English and in Spanish.

- It starts in English until you choose another language.
- The **Idioma / Language** menu switches at once, without closing the window or losing your
  changes, and remembers your choice.
- `D2SV_LANG=en` (or `es`) sets the language for one session without saving it.
- The command line is in Spanish only.
- The open and save file dialogs and the Yes/No buttons follow the Windows language.

The main window:

- **Objects** (left): grouped by editor folder, path or type, with filters by type, class and
  text.
- **Properties** (center): the object's tree. Double-clicking a reference (`→ …`) takes you to its
  target, and Alt+← and Alt+→ move through the history.
- **Details** (right): metadata, hex dump, references (“Points to” / “Used by”) and the symbols of
  compiled scripts.
- **Find in Object** (Ctrl+F): the bar above the property tree has one field per column: Name,
  Type and Value.
  - It searches the whole open object, even closed nodes.
  - Enter or F3 goes to the next result and Shift+Enter or Shift+F3 to the previous one, with a
    counter (“3 of 7”). Escape returns to the tree.
  - For example, in the `death/death` script, Type `op_3A` and Value `NumSlots` find the 7
    assignments of `NumSlots`.
- **Find in Whole File** (Ctrl+Shift+F): paths, names, classes, values (text or number) and
  symbols.
- **Go to Path** (Ctrl+G or Go → Go to Path…): paste a path such as `MoveStates[44].JumpImpulse`
  and the tree jumps to that row, even inside the ranges of long lists.
  - With the object in front, it switches objects:
    `death/playercommon_movestates · MoveStates[44].JumpImpulse` (or `::` instead of `·`).
  - That is what **Copy Property Path** and **Copy Full Path** copy (right-click).
  - If the path fails halfway, the tree stays on the last valid row, and the line under the tree
    says which part failed, with similar names.
  - Paths copied in the Spanish interface (`Funciones.onInit.0x004E`) also work in the English
    one, and the other way round.

### Editing

Double-click, F2 or Enter on a value edits it in the cell itself: Enter confirms and Escape
cancels. The line under the tree warns about errors and shows how the value will be saved (the
hex of an integer, the rounding of a float).

- **Integers:** decimal or `0x…` (32-bit pattern).
- **Floats:** a decimal comma is accepted; NaN and infinities are not.
- **Bools:** true/false.
- **Strings without a hash** (`'…'`): any ASCII text.
- **Names** (hashed strings): autocomplete offers the names already in the file.
  - A new name (ASCII) is also accepted. The tool computes its hash and asks for confirmation,
    because the game only recognizes it if something with that name exists.
  - Names are case-sensitive, and the tool warns if a new name differs from a known one only in
    case.
- **References** (`→ …`): F2 opens an object picker; double-click still takes you to the target.
- Ctrl+Z / Ctrl+Y undo and redo. The Edit menu and the right-click menu revert one property or the
  whole object. Ctrl+P opens the pending changes.
- Fields that look like identifiers (`…ID`, huge integers that look like a hash) ask for
  confirmation before changing.

Compiled scripts show in the center panel: members with their default values, initial values,
and the disassembled code of each function and state (lines, literals, calls, names). Only the
int, float and bool literals of the code and the values of those types can change, without
changing sizes. The argument count of a call and every other row are read-only.

### Changing the structure

On a list item or a map entry:

- **Ctrl+D** duplicates it (the copy goes right after it);
- **Del** deletes it;
- **Alt+↑ / Alt+↓** move it.

The right-click menu (or Edit → Structure) can also **set to null** an object or a reference, and
**fill a null** by copying an object of a class that already appears in that same slot in the
file.

- Tuples (vectors, colors) have a fixed size: only their values are edited.
- When you duplicate a map entry, its key is repeated. Change it before saving, because a repeated
  key prevents saving. A reference without a target also prevents it.
- If an `…ID` field starts repeating in a list where it used to be unique (the usual result of
  duplicating an item), the tool warns you and asks for confirmation when saving.

### Saving

- **Save** (Ctrl+S) rewrites the file in the same `.obsp` format. The first time you save over
  `scripts.obsp`, the tool first creates `scripts.original.obsp` in the same folder: an exact copy
  of the file as it was, verified by SHA-256 and read-only. That copy is **never** overwritten or
  deleted, and nothing can be saved over it.
- Each save also leaves the previous version in `.d2sv_backups\` (the last 5). You can turn this
  off in the File menu.
- The file is built in memory, read back and compared before writing. It is written to a `.tmp`
  and swapped in atomically, then read back and its SHA-256 compared. If anything fails before
  the swap, the file stays intact.
- **Save As…** writes to another file.
- **Restore Original…** copies `scripts.original.obsp` over `scripts.obsp` and verifies it.
- The status bar says whether the file is the Steam original, modified (with an original backup)
  or unknown.

Warnings:

- **Close Darksiders II before saving.** With the game open the file cannot be written, and the
  tool tells you so.
- Steam's “Verify integrity of game files”, or an update, brings back the original.

### Export and patches

- **Export to JSON and CSV…** writes to an empty folder, never inside the game folder:
  - one JSON file per object: its tree with types and resolved references, and for scripts, their
    members and disassembled code;
  - a `manifest.json` with the index;
  - a CSV file for each `FloatTable`.

  It is only for reading or comparing: it is not imported back.
- **Export Patch…** saves a `.d2svpatch.json` with what changed compared with the original
  (`scripts.original.obsp` if it exists).
  - It holds only values, paths and structure operations that copy content from the original
    itself, so you can share it without distributing game data.
  - Before writing it, the tool reapplies it to the original and checks that it gives exactly the
    current file.
  - The patch is the same whichever language you create it in, and it applies in either one. The
    paths inside the file always use the Spanish labels of the scripts (`Funciones`…).
- **Apply Patch…** applies a patch as pending changes, which are saved as usual and undone in
  one step with Ctrl+Z. It is useful, for example, to get your changes back after Steam restores
  the original. If any object, property or value is not what the patch expects, nothing is
  applied.

Command line (in Spanish only):

```powershell
python -m d2scriptviewer info
python -m d2scriptviewer list --tipo Desc --filtro death
python -m d2scriptviewer show death/death_desc --profundidad 3
python -m d2scriptviewer verify
python -m d2scriptviewer hash Death death/death_desc
python -m d2scriptviewer disasm death/death
python -m d2scriptviewer export --salida C:\export --tipo FloatTable
python -m d2scriptviewer patch crear --salida changes.d2svpatch.json
python -m d2scriptviewer patch aplicar changes.d2svpatch.json --salida C:\copy\scripts.obsp
```

- Every subcommand except `hash` accepts `--archivo path\to\scripts.obsp`.
- `patch crear` (create) uses `--base` as the base, or the `*.original.obsp` next to the file.
- `patch aplicar` (apply) always writes a new file.
- `hash` computes the game's 64-bit hash of each text and the object ID that an object with that
  name would have, without reading any file.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The tests that need the game's real file look for the `D2SV_OBSP` variable or the default Steam
path, and they are skipped if they do not find it:

```powershell
$env:D2SV_OBSP = 'C:\path\to\scripts.obsp'
```

## Building the executable

The [release.yml](.github/workflows/release.yml) workflow builds it when a `v*` tag is pushed. It
runs the tests and builds the wheel, the source archive and the `.exe`. It then runs the `.exe`
self-test and publishes the release with the third-party notices. Locally:

```powershell
python -m venv build\venv-pyinstaller
build\venv-pyinstaller\Scripts\python -m pip install pyinstaller==6.22.3
build\venv-pyinstaller\Scripts\python -m PyInstaller --noconfirm --workpath build\pyinstaller D2ScriptViewer.spec
```

The result is `dist\D2ScriptViewer.exe`. `D2ScriptViewer.exe --autoprueba report.txt` checks the
executable without opening the window: it writes the report (in Spanish) and exits with 0 if
everything is fine.

## Game data

The repository contains no game data: `*.obsp` is excluded, and the tests use synthetic fixtures.

## License

MIT. See [LICENSE](LICENSE) and [CREDITS.md](CREDITS.md).
