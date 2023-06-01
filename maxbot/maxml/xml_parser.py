"""Parsing XML documents containing commands."""
import logging
from dataclasses import dataclass
from xml.sax.handler import ContentHandler, ErrorHandler  # nosec

from defusedxml.sax import parseString

from ..errors import BotError, XmlSnippet
from . import fields, markup

logger = logging.getLogger(__name__)


_ROOT_ELEM_NAME = "root"
KNOWN_ROOT_ELEMENTS = frozenset(
    list(markup.PlainTextRenderer.KNOWN_START_TAGS.keys())
    + list(markup.PlainTextRenderer.KNOWN_END_TAGS.keys())
)


@dataclass(frozen=True)
class Pointer:
    """Pointer to specific line and column in XML document."""

    # Line number (zero-based)
    lineno: int

    # Number of column (zero-based)
    column: int


class _ContentHandler(ContentHandler):
    def __init__(self, schema, register_symbol):
        super().__init__()
        self.schema = schema
        self.register_symbol = register_symbol
        self.maxbot_commands = []
        self.nested = None
        self.startElement = self._create_hanler(self._on_start_element)
        self.endElement = self._create_hanler(self._on_end_element)
        self.characters = self._create_hanler(self._on_characters)

    def _on_start_element(self, name, attrs):
        if not self.nested:
            assert self.nested is None
            assert name == _ROOT_ELEM_NAME
            self.nested = [_RootElement(name, self.register_symbol_factory, attrs, self.schema)]
        else:
            nested = self.nested[-1].on_starttag(name, attrs)
            if nested:
                self.nested.append(nested)

    def _on_end_element(self, name):
        value = self.nested[-1].on_endtag(name)
        if value is not None:
            processed = self.nested.pop()
            if self.nested:
                self.nested[-1].on_nested_processed(processed.tag, value)
            else:
                assert isinstance(value, list)
                self.maxbot_commands += value

    def _on_characters(self, content):
        self.nested[-1].on_data(content)

    def _create_hanler(self, handler):
        def _impl(*args, **kwargs):
            try:
                return handler(*args, **kwargs)
            except _Error as exc:
                if exc.ptr is None:
                    # skip exception without pointer
                    raise _Error(exc.message, self._get_ptr()) from exc.__cause__
                raise

        return _impl

    def _get_ptr(self):
        if self._locator is None:
            return None
        lineno = self._locator.getLineNumber() - 1
        assert lineno >= 0
        return Pointer(lineno, self._locator.getColumnNumber())

    def register_symbol_factory(self):
        captured_ptr = self._get_ptr()

        def _register_symbol(value):
            if captured_ptr:
                self.register_symbol(value, captured_ptr)

        return _register_symbol


class _ErrorHandler(ErrorHandler):
    def error(self, exception):
        return self.fatalError(exception)

    def fatalError(self, exception):  # noqa: N802 (function name should be lowercase)
        get_lineno = getattr(exception, "getLineNumber", None)
        get_column = getattr(exception, "getColumnNumber", None)
        ptr = Pointer(get_lineno() - 1, get_column()) if get_lineno and get_column else None
        raise _Error(f"{exception.__class__.__name__}: {exception.getMessage()}", ptr)

    def warning(self, exception):
        logger.warning("XML warning: %s", exception)


class XmlParser:
    """Parse MaxBot commands from XML document."""

    CONTENT_HANDLER_CLASS = _ContentHandler
    ERROR_HANDLER_CLASS = _ErrorHandler

    PARSE_STRING_OPTIONS = {"forbid_dtd": True}

    def loads(self, document, *, maxml_command_schema=None, maxml_symbols=None, **kwargs):
        """Load MaxBot command list from headless XML document.

        :param str document: Headless XML document.
        :param type maxml_command_schema: A schema of commands.
        :param dict maxml_symbols: Map id of values to `Pointer`s
        :param dict kwargs: Ignored.
        """
        for command_name, command_schema in maxml_command_schema.declared_fields.items():
            if command_schema.metadata.get("maxml", "element") != "element":
                raise BotError(f"Command {command_name!r} is not described as an element")

        # +1 lineno
        encoded = f"<{_ROOT_ELEM_NAME}>\n{document}</{_ROOT_ELEM_NAME}>".encode("utf-8")

        def _register_symbol(value, ptr):
            assert ptr.lineno >= 1
            if maxml_symbols is not None:
                maxml_symbols[id(value)] = Pointer(ptr.lineno - 1, ptr.column)

        content_handler = self.CONTENT_HANDLER_CLASS(maxml_command_schema, _register_symbol)
        try:
            parseString(
                encoded,
                content_handler,
                errorHandler=self.ERROR_HANDLER_CLASS(),
                **self.PARSE_STRING_OPTIONS,
            )
        except _Error as exc:
            snippet = None
            if exc.ptr:
                # correct lineno
                assert exc.ptr.lineno >= 1
                snippet = XmlSnippet(document.splitlines(), exc.ptr.lineno - 1, exc.ptr.column)
            # skip _Error
            raise BotError(exc.message, snippet) from exc.__cause__

        return content_handler.maxbot_commands


