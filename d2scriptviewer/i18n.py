# SPDX-FileCopyrightText: 2026 BOTProT800
# SPDX-License-Identifier: MIT

"""Idioma de la interfaz (fase 12): ``_()``, ``ngettext()`` y ``pgettext()`` al estilo de gettext.

La clave de cada texto es el español que ya está en el código, y el catálogo inglés vive
en :mod:`.i18n_en`, un módulo de Python: no hay archivos de datos, así que el ejecutable
no cambia. Si a un texto le faltara la traducción, se vería en español (los tests lo
impiden).

Qué se traduce y qué no:

- Los mensajes (errores, avisos, resúmenes, la interfaz) se componen en el idioma activo
  al crearlos.
- El vocabulario canónico de la herramienta (las etiquetas de las rutas, los tipos, los
  mnemónicos, las filas de los scripts) sigue en español dentro del núcleo, porque forma
  parte de lo que se guarda, se exporta o se escribe en un parche, y de las huellas que
  los comparan. La interfaz lo traduce al mostrarlo (:mod:`.vocabulary`). Para eso hay
  textos que son un ``str`` canónico y además saben mostrarse en el idioma activo
  (:class:`Deferred`, :func:`shown`).

La CLI no llama nunca a :func:`set_language`: sigue en español y con la coma de miles de
Python, la salida de siempre. La interfaz fija el idioma al arrancar, y el español de la
interfaz separa los miles con un espacio duro («7 862»).
"""

from __future__ import annotations

import os
import string

SPANISH = "es"
ENGLISH = "en"
#: Los idiomas de la interfaz, con su nombre en su propio idioma (el menú los muestra así).
LANGUAGES = {ENGLISH: "English", SPANISH: "Español"}
#: El idioma de la interfaz mientras no se elija otro en el menú.
DEFAULT_LANGUAGE = ENGLISH
#: Variable de entorno que fija el idioma de la interfaz sin guardarlo (tests y revisión).
LANGUAGE_ENV = "D2SV_LANG"
#: El menú de idioma se entiende en los dos idiomas: no se traduce.
MENU_LABEL = "Idioma / Language"

#: Separador de miles de ``{n:,}`` en cada idioma de la interfaz.
_GROUPING = {SPANISH: " ", ENGLISH: ","}

_language = SPANISH
_grouping = ","
_messages: dict[object, str] = {}
_plurals: dict[tuple[str, str], tuple[str, str]] = {}


def _catalog(code: str) -> tuple[dict[object, str], dict[tuple[str, str], tuple[str, str]]]:
    if code == ENGLISH:
        from . import i18n_en

        return i18n_en.MESSAGES, i18n_en.PLURALS
    return {}, {}


def set_language(code: str) -> None:
    """Activa el idioma ``code`` (``es`` o ``en``) para todo el proceso."""
    global _language, _grouping, _messages, _plurals
    if code not in LANGUAGES:
        raise ValueError(f"Idioma desconocido: {code!r}")
    _messages, _plurals = _catalog(code)
    _language = code
    _grouping = _GROUPING[code]


def reset() -> None:
    """Vuelve al estado de la CLI: español, con la coma de miles de Python."""
    global _language, _grouping, _messages, _plurals
    _language, _grouping, _messages, _plurals = SPANISH, ",", {}, {}


def language() -> str:
    return _language


# --- Plantillas ------------------------------------------------------------------------------


class _Formatter(string.Formatter):
    """``str.format`` con el separador de miles del idioma en ``{n:,}``."""

    def __init__(self, grouping: str) -> None:
        super().__init__()
        self.grouping = grouping

    def format_field(self, value: object, format_spec: str) -> str:
        text = format(value, format_spec)
        if "," in format_spec and isinstance(value, int) and self.grouping != ",":
            text = text.replace(",", self.grouping)
        return text


class Template(str):
    """Un texto traducido; :meth:`format` usa el separador de miles del idioma activo."""

    __slots__ = ()

    def format(self, *args: object, **kwargs: object) -> str:  # type: ignore[override]
        if _grouping == "," or ":," not in self:
            return str.format(self, *args, **kwargs)
        return _Formatter(_grouping).vformat(self, args, kwargs)


