import logging

import pytest
from test_dialog_tree import make_context

from maxbot.context import RpcContext, RpcRequest, StateVariables, TurnContext
from maxbot.errors import BotError
from maxbot.flows._base import FlowResult
from maxbot.flows.dialog_tree import DialogNodeSchema, DialogTree, SubtreeSchema


async def test_dialog_node_unknown_type():
    with pytest.raises(BotError) as excinfo:
        DialogNodeSchema(many=True).loads("- {}")
    assert str(excinfo.value) == (
        "Unknown node type\n"
        '  in "<unicode string>", line 1, column 3:\n'
        "    - {}\n"
        "      ^^^\n"
    )


async def test_dialog_node_invalid_type():
    with pytest.raises(BotError) as excinfo:
        DialogNodeSchema(many=True).loads("- ''")
    assert str(excinfo.value) == (
        "Invalid input type\n"
        '  in "<unicode string>", line 1, column 3:\n'
        "    - ''\n"
        "      ^^^\n"
    )


async def test_dialog_node_invalid_type_iterable():
    with pytest.raises(BotError) as excinfo:
        DialogNodeSchema(many=True).loads("- abc")
    assert str(excinfo.value) == (
        "Invalid input type\n"
        '  in "<unicode string>", line 1, column 3:\n'
        "    - abc\n"
        "      ^^^\n"
    )


@pytest.mark.parametrize(
    "field",
    (
        "label: a",
        "condition: true",
        "slot_filling: []",
        "slot_handlers: []",
        "response: test",
        "followup: []",
        "settings: {}",
    ),
)
async def test_node_subtree_incompatible(field):
    with pytest.raises(BotError) as excinfo:
        DialogNodeSchema(many=True).loads(
            """
            - subtree: subtree_0
              """
            + field
        )
    assert str(excinfo.value).startswith(
        "caused by marshmallow.exceptions.ValidationError: Unknown field"
    )


async def test_subtree_not_found():
    with pytest.raises(BotError) as excinfo:
        DialogTree(
            DialogNodeSchema(many=True).loads(
                """
                - subtree: not_found
            """
            )
        )
    assert str(excinfo.value) == (
        "Sub-tree 'not_found' not found\n"
        '  in "<unicode string>", line 2, column 28:\n'
        "    - subtree: not_found\n"
        "               ^^^\n"
    )


async def test_subtrees_duplicate():
    with pytest.raises(BotError) as excinfo:
        DialogTree(
            [],
            [
                SubtreeSchema().loads(
                    """
                    name: subtree_0
                    nodes: []
                """
                ),
                SubtreeSchema().loads(
                    """
                    name: subtree_0
                    nodes: []
                """
                ),
            ],
        )
    assert str(excinfo.value) == (
        "Duplicate subtree name 'subtree_0'\n"
        '  in "<unicode string>", line 2, column 27:\n'
        "    name: subtree_0\n"
        "          ^^^\n"
        "    nodes: []"
    )


async def test_subtree_trigger_before():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: true
              response: success
            - subtree: subtree_0
            - condition: true
              response: fail
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                nodes:
                - condition: true
                  response: fail
            """
            ),
        ],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "success"}]
    assert state == {"node_stack": []}


async def test_subtree_trigger():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: false
              response: fail
            - subtree: subtree_0
            - condition: true
              response: fail
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                guard: true
                nodes:
                - condition: true
                  response: success
            """
            ),
        ],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "success"}]
    assert state == {"node_stack": []}


async def test_subtree_default_guard():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: false
              response: fail
            - subtree: subtree_0
            - condition: true
              response: fail
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                nodes:
                - condition: true
                  response: success
            """
            ),
        ],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "success"}]
    assert state == {"node_stack": []}


async def test_subtree_trigger_after():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: false
              response: fail
            - subtree: subtree_0
            - condition: true
              response: success
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                nodes:
                - condition: false
                  response: fail
            """
            ),
        ],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "success"}]
    assert state == {"node_stack": []}


