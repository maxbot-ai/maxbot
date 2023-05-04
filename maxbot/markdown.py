"""Parse markdown document to commands."""
import re

from markdown_it import MarkdownIt
from markdown_it.common.html_re import close_tag, open_tag
from markdown_it.presets import zero
from markupsafe import Markup as _Markup

from .xml import XmlError, XmlParser

_SPECIAL_SYMBOLS = "\\!\"#$%&'()*+,./:;<=>?@[]^_`{|}~-"


class MarkdownError(Exception):
    """Markdown parsing error."""

    def __init__(self, message, lineno):
        """Create new class instance.

        :param str message: Error message.
        :param int lineno: Zero-based line number.
        """
        super().__init__()
        self.message = message
        self.lineno = lineno


class Markup(_Markup):
    """A string that is ready to be safely inserted into Markdown document."""

    def __markdown__(self):
        """Return ecaped string."""
        return self


def escape(o):
    """Escape string for markdown document."""
    if hasattr(o, "__markdown__"):
        return Markup(o.__markdown__())

    escaped = "".join([(f"&#{ord(i)};" if i in _SPECIAL_SYMBOLS else i) for i in str(o)])
    return Markup("".join(escaped))


class MarkdownRender:
    """Markdown parser class."""

    # underscore symbol in tag names
    OPEN_TAG = open_tag.replace("[A-Za-z0-9\\-]*", "[A-Za-z0-9\\-_]*")
    CLOSE_TAG = close_tag.replace("[A-Za-z0-9\\-]*", "[A-Za-z0-9\\-_]*")

    INLINE_RULE_NAME = "maxml_inline"

    EXCEPTION_CLASS = MarkdownError

    MARKDOWN_CLASS = MarkdownIt
    XML_PARSER_CLASS = XmlParser

    def __init__(self, maxml_command_schema=None):
        """Create new instance of Markdown parser."""
        self.tag_re = re.compile("^(?:" + self.OPEN_TAG + "|" + self.CLOSE_TAG + ")")
        self.parser = self.MARKDOWN_CLASS(config=self.create_markdown_it_config())
        self.add_maxml_inline_rule()
        self.xml = self.XML_PARSER_CLASS()

    @staticmethod
    def create_markdown_it_config():
        """Create and return Markdown-it configuration."""
        config = zero.make()
        config["options"].update(html=True, xhtmlOut=True)
        config["components"]["inline"]["rules"].append("entity")
        config["components"]["inline"]["rules"].append("escape")
        config["components"]["inline"]["rules"].append("image")
        return config

    def add_maxml_inline_rule(self):
        """Add MAXML commands inline rule."""
        self.parser.inline.ruler.before("newline", self.INLINE_RULE_NAME, self.maxml_inline)
        self.parser.renderer.rules[self.INLINE_RULE_NAME] = self.parser.renderer.rules[
            "html_inline"
        ]

    def loads(self, document, *, maxml_command_schema=None, maxml_symbols=None, **kwargs):
        """Load maxml command from Markdown document."""
        if maxml_command_schema is None:
            raise AssertionError("Scheme of commands is not set")

        result_commands = []

        tokens = self.parser.parse(document)
        assert len(tokens) % 3 == 0
        for i in range(0, len(tokens), 3):
            assert tokens[i].type == "paragraph_open"
            assert tokens[i + 1].type == "inline"
            assert tokens[i + 2].type == "paragraph_close"
            paragraph_lineno = tokens[i].map[0]
            xhtml_document = self.parser.renderer.render(
                tokens[i : i + 3], self.parser.options, env={}  # noqa: E203
            )
            try:
                result_commands += self.xml.parse_paragraph(
                    xhtml_document,
                    maxml_command_schema,
                    self._register_symbol_factory(maxml_symbols, paragraph_lineno),
                )
            except XmlError as exc:
                raise self.EXCEPTION_CLASS(exc.message, paragraph_lineno + exc.lineno) from exc
        return result_commands

    # like a markdown_it/rules_inline/html_inline.py
    def maxml_inline(self, state, silent):
        """MAXML commands inline extractor."""
        pos = state.pos
        match = self.tag_re.search(state.src[pos:])
        if not match:
            return False

        if not silent:
            token = state.push(self.INLINE_RULE_NAME, "", 0)
            token.content = state.src[pos : pos + len(match.group(0))]  # noqa: E203

        state.pos += len(match.group(0))
        return True

    @staticmethod
    def _register_symbol_factory(maxml_symbols, paragraph_lineno):
        def _register_symbol(value, linenno):
            if maxml_symbols is not None:
                maxml_symbols[id(value)] = paragraph_lineno + linenno

        return _register_symbol
