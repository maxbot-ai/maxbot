"""Base classes for flow models."""
from dataclasses import dataclass
from enum import Enum


class FlowResult(Enum):
    """Result of the turn of the flow."""

    DIGRESS = "digress"
    LISTEN = "listen"
    DONE = "done"


class DigressionResult(Enum):
    """Result of digression."""

    FOUND = "found"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class FlowComponent:
    """Provide state to the flow model instance."""

    # Used to persist model's state.
    name: str

    # Instantiated flow model.
    flow: callable

    def __call__(self, ctx, digression_result=None):
        """Make a turn in a flow model with a state.

        :param TurnContext ctx: Context of the turn.
        :param bool digression_result: Are we returning after digression?
        :return FlowResult: The result of the turn of the flow.
        """
        state = ctx.get_state_variable(self.name) or {}
        if digression_result is None:
            result = self.flow(ctx, state)
        else:
            result = self.flow(ctx, state, digression_result)
        if result == FlowResult.DONE:
            # FXIME need to reset all the child states too
            ctx.set_state_variable(self.name, None)
        else:
            ctx.set_state_variable(self.name, state)
        return result
