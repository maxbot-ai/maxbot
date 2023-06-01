from unittest.mock import AsyncMock

import pytest

from maxbot.context import TurnContext
from maxbot.errors import BotError
from maxbot.flows.dialog_flow import DialogFlow


@pytest.fixture
def ctx(dialog_stub, state_stub):
    return TurnContext(message={"text": "hey bot"}, dialog=dialog_stub, state=state_stub)


async def test_clear_slots(ctx):
    df = DialogFlow()
    df.load_inline_resources(
        """
        dialog:
          - condition: true
            response: |
                {% set slots.slot1 = 'value1' %}
    """
    )
    await df.turn(ctx)
    assert "slot1" not in ctx.state.slots


async def test_preserve_slots(ctx):
    df = DialogFlow()
    df.load_inline_resources(
        """
        dialog:
          - condition: true
            label: node1
            response: |
                {% set slots.slot1 = 'value1' %}
            followup:
              - condition: true
                response: some text
    """
    )
    await df.turn(ctx)
    assert ctx.state.slots["slot1"] == "value1"


async def test_invalid_command(ctx):
    df = DialogFlow()
    df.load_inline_resources(
        """
        dialog:
         - condition: true
           response: <custom f="xxx" />
    """
    )
    await df.turn(ctx)
    assert str(ctx.error) == (
        "caused by maxbot.maxml.xml_parser._Error: Command 'custom' is not described in the schema\n"
        '  in "<unicode string>", line 4, column 22:\n'
        "    - condition: true\n"
        '      response: <custom f="xxx" />\n'
        "                ^^^\n"
        "\n"
        '  in "<Xml document>", line 1, column 1:\n'
        '    <custom f="xxx" />\n'
        "    ^^^\n"
    )


async def test_invalid_template(ctx):
    df = DialogFlow()
    df.load_inline_resources(
        """
        dialog:
          - condition: true
            response: |
              {{ abc.field + 1 }}
    """
    )
    await df.turn(ctx)
    assert str(ctx.error) == (
        "caused by jinja2.exceptions.UndefinedError: 'abc' is undefined\n"
        '  in "<unicode string>", line 5:\n'
        "    response: |\n"
        "      {{ abc.field + 1 }}\n"
        "      ^^^\n"
    )


async def test_before_turn(ctx):
    hook = AsyncMock()
    df = DialogFlow(before_turn=[hook])
    df.load_inline_resources(
        """
        dialog:
         - condition: true
           response: hello world
    """
    )
    await df.turn(ctx)
    hook.assert_called_once_with(ctx=ctx)


async def test_after_turn(ctx):
    hook = AsyncMock()
    df = DialogFlow(after_turn=[hook])
    df.load_inline_resources(
        """
        dialog:
         - condition: true
           response: hello world
    """
    )
    await df.turn(ctx)
    hook.assert_called_once_with(ctx=ctx, listening=False)
