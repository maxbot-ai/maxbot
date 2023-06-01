import pytest

from maxbot.errors import BotError
from maxbot.maxml import Schema, fields, markup
from maxbot.maxml.xml_parser import Pointer, XmlParser, _ContentHandler, _Error, _ErrorHandler
from maxbot.schemas import CommandSchema


class _XmlError(Exception):
    def getMessage(self):
        return "pytest"


def test_error_handler_error():
    with pytest.raises(_Error) as excinfo:
        _ErrorHandler().error(_XmlError())
    assert excinfo.value.message == "_XmlError: pytest"


def test_content_handler_no_ptr():
    assert _ContentHandler(None, None)._get_ptr() is None


def test_error_handler_warning(caplog):
    _ErrorHandler().warning(_XmlError())
    assert "XML warning" in caplog.text


def test_empty_text():
    commands = _parse_xml("")
    assert commands == []


def test_unknown_command():
    with pytest.raises(BotError) as excinfo:
        _parse_xml("<unknown_command />")
    assert "Command 'unknown_command' is not described in the schema" in excinfo.value.message


def test_text():
    (command,) = _parse_xml("Hello!")
    assert command == {"text": "Hello!"}


def test_text_with_br():
    (command,) = _parse_xml("Hello!<br />World")
    assert command == {"text": "Hello!\nWorld"}


def test_text_br_head():
    (command,) = _parse_xml("<br /> Hello, world!")
    assert command == {"text": "\nHello, world!"}


def test_text_br_tail():
    (command,) = _parse_xml("Hello, world! <br />")
    assert command == {"text": "Hello, world!\n"}


def test_text_whitespace_normalization():
    (command,) = _parse_xml(
        "<text>\n   Line 1 \n Line 2\n  <br />\n Line 3  <br />  Line 4</text>"
    )
    assert command == {"text": "Line 1 Line 2\nLine 3\nLine 4"}


def test_image():
    url = "http://localhost/image.png"
    (command,) = _parse_xml(f'<image url="{url}" />')
    assert command == {"image": {"url": url}}


def test_image_with_caption():
    url = "https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg"
    caption = "Hello, world!"
    (command,) = _parse_xml(f'<image url="{url}"><caption>{caption}</caption></image>')
    assert command == {"image": {"url": url, "caption": caption}}


def test_image_with_caption_markup():
    url = "https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg"
    (command,) = _parse_xml(f'<image url="{url}"><caption>Hello,<br />world!</caption></image>')
    assert command == {"image": {"url": url, "caption": "Hello,\nworld!"}}


@pytest.mark.parametrize("doc", ("<text>1</text></text>", "<text>"))
def test_mismatched_tag(doc):
    with pytest.raises(BotError) as excinfo:
        _parse_xml(doc)
    assert "SAXParseException: mismatched tag" in excinfo.value.message


def test_duplicate_attribute():
    with pytest.raises(BotError) as excinfo:
        _parse_xml('<image url="http://localhost/image1.png" url="http://localhost/image2.png" />')
    assert "SAXParseException: duplicate attribute" in excinfo.value.message


def test_attribute_without_quotes():
    with pytest.raises(BotError) as excinfo:
        _parse_xml("<image url=https://github.com/maxbot-ai/misc/raw/main/food_1.jpg />")
    assert "SAXParseException: not well-formed (invalid token)" in excinfo.value.message


def test_br_with_child():
    (command,) = _parse_xml("<text><br><unexpected /></br></text>")
    command["text"].items == [
        markup.Item(markup.START_TAG, "br"),
        markup.Item(markup.START_TAG, "unexpected"),
        markup.Item(markup.END_TAG, "unexpected"),
        markup.Item(markup.END_TAG, "br"),
    ]


def test_br_with_attr():
    (command,) = _parse_xml('<text><br unexpected="xxx" /></text>')
    command["text"].items == [
        markup.Item(markup.START_TAG, "br", {"unexpected": "xxx"}),
        markup.Item(markup.END_TAG, "br"),
    ]


def test_unexpected_text():
    class CustomCommandSchema(Schema):
        test = fields.Nested(Schema)

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<test>Hello world</test>", schema=CustomCommandSchema())
    assert "Element 'test' has undescribed text" in excinfo.value.message


def test_forbidden_field():
    class CustomCommandSchema(Schema):
        forbidden = fields.Dict()

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<forbidden />", schema=CustomCommandSchema())
    assert (
        "Unexpected schema (<class 'marshmallow.fields.Dict'>) for element 'forbidden'"
        in excinfo.value.message
    )


