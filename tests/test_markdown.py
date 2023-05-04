import pytest
import yaml
from marshmallow import Schema, fields

from maxbot.markdown import MarkdownError, MarkdownRender
from maxbot.schemas import CommandSchema


@pytest.fixture(scope="session")
def md():
    renderer = MarkdownRender()
    return lambda document, symbols=None, command_schema=CommandSchema: renderer.loads(
        document, maxml_command_schema=command_schema, maxml_symbols=symbols
    )


def test_image_in_paragraph(md):
    commands = md("line\n1![](https://127.0.0.1)line    2")
    assert commands == [
        {"text": "line 1"},
        {"image": {"url": "https://127.0.0.1"}},
        {"text": "line 2"},
    ]


def test_inline_html(md):
    commands = md(
        _load_yaml(
            """|+
                Paragraph    1 text   line
                1 <br /> line    2<br/>   line 3

                <p>Paragraph
                2</p>
                <p>Paragraph 3    </p>

                <text>
                    Paragraph
                    4
                </text>
        """
        )
    )
    assert commands == [
        {"text": "Paragraph 1 text line 1\nline 2\nline 3"},
        {"text": "Paragraph 2"},
        {"text": "Paragraph 3"},
        {"text": "Paragraph 4"},
    ]


@pytest.mark.parametrize(
    "doc",
    (
        "Hello!\n\nHow are you?",
        "<p>Hello!</p>\n<p>How are you?</p>",
        "<text>Hello!</text><text>How are you?</text>",
    ),
)
def test_paragraph_separation(md, doc):
    commands = md(doc)
    assert commands == [{"text": "Hello!"}, {"text": "How are you?"}]


def test_maxbot_command_multiple_elements(md):
    commands = md("<text><br /></text>")
    assert commands == [{"text": "\n"}]


def test_maxbot_command_new_line_after_tag(md):
    commands = md('<image\nurl="http://localhost/image1.png" />')
    assert commands == [{"image": {"url": "http://localhost/image1.png"}}]


@pytest.mark.parametrize(
    "document", ("<test><br /></text>", "<test />", '<test\nurl="http://127.0.0.1"/>')
)
def test_maxbot_command_misprint_open_tag(md, document):
    with pytest.raises(MarkdownError) as excinfo:
        md(document)
    assert excinfo.value.message == "'test' command not found"


def test_tail_text(md):
    commands = md("<text>1</text>2")
    assert commands == [{"text": "1"}, {"text": "2"}]


def test_tail_markdown(md):
    commands = md("<text>1</text>![](http://127.0.0.1)")
    assert commands == [{"text": "1"}, {"image": {"url": "http://127.0.0.1"}}]


def test_merge(md):
    commands = md(
        _load_yaml(
            """|+
        First line

        Text before
        image
        ![](http://localhost/image1.png)
        Text 1
        after
        image 1

        Text 2
        after image 1

        ![](http://localhost/image2.png)

        Text 1
        after
        image 2

        Last line
        """
        ),
    )
    assert commands == [
        {"text": "First line"},
        {"text": "Text before image"},
        {"image": {"url": "http://localhost/image1.png"}},
        {"text": "Text 1 after image 1"},
        {"text": "Text 2 after image 1"},
        {"image": {"url": "http://localhost/image2.png"}},
        {"text": "Text 1 after image 2"},
        {"text": "Last line"},
    ]


def test_paragraph_after_xml(md):
    commands = md(
        _load_yaml(
            """|+
                <text>Text from XML</text>

                Text from paragraph
        """
        ),
    )
    assert commands == [{"text": "Text from XML"}, {"text": "Text from paragraph"}]


@pytest.mark.parametrize(
    "case, lineno",
    (
        (
            "<text><br><unexpected /></br></text>",
            0,
        ),
        (
            "\n<unexpected />",
            1,
        ),
        (
            "paragraph\n\n<text><br><unexpected /></br></text>",
            2,
        ),
        (
            "paragraph one\n\n<text>\n<br>\n<image url=1 /></text>",
            4,
        ),
    ),
)
def test_markdown_error_line(case, lineno, md):
    with pytest.raises(MarkdownError) as excinfo:
        md(case)
    assert excinfo.value.lineno == lineno


