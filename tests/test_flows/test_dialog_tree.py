import pytest

from maxbot.context import RpcContext, RpcRequest, StateVariables, TurnContext
from maxbot.errors import BotError
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


def background_context(state=None, components_state=None):
    ctx = TurnContext(
        dialog=None,
        rpc=RpcContext(RpcRequest(method="say_hello")),
        state=StateVariables(components=components_state or {}),
    )
    if state is not None:
        ctx.state.components["ROOT"] = state
    return ctx, ctx.state.components.setdefault("ROOT", {})


async def test_root_node_match():
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
    assert ctx.commands == [{"text": "triggered"}]
    assert state == {"node_stack": []}


async def test_root_node_match_single():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response: triggered
      - condition: true
        response: unreachable
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "triggered"}]
    assert state == {"node_stack": []}


async def test_root_node_mismatch():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: false
        response: triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == []
    assert state == {"node_stack": []}


async def test_listen():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response: |
          triggered

          <listen />
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "triggered"}]
    assert state == {"node_stack": []}


async def test_followup_listen_implicit():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root triggered
        followup:
            - condition: true
              response: followup triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "root triggered"}]
    assert state == {"node_stack": [["root1", "followup"]]}


async def test_followup_listen_explicit():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: |
          root triggered

          <listen />
        followup:
            - condition: true
              response: followup triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "root triggered"}]
    assert state == {"node_stack": [["root1", "followup"]]}


async def test_followup_followup_match():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: |
          root triggered

          <followup />
        followup:
            - condition: true
              response: followup triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [
        {"text": "root triggered"},
        {"text": "followup triggered"},
    ]
    assert state == {"node_stack": []}


async def test_followup_followup_mismatch():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: |
          root triggered

          <followup />
        followup:
            - condition: false
              response: unreachable
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "root triggered"}]
    assert state == {"node_stack": []}
    (log,) = ctx.logs
    assert log.message == "Nothing matched from followup nodes of 'root1'."
    assert log.level == "WARNING"


async def test_focus_followup_match():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root triggered
        followup:
            - condition: true
              response: followup triggered
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1", "followup"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "followup triggered"}]
    assert state == {"node_stack": []}


async def test_focus_followup_mismatch_digression():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root triggered
        followup:
            - condition: false
              response: followup unexpected
      - condition: true
        response: digression triggered
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1", "followup"]]})
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "digression triggered"},
        {"text": "root triggered"},
    ]
    assert state == {"node_stack": [["root1", "followup"]]}


async def test_focus_unknown():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root triggered
        followup:
            - condition: true
              response: followup triggered
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1", "unknown"]]})
    with pytest.raises(ValueError) as excinfo:
        await model(ctx, state)
    assert "Unknown focus transition" in str(excinfo)


async def test_jumpt_to_condition_match():
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
    assert ctx.commands == [
        {"text": "jump from triggered"},
        {"text": "jump to triggered"},
    ]
    assert state == {"node_stack": []}


async def test_jumpt_to_condition_mismatch():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: digressing
        response: we are not expecting digression here
      - condition: true
        response: |
          jump from triggered

          <jump_to node="label1" transition="condition" />
      - label: label1
        condition: false
        response: unreachable
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "jump from triggered"}]
    assert state == {"node_stack": []}
    (log,) = ctx.logs
    assert log.message == "Nothing matched when jumping to 'label1' and its siblings."
    assert log.level == "WARNING"


async def test_jumpt_to_response():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response: |
          jump from triggered

          <jump_to  node="label1" transition="response" />
      - label: label1
        condition: false
        response: jump to triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [
        {"text": "jump from triggered"},
        {"text": "jump to triggered"},
    ]
    assert state == {"node_stack": []}


async def test_jumpt_to_unknown_node():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response: |
          jump from triggered

          <jump_to node="unknown" transition="response" />
    """
        )
    )
    ctx, state = make_context()
    with pytest.raises(RuntimeError) as excinfo:
        await model(ctx, state)
    assert "Unknown jump_to node" in str(excinfo)


async def test_followup_missing_label():
    with pytest.raises(BotError) as excinfo:
        DialogTree(
            DialogNodeSchema(many=True).loads(
                """
          - condition: true
            response: root triggered
            followup:
              - condition: true
                response: followup triggered
        """
            )
        )
    assert "Stateful node must have a label" in str(excinfo.value)


async def test_slot_filling_missing_label():
    with pytest.raises(BotError) as excinfo:
        DialogTree(
            DialogNodeSchema(many=True).loads(
                """
          - condition: true
            slot_filling:
              - name: slot1
                check_for: true
            response: root triggered
        """
            )
        )
    assert "Stateful node must have a label" in str(excinfo.value)


async def test_duplicate_label():
    with pytest.raises(BotError) as excinfo:
        DialogTree(
            DialogNodeSchema(many=True).loads(
                """
          - label: label1
            condition: true
            response: root triggered
          - label: label1
            condition: true
            response: root triggered
        """
            )
        )
    assert "Duplicate node label" in str(excinfo.value)


async def test_slot_filling_done():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: label1
        condition: true
        slot_filling:
          - name: slot1
            check_for: true
        response: triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "triggered"}]
    assert state == {"node_stack": []}
    assert ctx.state.slots == {"slot1": True}


async def test_slot_filling_listen():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: label1
        condition: true
        slot_filling:
          - name: slot1
            check_for: false
            prompt: prompt slot1
        response: triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "prompt slot1"}]
    assert state == {"node_stack": [["label1", "slot_filling"]]}
    assert ctx.state.slots == {}


async def test_slot_filling_digression():
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
    assert ctx.commands == [
        {"text": "triggered"},
        {"text": "prompt slot1"},
    ]
    assert state == {"node_stack": [["label1", "slot_filling"]]}
    assert ctx.state.slots == {}


async def test_digression_flag_digressing():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root triggered
        followup:
            - condition: false
              response: followup unexpected
      - condition: not digressing
        response: digression unexpected
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1", "followup"]]})
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "root triggered"}]
    assert state == {"node_stack": [["root1", "followup"]]}


async def test_digression_end():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root unexpected
        followup:
            - condition: false
              response: followup unexpected
      - condition: true
        response: |
          digression triggered

          <end />
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1", "followup"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "digression triggered"}]
    assert state == {"node_stack": []}


async def test_digression_end_slot_filling():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        slot_filling:
          - name: slot1
            check_for: false
            prompt: prompt unexpected
        response: root unexpected
      - condition: true
        response: |
          digression triggered

          <end />
    """
        )
    )
    ctx, state = make_context(
        state={"node_stack": [["root1", "slot_filling"]]},
        components_state={"root1": {"slot_in_focus": "slot1"}},
    )
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "digression triggered"}]
    assert state == {"node_stack": []}


