import pytest

from maxbot.errors import BotError
from maxbot.maxml import Schema, ValidationError, markup


def test_field_attribute_error():
    with pytest.raises(BotError) as excinfo:
        markup.Field(metadata={"maxml": "attribute"})
    assert "Unexpected `maxml` value: 'attribute'" in excinfo.value.message


def test_field_deserialize_not_value():
    class _Schema(Schema):
        m = markup.Field()

    with pytest.raises(ValidationError) as excinfo:
        _Schema().load({"m": "s"})
    assert str(excinfo.value) == "{'m': ['Not a MarkupValue.']}"


def test_value_repr():
    value = markup.Value(
        [
            markup.Item(markup.TEXT, "  abc \n def  "),
            markup.Item(markup.START_TAG, "br"),
            markup.Item(markup.END_TAG, "br"),
            markup.Item(markup.TEXT, "xyz"),
        ]
    )
    assert repr(value) == "<maxml.markup.Value'abc def\\nxyz'>"


def test_value_comparator():
    lhs = markup.Value([markup.Item(markup.TEXT, "a")])
    rhs = markup.Value([markup.Item(markup.TEXT, "a")])
    assert lhs == rhs


def test_value_comparator_false():
    lhs = markup.Value([markup.Item(markup.TEXT, "a")])
    rhs = markup.Value([markup.Item(markup.TEXT, " a")])
    assert not (lhs == rhs)


def test_value_comparator_str():
    lhs = markup.Value([markup.Item(markup.TEXT, "a")])
    assert lhs == "a"


def test_value_comparator_str_false():
    lhs = markup.Value([markup.Item(markup.TEXT, "a")])
    assert not (lhs == "b")


def test_render_keep_space_1():
    value = markup.Value(
        [
            markup.Item(markup.TEXT, "line "),
            markup.Item(markup.START_TAG, "x"),
            markup.Item(markup.TEXT, "content"),
            markup.Item(markup.END_TAG, "x"),
        ]
    )
    assert value.render() == "line content"


def test_render_keep_space_2():
    value = markup.Value(
        [
            markup.Item(markup.TEXT, "line "),
            markup.Item(markup.START_TAG, "x"),
            markup.Item(markup.END_TAG, "x"),
            markup.Item(markup.TEXT, "content"),
        ]
    )
    assert value.render() == "line content"