def _(message: str) -> Template:
    """El texto ``message`` (en español) en el idioma activo."""
    return Template(_messages.get(message, message))


def pgettext(context: str, message: str) -> Template:
    """Como :func:`_`, para un texto corto que cambia de sentido según ``context`` («nombre» como tipo)."""
    return Template(_messages.get((context, message), message))


def ngettext(singular: str, plural: str, count: int) -> Template:
    """La forma de ``count``: ``singular`` con 1 y ``plural`` con cualquier otro número (en los dos idiomas)."""
    forms = _plurals.get((singular, plural))
    if forms is not None:
        singular, plural = forms
    return Template(singular if count == 1 else plural)


def N_(message: str, context: str | None = None) -> str:
    """Marca un texto que se traduce más tarde (tablas de módulo); devuelve ``message`` tal cual."""
    return message


def term(message: str, context: str | None = None) -> Template:
    """Un término del vocabulario canónico declarado con :func:`N_` (y su ``context``), en el idioma activo.

    Es la única búsqueda con un texto variable: el resto de llamadas llevan el texto escrito.
    """
    return _(message) if context is None else pgettext(context, message)


def canonical(shown_text: str, context: str | None = None) -> str:
    """La inversa de :func:`term` en el idioma activo: el texto canónico que se ve como ``shown_text``."""
    for key, value in _messages.items():
        if value == shown_text and (key[0] == context if isinstance(key, tuple) else context is None):
            return key[1] if isinstance(key, tuple) else key  # type: ignore[return-value]
    return shown_text


def variants(message: str, context: str | None = None) -> tuple[str, ...]:
    """``message`` y su traducción en cada idioma (Ctrl+G acepta las dos formas)."""
    key: object = message if context is None else (context, message)
    found = [message]
    for code in LANGUAGES:
        translated = _catalog(code)[0].get(key)
        if translated is not None and translated not in found:
            found.append(translated)
    return tuple(found)


# --- Textos canónicos que se muestran traducidos ---------------------------------------------


class Deferred(str):
    """Un texto canónico (en español) que además sabe mostrarse en el idioma activo.

    Es un ``str`` con el texto español de siempre: lo que lo compara, lo serializa o lo
    guarda (las huellas, la CLI, los tests) ve lo mismo que antes. :func:`shown` lo vuelve a
    componer en el idioma activo; un valor que también sepa mostrarse se muestra a su vez.
    Así una descripción de deshacer creada en español se lee en inglés tras cambiar de idioma.
    """

    def __new__(cls, message: str, /, *, plural: str | None = None, count: int | None = None,
                context: str | None = None, **values: object) -> "Deferred":
        if count is not None:
            values.setdefault("count", count)
        template = message if plural is None or count == 1 else plural
        self = super().__new__(cls, template.format(**values))
        self._parts = (message, plural, count, context, values)
        return self

    def shown(self) -> str:
        message, plural, count, context, values = self._parts
        if plural is not None:
            template = ngettext(message, plural, count if count is not None else 0)
        elif context is not None:
            template = pgettext(context, message)
        else:
            template = _(message)
        return template.format(**{name: shown(value) for name, value in values.items()})


def shown(value: object) -> object:
    """``value`` en el idioma activo si sabe mostrarse (:class:`Deferred`, rutas); si no, tal cual."""
    method = getattr(value, "shown", None)
    return method() if callable(method) else value


def text(value: object) -> str:
    """Como :func:`shown`, siempre como ``str``."""
    return str(shown(value))


# --- Idioma inicial -------------------------------------------------------------------------


def initial_language(saved: object) -> str:
    """El idioma con que arranca la interfaz: ``D2SV_LANG``, luego el elegido en el menú y si no, inglés.

    No se sigue el idioma de Windows: por decisión del usuario, la interfaz arranca en inglés
    mientras no se elija otro idioma.
    """
    forced = os.environ.get(LANGUAGE_ENV, "").strip().lower()
    if forced in LANGUAGES:
        return forced
    if isinstance(saved, str) and saved in LANGUAGES:
        return saved
    return DEFAULT_LANGUAGE
