from datetime import datetime, timedelta

import pytest

from maxbot.context import TurnContext
from maxbot.errors import BotError
from maxbot.maxml import Schema, fields, validate
from maxbot.scenarios import Expression, ExpressionField, ScenarioField, Template
from maxbot.schemas import MaxmlSchema, ResourceSchema


def make_context():
    ctx = TurnContext(
        dialog=None,
        message={"text": "hello"},
    )
    return ctx


async def test_template():
    template = Template("hello")
    assert await template(make_context()) == [{"text": "hello"}]


async def test_expression():
    expr = Expression("true")
    ctx = make_context()
    assert expr(ctx) is True


async def test_variable_slot():
    template = Template("{% set slots.slot1 = 'value1' %}")
    ctx = make_context()
    assert await template(ctx) == []
    assert ctx.state.slots == {"slot1": "value1"}


async def test_variable_user():
    template = Template("{% set user.user1 = 'value1' %}")
    ctx = make_context()
    assert await template(ctx) == []
    assert ctx.state.user == {"user1": "value1"}


async def test_template_empty():
    template = Template("   ")
    ctx = make_context()
    assert await template(ctx) == []


async def test_template_params():
    template = Template("{{ param1 }}")
    ctx = make_context()
    assert await template(ctx, param1="hello") == [{"text": "hello"}]


async def test_expression_params():
    expr = Expression("param1")
    ctx = make_context()
    assert expr(ctx, param1="hello") == "hello"


async def test_expression_compile_error():
    with pytest.raises(BotError) as excinfo:
        Expression("$%")
    assert str(excinfo.value) == (
        "caused by jinja2.exceptions.TemplateSyntaxError: unexpected char '$' at 0"
    )


async def test_expression_eval_error():
    expr = Expression("0/0")
    with pytest.raises(BotError) as excinfo:
        expr(make_context())
    assert str(excinfo.value) == ("caused by builtins.ZeroDivisionError: division by zero")


async def test_template_compile_error():
    with pytest.raises(BotError) as excinfo:
        Template("{% if ")
    assert str(excinfo.value) == (
        "caused by jinja2.exceptions.TemplateSyntaxError: unexpected 'end of template'"
    )


async def test_template_eval_error():
    template = Template("{{ 0/0 }}")
    ctx = make_context()
    with pytest.raises(BotError) as excinfo:
        await template(ctx)
    assert str(excinfo.value) == ("caused by builtins.ZeroDivisionError: division by zero")


async def test_template_compile_error_snippet():
    class C(ResourceSchema):
        scenario = ScenarioField()

    with pytest.raises(BotError) as excinfo:
        config = C().loads(
            """
            scenario: |
                {% set date_default = "12 April 2024" %}
                {% set date_default_2 =  %}
                {% set date_default_3 = "25 July 2023" %}
        """
        )
    assert str(excinfo.value) == (
        "caused by jinja2.exceptions.TemplateSyntaxError: Expected an expression, got 'end of statement block'\n"
        '  in "<unicode string>", line 4:\n'
        "    scenario: |\n"
        '        {% set date_default = "12 April 2024" %}\n'
        "        {% set date_default_2 =  %}\n"
        "        ^^^\n"
        '        {% set date_default_3 = "25 July 2023" %}\n'
    )


async def test_template_compile_error_snippet_one_line():
    class C(ResourceSchema):
        scenario = ScenarioField()
        other_field = fields.Integer()

    with pytest.raises(BotError) as excinfo:
        config = C().loads(
            """
            scenario: "{% set date_default_2 =  %}"
            other_field: 123
        """
        )
    assert str(excinfo.value) == (
        "caused by jinja2.exceptions.TemplateSyntaxError: Expected an expression, got 'end of statement block'\n"
        '  in "<unicode string>", line 2:\n'
        '    scenario: "{% set date_default_2 =  %}"\n'
        "              ^^^\n"
        "    other_field: 123"
    )


