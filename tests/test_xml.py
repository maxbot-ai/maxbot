import pytest
from marshmallow import Schema, fields

from maxbot.schemas import CommandSchema
from maxbot.xml import XmlError, XmlParser, _ErrorHandler


class _XmlError(Exception):
    def getMessage(self):
        return "pytest"


def test_error_handler_error():
    with pytest.raises(XmlError) as excinfo:
        _ErrorHandler().error(_XmlError())
    assert excinfo.value.message == "_XmlError: pytest"


def test_error_handler_warning():
    _ErrorHandler().warning(_XmlError())


def test_unexpected_root_element():
    with pytest.raises(XmlError) as excinfo:
        XmlParser().parse_paragraph("<test></test>", Schema, lambda v: None)
    assert excinfo.value.message == "Unexpected root element: 'test'"


def test_without_text_command():
    with pytest.raises(XmlError) as excinfo:
        _parse_xml("content", Schema)
    assert excinfo.value.message == "'text' command not found"


def test_empty_text():
    commands = _parse_xml("")
    assert commands == []


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


@pytest.mark.parametrize("doc", ('<image url="{url}" />', '<img src="{url}" />'))
def test_image(doc):
    url = "http://localhost/image.png"
    (command,) = _parse_xml(doc.format(url=url))
    assert command == {"image": {"url": url}}


@pytest.mark.parametrize(
    "doc",
    (
        '<image url="{url}"><caption>{caption}</caption></image>',
        '<img src="{url}" alt="{caption}" />',
    ),
)
def test_image_with_caption(doc):
    url = "https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg"
    caption = "Hello, world!"
    (command,) = _parse_xml(doc.format(url=url, caption=caption))
    assert command == {"image": {"url": url, "caption": caption}}


@pytest.mark.parametrize("doc", ("<text>1</text></text>", "<text>"))
def test_mismatched_tag(doc):
    with pytest.raises(XmlError) as excinfo:
        _parse_xml(doc)
    assert excinfo.value.message == "SAXParseException: mismatched tag"


def test_duplicate_attribute():
    with pytest.raises(XmlError) as excinfo:
        _parse_xml('<image url="http://localhost/image1.png" url="http://localhost/image2.png" />')
    assert excinfo.value.message == "SAXParseException: duplicate attribute"


def test_attribute_without_quotes():
    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<image url=https://github.com/maxbot-ai/misc/raw/main/food_1.jpg />")
    assert excinfo.value.message == "SAXParseException: not well-formed (invalid token)"


def test_br_with_child():
    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<text><br><unexpected /></br></text>")
    assert excinfo.value.message == "Element 'text' has undescribed child element 'unexpected'"


def test_br_with_attr():
    with pytest.raises(XmlError) as excinfo:
        _parse_xml('<text><br unexpected="xxx" /></text>')
    assert excinfo.value.message == "Element 'br' has undescribed attributes {'unexpected': 'xxx'}"


def test_unexpected_text():
    class CustomCommandSchema(Schema):
        test = fields.Nested(Schema)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<test>Hello world</test>", CustomCommandSchema)
    assert excinfo.value.message == "Element 'test' has undescribed text"


