import pytest

from maxbot.context import (
    EntitiesProxy,
    EntitiesResult,
    IntentsResult,
    RecognizedEntity,
    RecognizedIntent,
    StateVariables,
    TurnContext,
)
from maxbot.flows._base import DigressionResult, FlowResult
from maxbot.flows.slot_filling import HandlerSchema, SlotFilling, SlotSchema


def make_context(state=None, intents=None, entities=None):
    ctx = TurnContext(
        dialog=None,
        message={"text": "hello"},
        intents=IntentsResult.resolve(intents or []),
        entities=entities or EntitiesResult(),
        state=StateVariables(slots={}, components={"xxx": state} if state else {}),
    )
    return ctx, ctx.state.components.setdefault("xxx", {})


async def test_check_for_match():
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
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.state.slots == {"slot1": True}
    assert state == {"slot_in_focus": None}


async def test_check_for_mismatch():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
    """
        ),
        [],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": None}


async def test_check_for_match_all():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: true
      - name: slot2
        check_for: true
    """
        ),
        [],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.state.slots == {"slot1": True, "slot2": True}
    assert state == {"slot_in_focus": None}


async def test_value():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: true
        value: 123
    """
        ),
        [],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.state.slots == {"slot1": 123}
    assert state == {"slot_in_focus": None}


async def test_from_entity():
    entity = RecognizedEntity(name="number", value=1, literal="1", start_char=0, end_char=1)
    entities = EntitiesResult.resolve([entity])

    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: entities.number
    """
        ),
        [],
    )
    ctx, state = make_context(entities=entities)
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.state.slots == {"slot1": 1}
    assert state == {"slot_in_focus": None}


async def test_from_recognized_intent():
    intent = RecognizedIntent(name="yes", confidence=1.0)

    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: intents.yes
    """
        ),
        [],
    )
    ctx, state = make_context(intents=[intent])
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.state.slots == {"slot1": True}
    assert state == {"slot_in_focus": None}


async def test_prompt():
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
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "prompt triggered"}]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_digression():
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
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state) == FlowResult.DIGRESS
    assert ctx.commands == []
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_prompt_listen_again():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: |
          prompt triggered

          <listen_again />
    """
        ),
        [],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "prompt triggered"}]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_prompt_response():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: |
          prompt triggered

          <response />
    """
        ),
        [],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "prompt triggered"}]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": None}


async def test_found():
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
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "found triggered"}]
    assert ctx.state.slots == {"slot1": True}
    assert state == {"slot_in_focus": None}


async def test_found_move_on():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: true
        found: |
          found triggered

          <move_on />
    """
        ),
        [],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "found triggered"}]
    assert ctx.state.slots == {"slot1": True}
    assert state == {"slot_in_focus": None}


async def test_found_prompt_again():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: true
        found: |
          found triggered

          <prompt_again />
        prompt: prompt triggered
    """
        ),
        [],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "found triggered"},
        {"text": "prompt triggered"},
    ]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_found_listen_again():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: true
        found: |
          found triggered

          <listen_again />
        prompt: prompt unexpected
    """
        ),
        [],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "found triggered"},
    ]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_found_response():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: true
        found: |
          found triggered

          <response />
        prompt: prompt unexpected
    """
        ),
        [],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [
        {"text": "found triggered"},
    ]
    assert ctx.state.slots == {"slot1": True}
    assert state == {"slot_in_focus": None}


async def test_not_found():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt unexpected
        not_found: not_found triggered
    """
        ),
        [],
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state, DigressionResult.NOT_FOUND) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "not_found triggered"},
    ]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_not_found_listen_again():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt unexpected
        not_found: |
          not_found triggered
          <listen_again />
    """
        ),
        [],
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state, DigressionResult.NOT_FOUND) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "not_found triggered"},
    ]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_not_found_listen_again_set_slot():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt unexpected
        not_found: |
          {% set slots.slot1 = true %}
          not_found triggered
          <listen_again />
    """
        ),
        [],
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state, DigressionResult.NOT_FOUND) == FlowResult.DONE
    assert ctx.commands == [
        {"text": "not_found triggered"},
    ]
    assert ctx.state.slots == {"slot1": True}
    assert state == {"slot_in_focus": None}


async def test_not_found_prompt_again():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt triggered
        not_found: |
          not_found triggered

          <prompt_again />
    """
        ),
        [],
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state, DigressionResult.NOT_FOUND) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "not_found triggered"},
        {"text": "prompt triggered"},
    ]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_not_found_response():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt unexpected
        not_found: |
          not_found triggered

          <response />
    """
        ),
        [],
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state, DigressionResult.NOT_FOUND) == FlowResult.DONE
    assert ctx.commands == [
        {"text": "not_found triggered"},
    ]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": None}


async def test_not_found_digression_found():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt expected
        not_found: not_found unexpected
    """
        ),
        [],
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state, DigressionResult.FOUND) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "prompt expected"},
    ]
    assert state == {"slot_in_focus": "slot1"}


async def test_handlers():
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
    assert await model(ctx, state, None) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "handler triggered"},
        {"text": "prompt triggered"},
    ]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_handlers_move_on():
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
        response: |
          handler triggered

          <move_on />
    """
        ),
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state, None) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "handler triggered"},
        {"text": "prompt triggered"},
    ]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": "slot1"}


async def test_handlers_response():
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
        response: |
          handler triggered

          <response />
    """
        ),
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state, None) == FlowResult.DONE
    assert ctx.commands == [
        {"text": "handler triggered"},
    ]
    assert ctx.state.slots == {}
    assert state == {"slot_in_focus": None}


async def test_slot_removed_gc_state():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
    """
        ),
        [],
    )
    ctx, state = make_context(state={"slot_in_focus": "slot_was_removed"})
    assert await model(ctx, state, DigressionResult.NOT_FOUND) == FlowResult.DONE
    assert state == {"slot_in_focus": None}


async def test_handlers_digression_found():
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
      - name: slot1
        check_for: false
        prompt: prompt expected
    """
        ),
        HandlerSchema(many=True).loads(
            """
      - condition: true
        response: handler unexpected
    """
        ),
    )
    ctx, state = make_context(state={"slot_in_focus": "slot1"})
    assert await model(ctx, state, DigressionResult.FOUND) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "prompt expected"},
    ]