async def test_validation_error():
    class Command(MaxmlSchema):
        i = fields.Int()

    template = Template("<i>not a int</i>", Command)
    ctx = make_context()
    with pytest.raises(BotError) as excinfo:
        await template(ctx)
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Not a valid integer.\n"
        '  in "<Xml document>", line 1, column 1:\n'
        "    <i>not a int</i>\n"
        "    ^^^\n"
    )


async def test_validation_error_validate():
    class List(Schema):
        l = fields.List(fields.Str, validate=validate.Length(10, 20))

    class Command(MaxmlSchema):
        c = fields.Nested(List)

    template = Template("<c>\n<l>text1</l>\n<l>text2</l>\n</c>", Command)
    ctx = make_context()
    with pytest.raises(BotError) as excinfo:
        await template(ctx)
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Length must be between 10 and 20.\n"
        '  in "<Xml document>", line 2, column 1:\n'
        "    <c>\n"
        "    <l>text1</l>\n"
        "    ^^^\n"
        "    <l>text2</l>\n"
        "    </c>"
    )


async def test_validation_error_attr():
    class List(Schema):
        l = fields.List(fields.Str)

    class Command(MaxmlSchema):
        c = fields.Nested(List)

    template = Template('<c l="" />', Command)
    ctx = make_context()
    with pytest.raises(BotError) as excinfo:
        await template(ctx)
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Not a valid list.\n"
        '  in "<Xml document>", line 1, column 1:\n'
        '    <c l="" />\n'
        "    ^^^\n"
    )


async def test_validation_markdown_image_url():
    template = Template('p1\n\np2\n<image url="123" />')
    ctx = make_context()
    with pytest.raises(BotError) as excinfo:
        await template(ctx)
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Not a valid URL.\n"
        '  in "<Xml document>", line 4, column 1:\n'
        "    p1\n"
        "\n"
        "    p2\n"
        '    <image url="123" />\n'
        "    ^^^\n"
    )


async def test_scalar_boolean():
    class Command(MaxmlSchema):
        test = fields.Boolean()

    template = Template("<test>true</test>", Command)
    ctx = make_context()
    commands = await template(ctx)
    assert commands == [{"test": True}]


async def test_scalar_datetime():
    class Command(MaxmlSchema):
        test = fields.DateTime()

    now = datetime.now()
    template = Template(
        f"<test>{now.isoformat()}</test>",
        Command,
    )
    ctx = make_context()
    commands = await template(ctx)
    assert commands == [{"test": now}]


async def test_scalar_timedelta():
    class Command(MaxmlSchema):
        test = fields.TimeDelta()

    template = Template(f"<test>1</test>", Command)
    ctx = make_context()
    commands = await template(ctx)
    assert commands == [{"test": timedelta(seconds=1)}]


class ControlCommands(MaxmlSchema):
    one = fields.Nested(Schema)
    two = fields.Nested(Schema)


def test_scenario_field_template_markdown():
    class C(ResourceSchema):
        scenario = ScenarioField(ControlCommands)

    config = C(context={"commands": MaxmlSchema}).loads(
        """
        scenario: "hello {{ name }}"
    """
    )
    assert config["scenario"].content == "hello {{ name }}"
    assert issubclass(config["scenario"].Schema, (ControlCommands, MaxmlSchema))


def test_expression_field():
    class C(ResourceSchema):
        condition = ExpressionField()

    config = C().loads("condition: intents.hello")
    assert config["condition"].source == "intents.hello"


def test_expression_field_validation_error():
    class C(ResourceSchema):
        condition = ExpressionField()

    with pytest.raises(BotError):
        C().loads("condition: {}")


def test_scenario_field_must_be_string():
    class C(ResourceSchema):
        scenario = ScenarioField(ControlCommands)

    with pytest.raises(BotError) as excinfo:
        C(context={"commands": MaxmlSchema}).loads("scenario: []")
    assert str(excinfo.value) == (
        "Scenario field should be a string\n"
        '  in "<unicode string>", line 1, column 11:\n'
        "    scenario: []\n"
        "              ^^^\n"
    )
