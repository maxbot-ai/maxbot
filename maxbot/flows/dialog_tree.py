"""Dialog Tree Conversation Flow."""
import logging
from functools import cached_property

from ..errors import BotError, YamlSnippet
from ..maxml import Schema, fields, validate
from ..scenarios import ExpressionField, ScenarioField
from ..schemas import MaxmlSchema, ResourceSchema
from ._base import DigressionResult, FlowComponent, FlowResult
from .slot_filling import HandlerSchema, SlotFilling, SlotSchema

logger = logging.getLogger(__name__)


class JumpTo(Schema):
    """Jump to a different node after response is processed."""

    # A node to jump to.
    node = fields.Str(required=True)

    # Specify when the target node is processed by choosing one of the following options.
    #     * `condition` - the bot checks first whether the condition of the targeted node evaluates to true.
    #         * If the condition evaluates to true, the system processes the target node immediately.
    #         * If the condition does not evaluate to true, the system moves to the next sibling
    #         node of the target node to evaluate its condition, and repeats this process until
    #         it finds a dialog node with a condition that evaluates to true.
    #         * If the system processes all the siblings and none of the conditions evaluate to true,
    #         the bot resets its current conversation state.
    #     * `response` - the bot does not evaluate the condition of the targeted
    #     dialog node; it processes the response of the targeted dialog node immediately.
    #     * `listen` - Waits for new input from the user, and then begins to process it from the
    #     node that you jump to.
    transition = fields.Str(
        required=True, validate=validate.OneOf(["condition", "response", "listen"])
    )


class NodeCommands(MaxmlSchema):
    """Control commands for node `response` scenarios."""

    # End the conversation and reset its state.
    end = fields.Nested(Schema)

    # Wait for the user to provide new input that the response elicits.
    listen = fields.Nested(Schema)

    # Bypass waiting for user input and go directly to the first followup node of the current node instead.
    # Note: the current node must have at least one followup node for this option to be available.
    followup = fields.Nested(Schema)

    # Go directly to an entirely different dialog node.
    jump_to = fields.Nested(JumpTo)


class NodeSettings(ResourceSchema):
    """Settings that change the behavior for an individual node."""

    # For nodes that have `followup` children, when digression triggered after the node's response.
    #     * `allow_return` - allow return from digression and continue to process its `followup` nodes.
    #     * `never_return` - prevent the dialog from returning to the current node.
    after_digression_followup = fields.Str(
        validate=validate.OneOf(["allow_return", "never_return"]), load_default="allow_return"
    )


class NodeSchema(ResourceSchema):
    """Definition of the dialog tree node."""

    # Unique node label. The following nodes must have a label.
    #     * Nodes that contains slot filling or followup nodes. This kind of nodes use labels
    #     internally to store their state.
    #     * Nodes that targeted by the jump_to command. Labels are used in the jump_to arguments.
    label = fields.Str()

    # Determines whether that node is used in the conversation.
    condition = ExpressionField(required=True)

    # List of slots for the Slot Filling Flow.
    slot_filling = fields.List(fields.Nested(SlotSchema))

    # List of slot handlers for the Slot Filling Flow.
    slot_handlers = fields.List(fields.Nested(HandlerSchema))

    # Defines how to reply to the user.
    response = ScenarioField(NodeCommands, required=True)

    # List of followup nodes.
    followup = fields.List(fields.Nested(lambda: DialogNodeSchema()))  # pylint: disable=W0108

    # Node settings.
    settings = fields.Nested(NodeSettings, load_default=NodeSettings().load({}))


class SubtreeRefSchema(ResourceSchema):
    """Definition of the subtree link."""

    # Link to subtree
    subtree = fields.Str(required=True)


class DialogNodeSchema(ResourceSchema):
    """Definition of the dialog tree node: real node or subtree link."""

    def load(self, data, *, many=None, **kwargs):
        """Load data: select NodeSchema or SubtreeRefSchema by required fields."""
        many = self.many if many is None else bool(many)
        if many:
            try:
                result = [self._load_one(i, **kwargs) for i in data]
            except BotError as error:
                if not error.snippets:
                    snippet = YamlSnippet.from_data(data)
                    if snippet:
                        error.snippets.append(snippet)
                raise
        else:
            result = self._load_one(data, **kwargs)
        return result

    def _load_one(self, data, **kwargs):
        if not isinstance(data, dict):
            raise BotError("Invalid input type", YamlSnippet.from_data(data))
        for schema in (NodeSchema(), SubtreeRefSchema()):
            for field_name in [n for n, t in schema.declared_fields.items() if t.required]:
                if field_name not in data:
                    break
            else:
                schema.context.update(getattr(self, "context", {}))
                return schema.load(data, many=False, **kwargs)
        raise BotError("Unknown node type", YamlSnippet.from_data(data))


