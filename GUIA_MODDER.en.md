# Modder's guide

[Español](GUIA_MODDER.md) · **English**

D2ScriptViewer's keyboard shortcuts and what people usually change in `scripts.obsp`. The
[README](README.en.md) covers installing, saving and patches; this guide is for working with the
tool day to day. It describes the English interface; the Spanish one is the same, with Spanish
names.

**Legend for part 2:**

- **Tested:** changed with the tool and played, and the effect was the expected one
  ([research/PRUEBAS_EN_JUEGO.md](research/PRUEBAS_EN_JUEGO.md), in Spanish).
- **To explore:** the object type exists in the file, but nobody has checked what each field
  does; what is said about it comes from the names.
- **Not tested in the game:** we know where the value is and the tool can change it, but nobody
  has checked in the game what happens when it changes.

## Part 1 — Keyboard shortcuts

### Anywhere in the window

| Key | Action |
|---|---|
| Ctrl+O | Open another `.obsp` |
| Ctrl+S | Save (with a cell open, it first confirms its value; if the value is not valid, it does not save) |
| Ctrl+Shift+S | Save As… |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+P | Pending changes (before → after for each property) |
| Ctrl+F | Find in the open object: goes to the bar above the properties |
| Ctrl+Shift+F | Find in the whole file |
| Ctrl+G | Go to a path: opens the “Go to” bar above the properties (also in Go → Go to Path…) |
| Alt+← | Back in the navigation history |
| Alt+→ | Forward in the navigation history |

Ctrl+Z, Ctrl+Y and Ctrl+P do nothing while you type in a text field (a filter, the search bar,
the “Go to” bar, the cell you are editing…): there, the keys belong to the field. Leave the field
to undo changes to the file.

The menus have no underlined letters. The actions without a shortcut are in them: File → Restore
Original…, Export to JSON and CSV…, Export Patch…, Apply Patch…, and Edit → Revert Object.

The **Idioma / Language** menu switches the interface between English and Spanish at once. It
does not close the window or lose your unsaved changes or your undo history, and it remembers
your choice. The interface starts in English until you choose. Switching closes the whole-file
search and the pending changes, and leaves the property tree open only down to the selected row.

### Object list (left)

| Key | Action |
|---|---|
| ↑ / ↓ | Select the previous or next object; it opens in the center when selected |
| → | Expand the group |
| ← | Collapse the group, or go up to the group that contains it |
| Enter or Space | Expand or collapse the group |
| Page Up / Page Down | Scroll the list by a page |
| Tab | Move between the filters (group by, type, class, text) and the list |

The filters apply as you type. Grouping by **Folder** uses the game editor's folders
(`oc\Body\slayer`…), by **Path** the prefix of the path (`death/…`), and by **Type** the object's
category.

### Properties (center)

| Key | Action |
|---|---|
| ↑ / ↓, → / ← | Move, expand and collapse, as in the object list |
| Enter | On a value: edit it. On a reference (`→ …`): go to its target. On a container: expand or collapse |
| F2 | Edit the value. On a reference: open the picker to change its target |
| Double-click | Same as Enter |
| Right-click | Menu: go to target, edit, revert the property, structure, copy value, copy property path and copy full path |
| Ctrl+D | Duplicate the list item or map entry (the copy goes right after it) |
| Del | Delete the item or entry |
| Alt+↑ / Alt+↓ | Move the item up or down within its list |
| F3 / Shift+F3 | Next or previous result of the in-object search |

- The structure keys only work on list items and map entries, and never in compiled scripts.
  **Set to Null** and **Fill Null with an Object…** have no shortcut: right-click, or Edit →
  Structure.
- The line under the tree explains why a row cannot be edited. While you type, it warns about
  errors and shows how the value will be saved.
- **Copy Property Path** (right-click) gives something like `MoveStates[44].JumpImpulse`: it is the
  handiest way to note down what you changed. **Copy Full Path** puts the object in front:
  `death/playercommon_movestates · MoveStates[44].JumpImpulse`. Both can be pasted into Ctrl+G to
  come back to that row.

### Find in object (bar above the properties)

Three fields, one per column of the tree: **Name**, **Type** and **Value**. They search the whole
open object, including nodes and ranges you have not expanded.

