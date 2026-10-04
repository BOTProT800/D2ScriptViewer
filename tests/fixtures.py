# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""OBSP sintético construido con el propio codificador: sin ningún dato del juego.

Cubre los 11 tags, las listas en modo 0 y 1, el mapa en modo 1, clases nativas y
de script, nombres nuevos y por referencia, nulos, referencias externas y un
script compilado de tipo 0 con cuerpo opaco.

Los hashes se calculan con la función del juego (``hashes.name_hash``) y las
identidades son el hash del nombre en minúsculas, como en el archivo real.
"""

from __future__ import annotations

import struct

from d2scriptviewer.formats import bod
from d2scriptviewer.formats.bod import (
    BodDocument,
    BodList,
    BodMap,
    BodObject,
    BodTuple,
    Bool,
    ClassRef,
    ExternalRef,
    Field,
    Float32,
    HashedString,
    Int32,
    Name,
    Null,
    Pair,
    RawString,
)
from d2scriptviewer.formats.hashes import name_hash, object_id
from d2scriptviewer.formats.obsp import IndexEntry, ObspHeader, build_obsp

GROUP = 10000
SCRIPT_GROUP = 10001


def N(text: str) -> Name:
    return Name(name_hash(text), text)


def native(name: str) -> ClassRef:
    return ClassRef(bod.CLASS_NATIVE, None, N(name))


def scripted(name: str, group: int = SCRIPT_GROUP) -> ClassRef:
    return ClassRef(bod.CLASS_SCRIPT, group, N(name))


def F(name: str, value: bod.Value) -> Field:
    return Field(N(name), value)


# Identidades de los objetos del fixture: el hash del nombre en minúsculas.
DESC_ID = object_id("Death_Desc")
INSTANCE_ID = object_id("WeaponBehavior_Inst")
SCRIPT_ID = object_id("Test")
TABLE_ID = object_id("Char_Test")


def desc_document() -> BodDocument:
    """Un ``Desc`` con todos los tags y todos los modos."""
    root = BodObject(
        None,
        native("ActorDesc"),
        [
            F("Health", Int32.of(100)),
            F("Speed", Float32.of(1.5)),
            F("Visible", Bool(1)),
            F("Comment", RawString("hola")),
            F("Mesh", HashedString(N("death_mesh"))),
            F("Behavior", ExternalRef(SCRIPT_GROUP, INSTANCE_ID)),
            F("Parent", Null()),
            F("Stats", BodObject(0, native("Stats"), [F("Damage", Int32.of(-7)), F("Crit", Float32.of(0.25))])),
            # "death_mesh" ya está definido: aquí sale como referencia (00).
            F("Tags", BodList(bod.MODE_VALUES, [HashedString(N("death_mesh")), HashedString(N("fire"))])),
            F("Pairs", BodList(bod.MODE_PAIRS, [Pair(Int32.of(1), RawString("uno")), Pair(Int32.of(2), Null())])),
            # Un nombre de campo reutilizado como cadena 0F: comparten tabla.
            F("Lookup", BodMap(bod.MODE_PAIRS, [Pair(HashedString(N("Health")), Float32.of(2.0))])),
            F("Color", BodTuple([Float32.of(1.0), Float32.of(0.5), Float32.of(0.0)])),
            F(
                "Script",
                BodObject(
                    1,
                    scripted("scripts/weaponbehavior"),
                    [F("Enabled", Bool(0)), F("Child", BodObject(2, native("Stats"), []))],
                ),
            ),
            F("Empty", BodList(bod.MODE_VALUES, [])),
            F("Label", RawString("")),
            # Con aspecto de identificador: la edición pide confirmación.
            F("ItemID", Int32.of(1234)),
            # Lista de objetos con un *ID único: duplicar un elemento debe avisar.
            F(
                "Slots",
                BodList(
                    bod.MODE_VALUES,
                    [
                        BodObject(3, native("Slot"), [F("SlotID", Int32.of(1)), F("Count", Int32.of(5))]),
                        BodObject(4, native("Slot"), [F("SlotID", Int32.of(2)), F("Count", Int32.of(7))]),
                    ],
                ),
            ),
        ],
    )
    return BodDocument(4, 1, root)


def instance_document() -> BodDocument:
    """Instancia de una clase de script que apunta al Desc."""
    root = BodObject(
        None,
        scripted("scripts/weaponbehavior"),
        [F("Owner", ExternalRef(GROUP, DESC_ID)), F("Enabled", Bool(1))],
    )
    return BodDocument(4, 1, root)


def table_document() -> BodDocument:
    rows = [
        BodObject(index, native("FloatTableRow"), [F("Values", BodList(bod.MODE_VALUES, [Float32.of(value)]))])
        for index, value in enumerate((10.0, 20.5))
    ]
    return BodDocument(4, 1, BodObject(None, native("FloatTable"), [F("Data", BodList(bod.MODE_VALUES, rows))]))


SCRIPT_SYMBOLS = ("OnStart", "NumSlots", "getInventory")
SCRIPT_BODY = bytes([0x3B, 1, 0, 0, 0, 0x23, 21, 0, 0, 0, 0x29, 0x32, 0x2F])


def script_blob(path: str = "scripts/test", group: int = SCRIPT_GROUP) -> bytes:
    symbols = b"".join(
        struct.pack("<QI", name_hash(text), len(text)) + text.encode("latin-1") for text in SCRIPT_SYMBOLS
    )
    head = struct.pack("<III", 1, len(SCRIPT_SYMBOLS), max(len(text) for text in SCRIPT_SYMBOLS))
    return head + symbols + struct.pack("<QI", name_hash(path), group) + SCRIPT_BODY


#: (ruta, nombre, carpeta, clase, grupo, id, tipo)
OBJECTS = (
    ("death/death_desc", "Death_Desc", "", "ActorDesc", GROUP, DESC_ID, 8),
    ("scripts/weaponbehavior_inst", "WeaponBehavior_Inst", "oc\\Body\\slayer", "scripts/weaponbehavior", SCRIPT_GROUP, INSTANCE_ID, 1),
    ("scripts/test", "Test", "", "", SCRIPT_GROUP, SCRIPT_ID, 0),
    ("base/char_test", "Char_Test", "tables", "", GROUP, TABLE_ID, 15),
)


def fixture_parts() -> tuple[list[IndexEntry], list[bytes], dict[int, str]]:
    blobs = [
        bod.encode(desc_document()),
        bod.encode(instance_document()),
        script_blob(),
        bod.encode(table_document()),
    ]
    entries = []
    strings: dict[int, str] = {}
    for (path, name, folder, class_name, group, identity, kind), blob in zip(OBJECTS, blobs):
        for text in (path, name, folder, class_name):
            strings[name_hash(text)] = text
        entries.append(
            IndexEntry(
                name_hash(path), identity, 0, len(blob), group, kind,
                name_hash(name), name_hash(folder), name_hash(class_name),
            )
        )
    return entries, blobs, strings


def make_obsp() -> bytes:
    entries, blobs, strings = fixture_parts()
    header = ObspHeader(version=10, unknown=1, object_count=0, strings_end=0, string_count=0, max_string_length=0)
    return build_obsp(header, entries, blobs, strings)