class SubtreeSchema(ResourceSchema):
    """Definition of the dialog sub-tree."""

    # Unique subtree name
    name = fields.Str(required=True)

    # Determines whether that subtree is used in the conversation.
    guard = ExpressionField()

    # Nodes of subtree
    nodes = fields.List(fields.Nested(DialogNodeSchema), required=True)


class NodeStack:
    """Internal state that holds the current and digressed nodes."""

    def __init__(self, stack, tree):
        """Create new class instance.

        :param list stack: Reference to the underlying state variable.
        :param Tree tree: A tree used to access node objects.
        """
        self.stack = stack
        self.tree = tree

    def gc(self):
        """Get rid of nodes that was removed from tree."""
        for label, transition in self.stack[:]:  # pylint: disable=consider-using-any-or-all
            if label not in self.tree.catalog:
                self.stack.remove([label, transition])

    def push(self, node, transition):
        """Push node into the stask.

        Remove other occurences of the node from the stack.

        :param Node node: A node to push into the stack.
        :param str transition: Node transition.
        """
        self.remove(node)
        self.stack.append([node.label, transition])

    def pop(self):
        """Remove and return node from stack.

        :return tuple[Node, str]: A node and its transition.
        """
        if self.stack:
            label, transition = self.stack.pop()
            return self.tree.catalog[label], transition
        return None, None

    def peek(self):
        """Return a node from the top of the stack.

        :return tuple[Node, str]: A node and its transition.
        """
        if self.stack:
            label, transition = self.stack[-1]
            return self.tree.catalog[label], transition
        return None, None

    def remove(self, node):
        """Remove node from the stack.

        :return bool: Was the node found on the stack?
        """
        label = node.label
        found = False
        for label, transition in self.stack[:]:  # pylint: disable=consider-using-any-or-all
            if label == node.label:
                self.stack.remove([label, transition])
                found = True
        return found

    def clear(self):
        """Clear the stack."""
        self.stack.clear()


class DialogTree:
    """Dialog tree conversational flow."""

    def __init__(self, definition, subtrees=None):
        """Create new class instance.

        :param dict definition: Specification of the tree.
        :param list subtrees: Subtree specifications.
        """
        self.tree = Tree(definition, subtrees or [])

    async def __call__(self, ctx, state):
        """Make a turn in a dialog tree flow.

        :param TurnContext ctx: Context of the turn.
        :param dict state: State of the flow model.
        :return FlowResult: The result of the turn of the flow.
        """
        stack = NodeStack(state.setdefault("node_stack", []), self.tree)
        stack.gc()
        turn = Turn(self.tree, stack, ctx)
        return await turn()


