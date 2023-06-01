import datetime
import logging
from unittest.mock import AsyncMock, Mock

import pytest

from maxbot.context import (
    EntitiesResult,
    IntentsResult,
    RecognizedEntity,
    RecognizedIntent,
    RpcRequest,
    StateVariables,
    TurnContext,
)
from maxbot.dialog_manager import DialogManager
from maxbot.errors import BotError
from maxbot.maxml import Schema, fields
from maxbot.resources import Resources
from maxbot.schemas import CommandSchema, MessageSchema


async def test_process_message(dialog_stub, state_stub):
    dm = DialogManager()
    dm.load_inline_resources(
        """
        intents:
          - name: say_hello
            examples:
              - do it
        dialog:
          - condition: intents.say_hello
            response: Hello world!
    """
    )
    (command,) = await dm.process_message("do it!", dialog_stub, state_stub)
    assert command == {"text": "Hello world!"}


async def test_process_message_not_reeady(dialog_stub, state_stub, caplog):
    dm = DialogManager()
    with caplog.at_level(logging.WARNING):
        assert [] == await dm.process_message("hey bot", dialog_stub, state_stub)
    assert (
        "The dialog is not ready, messages is skipped until you load the resources." in caplog.text
    )


async def test_process_rpc(dialog_stub, state_stub):
    dm = DialogManager()
    dm.load_inline_resources(
        """
        rpc:
          - method: say_hello
        dialog:
          - condition: rpc.say_hello
            response: Hello world!
    """
    )
    (command,) = await dm.process_rpc({"method": "say_hello"}, dialog_stub, state_stub)
    assert command == {"text": "Hello world!"}


async def test_process_rpc_not_reeady(dialog_stub, state_stub, caplog):
    dm = DialogManager()
    with caplog.at_level(logging.WARNING):
        assert [] == await dm.process_rpc({"method": "say_hello"}, dialog_stub, state_stub)
    assert (
        "The dialog is not ready, rpc requests is skipped until you load the resources."
        in caplog.text
    )


async def test_invalid_dialog(dialog_stub, state_stub):
    dm = DialogManager()
    dm.load_inline_resources(
        """
        dialog:
          - condition: true
            response: Hello world!
    """
    )
    del dialog_stub["user_id"]

    with pytest.raises(BotError) as excinfo:
        await dm.process_message("hey bot", dialog_stub, state_stub)
    assert "Missing required field 'user_id'." in excinfo.value.message


async def test_custom_message(dialog_stub, state_stub):
    class CustomSchema(Schema):
        f = fields.Str()

    dm = DialogManager(
        message_schema=MessageSchema.from_dict({"custom": fields.Nested(CustomSchema)})
    )
    dm.load_inline_resources(
        """
        dialog:
          - condition: message.custom.f == 'xxx'
            response: hello world
    """
    )
    (command,) = await dm.process_message({"custom": {"f": "xxx"}}, dialog_stub, state_stub)
    assert command == {"text": "hello world"}


async def test_invalid_message(dialog_stub, state_stub):
    dm = DialogManager()
    dm.load_inline_resources(
        """
        dialog:
          - condition: true
            response: Hello world!
    """
    )
    with pytest.raises(BotError) as excinfo:
        await dm.process_message({"custom": {"f": "xxx"}}, dialog_stub, state_stub)
    assert "Unknown field 'custom'" in excinfo.value.message


async def test_custom_command(dialog_stub, state_stub):
    class CustomSchema(Schema):
        f = fields.Str()

    dm = DialogManager(
        command_schema=CommandSchema.from_dict({"custom": fields.Nested(CustomSchema)})
    )
    dm.load_inline_resources(
        """
        dialog:
          - condition: true
            response: <custom f="xxx" />
    """
    )
    (command,) = await dm.process_message("hey bot", dialog_stub, state_stub)
    assert command == {"custom": {"f": "xxx"}}


async def test_invalid_command_on_reload(dialog_stub, state_stub, caplog):
    dm = DialogManager()
    dm.load_inline_resources(
        """
        dialog:
          - condition: true
            response: Hello world!
    """
    )
    (command,) = await dm.process_message("do it!", dialog_stub, state_stub)
    assert command == {"text": "Hello world!"}

    with pytest.raises(BotError) as excinfo:
        dm.load_inline_resources(
            """
            dialog:
             - condition: true
               response: []
        """
        )
    with caplog.at_level(logging.WARNING):
        assert [] == await dm.process_message("hey bot", dialog_stub, state_stub)
    assert (
        "The dialog is not ready, messages is skipped until you load the resources." in caplog.text
    )


async def test_default_journal_debug(dialog_stub, state_stub, caplog):
    dm = DialogManager()
    dm.load_inline_resources(
        """
        dialog:
         - condition: true
           response: |
               {% debug "hello world!" %}
    """
    )
    with caplog.at_level(logging.DEBUG):
        await dm.process_message("hey bot", dialog_stub, state_stub)
    assert ("maxbot.journal", logging.DEBUG, "hello world!") in caplog.record_tuples


async def test_default_journal_error(dialog_stub, state_stub):
    dm = DialogManager()
    dm.load_inline_resources(
        """
        dialog:
         - condition: true
           response: |
            {{ XXX }}
    """
    )
    with pytest.raises(BotError) as excinfo:
        await dm.process_message("hey bot", dialog_stub, state_stub)
    assert "'XXX' is undefined" in excinfo.value.message


async def test_journal_debug(dialog_stub, state_stub):
    hook = Mock()

    dm = DialogManager()
    dm.journal(hook)
    dm.load_inline_resources(
        """
        dialog:
         - condition: true
           response: |
               {% debug "hello world!" %}
    """
    )
    await dm.process_message("hey bot", dialog_stub, state_stub)
    assert hook.called
    (ctx,) = hook.call_args.args
    assert {
        "type": "log",
        "payload": {"level": "DEBUG", "message": "hello world!"},
    } in ctx.journal_events


async def test_journal_error(dialog_stub, state_stub):
    hook = Mock()

    dm = DialogManager()
    dm.journal(hook)
    dm.load_inline_resources(
        """
        dialog:
         - condition: true
           response: |
            {{ XXX }}
    """
    )
    await dm.process_message("hey bot", dialog_stub, state_stub)
    assert hook.called
    (ctx,) = hook.call_args.args
    assert "'XXX' is undefined" in ctx.error.message


async def test_load_resources(dialog_stub, state_stub):
    dm = DialogManager(dialog_flow=Mock(), nlu=Mock(), rpc=Mock())
    resources = Mock(Resources)
    dm.load_resources(resources)
    dm.nlu.load_resources.assert_called_with(resources)
    dm.dialog_flow.load_resources.assert_called_with(resources)
    dm.rpc.load_resources.assert_called_with(resources)


async def test_nlu_recognize(dialog_stub, state_stub):
    dm = DialogManager(
        nlu=AsyncMock(
            return_value=(IntentsResult(), EntitiesResult()),
            load_resources=Mock(),  # mock the nlu.load method with is not async
        ),
    )
    utc_time = datetime.datetime.now(datetime.timezone.utc)
    dm.utc_time_provider = lambda: utc_time
    dm.load_inline_resources(
        """
        dialog:
          - condition: true
            response: Hello world!
    """
    )
    (command,) = await dm.process_message("hey bot", dialog_stub, state_stub)
    assert command == {"text": "Hello world!"}
    dm.nlu.assert_awaited_once_with({"text": "hey bot"}, utc_time=utc_time)
