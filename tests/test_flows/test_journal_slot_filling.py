import pytest

from maxbot.context import EntitiesResult, StateVariables, TurnContext
from maxbot.flows._base import DigressionResult
from maxbot.flows.slot_filling import HandlerSchema, SlotFilling, SlotSchema


def make_context(state=None):
    ctx = TurnContext(
        dialog=None,
        message={"text": "hello"},
        entities=EntitiesResult(),
        state=StateVariables(components={"xxx": state} if state else {}),
    )
    return ctx, ctx.state.components.setdefault("xxx", {})


async def test_journal_slot_filling():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: true
    """
        ),
        [],
    )
    ctx, state = make_context()
    await model(ctx, state)
    event1, event2 = ctx.journal_events
    assert event1 == {"type": "slot_filling", "payload": {"slot": "slot1"}}
    assert event2 == {"type": "assign", "payload": {"slots": "slot1", "value": True}}


async def test_journal_found():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: true
        found: found triggered
    """
        ),
        [],
    )
    ctx, state = make_context()
    await model(ctx, state)
    (
        _,
        _,
        event,
    ) = ctx.journal_events
    assert event == {"type": "found", "payload": {"slot": "slot1"}}


@pytest.mark.parametrize(
    "control_command", ("response", "prompt_again", "listen_again", "move_on")
)
async def test_journal_found_control_command(control_command):
    model = SlotFilling(
        SlotSchema(many=True).loads(
            f"""
      - name: slot1
        check_for: true
        found:
            <{control_command} />
    """
        ),
        [],
    )
    ctx, state = make_context()
    await model(ctx, state)
    event = ctx.journal_events[2]  # slot_filling, assing, <EVENT>[, delete]
    assert event == {
        "type": "found",
        "payload": {"slot": "slot1", "control_command": control_command},
    }


async def test_journal_not_found():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt triggered
        not_found: not_found triggered
    """
        ),
        [],
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    await model(ctx, state, DigressionResult.NOT_FOUND)
    (event,) = ctx.journal_events
    assert event == {"type": "not_found", "payload": {"slot": "slot1"}}


@pytest.mark.parametrize("control_command", ("response", "prompt_again", "listen_again"))
async def test_journal_not_found_control_command(control_command):
    model = SlotFilling(
        SlotSchema(many=True).loads(
            f"""
      - name: slot1
        check_for: false
        prompt: prompt triggered
        not_found:
            <{control_command} />
    """
        ),
        [],
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    await model(ctx, state, DigressionResult.NOT_FOUND)
    event = ctx.journal_events[0]
    assert event == {
        "type": "not_found",
        "payload": {"slot": "slot1", "control_command": control_command},
    }


async def test_journal_prompt():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt triggered
    """
        ),
        [],
    )
    ctx, state = make_context()
    await model(ctx, state)
    (event,) = ctx.journal_events
    assert event == {"type": "prompt", "payload": {"slot": "slot1"}}


@pytest.mark.parametrize("control_command", ("response", "listen_again"))
async def test_journal_prompt_control_command(control_command):
    model = SlotFilling(
        SlotSchema(many=True).loads(
            f"""
      - name: slot1
        check_for: false
        prompt:
            <{control_command} />
    """
        ),
        [],
    )
    ctx, state = make_context()
    await model(ctx, state)
    (event,) = ctx.journal_events
    assert event == {
        "type": "prompt",
        "payload": {"slot": "slot1", "control_command": control_command},
    }


async def test_journal_handler():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt triggered
    """
        ),
        HandlerSchema(many=True).loads(
            """
      - condition: true
        response: handler triggered
    """
        ),
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    await model(ctx, state, None)
    event, _ = ctx.journal_events
    assert event == {"type": "slot_handler", "payload": {"condition": "true"}}


@pytest.mark.parametrize("control_command", ("response", "move_on"))
async def test_journal_handler_control_command(control_command):
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt triggered
    """
        ),
        HandlerSchema(many=True).loads(
            f"""
      - condition: true
        response:
            <{control_command} />
    """
        ),
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    await model(ctx, state, None)
    event = ctx.journal_events[0]
    assert event == {
        "type": "slot_handler",
        "payload": {"condition": "true", "control_command": control_command},
    }