async def test_digression_never_return_found():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root unexpected
        followup:
            - condition: false
              response: followup unexpected
        settings:
            after_digression_followup: never_return
      - condition: true
        response: digression triggered
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1", "followup"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "digression triggered"}]
    assert state == {"node_stack": []}


async def test_digression_never_return_not_found():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root unexpected
        followup:
            - condition: false
              response: followup unexpected
        settings:
            after_digression_followup: never_return
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1", "followup"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == []
    assert state == {"node_stack": []}


async def test_jump_to_digressed():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root triggered
        followup:
            - condition: false
              response: followup unexpected
        settings:
            after_digression_followup: never_return
      - condition: true
        response: |
          digression triggered

          <jump_to node="root1" transition="response" />
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1", "followup"]]})
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [
        {"text": "digression triggered"},
        {"text": "root triggered"},
    ]
    assert state == {"node_stack": [["root1", "followup"]]}


async def test_background_does_not_return_when_digression_not_found():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: root unexpected
        followup:
            - condition: false
              response: followup unexpected
      - condition: false
        response: digression unexpected
    """
        )
    )
    ctx, state = background_context(state={"node_stack": [["root1", "followup"]]})
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == []
    assert state == {"node_stack": [["root1", "followup"]]}


async def test_jump_to_listen_build_state():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: |
          root1 triggered

          <jump_to node="root2" transition="listen" />
      - label: root2
        condition: true
        response: root2 triggered
    """
        )
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "root1 triggered"}]
    assert state == {"node_stack": [["root2", "condition"]]}


async def test_jump_to_listen_use_state():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: |
          root1 triggered

          <jump_to node="root2" transition="listen" />
      - label: root2
        condition: true
        response: root2 triggered
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root2", "condition"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "root2 triggered"}]
    assert state == {"node_stack": []}


async def test_jump_to_listen_sibling():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root1
        condition: true
        response: |
          root1 triggered

          <jump_to node="root2" transition="listen" />
      - label: root2
        condition: false
        response: root2 triggered
      - label: root3
        condition: true
        response: root3 triggered
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root2", "condition"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "root3 triggered"}]
    assert state == {"node_stack": []}


async def test_jump_to_listen_digression():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root0
        condition: true
        response: root0 triggered
      - label: root1
        condition: false
        response: root1 triggered
        followup:
            - label: root1_1
              condition: false
              response: followup unexpected
      - label: root2
        condition: true
        response: root2 triggered
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1_1", "condition"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "root0 triggered"}]
    assert state == {"node_stack": []}


async def test_jump_to_listen_root_without_digression():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - label: root0
        condition: true
        response: root0 triggered
      - label: root1
        condition: false
        response: root1 triggered
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["root1", "condition"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == []
    assert state == {"node_stack": []}


async def test_node_condition_required():
    with pytest.raises(BotError) as excinfo:
        DialogNodeSchema(many=True).loads(
            """
            - response: triggered
        """
        )
    assert str(excinfo.value) == (
        "Unknown node type\n"
        '  in "<unicode string>", line 2, column 15:\n'
        "    - response: triggered\n"
        "      ^^^\n"
    )


async def test_node_response_required():
    with pytest.raises(BotError) as excinfo:
        DialogNodeSchema(many=True).loads(
            """
            - condition: true
        """
        )
    assert str(excinfo.value) == (
        "Unknown node type\n"
        '  in "<unicode string>", line 2, column 15:\n'
        "    - condition: true\n"
        "      ^^^\n"
    )


async def test_node_removed_gc_stack():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
      - condition: true
        response: root triggered
    """
        )
    )
    ctx, state = make_context(state={"node_stack": [["does_not_exist", "condition"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "root triggered"}]
    assert state == {"node_stack": []}
