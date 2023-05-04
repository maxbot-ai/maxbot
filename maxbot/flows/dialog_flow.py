"""MaxBot dialog."""
import logging

from ..errors import BotError
from ..resources import InlineResources
from ._base import FlowComponent, FlowResult
from .dialog_tree import DialogNodeSchema, DialogTree, SubtreeSchema

logger = logging.getLogger(__name__)


class DialogFlow:
    """The flow of the conversation."""

    def __init__(self, before_turn=None, after_turn=None, context=None):
        """Create new class instance.

        :param List[callable] before_turn: Functions to call before each dialog turn.
        :param List[callable] after_turn: Functions to call after each dialog turn.
        :param dict context: Context for scenarios.
        """
        self._context = context or {}
        self._before_turn_hooks = before_turn or []
        self._after_turn_hooks = after_turn or []
        self._root_component = None

    def load_resources(self, resources):
        """Load flow resources.

        :param Resources resources: Bot resources.
        """
        self._root_component = FlowComponent(
            "ROOT",
            DialogTree(
                resources.load_dialog(DialogNodeSchema(many=True, context=self._context)),
                resources.load_dialog_subtrees(SubtreeSchema(context=self._context)),
            ),
        )

    def load_inline_resources(self, source):
        """Load dialog resources from YAML-string.

        :param str source: A YAML-string with resources.
        """
        self.load_resources(InlineResources(source))

    async def turn(self, ctx):
        """Perform one step of the dialog."""
        # TODO: check root component before
        for func in self._before_turn_hooks:
            await func(ctx=ctx)

        try:
            result = await self._root_component(ctx)
        except BotError as exc:
            ctx.set_error(exc)
            result = FlowResult.DONE

        if result == FlowResult.DONE:
            ctx.clear_state_variables()

        for func in self._after_turn_hooks:
            await func(ctx=ctx, listening=result == FlowResult.LISTEN)
