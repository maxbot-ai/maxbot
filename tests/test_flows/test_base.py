from unittest.mock import Mock

from maxbot.flows._base import FlowComponent, FlowResult


def test_reset_state():
    ctx = Mock()
    FlowComponent("test", Mock(return_value=FlowResult.DONE))(ctx)
    ctx.set_state_variable.assert_called_once_with("test", None)
