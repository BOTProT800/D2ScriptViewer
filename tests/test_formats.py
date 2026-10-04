# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Tests sintéticos del núcleo de formato: no necesitan ningún dato del juego."""

from __future__ import annotations

import math
import struct
import unittest

from d2scriptviewer.errors import FormatError
from d2scriptviewer.formats import bod, script
from d2scriptviewer.formats.hashes import HashDictionary, document_names
from d2scriptviewer.formats.obsp import (
    HEADER,
    INDEX_ENTRY,
    ObspFile,
    build_obsp,
    rebuild,
    string_table_order,
)
from d2scriptviewer.verification import verify_data
from tests import fixtures
from tests.fixtures import N


def roundtrip(document: bod.BodDocument) -> tuple[bytes, bod.BodDocument]:
    encoded = bod.encode(document)
    decoded = bod.decode(encoded)
    return encoded, decoded


class BodCodecTests(unittest.TestCase):
    def test_all_tags_roundtrip(self) -> None:
        encoded, decoded = roundtrip(fixtures.desc_document())
        self.assertEqual(bod.encode(decoded), encoded)
        tags = {node.tag for _path, node in bod.walk(decoded.root) if isinstance(node, bod.Value)}
        self.assertEqual(
            tags,
            {
                bod.TAG_INT32, bod.TAG_FLOAT32, bod.TAG_BOOL, bod.TAG_RAW_STRING, bod.TAG_OBJECT,
                bod.TAG_LIST, bod.TAG_MAP, bod.TAG_TUPLE, bod.TAG_NAME, bod.TAG_EXTERNAL_REF, bod.TAG_NULL,
            },
        )

    def test_decoded_values(self) -> None:
        _encoded, decoded = roundtrip(fixtures.desc_document())
        fields = {field.name.text: field.value for field in decoded.root.fields}
        self.assertEqual(fields["Health"].value, 100)
        self.assertEqual(fields["Speed"].value, 1.5)
        self.assertIs(fields["Visible"].value, True)
        self.assertEqual(fields["Comment"].text, "hola")
        self.assertEqual(fields["Mesh"].name, N("death_mesh"))
        self.assertEqual(fields["Behavior"].identity, (fixtures.SCRIPT_GROUP, fixtures.INSTANCE_ID))
        self.assertIsInstance(fields["Parent"], bod.Null)
        self.assertEqual(fields["Stats"].fields[0].value.value, -7)
        self.assertEqual(fields["Tags"].mode, bod.MODE_VALUES)
        self.assertEqual(fields["Pairs"].mode, bod.MODE_PAIRS)
        self.assertEqual(fields["Pairs"].items[0].value.text, "uno")
        self.assertEqual(fields["Lookup"].mode, bod.MODE_PAIRS)
        self.assertEqual(fields["Lookup"].items[0].key.name, N("Health"))
        self.assertEqual([item.value for item in fields["Color"].items], [1.0, 0.5, 0.0])
        self.assertTrue(fields["Script"].cls.is_script)
        self.assertEqual(fields["Script"].cls.group, fixtures.SCRIPT_GROUP)
        self.assertEqual(fields["Empty"].items, [])
        self.assertEqual(fields["Label"].text, "")

    def test_names_are_interned_once(self) -> None:
        encoded = bod.encode(fixtures.desc_document())
        definition = b"\x01" + struct.pack("<QH", N("death_mesh").hash, len("death_mesh")) + b"death_mesh"
        self.assertEqual(encoded.count(definition), 1)
        # "Health" es nombre de campo y cadena 0F a la vez: una sola definición.
        health = b"\x01" + struct.pack("<QH", N("Health").hash, 6) + b"Health"
        self.assertEqual(encoded.count(health), 1)

    def test_header_counters_are_recomputed(self) -> None:
        document = fixtures.desc_document()
        names = {name for name in document_names(document)}
        encoded = bod.encode(document)
        _magic, version, flags, count, max_length = bod.HEADER.unpack_from(encoded)
        self.assertEqual((version, flags), (4, 1))
        self.assertEqual(count, len(names))
        self.assertEqual(max_length, max(len(name.text) for name in names))
        # Unos contadores declarados falsos se leen pero no se reescriben.
        tampered = encoded[:8] + struct.pack("<II", 999, 999) + encoded[16:]
        decoded = bod.decode(tampered)
        self.assertEqual((decoded.declared_name_count, decoded.declared_max_name_length), (999, 999))
        self.assertEqual(bod.encode(decoded), encoded)

    def test_objects_are_numbered_in_depth_first_order(self) -> None:
        document = fixtures.desc_document()
        # Numeración de partida desordenada: el codificador la rehace.
        for _path, node in bod.walk(document.root):
            if isinstance(node, bod.BodObject) and node.index is not None:
                node.index = 77
        _encoded, decoded = roundtrip(document)
        indices = [
            node.index for _path, node in bod.walk(decoded.root)
            if isinstance(node, bod.BodObject) and node.index is not None
        ]
        self.assertEqual(indices, [0, 1, 2, 3, 4])

    def test_raw_numbers_are_preserved(self) -> None:
        signalling_nan = b"\x01\x00\x80\x7f"
        negative_zero = struct.pack("<f", -0.0)
        document = bod.BodDocument(
            4, 1,
            bod.BodObject(None, fixtures.native("Raw"), [
                fixtures.F("Nan", bod.Float32(signalling_nan)),
                fixtures.F("Zero", bod.Float32(negative_zero)),
                fixtures.F("Odd", bod.Bool(2)),
                fixtures.F("Min", bod.Int32.of(-(2 ** 31))),
            ]),
        )
        _encoded, decoded = roundtrip(document)
        values = [field.value for field in decoded.root.fields]
        self.assertEqual(values[0].raw, signalling_nan)
        self.assertTrue(math.isnan(values[0].value))
        self.assertEqual(values[1].raw, negative_zero)
        self.assertEqual(values[2].raw, 2)
        self.assertIs(values[2].value, True)
        self.assertEqual(values[3].value, -(2 ** 31))

    def test_script_and_native_classes(self) -> None:
        encoded, decoded = roundtrip(fixtures.instance_document())
        self.assertEqual(encoded[16], bod.CLASS_SCRIPT)
        self.assertEqual(struct.unpack_from("<I", encoded, 17)[0], fixtures.SCRIPT_GROUP)
        self.assertTrue(decoded.root.cls.is_script)
        _encoded, table = roundtrip(fixtures.table_document())
        self.assertEqual(table.root.cls.kind, bod.CLASS_NATIVE)
        self.assertIsNone(table.root.cls.group)


class BodErrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.encoded = bod.encode(fixtures.instance_document())

    def test_bad_magic(self) -> None:
        with self.assertRaises(FormatError):
            bod.decode(b"XXXX" + self.encoded[4:])

    def test_truncated(self) -> None:
        for cut in (1, 5, 12, len(self.encoded) - 17):
            with self.subTest(cut=cut), self.assertRaises(FormatError):
                bod.decode(self.encoded[:-cut])

    def test_trailing_bytes(self) -> None:
        with self.assertRaises(FormatError):
            bod.decode(self.encoded + b"\x00")

    def _single_field(self, payload: bytes) -> bytes:
        """Blob con una clase nativa ``C`` y un campo ``f`` cuyo valor es ``payload``."""
        name = lambda text: b"\x01" + struct.pack("<QH", 1 + len(text), len(text)) + text  # noqa: E731
        body = b"\x01" + name(b"C") + struct.pack("<I", 1) + name(b"f") + payload
        return bod.HEADER.pack(bod.MAGIC, 4, 1, 2, 1) + body

    def test_well_formed_helper(self) -> None:
        decoded = bod.decode(self._single_field(b"\xfe"))
        self.assertIsInstance(decoded.root.fields[0].value, bod.Null)

    def test_unknown_tag(self) -> None:
        with self.assertRaises(FormatError):
            bod.decode(self._single_field(b"\x06"))

    def test_raw_string_without_marker(self) -> None:
        with self.assertRaises(FormatError):
            bod.decode(self._single_field(b"\x05\x00\x01\x00a"))

    def test_unknown_sequence_modes(self) -> None:
        for payload in (b"\x09" + struct.pack("<IB", 0, 2), b"\x0a" + struct.pack("<IB", 0, 0)):
            with self.subTest(payload=payload), self.assertRaises(FormatError):
                bod.decode(self._single_field(payload))

    def test_undefined_name_reference(self) -> None:
        with self.assertRaises(FormatError):
            bod.decode(self._single_field(b"\x0f\x00" + struct.pack("<I", 9)))

    def test_unknown_name_marker_and_class_kind(self) -> None:
        with self.assertRaises(FormatError):
            bod.decode(self._single_field(b"\x0f\x02"))
        blob = bytearray(self._single_field(b"\xfe"))
        blob[16] = 0x03
        with self.assertRaises(FormatError):
            bod.decode(bytes(blob))

    def test_encoder_rejects_invalid_values(self) -> None:
        for value in (bod.Int32(b"\x00"), bod.RawString("x" * 0x10000), bod.BodList(3, [])):
            document = bod.BodDocument(4, 1, bod.BodObject(None, fixtures.native("C"), [fixtures.F("f", value)]))
            with self.subTest(value=value), self.assertRaises(FormatError):
                bod.encode(document)