class Turn:
    """A turn of the dialog tree flow."""

    def __init__(self, tree, stack, ctx):
        """Create new class instance.

        :param Tree tree: A tree of nodes.
        :param NodeStack stack: A stack of current and digressed nodes.
        :param TurnContext ctx: Context of the turn.
        """
        self.tree = tree
        self.stack = stack
        self.ctx = ctx

    async def __call__(self):
        """Make a turn in a dialog tree flow.

        :return FlowResult: The result of the turn of the flow.
        """
        node, transition = self.stack.peek()
        if node:
            logger.debug("peek %s transition=%s", node, transition)
            if transition == "followup":
                return await self.focus_followup(node)
            if transition == "slot_filling":
                return await self.trigger(node)
            if transition == "condition":
                return await self.focus_condition(node)
            raise ValueError(f"Unknown focus transition {transition!r}")
        return await self.root_nodes()

    async def root_nodes(self):
        """Traverse the root nodes of the tree.

        :return FlowResult: The result of the turn of the flow.
        """
        for node in self.tree.root_nodes(self.ctx):
            if node.condition(self.ctx):
                return await self.trigger(node)
        return FlowResult.DONE

    async def focus_condition(self, focused_node):
        """Traverse node and right siblings after receiving user input.

        :return FlowResult: The result of the turn of the flow.
        """
        for node in focused_node.me_and_right_siblings(self.ctx):
            if node.condition(self.ctx):
                self.stack.remove(focused_node)
                return await self.trigger(node)
        if focused_node.parent:
            return await self.digression(focused_node)
        logger.warning("No node matched %s", focused_node)
        return await self.return_after_digression() or self.command_end()

    async def focus_followup(self, parent_node):
        """Traverse followup nodes after receiving user input.

        :return FlowResult: The result of the turn of the flow.
        """
        for node in parent_node.followup(self.ctx):
            if node.condition(self.ctx):
                self.stack.remove(parent_node)
                return await self.trigger(node)
        return await self.digression(parent_node)

    async def command_followup(self, parent_node):
        """Traverse followup nodes without waiting for user input.

        :param Node parent_node: Node containing followup children.
        :return FlowResult: The result of the turn of the flow.
        """
        logger.debug("followup %s", parent_node)
        for node in parent_node.followup(self.ctx):
            if node.condition(self.ctx):
                return await self.trigger_maybe_digressed(node)
        self.ctx.warning(f"Nothing matched from followup nodes of {parent_node!r}.")
        return FlowResult.LISTEN

    async def command_listen(self, node):
        """Wait for the user to provide new input.

        If the given node contains followup children, the new user input will be processed by them.

        :param Node node: Node to check for followup children.
        :return FlowResult: The result of the turn of the flow.
        """
        if node.followup:
            self.stack.push(node, "followup")
            return FlowResult.LISTEN
        return await self.return_after_digression() or FlowResult.LISTEN

    def command_end(self):
        """End the conversation and reset its state.

        :return FlowResult: The result of the turn of the flow.
        """
        self.stack.clear()
        return FlowResult.DONE

    async def command_jump_to(self, from_node, payload):
        """Go directly to an entirely different dialog node.

        :param Node from_node: Node to jump from.
        :param dict payload: Payload of jump_to command.
        :raise BotError: Unknown node or transition.
        :return FlowResult: The result of the turn of the flow.
        """
        logger.debug("jump_to %s", payload)
        jump_to_node = self.tree.catalog.get(payload["node"])
        if jump_to_node is None:
            raise BotError(f"Unknown jump_to node {payload['node']!r}")
        if payload["transition"] == "response":
            return await self.trigger_maybe_digressed(jump_to_node)
        if payload["transition"] == "condition":
            return await self.jump_to_condition(jump_to_node)
        if payload["transition"] == "listen":
            return await self.jump_to_listen(jump_to_node)
        raise BotError(f"Unknown jump_to transition {payload['transition']!r}")

    async def jump_to_condition(self, jump_to_node):
        """Jump to a different node evaluating conditions.

        :param Node jump_to_node: Node to jump to.
        :return FlowResult: The result of the turn of the flow.
        """
        for node in jump_to_node.me_and_right_siblings(self.ctx):
            if node.condition(self.ctx):
                return await self.trigger_maybe_digressed(node)
        self.ctx.warning(f"Nothing matched when jumping to {jump_to_node!r} and its siblings.")
        return await self.return_after_digression() or self.command_end()

    async def jump_to_listen(self, jump_to_node):
        """Jump to a different node and waiting for user input.

        :return FlowResult: The result of the turn of the flow.
        """
        self.stack.push(jump_to_node, "condition")
        return FlowResult.LISTEN

    async def digression(self, digressed_node):
        """Switch to a completely different user-initiated node.

        :param Node digressed_node: Node to switch from.
        :return FlowResult: The result of the turn of the flow.
        """
        logger.debug("digression from %s", digressed_node)
        for node in self.tree.root_nodes(self.ctx):
            if node == digressed_node:
                continue
            if node.condition(self.ctx, digressing=True):
                return await self.trigger_maybe_digressed(node)
        if self.ctx.rpc:
            return FlowResult.LISTEN
        if digressed_node.followup_allow_return:
            return (
                await self.return_after_digression(DigressionResult.NOT_FOUND)
                or self.command_end()
            )
        return self.command_end()

    async def return_after_digression(self, result=DigressionResult.FOUND):
        """Return to the dialog node that was interrupted when the digression occurred.

        :param DigressionResult result: The result with which we return from digression.
        :return FlowResult: The result of the turn of the flow.
        """
        node, transition = self.stack.pop()
        if node:
            logger.debug("return_after_digression %s %s", node, transition)
            if transition == "slot_filling":
                return await self.trigger(node, result)
            if transition == "followup":
                if node.followup_allow_return:
                    return await self.trigger(node, result)
                return await self.return_after_digression(result)
            if transition == "condition":
                return await self.return_after_digression(result)
            raise ValueError(f"Unknown focus transition {transition!r}")
        # nowere to return
        return None

    async def trigger_maybe_digressed(self, node):
        """Trigger the node or return to the node after digression.

        :param Node node: Triggered node.
        :return FlowResult: The result of the turn of the flow.
        """
        if self.stack.remove(node):
            return await self.trigger(node, DigressionResult.FOUND)
        return await self.trigger(node)

    async def trigger(self, node, digression_result=None):
        """Go through the node's slot filling flow (if any) and/or execute its response scenario.

        :param Node node: Triggered node.
        :param DigressionResult digression_result: The result with which we return from digression.
        :raise ValueError: Unknown slot filling result.
        :return FlowResult: The result of the turn of the flow.
        """
        self.journal_event("node_triggered", node)
        if node.slot_filling:
            result = await node.slot_filling(self.ctx, digression_result)
            if result == FlowResult.DONE:
                self.stack.remove(node)
                return await self.response(node, digression_result)
            if result == FlowResult.LISTEN:
                self.stack.push(node, "slot_filling")
                return FlowResult.LISTEN
            if result == FlowResult.DIGRESS:
                return await self.digression(node)
            raise ValueError(f"Unknown flow result {result!r}")
        return await self.response(node, digression_result)

    async def response(self, node, digression_result):
        """Execute the response scenario of the node.

        :param Node node: Triggered node.
        :param DigressionResult digression_result: The result with which we return from digression.
        :return FlowResult: The result of the turn of the flow.
        """
        payload = self.journal_event("response", node)
        for command in await node.response(self.ctx, returning=digression_result is not None):
            if "jump_to" in command:
                payload.update(control_command="jump_to")
                return await self.command_jump_to(node, command["jump_to"])
            if "listen" in command:
                payload.update(control_command="listen")
                return await self.command_listen(node)
            if "end" in command:
                payload.update(control_command="end")
                return self.command_end()
            if "followup" in command:
                payload.update(control_command="followup")
                return await self.command_followup(node)
            self.ctx.commands.append(command)
        if node.followup:
            payload.update(followup={})
            return await self.command_listen(node)
        result = await self.return_after_digression()
        if result:
            payload.update(return_after_digression={})
        else:
            payload.update(end={})
            result = self.command_end()
        return result

    def journal_event(self, event_type, node, payload=None):
        """Add journal event.

        :param str event_type: Type of the event.
        :param Node node: Traget node.
        :param dict payload: Additional payload (optinal).
        """
        payload = payload or {}
        payload["node"] = {"condition": node.condition.source}
        if node.label:
            payload["node"].update(label=node.label)
        return self.ctx.journal_event(event_type, payload)