def test_list_of_scalar():
    class QuickReply(Schema):
        caption = fields.String(metadata={"maxml": "element"})
        button = fields.List(fields.String())

    class CustomCommandSchema(Schema):
        quick_reply = fields.Nested(QuickReply)

    (command,) = _parse_xml(
        (
            "<quick_reply>\n"
            "<caption>Quick reply\ncaption text</caption>\n"
            "<button>case 1</button><button>case 2</button><button>case 3</button><button>case 4</button>"
            "</quick_reply>"
        ),
        schema=CustomCommandSchema(),
    )
    assert command == {
        "quick_reply": {
            "caption": "Quick reply\ncaption text",
            "button": ["case 1", "case 2", "case 3", "case 4"],
        },
    }


def test_list_one_element():
    class QuickReply(Schema):
        caption = fields.String(metadata={"maxml": "element"})
        button = fields.List(fields.String())

    class CustomCommandSchema(Schema):
        quick_reply = fields.Nested(QuickReply)

    (command,) = _parse_xml(
        (
            "<quick_reply>\n"
            "<caption>Quick reply caption text</caption>\n"
            "<button>case 1</button>\n"
            "</quick_reply>"
        ),
        schema=CustomCommandSchema(),
    )
    assert command == {
        "quick_reply": {
            "caption": "Quick reply caption text",
            "button": ["case 1"],
        },
    }


def test_list_complex():
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

    class CustomCommandSchema(Schema):
        carousel = fields.Nested(Carousel)

    (command,) = _parse_xml(
        (
            "<carousel>\n"
            "<caption>Caption 1</caption>\n"
            "<item>\n"
            '<image url="http:://127.0.0.1/image1.jpg" />\n'
            "<title>Item 1 title</title>\n"
            "<button>Item 1 button 1</button>\n"
            "<button>Item 1 button 2</button>\n"
            "</item>\n"
            "<item>\n"
            '<image url="http:://127.0.0.1/image2.jpg" />\n'
            "<title>Item 2 title</title>\n"
            "<button>Item 2 button 1</button>\n"
            "<button>Item 2 button 2</button>\n"
            "</item>\n"
            "</carousel>"
        ),
        schema=CustomCommandSchema(),
    )
    assert command == {
        "carousel": {
            "caption": "Caption 1",
            "item": [
                {
                    "image": {"url": "http:://127.0.0.1/image1.jpg"},
                    "title": "Item 1 title",
                    "button": ["Item 1 button 1", "Item 1 button 2"],
                },
                {
                    "image": {"url": "http:://127.0.0.1/image2.jpg"},
                    "title": "Item 2 title",
                    "button": ["Item 2 button 1", "Item 2 button 2"],
                },
            ],
        }
    }


def test_attribute_redefined_by_element():
    with pytest.raises(BotError) as excinfo:
        _parse_xml('<image url="http://127.0.0.1"><url>http://127.0.0.2</url></image>')
    assert str(excinfo.value) == (
        "caused by maxbot.maxml.xml_parser._Error: Element 'url' is duplicated\n"
        '  in "<Xml document>", line 1, column 31:\n'
        '    <image url="http://127.0.0.1"><url>http://127.0.0.2</url></image>\n'
        "                                  ^^^\n"
    )


def test_element_redefined_by_element():
    with pytest.raises(BotError) as excinfo:
        _parse_xml(
            '<image url="http://127.0.0.1"><caption>1</caption><caption>2</caption></image>'
        )
    assert str(excinfo.value) == (
        "caused by maxbot.maxml.xml_parser._Error: Element 'caption' is duplicated\n"
        '  in "<Xml document>", line 1, column 51:\n'
        '    <image url="http://127.0.0.1"><caption>1</caption><caption>2</caption></image>\n'
        "                                                      ^^^\n"
    )


def test_not_described():
    class CustomCommandSchema(Schema):
        command = fields.Nested(Schema)

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<command><test /></command>", schema=CustomCommandSchema())
    assert "Element 'test' is not described in the schema" in excinfo.value.message


def test_list_of_list_case1():
    class Command(Schema):
        test = fields.List(fields.List(fields.String()))

    class CustomCommandSchema(Schema):
        command = fields.Nested(Command)

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<command><test></test></command>", schema=CustomCommandSchema())
    assert "The list ('test') should be a dictionary field" in excinfo.value.message


def test_list_of_list_case2():
    class Command2(Schema):
        test2 = fields.Nested(Schema)

    class Command1(Schema):
        test1 = fields.List(fields.Nested(Command2, many=True))

    class CustomCommandSchema(Schema):
        command = fields.Nested(Command1)

    with pytest.raises(BotError) as excinfo:
        _parse_xml(
            "<command><test1><test2></test2></test1></command>", schema=CustomCommandSchema()
        )
    assert "The list ('test1') should be a dictionary field" in excinfo.value.message