def test_forbidden_field():
    class CustomCommandSchema(Schema):
        forbidden = fields.Dict()

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<forbidden />", CustomCommandSchema)
    assert (
        excinfo.value.message
        == "Unexpected schema (<class 'marshmallow.fields.Dict'>) for element 'forbidden'"
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
        CustomCommandSchema,
    )
    assert command == {
        "quick_reply": {
            "caption": "Quick reply caption text",
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
        CustomCommandSchema,
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
        CustomCommandSchema,
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
    with pytest.raises(XmlError) as excinfo:
        _parse_xml('<image url="http://127.0.0.1"><url>http://127.0.0.2</url></image>')
    assert excinfo.value.message == "Value 'url' already defined"


def test_element_redefined_by_element():
    with pytest.raises(XmlError) as excinfo:
        _parse_xml(
            '<image url="http://127.0.0.1"><caption>1</caption><caption>2</caption></image>'
        )
    assert excinfo.value.message == "Value 'caption' already defined"


def test_not_described():
    class CustomCommandSchema(Schema):
        command = fields.Nested(Schema)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<command><test /></command>", CustomCommandSchema)
    assert excinfo.value.message == "Element 'test' is not described in the schema"


def test_list_of_list_case1():
    class Command(Schema):
        test = fields.List(fields.List(fields.String()))

    class CustomCommandSchema(Schema):
        command = fields.Nested(Command)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<command><test></test></command>", CustomCommandSchema)
    assert excinfo.value.message == "The list ('test') should be a dictionary field"


def test_list_of_list_case2():
    class Command2(Schema):
        test2 = fields.Nested(Schema)

    class Command1(Schema):
        test1 = fields.List(fields.Nested(Command2, many=True))

    class CustomCommandSchema(Schema):
        command = fields.Nested(Command1)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<command><test1><test2></test2></test1></command>", CustomCommandSchema)
    assert excinfo.value.message == "The list ('test1') should be a dictionary field"


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
        CustomCommandSchema,
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

    (command,) = _parse_xml('<message to="operator">Hello</message>', CustomCommandSchema)
    assert command == {"message": {"text": "Hello", "to": "operator"}}


def test_text_with_attrs():
    with pytest.raises(XmlError) as excinfo:
        _parse_xml('<text url="http://127.0.0.1">1</text>')
    assert (
        excinfo.value.message
        == "Element 'text' has undescribed attributes {'url': 'http://127.0.0.1'}"
    )


def test_content_field_text_normalization():
    class Message(Schema):
        text = fields.String(required=True, metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml(
        ("<message>\n" "  line 1-1  \n" " line  1-2<br />\n" "line 2 \n" "</message>"),
        CustomCommandSchema,
    )
    assert command == {"message": {"text": "line 1-1 line 1-2\nline 2"}}


def test_command_explicit_element():
    class CustomCommandSchema(Schema):
        message = fields.Str(metadata={"maxml": "element"})

    (command,) = _parse_xml("<message>content</message>", CustomCommandSchema)
    assert command == {"message": "content"}


@pytest.mark.parametrize(
    "maxml",
    (
        "content",
        "attribute",
    ),
)
def test_command_not_element(maxml):
    class CustomCommandSchema(Schema):
        message = fields.Str(metadata={"maxml": maxml})

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<message />", CustomCommandSchema)
    assert excinfo.value.message == "Command 'message' is not described as an element"


def test_undescribed_attr():
    class CustomCommandSchema(Schema):
        message = fields.Nested(Schema)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml('<message attr="" />', CustomCommandSchema)
    assert excinfo.value.message == "Field 'attr' is not described in the schema"


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

    with pytest.raises(XmlError) as excinfo:
        _parse_xml('<message attr="" />', CustomCommandSchema)
    assert excinfo.value.message == "Field 'attr' is not described as an attribute"


def test_child_default_attribute():
    class Message(Schema):
        field = fields.Str()

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml('<message field="val" />', CustomCommandSchema)
    assert command == {"message": {"field": "val"}}


def test_child_default_element_list():
    class Message(Schema):
        field = fields.List(fields.Str())

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml("<message><field>val</field></message>", CustomCommandSchema)
    assert command == {"message": {"field": ["val"]}}


def test_child_default_element_dict():
    class Message(Schema):
        field = fields.Nested(Schema)

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    (command,) = _parse_xml("<message><field /></message>", CustomCommandSchema)
    assert command == {"message": {"field": {}}}


def test_element_maxml_mismatch():
    class Message(Schema):
        field = fields.Str(metadata={"maxml": "attribute"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<message><field /></message>", CustomCommandSchema)
    assert excinfo.value.message == "Field 'field' is not described as an element"


def test_element_maxml_content():
    class Message(Schema):
        field = fields.Str(metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<message><field /></message>", CustomCommandSchema)
    assert excinfo.value.message == "Element 'message' has undescribed child element 'field'"


def test_list_field_text_normalization():
    class Message(Schema):
        line = fields.List(fields.String())

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
        CustomCommandSchema,
    )
    assert command == {"message": {"line": ["line 1-1 line 1-2\nline 2"]}}


def test_content_error_child_element():
    class Message(Schema):
        field = fields.Str(metadata={"maxml": "content"})
        child1 = fields.Str(metadata={"maxml": "element"})
        child2 = fields.Str(metadata={"maxml": "element"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<message></message>", CustomCommandSchema)
    assert (
        excinfo.value.message
        == "An 'message' element with a 'field' content field cannot contain child elements: 'child1', 'child2'"
    )


def test_content_error_must_be_scalar():
    class Message(Schema):
        field = fields.Nested(Schema, metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<message></message>", CustomCommandSchema)
    assert excinfo.value.message == "Field 'field' must be a scalar"


def test_content_error_more_than_one():
    class Message(Schema):
        field1 = fields.Str(metadata={"maxml": "content"})
        field2 = fields.Str(metadata={"maxml": "content"})

    class CustomCommandSchema(Schema):
        message = fields.Nested(Message)

    with pytest.raises(XmlError) as excinfo:
        _parse_xml("<message></message>", CustomCommandSchema)
    assert (
        excinfo.value.message
        == "There can be no more than one field marked `content`: 'field1', 'field2'"
    )


@pytest.mark.parametrize(
    "doc,lineno",
    (
        ("<text></test>", 0),
        ("<text>\n</test>", 1),
        ("<image\nnurl=https://127.0.0.1\n/>", 1),
        ("\n<unknown_command />", 1),
    ),
)
def test_xml_error_lineno(doc, lineno):
    with pytest.raises(XmlError) as excinfo:
        _parse_xml(doc)

    assert excinfo.value.lineno == lineno


def test_regiter_symbol():
    symbols = []

    def register_symbol(value, lineno):
        assert value != ""
        symbols.append([value, lineno])

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
    _parse_xml(doc, register_symbol=register_symbol)
    assert symbols == [
        ["first line", 0],
        ["value 1", 2],
        ["https://127.0.0.1", 3],
        ["image caption", 5],
        [{"url": "https://127.0.0.1", "caption": "image caption"}, 3],
        ["last line", 7],
    ]


def _parse_xml(doc, schema=CommandSchema, register_symbol=lambda *_: None):
    return XmlParser().parse_paragraph(f"<p>{doc}</p>", schema, register_symbol)
