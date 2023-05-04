import json

import pytest
from marshmallow import fields
from rich.console import Console

from maxbot.cli._journal import JsonLineJournal
from maxbot.cli._rich import PrettyJournal
from maxbot.context import LogRecord, RpcContext, RpcRequest, TurnContext
from maxbot.errors import BotError, YamlSnippet
from maxbot.schemas import ResourceSchema


@pytest.fixture
def console_journal():
    console = Console(force_terminal=False, soft_wrap=True)
    journal = PrettyJournal(console)

    def call(ctx):
        with console.capture() as capture:
            journal(ctx)
        return capture.get()

    return call


@pytest.fixture
def jsonl_journal(tmp_path):
    journal_file = tmp_path / "maxbot.jsonl"
    journal = JsonLineJournal(journal_file)

    def call(ctx):
        journal(ctx)
        return journal_file.read_text()

    return call


@pytest.fixture
def ctx():
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": 123}, message={"text": "hello world"}
    )
    return ctx


def test_console_basic(ctx, console_journal):
    ctx.commands.append({"text": "Good day to you!"})

    out = console_journal(ctx)

    assert "test#123" in out
    assert "hello world" in out
    assert "Good day to you!" in out


def test_console_commands_yaml(ctx, console_journal):
    ctx.commands.append({"text": "Hello, John!"})
    ctx.commands.append({"text": "It's lovely to meet you.\nHow can I help you today?"})

    out = console_journal(ctx)

    assert "- text: Hello, John!" in out
    assert "- text: |-" in out
    assert "It's lovely to meet you." in out
    assert "How can I help you today?" in out


def test_console_logs(ctx, console_journal):
    ctx.debug(("what is here?", {"xxx": "yyy"}))
    ctx.warning("something wrong")
    ctx.set_error(BotError("some error"))

    out = console_journal(ctx)

    assert "ⓘ  ('what is here?', {'xxx': 'yyy'})" in out
    assert "⚠  something wrong" in out
    assert "✗  some error" in out


def test_console_error_snippet(ctx, console_journal):
    class C(ResourceSchema):
        s = fields.String()

    data = C().loads("s: hello world")
    ctx.set_error(BotError("some error", YamlSnippet.from_data(data)))

    out = console_journal(ctx)

    assert "✗  some error" in out
    assert 'in "<unicode string>", line 1, column 1' in out
    assert "❱ 1 s: hello world" in out


def test_console_rpc(console_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": 123}, rpc=RpcContext(RpcRequest("say_hello"))
    )

    out = console_journal(ctx)

    assert "test#123" in out
    assert "method: say_hello" in out


def test_jsonl_basic(ctx, jsonl_journal):
    ctx.commands.append({"text": "Good day to you!"})

    out = jsonl_journal(ctx)

    assert (
        '"dialog": {"channel_name": "test", "user_id": 123}, '
        '"message": {"text": "hello world"}, '
        '"response": [{"text": "Good day to you!"}]}\n'
    ) in out


def test_jsonl_logs(ctx, jsonl_journal):
    ctx.debug(("what is here?", {"xxx": "yyy"}))
    ctx.warning("something wrong")
    ctx.set_error(BotError("some error"))

    out = jsonl_journal(ctx)

    assert (
        '"logs": ['
        '{"level": "DEBUG", "message": "(\'what is here?\', {\'xxx\': \'yyy\'})"}, '
        '{"level": "WARNING", "message": "something wrong"}'
        "], "
        '"error": {"message": "some error"}}\n'
    ) in out


def test_jsonl_error_snippet(ctx, jsonl_journal):
    class C(ResourceSchema):
        s = fields.String()

    data = C().loads("s: hello world")
    ctx.set_error(BotError("some error", YamlSnippet.from_data(data)))

    out = jsonl_journal(ctx)

    assert (
        '"error": {"message": "some error", "snippets": '
        '["in \\"<unicode string>\\", line 1, column 1:\\n  s: hello world\\n  ^^^\\n"]}}'
    ) in out


def test_jsonl_rpc(jsonl_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": 123}, rpc=RpcContext(RpcRequest("say_hello"))
    )

    out = jsonl_journal(ctx)

    assert (
        '"dialog": {"channel_name": "test", "user_id": 123}, '
        '"rpc": {"method": "say_hello", "params": {}}'
    ) in out
