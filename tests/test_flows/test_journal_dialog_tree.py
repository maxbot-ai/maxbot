from maxbot.context import StateVariables, TurnContext
from maxbot.flows._base import FlowResult
from maxbot.flows.dialog_tree import DialogNodeSchema, DialogTree


def make_context(state=None, components_state=None):
    ctx = TurnContext(
        dialog=None,
        message={"text": "hello"},
        state=StateVariables(components=components_state or {}),
    )
    if state is not None:
        ctx.state.components["ROOT"] = state
    return ctx, ctx.state.components.setdefault("ROOT", {})


async def test_journal_node_triggered():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response: triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    (
        event,
        _,
    ) = ctx.journal_events
    assert event == {"type": "node_triggered", "payload": {"node": {"condition": "true"}}}


async def test_journal_response_jump_to():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response: |
          jump from triggered
          <jump_to node="label1" transition="condition" />
      - label: label1
        condition: true
        response: jump to triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    _, event, _, _ = ctx.journal_events
    assert event == {
        "type": "response",
        "payload": {
            "node": {"condition": "true"},
            "control_command": {"jump_to": {"node": "label1", "transition": "condition"}},
        },
    }


async def test_journal_response_listen():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response:
          triggered
          <listen />
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    (
        _,
        event,
    ) = ctx.journal_events
    assert event == {
        "type": "response",
        "payload": {"node": {"condition": "true"}, "control_command": {"listen": {}}},
    }


async def test_journal_response_end():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response:
          triggered
          <end />
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    (
        _,
        event,
    ) = ctx.journal_events
    assert event == {
        "type": "response",
        "payload": {"node": {"condition": "true"}, "control_command": {"end": {}}},
    }


async def test_journal_response_followup():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response:
          root triggered
          <followup />
        followup:
            - condition: 1
              response: followup triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    _, event, _, _ = ctx.journal_events
    assert event == {
        "type": "response",
        "payload": {
            "node": {"condition": "true", "label": "root1"},
            "control_command": {"followup": {}},
        },
    }


async def test_journal_response_default_followup():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response:
          root triggered
        followup:
            - condition: 1
              response: followup triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    (
        _,
        event,
    ) = ctx.journal_events
    assert event == {
        "type": "response",
        "payload": {"node": {"condition": "true", "label": "root1"}, "followup": {}},
    }


async def test_journal_response_default_end():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response:
          triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    (
        _,
        event,
    ) = ctx.journal_events
    assert event == {"type": "response", "payload": {"node": {"condition": "true"}, "end": {}}}


async def test_journal_digression():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: label1
        condition: true
        slot_filling:
          - name: slot1
            check_for: false
            prompt: prompt slot1
        response: unexpected
      - condition: true
        response: triggered
    """
        )
    )
    ctx, state = make_context(
        state={"node_stack": [["label1", "slot_filling"]]},
        components_state={"label1": {"slot_in_focus": "slot1"}},
    )
    assert await model(ctx, state) == FlowResult.LISTEN
    _, event1, _, event2, _, _ = ctx.journal_events
    assert event1 == {
        "type": "digression_from",
        "payload": {"node": {"condition": "true", "label": "label1"}},
    }
    assert event2 == {
        "type": "response",
        "payload": {"return_after_digression": {}, "node": {"condition": "true"}},
    }