def test_list_of_nested():
    class Command3(Schema):
        test3 = fields.Str(metadata={"maxml": "element"})

    class Command2(Schema):
        test2 = fields.Nested(Command3)

    class Command1(Schema):
        test1 = fields.List(fields.Nested(Command2))

    class CustomCommandSchema(Schema):
        command = fields.Nested(Command1)

    (command,) = _parse_xml(
        (
            "<command>\n"
            "<test1><test2><test3>1</test3></test2></test1>\n"
            "<test1><test2><test3>2</test3></test2></test1>\n"
            "</command>"
        ),
        schema=CustomCommandSchema(),
    )
    assert command == {
        "command": {"test1": [{"test2": {"test3": "1"}}, {"test2": {"test3": "2"}}]}
    }


def test_text_command_with_attribute():
    class Message(Schema):
        text = fields.String(required=True, metadata={"maxml": "content"})
        to = fields.String(metadata={"maxml": "attribute"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml('<message to="operator">Hello</message>', schema=CustomCommandSchema())
    assert command == {"message": {"text": "Hello", "to": "operator"}}


def test_text_with_attrs():
    with pytest.raises(BotError) as excinfo:
        _parse_xml('<text url="http://127.0.0.1">1</text>')
    assert str(excinfo.value) == (
        "caused by maxbot.maxml.xml_parser._Error: Attribute 'url' is not described in the schema\n"
        '  in "<Xml document>", line 1, column 1:\n'
        '    <text url="http://127.0.0.1">1</text>\n'
        "    ^^^\n"
    )


def test_content_field_markup():
    class Message(Schema):
        text = markup.Field(required=True, metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml(
        ("<message>\n" "  line 1-1  \n" " line  1-2<br />\n" "line 2 \n" "</message>"),
        schema=CustomCommandSchema(),
    )
    assert command == {"message": {"text": "line 1-1 line 1-2\nline 2"}}


def test_command_explicit_element():
    class CustomCommandSchema(Schema):
        message = fields.Str(metadata={"maxml": "element"})

    (command,) = _parse_xml("<message>content</message>", schema=CustomCommandSchema())
    assert command == {"message": "content"}


@pytest.mark.parametrize(
    "maxml",
    (
        "content",
        "attribute",
    ),
)
def test_command_not_element_on_load(maxml):
    class CustomCommandSchema(Schema):
        message = fields.Str(metadata={"maxml": maxml})

    with pytest.raises(BotError) as excinfo:
        _parse_xml("", schema=CustomCommandSchema())
    assert "Command 'message' is not described as an element" in excinfo.value.message


def test_undescribed_attr():
    class CustomCommandSchema(Schema):
        message = fields.Nested(Schema)

    with pytest.raises(BotError) as excinfo:
        _parse_xml('<message attr="" />', schema=CustomCommandSchema())
    assert str(excinfo.value) == (
        "caused by maxbot.maxml.xml_parser._Error: Attribute 'attr' is not described in the schema\n"
        '  in "<Xml document>", line 1, column 1:\n'
        '    <message attr="" />\n'
        "    ^^^\n"
    )


@pytest.mark.parametrize(
    "maxml",
    (
        "element",
        "content",
    ),
)
def test_attr_maxml_mismatch(maxml):
    class Message(Schema):
        attr = fields.Str(metadata={"maxml": maxml})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(BotError) as excinfo:
        _parse_xml('<message attr="" />', schema=CustomCommandSchema())
    assert str(excinfo.value) == (
        "caused by maxbot.maxml.xml_parser._Error: Attribute 'attr' is not described in the schema\n"
        '  in "<Xml document>", line 1, column 1:\n'
        '    <message attr="" />\n'
        "    ^^^\n"
    )


def test_child_default_attribute():
    class Message(Schema):
        field = fields.Str()

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml('<message field="val" />', schema=CustomCommandSchema())
    assert command == {"message": {"field": "val"}}


def test_child_default_element_list():
    class Message(Schema):
        field = fields.List(fields.Str())

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml("<message><field>val</field></message>", schema=CustomCommandSchema())
    assert command == {"message": {"field": ["val"]}}


def test_child_default_element_dict():
    class Message(Schema):
        field = fields.Nested(Schema)

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml("<message><field /></message>", schema=CustomCommandSchema())
    assert command == {"message": {"field": {}}}


@pytest.mark.parametrize("metadata", (None, {"maxml": "attribute"}))
def test_element_maxml_mismatch(metadata):
    class Message(Schema):
        field = fields.Str(metadata=metadata)

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<message><field /></message>", schema=CustomCommandSchema())
    assert str(excinfo.value) == (
        "caused by maxbot.maxml.xml_parser._Error: Element 'field' is not described in the schema\n"
        '  in "<Xml document>", line 1, column 10:\n'
        "    <message><field /></message>\n"
        "             ^^^\n"
    )


def test_element_maxml_content():
    class Message(Schema):
        field = fields.Str(metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<message><field /></message>", schema=CustomCommandSchema())
    assert str(excinfo.value) == (
        "caused by maxbot.maxml.xml_parser._Error: Element 'field' is not described in the schema\n"
        '  in "<Xml document>", line 1, column 10:\n'
        "    <message><field /></message>\n"
        "             ^^^\n"
    )


def test_list_field_markup():
    class Message(Schema):
        line = fields.List(markup.Field())

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml(
        (
            "<message>\n"
            "<line>\n"
            "line 1-1 \n"
            " line  1-2<br /> \n"
            "  line 2\n"
            "</line>\n"
            "</message>"
        ),
        schema=CustomCommandSchema(),
    )
    assert command == {"message": {"line": ["line 1-1 line 1-2\nline 2"]}}


def test_content_error_child_element():
    class Message(Schema):
        field = fields.Str(metadata={"maxml": "content"})
        child1 = fields.Str(metadata={"maxml": "element"})
        child2 = fields.Str(metadata={"maxml": "element"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<message></message>", schema=CustomCommandSchema())
    assert (
        "An 'message' element with a 'field' content field cannot contain child elements: 'child1', 'child2'"
        in excinfo.value.message
    )


def test_content_error_must_be_scalar():
    class Message(Schema):
        field = fields.Nested(Schema, metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<message></message>", schema=CustomCommandSchema())
    assert "Field 'field' must be a scalar" in excinfo.value.message


def test_content_error_more_than_one():
    class Message(Schema):
        field1 = fields.Str(metadata={"maxml": "content"})
        field2 = fields.Str(metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<message></message>", schema=CustomCommandSchema())
    assert (
        "There can be no more than one field marked `content`: 'field1', 'field2'"
        in excinfo.value.message
    )


@pytest.mark.parametrize(
    "doc,lineno,column",
    (
        ("<text></test>", 0, 8),
        ("<text>\n</test>", 1, 2),
        ("<image\nurl=https://127.0.0.1\n/>", 1, 4),
    ),
)
def test_xml_error_ptr(doc, lineno, column):
    with pytest.raises(BotError) as excinfo:
        _parse_xml(doc)

    (snippet,) = excinfo.value.snippets
    assert snippet.line == lineno, excinfo.value.message
    assert snippet.column == column, excinfo.value.message


def test_xml_custom_markup():
    class Message(Schema):
        field = markup.Field(metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml("<message><br /></message>", schema=CustomCommandSchema())
    assert command == {"message": {"field": "\n"}}


def test_xml_error_unexpected_element_str_content():
    class Message(Schema):
        field = fields.Str(metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(BotError) as excinfo:
        _parse_xml("<message><br /></message>", schema=CustomCommandSchema())
    assert str(excinfo.value) == (
        "caused by maxbot.maxml.xml_parser._Error: Element 'br' is not described in the schema\n"
        '  in "<Xml document>", line 1, column 10:\n'
        "    <message><br /></message>\n"
        "             ^^^\n"
    )


def test_xml_error_unexpected_element_nested():
    with pytest.raises(BotError) as excinfo:
        _parse_xml('<image url="http://127.0.0.1"><br /></image>')
    assert "Element 'br' is not described in the schema" in excinfo.value.message


def test_regiter_symbol():
    doc = """first
line
        <text>value 1</text>
        <image
            url="https://127.0.0.1">
            <caption>image caption</caption>
        </image>
last
line
    """
    symbols = {}
    c1, c2, c3, c4 = _parse_xml(doc, symbols=symbols)
    assert symbols[id(c1["text"])] == Pointer(0, 0)
    assert symbols[id(c2["text"])] == Pointer(2, 8)
    assert symbols[id(c3["image"])] == Pointer(3, 8)
    assert symbols[id(c3["image"]["url"])] == Pointer(3, 8)
    assert symbols[id(c3["image"]["caption"])] == Pointer(5, 12)
    assert symbols[id(c4["text"])] == Pointer(7, 0)


def test_escaped_quotation():
    (command,) = _parse_xml("&#34;")
    command = {"text": '"'}


def _parse_xml(doc, schema=CommandSchema(), symbols=None):
    return XmlParser().loads(doc, maxml_command_schema=schema, maxml_symbols=symbols)
