import pytest

from maxbot.errors import BotError
from maxbot.maxml import Schema, fields
from maxbot.schemas import (
    CommandSchema,
    MarshmallowSchema,
    MessageSchema,
    ResourceSchema,
    YamlParsingError,
)


def test_all_scalars_are_strings():
    assert (
        ResourceSchema.Meta.render_module.loads(
            """
        bool: no
        float: nan
        int: 1
        null: NULL
        timestamp: "2001-12-15T02:59:43.1Z"
        """
        )
        == {
            "bool": "no",
            "float": "nan",
            "int": "1",
            "null": "NULL",
            "timestamp": "2001-12-15T02:59:43.1Z",
        }
    )


def test_config():
    class C(ResourceSchema):
        k1 = fields.Str()
        k2 = fields.Number()

    assert C().loads("{k1: xxx, k2: 123}") == {"k1": "xxx", "k2": 123.0}


def test_messages_short_syntax():
    # @see hook MessageSchema.short_syntax
    assert MessageSchema().loads("hello world") == {"text": "hello world"}


@pytest.mark.parametrize("doc", ("Hello world!", "<text>Hello world!</text>"))
def test_loads_text(doc):
    (command,) = CommandSchema(many=True).loads(doc)
    assert command == {"text": "Hello world!"}


def test_loads_image():
    (command,) = CommandSchema(many=True).loads(
        """
        <image url="http://hello.jpg">
            <caption>this is a hello image</caption>
        </image>
    """
    )
    assert command == {"image": {"url": "http://hello.jpg", "caption": "this is a hello image"}}


def test_variable_substitution(monkeypatch):
    class C(ResourceSchema):
        s = fields.Str()

    monkeypatch.setenv("SOME_VAR", "xxx")

    config = C().loads(
        """
        s: !ENV ${SOME_VAR}
    """
    )
    assert config["s"] == "xxx"


def test_variable_substitution_default():
    class C(ResourceSchema):
        s = fields.Str()

    config = C().loads(
        """
        s: !ENV ${SOME_VAR:xxx}
    """
    )
    assert config["s"] == "xxx"


def test_variable_substitution_missing():
    class C(ResourceSchema):
        s = fields.Str()

    with pytest.raises(BotError) as excinfo:
        C().loads(
            """
            s: !ENV ${SOME_VAR}
        """
        )
    assert str(excinfo.value) == (
        "Missing required environment variable 'SOME_VAR'\n"
        '  in "<unicode string>", line 2, column 16:\n'
        "    s: !ENV ${SOME_VAR}\n"
        "       ^^^\n"
    )


def test_variable_substitution_multiple(monkeypatch):
    class C(ResourceSchema):
        s = fields.Str()

    monkeypatch.setenv("SOME_VAR", "xxx")
    monkeypatch.setenv("OTHER_VAR", "yyy")

    config = C().loads(
        """
        s: !ENV ${SOME_VAR}/${OTHER_VAR}
    """
    )
    assert config["s"] == "xxx/yyy"


def test_variable_substitution_different_defaults():
    class C(ResourceSchema):
        s = fields.Str()

    config = C().loads(
        """
        s: !ENV ${SOME_VAR:xxx}/${SOME_VAR:yyy}
    """
    )
    assert config["s"] == "xxx/yyy"


def test_yaml_error():
    class C(ResourceSchema):
        s = fields.Str()

    with pytest.raises(BotError) as excinfo:
        C().loads(
            """
            s: {}
            x y
        """.strip()
        )

    assert str(excinfo.value) == (
        "caused by yaml.parser.ParserError: while parsing a block mapping\n"
        '  in "<unicode string>", line 1, column 1:\n'
        "    s: {}\n"
        "    ^^^\n"
        "                x y\n"
        "expected <block end>, but found '<scalar>'\n"
        '  in "<unicode string>", line 2, column 13:\n'
        "    s: {}\n"
        "                x y\n"
        "                ^^^\n"
    )


def test_validation_error():
    class S(Schema):
        x = fields.Str()

    class C(ResourceSchema):
        s = fields.Nested(S)

    with pytest.raises(BotError) as excinfo:
        C().loads(
            """
            s:
                x: {}
        """.strip()
        )

    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Not a valid string.\n"
        '  in "<unicode string>", line 2, column 20:\n'
        "    s:\n"
        "                    x: {}\n"
        "                       ^^^\n"
    )


def test_missing_required_field():
    class C(ResourceSchema):
        a = fields.String()
        b = fields.String(required=True)
        c = fields.String()

    with pytest.raises(BotError) as excinfo:
        C().loads("{a: aaa, c: ccc}")
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Missing required field 'b'.\n"
        '  in "<unicode string>", line 1, column 1:\n'
        "    {a: aaa, c: ccc}\n"
        "    ^^^\n"
    )


def test_unknown_field():
    class C(ResourceSchema):
        a = fields.String()
        b = fields.String()

    with pytest.raises(BotError) as excinfo:
        C().loads("{a: aaa, c: ccc}")
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Unknown field 'c'.\n"
        '  in "<unicode string>", line 1, column 10:\n'
        "    {a: aaa, c: ccc}\n"
        "             ^^^\n"
    )


def test_invalid_input_type():
    class C(ResourceSchema):
        a = fields.String()

    with pytest.raises(BotError) as excinfo:
        C().loads("xxx")
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Invalid input type.\n"
        '  in "<unicode string>", line 1, column 1:\n'
        "    xxx\n"
        "    ^^^\n"
    )


def test_load_file(tmpdir):
    class C(ResourceSchema):
        a = fields.String()

    p = tmpdir / "p.yaml"
    p.write("a: A")
    data = C().load_file(p)
    assert data == {"a": "A"}


def test_mapping_twice():
    class C(ResourceSchema):
        a = fields.String()

    with pytest.raises(BotError) as excinfo:
        C().loads(
            """
            a: X
            a: Y
        """
        )
    assert str(excinfo.value) == (
        "caused by yaml.constructor.ConstructorError: While constructing a mapping\n"
        '  in "<unicode string>", line 2, column 13:\n'
        "    a: X\n"
        "    ^^^\n"
        "    a: Y\n"
        'found duplicate key: "a"\n'
        '  in "<unicode string>", line 3, column 13:\n'
        "    a: X\n"
        "    a: Y\n"
        "    ^^^\n"
    )


def test_marshmallow_schema_is_abstract():
    class C(MarshmallowSchema):
        k = fields.Number()

    with pytest.raises(AssertionError):
        C().load({"k": "abc"})


def test_misprint_dictionary_instead_of_string():
    class C(ResourceSchema):
        s = fields.String()

    with pytest.raises(BotError) as excinfo:
        C().loads("s: {{ a.b }}")
    assert str(excinfo.value) == (
        "caused by yaml.constructor.ConstructorError: while constructing a mapping\n"
        '  in "<unicode string>", line 1, column 4:\n'
        "    s: {{ a.b }}\n"
        "       ^^^\n"
        "\n"
        "found unhashable key\n"
        '  in "<unicode string>", line 1, column 5:\n'
        "    s: {{ a.b }}\n"
        "        ^^^\n"
    )


def test_error_on_unknown_tag():
    class C(ResourceSchema):
        s = fields.String()

    with pytest.raises(YamlParsingError) as excinfo:
        C().loads("s: !UNK")

    assert str(excinfo.value) == (
        "caused by yaml.constructor.ConstructorError: could not determine a constructor for the tag '!UNK'\n"
        '  in "<unicode string>", line 1, column 4:\n'
        "    s: !UNK\n"
        "       ^^^\n"
    )