class _Error(Exception):
    def __init__(self, message, ptr=None):
        self.message = message
        self.ptr = ptr


class _ElementBase:
    def __init__(self, tag, register_symbol_factory):
        self.tag = tag
        self.register_symbol_factory = register_symbol_factory
        self.register_symbol = self.register_symbol_factory()

    def attrs_to_dict(self, attrs, schema):
        value = {}
        for field_name, field_value in attrs.items():
            field_schema = _get_object_field_schema(schema, field_name, "Attribute")
            if field_schema.metadata.get("maxml", "attribute") != "attribute":
                _raise_not_described("Attribute", field_name)
            self.register_symbol_factory()(field_value)
            value[field_name] = field_value
        return value

    def check_no_attr(self, attrs, tag=None):
        if attrs:
            _raise_not_described("Attribute", attrs.keys()[0])


class _ScalarElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs):
        super().__init__(tag, register_symbol_factory)
        self.check_no_attr(attrs)
        self.value = ""

    def on_starttag(self, tag, attrs):
        _raise_not_described("Element", tag)

    def on_endtag(self, tag):
        assert tag == self.tag
        self.register_symbol(self.value)
        return self.value

    def on_data(self, data):
        assert isinstance(data, str)
        self.value += data


class _MarkupElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs):
        super().__init__(tag, register_symbol_factory)
        self.check_no_attr(attrs)
        self.tag_level = 1
        self.items = []

    def on_starttag(self, tag, attrs):
        assert self.tag_level >= 1
        self.tag_level += 1
        self.items.append(markup.Item(markup.START_TAG, tag, dict(attrs) if attrs else None))

    def on_endtag(self, tag):
        assert self.tag_level >= 1
        self.tag_level -= 1
        if self.tag_level > 0:
            self.items.append(markup.Item(markup.END_TAG, tag))
            return None

        assert self.tag == tag
        value = markup.Value(self.items)
        self.register_symbol(value)
        return value

    def on_data(self, data):
        assert isinstance(data, str)
        if self.items and self.items[-1].kind == markup.TEXT:
            self.items[-1] = markup.Item(markup.TEXT, self.items[-1].value + data)
        else:
            self.items.append(markup.Item(markup.TEXT, data))


class _DictElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs, schema):
        super().__init__(tag, register_symbol_factory)
        self.schema = schema
        self.value = self.attrs_to_dict(attrs, schema)

    def on_starttag(self, tag, attrs):
        if tag in self.value and not isinstance(self.value[tag], list):
            raise _Error(f"Element {tag!r} is duplicated")

        field_schema = _get_object_field_schema(self.schema, tag, "Element")

        if get_metadata_maxml(field_schema) != "element":
            _raise_not_described("Element", tag)

        return _factory(tag, self.register_symbol_factory, attrs, field_schema, self.value)

    def on_endtag(self, tag):
        assert tag == self.tag
        self.register_symbol(self.value)
        return self.value

    def on_data(self, data):
        if _normalize_spaces(data):
            raise _Error(f"Element {self.tag!r} has undescribed text")

    def on_nested_processed(self, tag, value):
        self.value[tag] = value


class _ListElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs, item_schema, parent):
        if not isinstance(parent, dict):
            raise _Error(f"The list ({tag!r}) should be a dictionary field")

        super().__init__(tag, register_symbol_factory)
        self.parent = parent
        self.item = _factory(tag, register_symbol_factory, attrs, item_schema)

    def on_starttag(self, tag, attrs):
        return self.item.on_starttag(tag, attrs)

    def on_endtag(self, tag):
        value = self.item.on_endtag(tag)
        if value is None:
            return None

        container = self.parent.get(self.tag)
        if container is None:
            container = []
            self.register_symbol(container)
        container.append(value)
        return container

    def on_data(self, data):
        return self.item.on_data(data)

    def on_nested_processed(self, tag, value):
        return self.item.on_nested_processed(tag, value)