async def test_subtree_loop():
    with pytest.raises(BotError) as excinfo:
        DialogTree(
            DialogNodeSchema(many=True).loads(
                """
                - subtree: subtree_0
            """
            ),
            [
                SubtreeSchema().loads(
                    """
                    name: subtree_0
                    nodes:
                    - subtree: subtree_0
                """
                ),
            ],
        )
    assert str(excinfo.value) == (
        "Sub-tree 'subtree_0' already used\n"
        '  in "<unicode string>", line 4, column 32:\n'
        "    nodes:\n"
        "    - subtree: subtree_0\n"
        "               ^^^\n"
    )


async def test_subtree_in_subtree():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - subtree: subtree_0
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                nodes:
                - subtree: subtree_1
            """
            ),
            SubtreeSchema().loads(
                """
                name: subtree_1
                nodes:
                - condition: true
                  response: success
            """
            ),
        ],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "success"}]
    assert state == {"node_stack": []}


async def test_subtree_followup_listen():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - label: root_1
              condition: true
              response: root triggered
              followup:
              - subtree: subtree_0
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                nodes:
                - condition: true
                  response: followup triggered
            """
            ),
        ],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "root triggered"}]
    assert state == {"node_stack": [["root_1", "followup"]]}


async def test_subtree_followup_match():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - label: root_1
              condition: true
              response: root triggered
              followup:
              - subtree: subtree_0
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                nodes:
                - condition: true
                  response: followup triggered
            """
            ),
        ],
    )
    ctx, state = make_context(state={"node_stack": [["root_1", "followup"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "followup triggered"}]
    assert state == {"node_stack": []}


async def test_subtree_jump_to_listen():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: true
              response: |
                root triggered

                <jump_to node="followup_2" transition="listen" />
            - label: root_1
              condition: true
              response: fail
              followup:
              - subtree: subtree_0
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                nodes:
                - condition: true
                  response: fail
                - label: followup_2
                  condition: true
                  response: success
                - condition: true
                  response: fail
            """
            ),
        ],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "root triggered"}]
    assert state == {"node_stack": [["followup_2", "condition"]]}


async def test_subtree_jump_to_listen_match():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: true
              response: |
                root triggered

                <jump_to node="followup_2" transition="listen" />
            - label: root_1
              condition: true
              response: fail
              followup:
              - subtree: subtree_0
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                nodes:
                - condition: true
                  response: fail
                - label: followup_2
                  condition: true
                  response: success
                - condition: true
                  response: fail
            """
            ),
        ],
    )
    ctx, state = make_context(state={"node_stack": [["followup_2", "condition"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == [{"text": "success"}]
    assert state == {"node_stack": []}


async def test_subtree_jump_to_listen_mismatch_parent_subtree():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - label: root_1
              condition: false
              response: fail
              followup:
                - subtree: subtree_0
                - condition: true
                  response: fail
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                nodes:
                - label: followup_2
                  condition: false
                  response: fail
            """
            ),
        ],
    )
    ctx, state = make_context(state={"node_stack": [["followup_2", "condition"]]})
    assert await model(ctx, state) == FlowResult.DONE
    assert ctx.commands == []
    assert state == {"node_stack": []}


async def test_subtree_jump_to_listen_ignore_guard():
    model = DialogTree(
        DialogNodeSchema(many=True).loads(
            """
            - condition: true
              response: |
                root triggered

                <jump_to node="followup_2" transition="listen" />
            - label: root_1
              condition: true
              response: fail
              followup:
              - subtree: subtree_0
        """
        ),
        [
            SubtreeSchema().loads(
                """
                name: subtree_0
                guard: false
                nodes:
                - label: followup_2
                  condition: true
                  response: success
            """
            ),
        ],
    )
    ctx, state = make_context()
    assert await model(ctx, state) == FlowResult.LISTEN
    assert ctx.commands == [{"text": "root triggered"}]
    assert state == {"node_stack": [["followup_2", "condition"]]}


def test_subtree_unused(caplog):
    with caplog.at_level(logging.WARNING):
        model = DialogTree(
            DialogNodeSchema(many=True).loads(
                """
                - condition: true
                  response: triggered
            """
            ),
            [
                SubtreeSchema().loads(
                    """
                    name: subtree_0
                    nodes:
                    - condition: true
                      response: triggered
                """
                ),
            ],
        )
    assert "Unused sub-trees: subtree_0" in caplog.text
