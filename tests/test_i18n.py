# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Idioma de la interfaz (fase 12): catálogo, plantillas, idioma inicial, vocabulario y rutas."""

from __future__ import annotations

import ast
import json
import os
import re
import string
import sys
import unittest
from pathlib import Path
from unittest import mock

import d2scriptviewer
from d2scriptviewer import i18n, i18n_en, settings, vocabulary
from d2scriptviewer.document import Document
from d2scriptviewer.formats import bod, script
from tests import fixtures
from tests.support import TempDirMixin

PACKAGE = Path(d2scriptviewer.__file__).parent
#: Lo que no puede salir en una traducción inglesa.
SPANISH_MARKS = re.compile(r"[áéíóúÁÉÍÓÚñÑüÜ¿¡«»]")
#: Módulos que definen las funciones de traducción y las llaman con textos variables.
DYNAMIC = {"i18n.py", "i18n_en.py"}


def _function_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "i18n":
        return func.attr
    return None


def _literal(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _keyword(call: ast.Call, name: str) -> ast.AST | None:
    return next((keyword.value for keyword in call.keywords if keyword.arg == name), None)


def collect_messages() -> tuple[dict[object, str], dict[tuple[str, str], str], list[str]]:
    """(textos, plurales, problemas) de todas las llamadas de traducción del paquete."""
    messages: dict[object, str] = {}
    plurals: dict[tuple[str, str], str] = {}
    problems: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if path.name in DYNAMIC:
            continue
        where = path.relative_to(PACKAGE).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "_" and isinstance(node.ctx, ast.Store):
                problems.append(f"{where}:{node.lineno}: se asigna a «_», que es la función de traducción")
            if not isinstance(node, ast.Call):
                continue
            name = _function_name(node)
            place = f"{where}:{node.lineno}"
            if name == "_":
                text = _literal(node.args[0]) if len(node.args) == 1 and not node.keywords else None
                if text is None:
                    problems.append(f"{place}: _() sin un texto literal")
                else:
                    messages.setdefault(text, place)
            elif name == "N_":
                text = _literal(node.args[0]) if node.args else None
                context_node = node.args[1] if len(node.args) > 1 else _keyword(node, "context")
                context = _literal(context_node)
                if text is None or (context_node is not None and context is None):
                    problems.append(f"{place}: N_() sin textos literales")
                else:
                    messages.setdefault(text if context is None else (context, text), place)
            elif name == "pgettext":
                context, text = (_literal(arg) for arg in node.args) if len(node.args) == 2 else (None, None)
                if context is None or text is None:
                    problems.append(f"{place}: pgettext() sin textos literales")
                else:
                    messages.setdefault((context, text), place)
            elif name == "ngettext":
                singular, plural = (_literal(arg) for arg in node.args[:2]) if len(node.args) == 3 else (None, None)
                if singular is None or plural is None:
                    problems.append(f"{place}: ngettext() sin textos literales")
                else:
                    plurals.setdefault((singular, plural), place)
            elif name == "Deferred":
                text = _literal(node.args[0]) if node.args else None
                plural_node, context_node = _keyword(node, "plural"), _keyword(node, "context")
                plural, context = _literal(plural_node), _literal(context_node)
                if text is None or (plural_node is not None and plural is None) or (
                        context_node is not None and context is None):
                    problems.append(f"{place}: Deferred() sin textos literales")
                elif plural is not None:
                    plurals.setdefault((text, plural), place)
                else:
                    messages.setdefault(text if context is None else (context, text), place)
    return messages, plurals, problems


def fields(text: str) -> list[tuple[str, str, str | None]]:
    """Los marcadores de una plantilla: (nombre, formato, conversión)."""
    return sorted((name, spec or "", conversion) for _literal_text, name, spec, conversion
                  in string.Formatter().parse(text) if name is not None)


class CatalogTests(unittest.TestCase):
    """Cada texto marcado tiene su traducción inglesa, con los mismos marcadores, y no sobra ninguna."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.messages, cls.plurals, cls.problems = collect_messages()

    def test_calls_use_literal_texts(self) -> None:
        self.assertEqual(self.problems, [])

    def test_every_message_is_translated(self) -> None:
        missing = [f"{where}: {key!r}" for key, where in self.messages.items() if key not in i18n_en.MESSAGES]
        missing += [f"{where}: {key!r}" for key, where in self.plurals.items() if key not in i18n_en.PLURALS]
        self.assertEqual(missing, [])

    def test_no_unused_entries(self) -> None:
        self.assertEqual(sorted(map(repr, set(i18n_en.MESSAGES) - set(self.messages))), [])
        self.assertEqual(sorted(map(repr, set(i18n_en.PLURALS) - set(self.plurals))), [])

    def test_same_placeholders(self) -> None:
        for key, english in i18n_en.MESSAGES.items():
            spanish = key[1] if isinstance(key, tuple) else key
            with self.subTest(texto=spanish):
                self.assertEqual(fields(english), fields(spanish))
        for (singular, plural), (english_singular, english_plural) in i18n_en.PLURALS.items():
            with self.subTest(texto=plural):
                self.assertEqual(fields(english_singular), fields(singular))
                self.assertEqual(fields(english_plural), fields(plural))

    def test_english_has_no_spanish_marks(self) -> None:
        texts = list(i18n_en.MESSAGES.values()) + [form for forms in i18n_en.PLURALS.values() for form in forms]
        self.assertEqual([text for text in texts if SPANISH_MARKS.search(text)], [])


class TemplateTests(unittest.TestCase):
    def tearDown(self) -> None:
        i18n.reset()

    def test_cli_default_is_spanish_with_python_grouping(self) -> None:
        i18n.reset()
        self.assertEqual(i18n.language(), i18n.SPANISH)
        self.assertEqual(i18n._("Guardar"), "Guardar")
        self.assertEqual(i18n._("… y {count:,} más").format(count=7862), "… y 7,862 más")

    def test_interface_grouping(self) -> None:
        i18n.set_language(i18n.SPANISH)
        self.assertEqual(i18n._("… y {count:,} más").format(count=1145518), "… y 1 145 518 más")
        i18n.set_language(i18n.ENGLISH)
        self.assertEqual(i18n._("… y {count:,} más").format(count=1145518), "… and 1,145,518 more")
        self.assertEqual(i18n._("Guardar"), "Save")

    def test_plurals(self) -> None:
        for code, one, many in ((i18n.SPANISH, "1 elemento", "1 200 elementos"), (i18n.ENGLISH, "1 item", "1,200 items")):
            i18n.set_language(code)
            with self.subTest(idioma=code):
                self.assertEqual(vocabulary.value_text(bod.BodList(0, [bod.Int32.of(1)])), one)
                self.assertEqual(vocabulary.value_text(bod.BodList(0, [bod.Int32.of(1)] * 1200)), many)

    def test_deferred_is_canonical_and_shows_translated(self) -> None:
        i18n.set_language(i18n.ENGLISH)
        params = i18n.Deferred("{count:,} parámetro", plural="{count:,} parámetros", count=2)
        label = i18n.Deferred("función · {params} · {size:,} bytes", params=params, size=1234)
        self.assertEqual(label, "función · 2 parámetros · 1,234 bytes")
        self.assertEqual(i18n.shown(label), "function · 2 parameters · 1,234 bytes")
        i18n.set_language(i18n.SPANISH)
        self.assertEqual(i18n.shown(label), "función · 2 parámetros · 1 234 bytes")
        self.assertEqual(i18n.shown("texto normal"), "texto normal")

    def test_variants_and_inverse(self) -> None:
        self.assertEqual(i18n.variants("Funciones", "ruta"), ("Funciones", "Functions"))
        i18n.set_language(i18n.ENGLISH)
        self.assertEqual(i18n.canonical("string", "tipo"), "cadena")
        self.assertEqual(vocabulary.canonical_type("(any)"), "(cualquiera)")
        self.assertEqual(vocabulary.shown_type("cadena"), "string")
        self.assertEqual(vocabulary.shown_type("op_3A"), "op_3A")


class InitialLanguageTests(unittest.TestCase):
    def test_order(self) -> None:
        with mock.patch.dict(os.environ, {i18n.LANGUAGE_ENV: ""}), \
                mock.patch.object(i18n, "system_language", return_value=i18n.ENGLISH):
            self.assertEqual(i18n.initial_language(None), i18n.ENGLISH)
            self.assertEqual(i18n.initial_language("es"), i18n.SPANISH)
            self.assertEqual(i18n.initial_language("fr"), i18n.ENGLISH)  # un valor no válido se ignora
            self.assertEqual(i18n.initial_language(3), i18n.ENGLISH)
        with mock.patch.dict(os.environ, {i18n.LANGUAGE_ENV: " EN "}):
            self.assertEqual(i18n.initial_language("es"), i18n.ENGLISH)

    @unittest.skipUnless(sys.platform == "win32", "idioma de la pantalla de Windows")
    def test_windows_display_language(self) -> None:
        import ctypes

        for langid, expected in ((0x0C0A, i18n.SPANISH), (0x080A, i18n.SPANISH), (0x0409, i18n.ENGLISH),
                                 (0x040C, i18n.ENGLISH)):
            with self.subTest(langid=hex(langid)), \
                    mock.patch.object(ctypes.windll.kernel32, "GetUserDefaultUILanguage", return_value=langid):
                self.assertEqual(i18n.system_language(), expected)

    def test_locale_fallback(self) -> None:
        with mock.patch.object(i18n.sys, "platform", "linux"):
            for value, expected in (("es_MX.UTF-8", i18n.SPANISH), ("en_US.UTF-8", i18n.ENGLISH),
                                    ("Spanish_Spain", i18n.SPANISH), ("de_DE", i18n.ENGLISH)):
                with self.subTest(valor=value), mock.patch.dict(os.environ, {"LC_ALL": value}):
                    self.assertEqual(i18n.system_language(), expected)

    def test_language_is_a_known_setting(self) -> None:
        self.assertIn("language", settings.KNOWN_KEYS)


class SettingsPersistenceTests(TempDirMixin, unittest.TestCase):
    def test_language_round_trip(self) -> None:
        path = self.make_temp_dir() / "config.json"
        settings.save_settings({"language": "en", "otra": 1}, path)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"language": "en"})
        self.assertEqual(settings.load_settings(path), {"language": "en"})


class VocabularyTests(unittest.TestCase):
    """Las rutas canónicas no cambian; la interfaz las muestra traducidas y Ctrl+G acepta las dos."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.document = Document.from_bytes(fixtures.make_obsp())

    def tearDown(self) -> None:
        i18n.reset()

    def script_tree(self) -> script.ScriptTree:
        info = next(info for info in self.document.objects if info.is_script)
        tree = self.document.bod(info.position)
        assert isinstance(tree, script.ScriptTree)
        return tree

    def test_script_labels(self) -> None:
        tree = self.script_tree()
        functions = next(index for index, field in enumerate(tree.root.fields) if field.name.text == "Funciones")
        path = (functions, 0, 0)
        self.assertEqual(bod.path_label(tree, path), "Funciones." + tree.root.fields[functions].value.fields[0].name.text
                         + ".Parámetros")
        canonical = vocabulary.path_text(tree, path)
        self.assertEqual(canonical, bod.path_label(tree, path))
        i18n.set_language(i18n.ENGLISH)
        self.assertEqual(vocabulary.path_label(tree, path), canonical.replace("Funciones", "Functions")
                         .replace("Parámetros", "Parameters"))
        self.assertEqual(i18n.text(canonical), vocabulary.path_label(tree, path))
        self.assertEqual(vocabulary.path_label(tree, ()), "(root)")

    def test_round_trip_in_both_languages(self) -> None:
        """Cada fila de los fixtures: la ruta que se ve, en los dos idiomas, lleva a la misma fila."""
        for code in (i18n.SPANISH, i18n.ENGLISH):
            i18n.set_language(code)
            for info in self.document.objects:
                tree = self.document.bod(info.position)
                for path, _node in bod.walk(tree.root):
                    if not path:
                        continue
                    for text in (vocabulary.path_label(tree, path), bod.path_label(tree, path)):
                        with self.subTest(idioma=code, ruta=text):
                            steps = bod.parse_path_label(text)
                            self.assertEqual(bod.find_path(tree, steps, vocabulary.NAMES).path, path)

    def test_english_terms_and_messages(self) -> None:
        i18n.set_language(i18n.ENGLISH)
        tree = self.script_tree()
        for text in ("Functions", "functions", "FUNCIONES", "Funciones"):
            with self.subTest(texto=text):
                match = bod.find_path(tree, bod.parse_path_label(text), vocabulary.NAMES)
                self.assertTrue(match.complete, match.message)
        match = bod.find_path(tree, bod.parse_path_label("Functons"), vocabulary.NAMES)
        self.assertIn("«Functions»", match.message)  # el parecido se nombra como se ve
        # Sin el vocabulario de la interfaz, solo vale la etiqueta canónica.
        self.assertFalse(bod.find_path(tree, bod.parse_path_label("Functions")).complete)

    def test_pairs(self) -> None:
        pairs = bod.BodList(bod.MODE_PAIRS, [bod.Pair(bod.Int32.of(1), bod.Int32.of(2))])
        root = bod.BodObject(None, bod.ClassRef(bod.CLASS_NATIVE, None, bod.Name(0, "Test")),
                             [bod.Field(bod.Name(0, "Table"), pairs)])
        tree = bod.BodDocument(4, 1, root)
        i18n.set_language(i18n.ENGLISH)
        self.assertEqual(vocabulary.path_label(tree, (0, 0, 1)), "Table[0].value")
        self.assertEqual(bod.path_label(tree, (0, 0, 1)), "Table[0].valor")
        for text in ("Table[0].value", "Table[0].valor", "Table[0].VALUE"):
            with self.subTest(texto=text):
                self.assertEqual(bod.find_path(tree, bod.parse_path_label(text), vocabulary.NAMES).path, (0, 0, 1))
        self.assertEqual(bod.find_path(tree, bod.parse_path_label("(root)"), vocabulary.NAMES).path, ())

    def test_types_and_kinds(self) -> None:
        i18n.set_language(i18n.ENGLISH)
        self.assertEqual(vocabulary.type_text(bod.RawString("x")), "string")
        self.assertEqual(vocabulary.type_text(bod.Int32.of(1)), "int32")
        self.assertEqual(vocabulary.kind_label(1), "Instance")
        self.assertEqual(vocabulary.kind_label(8), "Desc")
        self.assertEqual(vocabulary.kind_label(12), "Type 12")
        # El vocabulario canónico no cambia con el idioma.
        self.assertEqual(bod.type_text(bod.RawString("x")), "cadena")
        self.assertEqual(bod.Note(i18n.Deferred("sin código"), "función").text, "sin código")

    def test_descriptions_follow_the_language(self) -> None:
        document = Document.from_bytes(fixtures.make_obsp())
        info = document.find("death/death_desc")[0]
        path = next(path for path, node in bod.walk(document.bod(info.position).root) if isinstance(node, bod.Int32))
        document.edit(info.position, path, bod.Int32.of(12345).raw)
        spanish = document.undo_description
        self.assertTrue(spanish.startswith("Editar death/death_desc · "))
        i18n.set_language(i18n.ENGLISH)
        self.assertEqual(document.undo_description, "Edit" + spanish.removeprefix("Editar"))


if __name__ == "__main__":
    unittest.main()
