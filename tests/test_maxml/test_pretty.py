from os import linesep

import pytest

from maxbot.maxml import Schema, fields, markup, pretty
from maxbot.schemas import CommandSchema


def test_markup_single_line():
    items = [markup.Item(markup.TEXT, "line content")]
    result = pretty.print_xml([{"text": markup.Value(items)}], CommandSchema())
    assert result == "<text>line content</text>"


def test_markup_multi_line():
    items = [markup.Item(markup.TEXT, "line 1\nline 2")]
    result = pretty.print_xml([{"text": markup.Value(items)}], CommandSchema())
    assert result == linesep.join(
        [
            "<text>",
            "  line 1",
            "  line 2",
            "</text>",
        ]
    )


def test_markup_start_end():
    items = [markup.Item(markup.START_TAG, "br"), markup.Item(markup.END_TAG, "br")]
    result = pretty.print_xml([{"text": markup.Value(items)}], CommandSchema())
    assert result == "<text><br /></text>"


def test_markup_start_text_end():
    items = [
        markup.Item(markup.TEXT, "line "),
        markup.Item(markup.START_TAG, "x"),
        markup.Item(markup.TEXT, "content"),
        markup.Item(markup.END_TAG, "x"),
    ]
    result = pretty.print_xml([{"text": markup.Value(items)}], CommandSchema())
    assert result == "<text>line <x>content</x></text>"


def test_markup_normalization():
    items = [
        markup.Item(markup.TEXT, "The temperature outside         is 30°F."),
        markup.Item(markup.START_TAG, "br"),
        markup.Item(markup.END_TAG, "br"),
        markup.Item(
            markup.TEXT, "It's very cold. \n\nConsider wearing a scarf.\n      Have a nice day!"
        ),
    ]
    result = pretty.print_xml([{"text": markup.Value(items)}], CommandSchema())
    assert result == linesep.join(
        [
            "<text>",
            "  The temperature outside is 30°F.<br />It&#39;s very cold.",
            "  Consider wearing a scarf.",
            "  Have a nice day!",
            "</text>",
        ]
    )


def test_commands_separator():
    items = [markup.Item(markup.TEXT, "test")]
    result = pretty.print_xml([{"text": markup.Value(items)}] * 2, CommandSchema())
    assert result == linesep.join(["<text>test</text>", "<text>test</text>"])


def test_plain_text():
    class MyCommandSchema(Schema):
        i = fields.String()

    result = pretty.print_xml([{"i": "test"}], MyCommandSchema())
    assert result == "<i>test</i>"


def test_number():
    class MyCommandSchema(Schema):
        i = fields.Number()

    result = pretty.print_xml([{"i": 1}], MyCommandSchema())
    assert result == "<i>1</i>"


def test_escape():
    class MyCommandSchema(Schema):
        i = fields.String()

    result = pretty.print_xml([{"i": '"'}], MyCommandSchema())
    assert result == "<i>&#34;</i>"


def test_nested():
    command = {
        "image": {
            "url": "http://127.0.0.2",
            "caption": markup.Value([markup.Item(markup.TEXT, "test")]),
        }
    }
    result = pretty.print_xml([command], CommandSchema())
    assert result == linesep.join(
        [
            '<image url="http://127.0.0.2">',
            "  <caption>test</caption>",
            "</image>",
        ]
    )


def test_nested_empty():
    class MyCommandSchema(Schema):
        test = fields.Nested(Schema)

    result = pretty.print_xml([{"test": {}}], MyCommandSchema())
    assert result == "<test />"


def test_escaped_attr():
    command = {
        "image": {
            "url": '"',
        }
    }
    result = pretty.print_xml([command], CommandSchema())
    assert result == '<image url="&#34;" />'


def test_carousel():
    class CarouselImage(Schema):
        url = fields.Url()

    class CarouselItem(Schema):
        image = fields.Nested(CarouselImage)
        title = fields.String(metadata={"maxml": "element"})
        subtitle = fields.String(metadata={"maxml": "element"})
        button = fields.List(fields.String())

    class Carousel(Schema):
        caption = fields.String(metadata={"maxml": "element"})
        item = fields.Nested(CarouselItem, many=True)

    class MyCommandSchema(Schema):
        carousel = fields.Nested(Carousel)

    command = {
        "carousel": {
            "caption": "Caption 1",
            "item": [
                {
                    "image": {"url": "http://127.0.0.1/image1.jpg"},
                    "title": "Item 1 title",
                    "button": ["Item 1 button 1", "Item 1 button 2"],
                },
                {
                    "image": {"url": "http://127.0.0.1/image2.jpg"},
                    "title": "Item 2 title",
                    "button": ["Item 2 button 1", "Item 2 button 2"],
                },
            ],
        }
    }
    result = pretty.print_xml([command], MyCommandSchema())
    assert result == linesep.join(
        [
            "<carousel>",
            "  <caption>Caption 1</caption>",
            "  <item>",
            '    <image url="http://127.0.0.1/image1.jpg" />',
            "    <title>Item 1 title</title>",
            "    <button>Item 1 button 1</button>",
            "    <button>Item 1 button 2</button>",
            "  </item>",
            "  <item>",
            '    <image url="http://127.0.0.1/image2.jpg" />',
            "    <title>Item 2 title</title>",
            "    <button>Item 2 button 1</button>",
            "    <button>Item 2 button 2</button>",
            "  </item>",
            "</carousel>",
        ]
    )


def test_content_strting():
    class Message(Schema):
        text = fields.String(metadata={"maxml": "content"})
        to = fields.String()

    class MyCommandSchema(Schema):
        message = fields.Nested(Message)

    command = {"message": {"text": "Hello", "to": "operator"}}
    result = pretty.print_xml([command], MyCommandSchema())
    assert result == '<message to="operator">Hello</message>'


def test_content_markdown():
    class Message(Schema):
        text = markup.Field(metadata={"maxml": "content"})
        to = fields.String()

    class MyCommandSchema(Schema):
        message = fields.Nested(Message)

    items = [
        markup.Item(markup.TEXT, "line "),
        markup.Item(markup.START_TAG, "br"),
        markup.Item(markup.END_TAG, "br"),
        markup.Item(markup.TEXT, "content"),
    ]
    command = {"message": {"text": markup.Value(items), "to": "operator"}}
    result = pretty.print_xml([command], MyCommandSchema())
    assert result == '<message to="operator">line <br />content</message>'


def test_content_markdown_multiline():
    class Message(Schema):
        text = markup.Field(metadata={"maxml": "content"})
        to = fields.String()

    class MyCommandSchema(Schema):
        message = fields.Nested(Message)

    items = [
        markup.Item(markup.TEXT, "line 1"),
        markup.Item(markup.START_TAG, "br"),
        markup.Item(markup.END_TAG, "br"),
        markup.Item(markup.TEXT, "\nline 2"),
    ]
    command = {"message": {"text": markup.Value(items), "to": "operator"}}
    result = pretty.print_xml([command], MyCommandSchema())
    assert result == linesep.join(
        [
            '<message to="operator">',
            "  line 1<br />",
            "  line 2",
            "</message>",
        ]
    )


def test_unknown_element():
    class Command(Schema):
        f = fields.Field()

    class MyCommandSchema(Schema):
        command = fields.Nested(Command)

    with pytest.raises(RuntimeError) as excinfo:
        result = pretty.print_xml([{"command": {"f": None}}], MyCommandSchema())
    assert str(excinfo.value).startswith("Unknown element: f, None, <fields.Field")
