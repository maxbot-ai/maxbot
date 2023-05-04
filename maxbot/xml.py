"""Parsing XML documents containing commands."""
import logging
from xml.sax.handler import ContentHandler, ErrorHandler  # nosec

from defusedxml.sax import parseString
from marshmallow import fields

logger = logging.getLogger(__name__)


class XmlError(Exception):
    """XML parsing error."""

    def __init__(self, message, lineno):
        """Create new class instance.

        :param str message: Error message.
        :param int lineno: Zero-based line number.
        """
        super().__init__()
        self.message = message
        self.lineno = lineno


class _ContentHandler(ContentHandler):
    def __init__(self, schema, register_symbol):
        super().__init__()
        self.__schema = schema
        self.__register_symbol = register_symbol
        self.maxbot_commands = []
        self.__nested = []

    def startElement(self, name, attrs):  # noqa: N802 (function name should be lowercase)
        if not self.__nested:
            if name != "p":
                raise _InternalError(f"Unexpected root element: {name!r}")
            self.__nested.append(
                _ParagraphElement(name, self.register_symbol_factory, attrs, self.__schema)
            )
        else:
            nested = self.__nested[-1].on_starttag(name, attrs)
            if nested:
                self.__nested.append(nested)

    def endElement(self, name):  # noqa: N802 (function name should be lowercase)
        value = self.__nested[-1].on_endtag(name)
        if value is not None:
            processed = self.__nested.pop()
            if self.__nested:
                self.__nested[-1].on_nested_processed(processed.tag, value)
            else:
                assert isinstance(value, list)
                self.maxbot_commands += value

    def characters(self, content):
        self.__nested[-1].on_data(content)

    def get_lineno(self):
        lineno = (1 if self._locator is None else self._locator.getLineNumber()) - 1
        assert lineno >= 0
        return lineno

    def register_symbol_factory(self):
        register_symbol_fn, lineno = self.__register_symbol, self.get_lineno()

        def _register_symbol(value):
            return register_symbol_fn(value, lineno)

        return _register_symbol


class _ErrorHandler(ErrorHandler):
    def error(self, exception):
        return self.fatalError(exception)

    def fatalError(self, exception):  # noqa: N802 (function name should be lowercase)
        lineno = getattr(exception, "getLineNumber", lambda: 1)() - 1
        assert lineno >= 0
        raise XmlError(f"{exception.__class__.__name__}: {exception.getMessage()}", lineno)

    def warning(self, exception):
        logger.warning("XML warning: %s", exception)


class XmlParser:
    """Parse MaxBot commands from XML document."""

    CONTENT_HANDLER_CLASS = _ContentHandler
    ERROR_HANDLER_CLASS = _ErrorHandler

    PARSE_STRING_OPTIONS = {"forbid_dtd": True}

    def parse_paragraph(self, content, schema, register_symbol):
        """Parse MaxBot commands from XML document.

        :param str content: XML document.
        :param type schema: A schema of commands.
        :param callable register_symbol: Register symbol as code snippet.
        :raise XmlError: XML parsing error.
        """
        encoded = content.encode("utf-8")
        content_handler = self.CONTENT_HANDLER_CLASS(schema, register_symbol)
        try:
            parseString(
                encoded,
                content_handler,
                errorHandler=self.ERROR_HANDLER_CLASS(),
                **self.PARSE_STRING_OPTIONS,
            )
        except _InternalError as exc:
            raise XmlError(exc.message, content_handler.get_lineno()) from exc
        return content_handler.maxbot_commands


class _InternalError(Exception):
    def __init__(self, message):
        self.message = message


class _UnexpectedScalarChild(_InternalError):
    pass


class _ElementBase:
    def __init__(self, tag, register_symbol_factory):
        self.tag = tag
        self.register_symbol_factory = register_symbol_factory
        self.register_symbol = self.register_symbol_factory()

    def attrs_to_dict(self, attrs, schema):
        value = {}
        for field_name, field_value in attrs.items():
            field_schema = _get_object_field_schema(schema, field_name, entity="Field")
            if field_schema.metadata.get("maxml", "attribute") != "attribute":
                raise _InternalError(f"Field {field_name!r} is not described as an attribute")
            self.register_symbol_factory()(field_value)
            value[field_name] = field_value
        return value

    def check_no_attr(self, attrs, tag=None):
        if attrs:
            element_name = self.tag if tag is None else tag
            raise _InternalError(
                f"Element {element_name!r} has undescribed attributes {dict(attrs)}"
            )


class _ScalarElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs):
        super().__init__(tag, register_symbol_factory)
        self.check_no_attr(attrs)
        self.value = [""]

    def on_starttag(self, tag, attrs):
        if tag == "br":
            self.check_no_attr(attrs, tag)
            self.value.append("")
        else:
            raise _UnexpectedScalarChild(
                f"Element {self.tag!r} has undescribed child element {tag!r}"
            )

    def on_endtag(self, tag):
        if tag == "br":
            return None

        assert tag == self.tag
        value = "\n".join([_normalize_spaces(s) for s in self.value])
        self.register_symbol(value)
        return value

    def on_data(self, data):
        self.value[-1] += f"{data}"