class BodPresentationTests(unittest.TestCase):
    def test_paths_and_labels(self) -> None:
        document = fixtures.desc_document()
        stats_damage = None
        for path, node in bod.walk(document.root):
            if bod.path_label(document, path) == "Stats.Damage":
                stats_damage = path
        self.assertIsNotNone(stats_damage)
        self.assertIs(bod.resolve(document, stats_damage), document.root.fields[7].value.fields[0].value)
        self.assertEqual(bod.path_label(document, ()), "(raíz)")
        pair_path = (9, 0, 1)  # Pairs[0].valor
        self.assertEqual(bod.path_label(document, pair_path), "Pairs[0].valor")
        self.assertEqual(bod.value_text(bod.resolve(document, pair_path)), "'uno'")

    def test_value_texts(self) -> None:
        self.assertEqual(bod.value_text(bod.Float32.of(0.1)), "0.1")
        self.assertEqual(bod.value_text(bod.Float32.of(1.0)), "1")
        # Notación decimal salvo en magnitudes extremas.
        self.assertEqual(bod.value_text(bod.Float32.of(200.0)), "200")
        self.assertEqual(bod.value_text(bod.Float32.of(148360.0)), "148360")
        self.assertEqual(bod.value_text(bod.Float32.of(3.4e38)), "3.4e+38")
        self.assertEqual(bod.value_text(bod.Float32.of(-0.0)), "-0")
        self.assertEqual(bod.value_text(bod.BodTuple([bod.Null()])), "1 elemento")
        self.assertEqual(bod.value_text(bod.Bool(2)), "true (0x02)")
        self.assertEqual(bod.value_text(bod.ExternalRef(10000, 255)), "→ 10000:00000000000000FF")
        self.assertEqual(bod.type_text(bod.BodList(bod.MODE_PAIRS, [])), "pares")


class ObspTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = fixtures.make_obsp()
        self.obsp = ObspFile.parse(self.data)

    def test_parse_and_rebuild(self) -> None:
        self.assertEqual(len(self.obsp.entries), len(fixtures.OBJECTS))
        self.assertEqual(rebuild(self.obsp), self.data)
        self.assertEqual(self.obsp.layout_problems(), [])

    def test_header_is_recomputed(self) -> None:
        header = self.obsp.header
        self.assertEqual((header.version, header.unknown, header.pad), (10, 1, 0))
        self.assertEqual(header.object_count, 4)
        self.assertEqual(header.string_count, len(self.obsp.strings))
        self.assertEqual(header.max_string_length, max(len(text) for text in self.obsp.strings.values()))
        self.assertEqual(self.obsp.index_end, header.strings_end + 4 * INDEX_ENTRY.size)

    def test_string_table_order_and_empty_string(self) -> None:
        self.assertEqual(list(self.obsp.strings), string_table_order(self.obsp.entries))
        first = self.obsp.entries[0]
        self.assertEqual(list(self.obsp.strings)[:3], [first.path_hash, first.name_hash, 0])
        self.assertEqual(self.obsp.strings[0], "")

    def test_offsets_follow_blob_sizes(self) -> None:
        script_blob = fixtures.script_blob() + b"\x00\x00"
        changed = ObspFile.parse(rebuild(self.obsp, {2: script_blob}))
        self.assertEqual(changed.blob(2), script_blob)
        self.assertEqual(changed.entries[3].offset, self.obsp.entries[3].offset + 2)
        self.assertEqual(changed.blob(3), self.obsp.blob(3))
        self.assertEqual(changed.layout_problems(), [])

    def test_missing_string_is_an_error(self) -> None:
        strings = dict(self.obsp.strings)
        del strings[self.obsp.entries[0].path_hash]
        with self.assertRaises(FormatError):
            build_obsp(self.obsp.header, self.obsp.entries, self.obsp.blobs(), strings)

    def test_parse_errors(self) -> None:
        with self.assertRaises(FormatError):
            ObspFile.parse(b"OBS")
        with self.assertRaises(FormatError):
            ObspFile.parse(b"XXXX" + self.data[4:])
        with self.assertRaises(FormatError):
            ObspFile.parse(self.data[:-1])  # el último blob sale del archivo
        bad_header = bytearray(self.data)
        struct.pack_into("<I", bad_header, 0x11, len(self.data) + 10)
        with self.assertRaises(FormatError):
            ObspFile.parse(bytes(bad_header))
        self.assertEqual(HEADER.size, 29)
        self.assertEqual(INDEX_ENTRY.size, 51)

    def test_layout_problems_detect_gaps(self) -> None:
        padded = ObspFile.parse(self.data + b"\x00")
        self.assertTrue(padded.layout_problems())


class ScriptTests(unittest.TestCase):
    def test_header(self) -> None:
        data = fixtures.make_obsp()
        obsp = ObspFile.parse(data)
        entry = obsp.entries[2]
        header = script.parse_header(obsp.blob(2))
        self.assertEqual([symbol.text for symbol in header.symbols], list(fixtures.SCRIPT_SYMBOLS))
        self.assertEqual(script.header_problems(header, entry), [])
        self.assertEqual(obsp.blob(2)[header.body_offset:], fixtures.SCRIPT_BODY)

    def test_problems_are_reported(self) -> None:
        obsp = ObspFile.parse(fixtures.make_obsp())
        blob = bytearray(obsp.blob(2))
        struct.pack_into("<II", blob, 0, 2, len(fixtures.SCRIPT_SYMBOLS))
        struct.pack_into("<I", blob, 8, 99)
        header = script.parse_header(bytes(blob))
        problems = script.header_problems(header, obsp.entries[0])
        self.assertEqual(len(problems), 4)

    def test_truncated(self) -> None:
        with self.assertRaises(FormatError):
            script.parse_header(fixtures.script_blob()[:20])
        with self.assertRaises(FormatError):
            script.parse_header(struct.pack("<III", 1, 0xFFFFFF, 0))


class HashDictionaryTests(unittest.TestCase):
    def test_lookup_and_conflicts(self) -> None:
        dictionary = HashDictionary()
        dictionary.update([(1, "a"), (2, "b"), (1, "a")])
        self.assertEqual(len(dictionary), 2)
        self.assertEqual(dictionary.text(1), "a")
        self.assertEqual(dictionary.hash_of("b"), 2)
        self.assertIsNone(dictionary.hash_of("B"))
        self.assertEqual(dictionary.name_for("a"), bod.Name(1, "a"))
        dictionary.add(1, "z")
        self.assertEqual(dictionary.conflicts, [(1, "a", "z")])
        dictionary.add(3, "a")
        self.assertEqual(dictionary.reverse_conflicts(), [("a", [1, 3])])


class VerificationTests(unittest.TestCase):
    def test_synthetic_file_passes(self) -> None:
        report = verify_data(fixtures.make_obsp())
        self.assertTrue(report.ok, [check for check in report.checks if not check.ok])
        self.assertFalse(report.is_steam_original)

    def test_broken_file_fails(self) -> None:
        self.assertFalse(verify_data(b"nada").ok)
        data = bytearray(fixtures.make_obsp())
        obsp = ObspFile.parse(bytes(data))
        # Rompe un BOD: cambia su firma.
        data[obsp.entries[0].offset] = ord("X")
        self.assertFalse(verify_data(bytes(data)).ok)


if __name__ == "__main__":
    unittest.main()