class _ContentElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs, schema, field_name, field_schema):
        child_elements = [
            f for f in schema().declared_fields.items() if f[1].metadata.get("maxml") == "element"
        ]
        if child_elements:
            child_names = ", ".join(repr(i[0]) for i in child_elements)
            raise _Error(
                f"An {tag!r} element with a {field_name!r} content field cannot contain child elements: {child_names}"
            )
        if not is_known_scalar(field_schema) and not isinstance(field_schema, markup.Field):
            raise _Error(f"Field {field_name!r} must be a scalar")

        super().__init__(tag, register_symbol_factory)
        self.field_name = field_name
        self.field = _factory(tag, register_symbol_factory, attrs={}, schema=field_schema)
        self.value = self.attrs_to_dict(attrs, schema)

    def on_starttag(self, tag, attrs):
        return self.field.on_starttag(tag, attrs)

    def on_endtag(self, tag):
        value = self.field.on_endtag(tag)
        if value is None:
            return None

        self.value[self.field_name] = value
        self.register_symbol(self.value)
        return self.value

    def on_data(self, data):
        return self.field.on_data(data)


class _RootElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs, schema):
        super().__init__(tag, register_symbol_factory)
        self.check_no_attr(attrs)
        self.schema = schema
        self.commands = []
        self._text_harverter = None
        self._text_harverter_level = 1

    def on_starttag(self, name, attrs):
        command_schema = self.schema.declared_fields.get(name)
        if command_schema:
            self._end_of_text_harverter()
            return _factory(name, self.register_symbol_factory, attrs, command_schema)

        if name not in KNOWN_ROOT_ELEMENTS:
            _raise_not_described("Command", name)

        self._text_harverter_level += 1
        return self.text_harverter.on_starttag(name, attrs)

    def on_endtag(self, name):
        self._text_harverter_level -= 1
        if self._text_harverter_level:
            value = self.text_harverter.on_endtag(name)
            assert value is None
            return None

        assert name == self.tag
        self._end_of_text_harverter()
        return self.commands

    def on_data(self, data):
        if data.strip() or self._text_harverter:
            self.text_harverter.on_data(data)

    def on_nested_processed(self, tag, value):
        self.commands.append({tag: value})

    @property
    def text_harverter(self):
        if self._text_harverter is None:
            self._text_harverter = _MarkupElement(self.tag, self.register_symbol_factory, attrs={})
        return self._text_harverter

    def _end_of_text_harverter(self):
        if self._text_harverter:
            value = self._text_harverter.on_endtag(self._text_harverter.tag)
            assert value is not None
            if value:
                self.commands.append({"text": value})
            self._text_harverter = None


def _factory(tag, register_symbol_factory, attrs, schema, parent=None):
    if isinstance(schema, markup.Field):
        return _MarkupElement(tag, register_symbol_factory, attrs)
    if is_known_scalar(schema):
        return _ScalarElement(tag, register_symbol_factory, attrs)
    if isinstance(schema, fields.Nested):
        if schema.many:
            return _ListElement(
                tag,
                register_symbol_factory,
                attrs,
                fields.Nested(schema.nested),
                parent,
            )
        content_fields = [
            f
            for f in schema.nested().declared_fields.items()
            if f[1].metadata.get("maxml") == "content"
        ]
        if len(content_fields) > 1:
            field_names = ", ".join(repr(i[0]) for i in content_fields)
            raise _Error(f"There can be no more than one field marked `content`: {field_names}")
        if len(content_fields) == 1:
            return _ContentElement(
                tag, register_symbol_factory, attrs, schema.nested, *content_fields[0]
            )
        return _DictElement(tag, register_symbol_factory, attrs, schema.nested)
    if isinstance(schema, fields.List):
        return _ListElement(tag, register_symbol_factory, attrs, schema.inner, parent)
    raise _Error(f"Unexpected schema ({type(schema)}) for element {tag!r}")


def _raise_not_described(entity, name):
    raise _Error(f"{entity} {name!r} is not described in the schema")


def _get_object_field_schema(schema, field_name, entity):
    field_schema = schema().declared_fields.get(field_name)
    if field_schema is None:
        _raise_not_described(entity, field_name)
    return field_schema


def _normalize_spaces(s):
    return " ".join(s.split()) if s else ""


def is_known_scalar(schema):
    """Check for known scalar field (or inherited)."""
    if isinstance(schema, fields.String):
        return True
    if isinstance(schema, fields.Number):
        return True
    if isinstance(schema, fields.Boolean):
        return True
    if isinstance(schema, fields.DateTime):
        return True
    if isinstance(schema, fields.TimeDelta):
        return True
    return False


def get_metadata_maxml(schema):
    """Get "maxml" value of metadata."""
    return schema.metadata.get("maxml", "attribute" if is_known_scalar(schema) else "element")