class Tree:
    """A tree of nodes."""

    def __init__(self, definition, subtrees):
        """Create new class instance.

        :param list definition: Specification of the tree.
        :param list subtrees: Specification of the subtree.
        """
        self.catalog = {}

        self._subtree_map = {}
        for s in subtrees:
            if s["name"] in self._subtree_map:
                raise BotError(
                    f"Duplicate subtree name {s['name']!r}",
                    YamlSnippet.from_data(s["name"]),
                )
            self._subtree_map[s["name"]] = s

        self.root_nodes = self.create_branch(definition)

        unused_subtree = [name for name, d in self._subtree_map.items() if d]
        if unused_subtree:
            logger.warning("Unused sub-trees: %s", ", ".join(unused_subtree))
        self._subtree_map = None

    def create_branch(self, definition, parent=None):
        """Create tree branch: enumeration of nodes and subtrees.

        :param list definition: Specification of the tree.
        :param Node parent: The parent for the node being created.
        :return Branch
        """
        items = [
            self.create_subtree(d, parent) if "subtree" in d else self.create_node(d, parent)
            for d in definition
        ]
        for i in items:
            if isinstance(i, Node):
                i.siblings = items
        return Branch(items)

    def create_subtree(self, definition, parent=None):
        """Create subtree by definition.

        :param dict definition: Specification of the subtree.
        :param Node parent: The parent for the node being created.
        :raise BotError: Subtree is already used or not found.
        :return Subtree:
        """
        if definition["subtree"] not in self._subtree_map:
            raise BotError(
                f"Sub-tree {definition['subtree']!r} not found",
                YamlSnippet.from_data(definition["subtree"]),
            )

        subtree_definition = self._subtree_map[definition["subtree"]]
        if subtree_definition is None:  # check "used" flag
            raise BotError(
                f"Sub-tree {definition['subtree']!r} already used",
                YamlSnippet.from_data(definition["subtree"]),
            )
        self._subtree_map[definition["subtree"]] = None  # mark as "used"

        return Subtree(subtree_definition, self, parent)

    def create_node(self, definition, parent=None):
        """Create tree node or sub-tree object.

        :param dict definition: Specification of the node.
        :param Node parent: The parent for the node being created.
        :raise BotError: Missing or duplicating label.
        :return Node:
        """
        if "label" not in definition and (
            "followup" in definition or "slot_filling" in definition
        ):
            raise BotError("Stateful node must have a label", YamlSnippet.from_data(definition))
        node = Node(definition, self, parent)
        if "label" in definition:
            if definition["label"] in self.catalog:
                raise BotError(
                    f"Duplicate node label {definition['label']!r}",
                    YamlSnippet.from_data(definition["label"]),
                )
            self.catalog[definition["label"]] = node
        return node


