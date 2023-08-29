import pytest

from maxbot.context import StateVariables, TurnContext
from maxbot.flows._base import FlowResult
from maxbot.flows.dialog_flow import DialogFlow
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


@pytest.mark.parametrize(
    "kind",
    (
        "slots",
        "user",
    ),
)
async def test_journal_two_nodes(kind):
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: true
              response: |
                {% set """
            + kind
            + """.slot1 = 1 %}
                <jump_to node="target_node" transition="response" />
            - condition: false
              label: target_node
              response: |
                {% set """
            + kind
            + """.slot1 = 2 %}

    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    _, _, event1, _, _, event2 = ctx.journal_events
    assert event1 == {"type": "assign", "payload": {kind: "slot1", "value": 1}}
    assert event2 == {"type": "assign", "payload": {kind: "slot1", "value": 2}}


@pytest.mark.parametrize(
    "kind",
    (
        "slots",
        "user",
    ),
)
async def test_journal_equal_changes(kind):
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: true
              response: |
                {% set """
            + kind
            + """.slot1 = 1 %}
                {% set """
            + kind
            + """.slot1 = 1 %}
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE

    _, _, event1, event2 = ctx.journal_events
    assert event1 == {"type": "assign", "payload": {kind: "slot1", "value": 1}}
    assert event2 == {"type": "assign", "payload": {kind: "slot1", "value": 1}}


@pytest.mark.parametrize(
    "kind",
    (
        "slots",
        "user",
    ),
)
async def test_journal_delete(kind):
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: true
              response: |
                {% set """
            + kind
            + """.slot1 = 1 %}
                <jump_to node="target_node" transition="response" />
            - condition: false
              label: target_node
              response: |
                {% delete """
            + kind
            + """.slot1 %}

    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    _, _, event1, _, _, event2 = ctx.journal_events
    assert event1 == {"type": "assign", "payload": {kind: "slot1", "value": 1}}
    assert event2 == {"type": "delete", "payload": {kind: "slot1"}}


async def test_journal_clear():
    ctx, state = make_context()
    df = DialogFlow()
    df.load_inline_resources(
        """
            dialog:
            - condition: true
              response: |
                {% set slots.slot1 = 1 %}
                <end />"""
    )
    await df.turn(ctx)

    _, _, _, event = ctx.journal_events
    assert event == {"type": "delete", "payload": {"slots": "slot1"}}
