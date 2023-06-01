"""Command pretty printer."""

from io import StringIO
from os import linesep

from markupsafe import escape

from . import fields, markup
from .xml_parser import get_metadata_maxml, is_known_scalar


def print_xml(commands, schema):
    """Pretty XML printer."""
    return _XmlPrinter()(commands, schema)


class _XmlPrinter:
    def __init__(self, indent="  ", newline=linesep):
        self._result = StringIO()
        self._indent = indent
        self._newline = newline

    @property
    def result(self):
        return self._result.getvalue()

    def _write_element_markup(self, level, name, value):
        self._result.write(f"{self._indent * level}<{name}>")
        self._write_element_markup_headless(level, name, value)

    def _write_element_markup_headless(self, level, name, value):
        lines = _markup_to_lines(value)
        if len(lines) > 1:
            self._result.write(self._newline)
            for line in lines:
                self._result.write(f"{self._indent * (level + 1)}{line}")
                self._result.write(self._newline)
            self._result.write(f"{self._indent * level}</{name}>")
        else:
            self._result.write(f"{''.join(lines)}</{name}>")

    def _write_element_nested(self, level, name, value, schema):
        if not value:
            self._result.write(f"{self._indent * level}<{name} />")
            return
        value = {**value}
        nested_schema = schema.nested()

        attrs = {}
        for field_name, field_schema in nested_schema.declared_fields.items():
            if field_name not in value:
                continue
            if get_metadata_maxml(field_schema) == "attribute":
                attrs[field_name] = value.pop(field_name)

        self._result.write(f"{self._indent * level}<{name}")
        if attrs:
            self._result.write(" ")
            self._result.write(" ".join(f'{escape(k)}="{escape(v)}"' for k, v in attrs.items()))

        if not value:
            self._result.write(" />")
            return

        self._result.write(">")

        if len(value) == 1:
            (field_name,) = value.keys()
            field_schema = nested_schema.declared_fields[field_name]
            if get_metadata_maxml(field_schema) == "content":
                (field_value,) = value.values()
                if is_known_scalar(field_schema):
                    self._result.write(f"{escape(field_value)}</{name}>")
                else:
                    self._write_element_markup_headless(level, name, field_value)
                return

        self._result.write(self._newline)
        for field_name, field_value in value.items():
            field_schema = nested_schema.declared_fields[field_name]
            assert get_metadata_maxml(field_schema) == "element"
            self._write_element(level + 1, field_name, field_value, field_schema)
            self._result.write(self._newline)
        self._result.write(f"{self._indent * level}</{name}>")

    def _write_element_list(self, level, name, value, item_schema):
        for i, item_value in enumerate(value):
            self._write_element(level, name, item_value, item_schema)
            if (i + 1) < len(value):
                self._result.write(self._newline)

    def _write_element(self, level, name, value, schema):
        if isinstance(schema, markup.Field):
            assert isinstance(value, markup.Value)
            self._write_element_markup(level, name, value)
        elif isinstance(schema, fields.Nested) and not schema.many:
            self._write_element_nested(level, name, value, schema)
        elif isinstance(schema, fields.Nested) and schema.many:
            self._write_element_list(level, name, value, fields.Nested(schema.nested))
        elif isinstance(schema, fields.List):
            self._write_element_list(level, name, value, schema.inner)
        elif is_known_scalar(schema):
            self._result.write(f"{self._indent * level}<{name}>{escape(value)}</{name}>")
        else:
            raise RuntimeError(f"Unknown element: {name}, {value}, {schema}")

    def __call__(self, commands, schema):
        for i, c in enumerate(commands):
            (name,) = c.keys()
            self._write_element(0, name, c[name], schema.declared_fields[name])
            if (i + 1) < len(commands):
                self._result.write(self._newline)

        return self.result


class _Lines:
    def __init__(self):
        self.result = []
        self._new_line = False

    def concat_last(self, value):
        assert value

        if self._new_line:
            self.result.append("")
            self._new_line = False

        if self.result:
            self.result[-1] = self.result[-1] + value
        else:
            self.result.append(value)

    def new_line(self):
        self._new_line = True


def _markup_to_lines(value):
    lines = _Lines()
    for i, item in enumerate(value.items):
        if item.kind == markup.START_TAG:
            if value.items[i + 1].kind == markup.END_TAG:
                lines.concat_last(f"<{escape(item.value)} />")
            else:
                lines.concat_last(f"<{escape(item.value)}>")
        elif item.kind == markup.END_TAG:
            if value.items[i - 1].kind == markup.START_TAG:
                continue
            lines.concat_last(f"</{escape(item.value)}>")
        else:
            assert item.kind == markup.TEXT
            item_lines = item.value.split("\n")
            for i, raw_line in enumerate(item_lines):
                if i:
                    lines.new_line()
                line = " ".join(raw_line.split())
                if line:
                    lines.concat_last(f"{escape(line)}")

            # keep spaces between pieces of text
            if item_lines and item_lines[-1] and item_lines[-1][-1].isspace():
                if (i + 1) < len(value.items) and value.items[i + 1].kind != markup.TEXT:
                    lines.concat_last(" ")

    return lines.result