class Node:
    """Node of the dialog tree."""

    def __init__(self, definition, tree, parent):
        """Create tree node.

        :param dict definition: Specification of the node.
        :param Tree tree: A tree of nodes.
        :param Node parent: The parent for the node being created.
        :return Node:
        """
        self.label = definition.get("label")
        self.definition = definition
        self.siblings = []
        self.parent = parent
        self.tree = tree
        self.condition = definition["condition"]
        self.response = definition["response"]
        self.followup = tree.create_branch(definition.get("followup", []), self)
        self.slot_filling = None
        if "slot_filling" in definition:
            self.slot_filling = FlowComponent(
                definition["label"],
                SlotFilling(
                    definition["slot_filling"],
                    definition.get("slot_handlers", []),
                ),
            )

    @cached_property
    def me_and_right_siblings(self):
        """Get the node itself and its next siblings on the tree.

        :return list[Node]: A list of nodes.
        """
        index = self.siblings.index(self)
        return Branch(self.siblings[index:])

    @cached_property
    def followup_allow_return(self):
        """Check that return is allowed from digression triggered after the node's response.

        :raise ValueError: Invalid policy value.
        :return bool: `True` - return is allowed, `False` - otherwise.
        """
        policy = self.definition["settings"]["after_digression_followup"]
        if policy == "allow_return":
            return True
        if policy == "never_return":
            return False
        raise ValueError(f"Unknown returning policy {policy!r}")

    @cached_property
    def title(self):
        """Human readable unique title of the node.

        :return str:
        """
        if self.label:
            return f"{self.label!r}"
        if self.parent:
            return f'{self.parent.title} -> {self.definition["condition"]!r}'
        return f'{self.definition["condition"]!r}'

    def __str__(self):
        """Human readable unique title of the node.

        :return str:
        """
        return self.title

    def __repr__(self):
        """Human readable unique title of the node.

        :return str:
        """
        return self.title


class Subtree:
    """Sub-tree of dialog three."""

    def __init__(self, definition, tree, parent):
        """Create sub-tree tree object.

        :param dict definition: Specification of subtree.
        :param Tree tree: A tree of nodes.
        :param Node parent: The parent for the node being created.
        :return Subtree:
        """
        self.guard = definition.get("guard", lambda ctx: True)
        self.nodes = tree.create_branch(definition["nodes"], parent)


class Branch:
    """Dialog tree branch."""

    def __init__(self, items):
        """Create branch of dialog tree.

        :param list items: List of Node and Subtree items.
        :return Branch:
        """
        self.items = items

    def __bool__(self):
        """Check branch is empty."""
        return bool(self.items)

    def __call__(self, ctx):
        """Enumerate nodes of branch.

        :param TurnContext ctx: Context of the turn.
        :return Node:
        """
        for i in self.items:
            if isinstance(i, Node):
                yield i
            else:
                assert isinstance(i, Subtree)
                if i.guard(ctx):
                    for n in i.nodes(ctx):
                        yield n