- **Name** and **Value** search for the text they contain, as it shows in the column and
  ignoring case. On a reference, the value is `→` and the target: `death_desc` finds the
  references to `death/death_desc`.
- **Type** is exact (`int32`, `float32`, `name`, `reference`, `op_3A`…). The list (↓ or the
  arrow) has the types of the open object; “(any)” does not filter. In the Spanish interface the
  types are shown and searched in Spanish; `int32`, `float32`, `bool` and `op_XX` do not change.
- An empty field does not filter, and the fields with text combine with “and”.
- The counter says “3 of 7” on a result, “7 results” if the selected row is not one, and “No
  results” if there are none.
- The fields stay when you change objects, and the results are recalculated after editing,
  undoing or changing the structure.

| Key | Action |
|---|---|
| Ctrl+F | Go to the bar, to the last field used, with its text selected (cancels the cell you were editing) |
| Typing | After a short pause, goes to the first result from the selected row on |
| Enter or F3 | Next result; after the last one it goes back to the first |
| Shift+Enter or Shift+F3 | Previous result |
| ‹ / › | The same with the mouse |
| F2 | Edit the selected row, as in the tree |
| Escape | Back to the tree (the arrows move from the result) |

### Go to a path (“Go to” bar above the properties)

Ctrl+G opens a bar between the search bar and the tree. Type or paste a path and press Enter: the
tree opens down to that row and selects it, even inside the ranges of long lists
(`[1000…1499]`).

- **Formats:**
  - `MoveStates[44].JumpImpulse`: a row of the open object, as Copy Property Path gives it. In
    scripts, `Functions.onInit.0x004E`.
  - `death/playercommon_movestates · MoveStates[44].JumpImpulse`: jumps to that object and row.
    If your keyboard has no `·`, `::` works too
    (`death/playercommon_movestates::MoveStates[44].JumpImpulse`). Alt+← goes back to the
    previous object.
  - `death/death`: opens the object.
- **When the bar opens**, if the clipboard holds something that looks like a path, it is already
  typed in and selected. If not, the last path you used stays.
- **Case and accents:** the exact name is tried first. If it is not there, the name is accepted
  ignoring case and accents (`movestates[44].jumpimpulse`), as long as there is only one match.
  In scripts, `0x4e` works as `0x004E`.
- **If the path fails halfway**, the tree stays on the last valid row, and the bar stays open with
  the failing part selected. The line under the tree says why:
  - similar names (“JumpImpuls” is not a field of MoveStates[44]. Similar: “JumpImpulse”);
  - how many items the list has;
  - or what was expected.

  If the object does not exist, nothing moves and objects with similar names are suggested.
