# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Tests de oro: reproducen sobre el archivo real lo verificado en el apéndice A del plan.

Se omiten si no hay archivo real (``D2SV_OBSP`` o la ruta del juego).
"""

from __future__ import annotations

import hashlib
import unittest
from collections import Counter

from d2scriptviewer.formats import bod, script
from d2scriptviewer.formats.hashes import HashDictionary, document_names
from d2scriptviewer.formats.obsp import ObspFile, rebuild, string_table_order
from d2scriptviewer.verification import verify_data
from tests.support import ORIGINAL_SHA256, ORIGINAL_SIZE, real_bytes, requires_real_file

#: Tabla del apéndice A.1: objetos y bytes por tipo.
KIND_TABLE = {
    0: (3690, 5_795_617),
    1: (757, 1_525_649),
    2: (275, 1_945_850),
    3: (275, 830_826),
    4: (1071, 3_603_893),
    5: (7, 64_591),
    6: (5, 53_506),
    7: (3, 64_617),
    8: (1668, 2_686_596),
    9: (4, 47_565),
    14: (42, 25_559),
    15: (65, 650_026),
}

#: Tabla del apéndice A.2: apariciones de cada tag (los 07 sin contar las raíces).
TAG_TABLE = {
    0x02: 196_222,
    0x03: 127_484,
    0x04: 34_997,
    0x05: 2_865,
    0x07: 146_328,
    0x09: 37_046,
    0x0A: 39,
    0x0B: 1_716,
    0x0F: 151_488,
    0xFC: 3_406,
    0xFE: 220,
}


@requires_real_file
class GoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = real_bytes()
        cls.obsp = ObspFile.parse(cls.data)

    def test_original_fingerprint(self) -> None:
        self.assertEqual(len(self.data), ORIGINAL_SIZE)
        self.assertEqual(self.obsp.sha256(), ORIGINAL_SHA256)

    def test_container_header(self) -> None:
        header = self.obsp.header
        self.assertEqual(
            (header.version, header.unknown, header.object_count, header.strings_end,
             header.string_count, header.max_string_length),
            (10, 1, 7862, 0x9C0E6, 15520, 74),
        )
        self.assertEqual(self.obsp.index_end, 0xFDF28)
        self.assertEqual(self.obsp.layout_problems(), [])

    def test_kind_table(self) -> None:
        counts = Counter(entry.kind for entry in self.obsp.entries)
        sizes = Counter()
        for entry in self.obsp.entries:
            sizes[entry.kind] += entry.size
        self.assertEqual({kind: (counts[kind], sizes[kind]) for kind in counts}, KIND_TABLE)

    def test_string_table_first_appearance(self) -> None:
        self.assertEqual(list(self.obsp.strings), string_table_order(self.obsp.entries))
        self.assertEqual(self.obsp.strings[0], "")

    def test_rebuild_gives_original_sha(self) -> None:
        rebuilt = rebuild(self.obsp)
        self.assertEqual(hashlib.sha256(rebuilt).hexdigest().upper(), ORIGINAL_SHA256)

    def test_every_bod_roundtrips(self) -> None:
        tags: Counter[int] = Counter()
        identical = 0
        recoded = {}
        for position, entry in enumerate(self.obsp.entries):
            if entry.is_script:
                continue
            blob = self.obsp.blob(position)
            document = bod.decode(blob)
            encoded = bod.encode(document)
            recoded[position] = encoded
            identical += encoded == blob
            counters = bod.HEADER.unpack_from(encoded)[3:]
            self.assertEqual(counters, (document.declared_name_count, document.declared_max_name_length))
            for _path, node in bod.walk(document.root):
                if isinstance(node, bod.Value):
                    tags[node.tag] += 1
        self.assertEqual(identical, 4172)
        tags[bod.TAG_OBJECT] -= 4172  # las raíces no llevan tag 07
        self.assertEqual(dict(tags), TAG_TABLE)
        # Guardar con todos los BOD «modificados» sigue dando el original.
        self.assertEqual(hashlib.sha256(rebuild(self.obsp, recoded)).hexdigest().upper(), ORIGINAL_SHA256)

    def test_script_headers_are_coherent(self) -> None:
        coherent = 0
        for position, entry in enumerate(self.obsp.entries):
            if not entry.is_script:
                continue
            header = script.parse_header(self.obsp.blob(position))
            self.assertEqual(script.header_problems(header, entry), [])
            coherent += 1
        self.assertEqual(coherent, 3690)

    def test_hash_dictionary(self) -> None:
        dictionary = HashDictionary()
        dictionary.update(self.obsp.strings.items())
        for position, entry in enumerate(self.obsp.entries):
            blob = self.obsp.blob(position)
            if entry.is_script:
                for symbol in script.parse_header(blob).symbols:
                    dictionary.add(symbol.hash, symbol.text)
            else:
                for name in document_names(bod.decode(blob)):
                    dictionary.add(name.hash, name.text)
        self.assertEqual(len(dictionary), 70_182)
        self.assertEqual(dictionary.conflicts, [])
        self.assertEqual(dictionary.reverse_conflicts(), [])
        self.assertTrue(all(text.isascii() for _hash, text in dictionary.pairs()))

    def test_verify_report(self) -> None:
        report = verify_data(self.data)
        self.assertTrue(report.ok, [check for check in report.checks if not check.ok])
        self.assertTrue(report.is_steam_original)


if __name__ == "__main__":
    unittest.main()