def test_text_around_image(md):
    commands = md("How are you? ![](https://github.com/maxbot-ai/misc/raw/main/food_1.jpg) Hello!")
    assert commands == [
        {"text": "How are you?"},
        {"image": {"url": "https://github.com/maxbot-ai/misc/raw/main/food_1.jpg"}},
        {"text": "Hello!"},
    ]


def test_image_without_caption(md):
    url = "https://github.com/maxbot-ai/misc/raw/main/food_1.jpg"
    commands = md("![]({url})".format(url=url))
    assert commands == [{"image": {"url": url}}]


def test_image_with_caption(md):
    url = "https://github.com/maxbot-ai/misc/raw/main/food_1.jpg"
    caption = "Hello, world!"
    commands = md("![{caption}]({url})".format(url=url, caption=caption))
    assert commands == [{"image": {"url": url, "caption": caption}}]


@pytest.mark.parametrize(
    "tmpl",
    (
        "![Hello, world\\!]({url})",
        "![Hello, world&#33;]({url})",
    ),
)
def test_image_with_escaped_caption(md, tmpl):
    url = "https://github.com/maxbot-ai/misc/raw/main/food_1.jpg"
    commands = md(tmpl.format(url=url))
    assert commands == [{"image": {"url": url, "caption": "Hello, world!"}}]


def test_load_escaped_html(md):
    commands = md("&amp;&lt;&gt;&#34;&#39;")
    assert commands == [{"text": "&<>\"'"}]


def test_load_escaped_markdown(md):
    value = "![]()*_"
    commands = md("".join("\\" + ch for ch in value))
    assert commands == [{"text": value}]


def test_assertion_error_if_schema_not_set(md):
    with pytest.raises(AssertionError) as excinfo:
        MarkdownRender().loads("")


def test_symbols(md):
    doc = """first
        paragraph line 1
        <text>first paragraph line 2</text>

        second
        paragraph line 1
        <text>second paragraph line 2</text>
    """
    symbols = {}
    commands = md(doc, symbols=symbols)
    assert commands[0]["text"] == "first paragraph line 1"
    assert symbols[id(commands[0]["text"])] == 0
    assert commands[1]["text"] == "first paragraph line 2"
    assert symbols[id(commands[1]["text"])] == 2
    assert commands[2]["text"] == "second paragraph line 1"
    assert symbols[id(commands[2]["text"])] == 4
    assert commands[3]["text"] == "second paragraph line 2"
    assert symbols[id(commands[3]["text"])] == 6


def test_attr_value_escaped(md):
    (command,) = md(
        (
            '<image url="https&#58;&#47;&#47;api&#46;telegram&#46;org'
            '&#47;file&#47;botXXX&#58;YYYYYYYY&#47;photos&#47;file&#95;0&#46;jpg" />'
        )
    )
    assert (
        command["image"]["url"]
        == "https://api.telegram.org/file/botXXX:YYYYYYYY/photos/file_0.jpg"
    )


def test_two_spaces_nl(md):
    class QuickRepliesCommand(Schema):
        text = fields.String(required=True)
        button = fields.List(fields.String)

    class _CommandSchema(Schema):
        quick_replies = fields.Nested(QuickRepliesCommand)

    commands = md(
        _load_yaml(
            """|
            I can help you find a credit card to suit your needs.<br />
            We have credit cards to build credit, provide rewards,<br />
            and help you save money.
            <quick_replies text="What are you looking for most in a credit card?">"""
            + "  "
            + """
                <button>Rewards</button>
                <button>Increase credit score</button>
                <button>Save money</button>
            </quick_replies>
            """
        ),
        command_schema=type("UnionCommandSchema", (_CommandSchema, CommandSchema), {}),
    )
    assert commands == [
        {
            "text": (
                "I can help you find a credit card to suit your needs.\n"
                "We have credit cards to build credit, provide rewards,\n"
                "and help you save money."
            )
        },
        {
            "quick_replies": {
                "text": "What are you looking for most in a credit card?",
                "button": ["Rewards", "Increase credit score", "Save money"],
            }
        },
    ]


def _load_yaml(s):
    return yaml.load(s, Loader=yaml.SafeLoader)