- Indices are numbers: `MoveStates[Jump]` (by the item's `Name`) is not available.
- **Both languages work.** The fixed rows of scripts and the children of a pair are shown in the
  language of the interface. Ctrl+G accepts both forms in both languages, and a path copied in
  Spanish works here as it is. The game's own names (fields, objects, functions) never change.

  | English | Spanish |
  |---|---|
  | `Version`, `Symbols`, `Path hash`, `Group`, `Name`, `Base class` | `Versión`, `Símbolos`, `Hash de ruta`, `Grupo`, `Nombre`, `Clase base` |
  | `Members`, `Initial values`, `Functions`, `States`, `Parameters` | `Miembros`, `Valores iniciales`, `Funciones`, `Estados`, `Parámetros` |
  | `key`, `value` (children of a pair), `(root)` | `clave`, `valor`, `(raíz)` |

  Patch files always store the Spanish form, so a patch made in one language applies in the
  other.

| Key | Action |
|---|---|
| Ctrl+G | Open the bar or go back to it (cancels the cell you were editing) |
| Enter | Go to the path. If it gets there, the bar closes and the focus goes to the tree: F2 edits the row |
| Escape | Close the bar and go back to the tree; if the object was still opening, it no longer jumps to the row |

### Cell editor

| Key | Action |
|---|---|
| Enter (also the keypad one) | Confirm |
| Escape | Cancel |
| Clicking outside the cell or turning the mouse wheel | Cancel |
| ↓ | In names (hashed strings) and bools: open the list of options |

In a bool, choosing an option from the list confirms it. In a name, the list suggests the names
that already exist in the file and narrows as you type; choosing one copies it into the cell, and
you confirm with Enter.

### Details (right)

In the **References** tab, Enter or double-click on a row of “Points to” or “Used by” opens that
object. Alt+← goes back to the previous one.

### Windows

| Window | Key | Action |
|---|---|---|
| Find in whole file (Ctrl+Shift+F) | Enter in the text field | Search |
| Find in whole file | Enter or double-click on a result | Go to the object and the property |
| Pending Changes | Enter or double-click | Go to the changed property |
| Pending Changes | Escape | Close |
| Change Reference | Typing | Filter by path or name (the filter has the focus when it opens) |
| Change Reference | Enter or double-click in the list | Accept the chosen object |
| Change Reference | Escape | Cancel |
| Fill Null | Double-click | Copy the chosen example |
| Fill Null | Escape | Cancel |

In **Change Reference**, Enter only accepts when the focus is on the list: move to it with a click
or with Tab.

### How to type values

| Type | Accepted | Examples |
|---|---|---|
| Integer (int32) | Decimal, or `0x…` as a 32-bit pattern; `_` as a separator | `700`, `-1`, `0xFFFFFFFF`, `1_000` |
| Float (float32) | Decimal point or comma; no NaN or infinities | `700`, `0.5`, `0,5`, `1e-3` |
| Bool | `true`, `1`, `yes`, `on` (also `sí`, `verdadero`) / `false`, `0`, `no`, `off` (also `falso`) | `true` |
| String without a hash (`'…'`) | ASCII text | `flag_my_mod` |
| Name (hashed string) | A name from the file or a new ASCII one (asks for confirmation) | `D_WScy_Combo04` |

Names are case-sensitive: `D_Jump` and `d_jump` are different names to the game.

## Part 2 — What people usually change

### Before you start: back up your saves

**Back up your saved games before trying changes**, and above all before testing limits
(extreme values, duplicated or emptied lists, patched scripts). If the game saves while a change
has it in a bad state, that save can end up damaged.

- The tool only protects `scripts.obsp`: `scripts.original.obsp`, the copies in `.d2sv_backups\`
  and Restore Original… bring back the scripts file, **not your saves**. A damaged save is not
  fixed by restoring the original.
- Copy the whole saves folder somewhere else, and repeat the copy each time you reach a point you
  do not want to lose.
- If Steam Cloud is on for the game, a damaged save can be uploaded and replace the one in the
  cloud. Keep your own copy outside the game folder.
- For testing, use a new save or one you do not mind losing.

### How to work

1. Back up your saves (see above) and close the game (with it open, the tool cannot save).
2. Change **one thing**, or a few related ones.
3. Ctrl+P to review the pending changes and Ctrl+S to save. The first time, `scripts.original.obsp`
   is created.
4. Test it in the game, on a test save. If you see no effect, try a new save as well: the save
   may store some values and keep the old ones (**hypothesis**, not checked).
5. When it works, File → Export Patch…, so you do not lose it if Steam restores the file.
6. To go back to the original: File → Restore Original… If a save was damaged, replace it with
   your copy.

### What has been tested in the game

| What changes | Object | Property | Example | Result |
|---|---|---|---|---|
| Death's jump height | `death/playercommon_movestates` (`CharacterMoveStateList`) | `MoveStates[44].JumpImpulse` (float), the state with `Name` = `Jump` | 350 → 700 | A much higher normal jump |
| Animation that plays | `death/death_animations` (`AnimationList`) | `Animations[n].AnimationName` (hashed name) | `D_Jump` → `D_WScy_Combo04` | The jump plays a scythe combo |
| Logic of a script | `ui_core/pausemenu` (script) | `Functions.onInit.0x004E`, the `true` of `Game.setPaused(true)` | `true` → `false` | The pause menu no longer stops the game |
| Structure of a list | `death/playercommon_movestates` | Duplicate `MoveStates[0]` (Ctrl+D) | — | The game loads the longer list without problems |
| Longer string without a hash | `base/quest_test_dialog` (`DialogSet`) | `Dialogs[0].Actions[1].FlagID` | +5 characters | The file changes size and the game loads it |
| Sound of an action | `death/death_sounds` (`SoundList`) | `Sounds[47].Event`, the entry with `Name` = `death_whoosh_jump` | `Jump_Whoosh` → `Voc_Death_Death` | Jumping sounds like Death's death scream |
| Another character's sound | `death/death_sounds` | `Sounds[47].Bank` and `Sounds[47].Event` | `SFX_Character_Archon` and `Voc_Archon_Corrupted_Scream` | The double jump sounds like the Archon's scream, even far from his area |
| Chained evades | `death/death_desc` (`Desc`) | `Conditionals.Conditionals[2].ConditionalInput[0].TargetEvadeNumber` (int), in the `--(Evade)(End)` conditional | 2 → 6 or 12 | Death chains more normal evades than the usual three |

The paths in the Property column can be pasted into Ctrl+G with the object open, or with the
object in front: `death/playercommon_movestates · MoveStates[44].JumpImpulse`,
`ui_core/pausemenu · Functions.onInit.0x004E`, `base/quest_test_dialog · Dialogs[0].Actions[1].FlagID`,
`death/death_sounds · Sounds[47].Event` or
`death/death_desc · Conditionals.Conditionals[2].ConditionalInput[0].TargetEvadeNumber`.
In `Animations[n].AnimationName`, replace `n` with the animation's index.

What those tests teach:

- **Find list items by their `Name`, not by their index.** Duplicating `MoveStates[0]` moved the
  `Jump` state from `[44]` to `[45]`. Indices change; the `Name` does not.
- **An entry's `Name` is the key the game looks it up by: do not change it.** In the phase 8 test,
  `Animations[435].Name` (`PaperDoll_Idle`) was changed by mistake instead of `AnimationName`, the
  row below it, and the menu doll was left without animation. To change an animation, edit
  `AnimationName`.
- **A new `AnimationName`** must be the name (without `.anm`) of an animation the game ships in
  its `.upak` files. If you put a non-looping animation where an idle is expected (for example
  `PaperDoll_Idle`), it plays once and freezes on its last frame.
- **In scripts**, only `int`, `float` and `bool` literals change, without changing sizes. The
  argument count of a call (the `int n` before the call) is read-only.
- **To change a sound, edit `Event`** (and `Bank` if the event is from another bank), not `ID` or
  `Name`.
  - Each animation fires its sounds by number (`SoundID` in `Triggers`), which is the `ID` of an
    entry in the character's sound list.
  - So the change affects every animation that uses that entry: `death_whoosh_jump` sounds in
    the jump, the double jump, ledges and more.
  - The existing events come from the `Event` of other entries: find one with Ctrl+Shift+F.
  - Whether the game loads a new bank, one it does not ship with, is untested.
- **For testing, pick a sound that repeats and is easy to hear.** A short whoosh that fades away
  is hard to notice; a scream where there was a whoosh is not.
- **Some data is stored twice.**
  - `death/death_desc` carries an exact copy of `death/death_conditionals` (in `Conditionals`),
    of `death/death_windows` (`InputWindows`) and of `death/death_visuals` (`Visuals`).
  - The whole file has 432 such copies. Changing one does not change the other, and the tool
    does not warn you.
  - For the evades, the change worked in the `death_desc` copy. That the standalone object does
    not count is a deduction, not yet confirmed by a single-change test.
  - If a change has no visible effect, try the other copy.
- **A single value controls all normal evades**, in the four directions and with or without lock-on.
  The evades of the Reaper form and of the two-handed rifle are untested.

### Not tested in the game: the inventory slots

An example of reaching a value with the in-object search. **It has not been tested in the
game**: we know where the number is and that the tool can change it, not what happens when it
changes.

1. Open the `death/death` script (the object list filter helps you find it).
2. Ctrl+F. In **Type**, type or choose `op_3A`; in **Value**, type `NumSlots`. The counter says
   “1 of 7”.
3. They are the seven `op_3A NumSlots` rows of `Functions.onInit`, from `0x0770` to `0x0A4A`.
   Enter goes through them. Ctrl+G with `death/death · Functions.onInit.0x0770` also takes you to
   the first one.
4. The number is in the row below each one (Escape and ↓): an `int32` worth 21, 21, 21, 22, 22,
   22 and 21. It is a code literal, so F2 changes it without changing the size of the script.

Going by the name, each one would be the number of slots of a part of the inventory. Which part
each one is, whether the game accepts other values and whether the interface shows them is still
to be checked. If you try it, back up your saves first (see above): what you carry in your
inventory is stored in the save.

### To explore: where things usually are

Categories in the file (the Type column of the object list and the **Type** filter):

| Type | Objects | What it contains | Interest for modders |
|---|---|---|---|
| `Desc` | 1,668 | Descriptions of actors, characters, projectiles, items… (`death/death_desc` is Death) | Floats and ints of each entity. The first place to look for stats |
| `CharacterMoveStateList` | 275 | Movement states per character | Jump (tested), and the other states to explore |
| `AnimationList` | 1,071 | Which animation each action uses | Changing animations (tested) |
| `FloatTable` | 65 | Float tables with row and column names | Numeric tables: export them to CSV to see what each one is |
| `Instance` | 757 | `ItemGeneratorTable`, `Quest`, `DialogSet` and other script classes | Item generation, quests and dialogs, going by the names |
| `Script` | 3,690 | Compiled scripts | Code literals (tested) |
| `SoundList` | 275 | Sounds per character (`ID`, `Name`, `Bank`, `Event`) | Changing sounds (tested) |
| `HitInfoList` | 3 | Hit information | To explore |
| `InputWindowList` | 5 | Input windows (combos, going by the name) | To explore |
| `CharacterConditionalList` | 7 | Conditions per character | Chained evades (tested in the `death_desc` copy), and the rest to explore |
| `ModuleSystem` | 4 | Module graphs | To explore |
| `TerrainMaterialDesc` | 42 | Terrain materials | To explore |

### How to find what you want to change

- **By its path.** If you already know the path (from your notes, this guide or a patch), Ctrl+G
  and paste it.
- **By field name.** Ctrl+Shift+F, tick “Field names” and type an English term for the concept.
  `Jump` leads to `JumpImpulse`; try others that come to mind. If there are no results, no field
  contains that text.
- **By the number you see in the game.** Ctrl+Shift+F with a number (`350`) finds the integers and
  floats with exactly that value. It helps to locate a value you know.
- **Inside a large object.** Ctrl+F and the Name, Type and Value fields of the bar, instead of
  expanding the tree by hand. Name `JumpImpulse` in `death/playercommon_movestates` goes through
  the rows with that name without opening the states one by one. The bar searches for contained
  text (Value `350` also finds `3500`); for the exact value of a number, use the whole-file search.
- **Following references.** From a character's `Desc`, the `→ …` rows lead to their movement
  lists, animations, and so on (`death/death_desc` → `MoveStateListArray.MoveStateLists[0]` →
  `death/playercommon_movestates`). In Details → References, “Used by” says who points to the open
  object. Alt+← goes back.
- **By class.** The **Class** filter on the left lists every object of a class (`PlayerJumpDesc`,
  `DialogSet`…).
- **Outside the tool.** File → Export to JSON and CSV… dumps everything to a folder you can search
  with any editor, and each `FloatTable` to a CSV that opens in a spreadsheet. It is only for
  reading: changes are made in the tool.
- **Scripts.** The center panel shows the disassembled code of each function, and Details →
  Script shows the symbols.
  - Ctrl+Shift+F with “Values and symbols” finds the scripts that have the text among their
    symbols (their members, functions and states).
  - Names that only appear inside the code, such as the `setPaused` method, do not show up in
    that search. With the script open, the bar does find them (Ctrl+F, Value `setPaused`).
  - To search them in every script at once, use the JSON export, which includes the disassembled
    code, or `python -m d2scriptviewer disasm path`.

### What not to touch (or to touch carefully)

- **Identifiers.** Fields named `…ID` or `…Id`, the ones containing `Hash`, and huge integers
  (|value| ≥ 1,000,000, almost always identifiers the editor created from the date) link to other
  things in the game. For example, the `SoundID` of an animation trigger is the `ID` of a sound in
  the character's list. The tool asks for confirmation before changing them.
- **The `Name` of list entries**, for the reasons above.
- **Repeated keys.** After Ctrl+D on a map entry, change the key of the copy: a repeated key
  prevents saving.
- **References without a target.** Saving is also blocked if a reference points to an object that
  does not exist.
- **Extreme values.** Doubling a value is noticeable and easy to undo; multiplying it by 1,000 can
  break the physics or the save. Only try them with your saves backed up.
- **Things the tool does not allow** (no need to try): renaming or creating objects, changing
  field or class names, or changing the size of a script's code.