class _DictElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs, schema):
        super().__init__(tag, register_symbol_factory)
        self.schema = schema
        self.value = self.attrs_to_dict(attrs, schema)

    def on_starttag(self, tag, attrs):
        if tag in self.value and not isinstance(self.value[tag], list):
            raise _InternalError(f"Value {tag!r} already defined")

        field_schema = _get_object_field_schema(self.schema, tag)
        default_maxml = "attribute" if _is_known_scalar(field_schema) else "element"
        if field_schema.metadata.get("maxml", default_maxml) != "element":
            raise _InternalError(f"Field {tag!r} is not described as an element")

        return _factory(tag, self.register_symbol_factory, attrs, field_schema, self.value)

    def on_endtag(self, tag):
        assert tag == self.tag
        self.register_symbol(self.value)
        return self.value

    def on_data(self, data):
        if _normalize_spaces(data):
            raise _InternalError(f"Element {self.tag!r} has undescribed text")

    def on_nested_processed(self, tag, value):
        self.value[tag] = value


class _ListElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs, item_schema, parent):
        if not isinstance(parent, dict):
            raise _InternalError(f"The list ({tag!r}) should be a dictionary field")

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
            f
            for f in _get_declared_fields(schema).items()
            if f[1].metadata.get("maxml") == "element"
        ]
        if child_elements:
            child_names = ", ".join(repr(i[0]) for i in child_elements)
            raise _InternalError(
                f"An {tag!r} element with a {field_name!r} content field cannot contain child elements: {child_names}"
            )
        if not _is_known_scalar(field_schema):
            raise _InternalError(f"Field {field_name!r} must be a scalar")

        super().__init__(tag, register_symbol_factory)
        self.field_name = field_name
        self.field = _ScalarElement(tag, register_symbol_factory, {})
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


class _ParagraphElement(_ElementBase):
    def __init__(self, tag, register_symbol_factory, attrs, schema):
        super().__init__(tag, register_symbol_factory)
        self.check_no_attr(attrs)
        self.schema = schema
        self.commands = []
        self._text_harverter = None
        self._text_harverter_register_symbol = None
        self.tag_level = 1

    def on_starttag(self, name, attrs):
        if name == "p":
            self._end_of_text_harverter()
            return _ParagraphElement(name, self.register_symbol_factory, attrs, self.schema)

        command_schema = _get_declared_fields(self.schema).get(name)
        if command_schema:
            self._end_of_text_harverter()
            _check_command_schema(name, command_schema)
            return _factory(name, self.register_symbol_factory, attrs, command_schema)

        self.tag_level += 1
        if name == "img":
            self._end_of_text_harverter()
            value = {}
            for src, dst in {"src": "url", "alt": "caption"}.items():
                field = attrs.get(src)
                if field:
                    value[dst] = field
            self.register_symbol_factory()(value)
            self.commands.append({"image": value})
            return None

        try:
            return self.text_harverter.on_starttag(name, attrs)
        except _UnexpectedScalarChild as exc:
            raise _InternalError(f"{name!r} command not found") from exc

    def on_endtag(self, name):
        self.tag_level -= 1
        if name == "img":
            return None

        if self.tag_level:
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
        if isinstance(value, list):
            self.commands += value
        else:
            self.commands.append({tag: value})

    @property
    def text_harverter(self):
        if self._text_harverter is None:

            def _empty_register_symbol_factory():
                return lambda *_: None

            self._text_harverter = _create_command_element(
                self.schema, "text", _empty_register_symbol_factory, attrs={}
            )
            self._text_harverter_register_symbol = self.register_symbol_factory()
            self._text_harverter.tag = self.tag
        return self._text_harverter

    def _end_of_text_harverter(self):
        if self._text_harverter:
            value = self._text_harverter.on_endtag(self._text_harverter.tag)
            assert value is not None
            if value:
                self._text_harverter_register_symbol(value)
                self.commands.append({"text": value})
            self._text_harverter = None


def _factory(tag, register_symbol_factory, attrs, schema, parent=None):
    if _is_known_scalar(schema):
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
            for f in _get_declared_fields(schema.nested).items()
            if f[1].metadata.get("maxml") == "content"
        ]
        if len(content_fields) > 1:
            field_names = ", ".join(repr(i[0]) for i in content_fields)
            raise _InternalError(
                f"There can be no more than one field marked `content`: {field_names}"
            )
        if len(content_fields) == 1:
            return _ContentElement(
                tag, register_symbol_factory, attrs, schema.nested, *content_fields[0]
            )
        return _DictElement(tag, register_symbol_factory, attrs, schema.nested)
    if isinstance(schema, fields.List):
        return _ListElement(tag, register_symbol_factory, attrs, schema.inner, parent)
    raise _InternalError(f"Unexpected schema ({type(schema)}) for element {tag!r}")


def _get_declared_fields(schema):
    return schema._declared_fields  # pylint: disable-msg=W0212


def _get_object_field_schema(schema, field_name, entity="Element"):
    field_schema = _get_declared_fields(schema).get(field_name)
    if field_schema is None:
        raise _InternalError(f"{entity} {field_name!r} is not described in the schema")
    return field_schema


def _check_command_schema(name, command_schema):
    if command_schema.metadata.get("maxml", "element") != "element":
        raise _InternalError(f"Command {name!r} is not described as an element")


def _create_command_element(schema, name, register_symbol_factory, attrs):
    command_schema = _get_declared_fields(schema).get(name)
    if command_schema is None:
        raise _InternalError(f"{name!r} command not found")
    _check_command_schema(name, command_schema)
    return _factory(name, register_symbol_factory, attrs, command_schema)


def _normalize_spaces(s):
    return " ".join(s.split()) if s else ""


def _is_known_scalar(schema):
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
