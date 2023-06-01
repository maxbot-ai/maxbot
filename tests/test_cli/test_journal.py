import os

import pytest

from maxbot.cli._journal import Dumper, FileJournal, JournalChain
from maxbot.context import (
    EntitiesResult,
    IntentsResult,
    RecognizedEntity,
    RecognizedIntent,
    RpcContext,
    RpcRequest,
    TurnContext,
)
from maxbot.errors import BotError, YamlSnippet
from maxbot.maxml import fields, markup
from maxbot.schemas import CommandSchema, ResourceSchema


@pytest.fixture
def jsonl_journal(tmp_path):
    yield from _file_journal(tmp_path, Dumper.json_line)


@pytest.fixture
def yaml_journal(tmp_path):
    yield from _file_journal(tmp_path, Dumper.yaml_triple_dash)


@pytest.fixture
def ctx():
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "123"},
        message={"text": "hello world"},
        command_schema=CommandSchema(many=True),
    )
    return ctx


def test_jsonl_basic(ctx, jsonl_journal):
    ctx.commands.append({"text": markup.Value([markup.Item(markup.TEXT, "Good day to you!")])})

    out = jsonl_journal(ctx)

    assert '"dialog": {"channel_name": "test", "user_id": "123"}' in out, out
    assert '"message": {"text": "hello world"}, ' in out, out
    assert '"response": "<text>Good day to you!</text>"' in out, out


def test_yaml_basic(ctx, yaml_journal):
    ctx.commands.append({"text": markup.Value([markup.Item(markup.TEXT, "Good day to you!")])})

    out = yaml_journal(ctx)

    assert "dialog:" in out, out
    assert "  channel_name: test" in out, out
    assert "  user_id: '123'" in out, out
    assert "message:" in out, out
    assert "  text: hello world" in out, out
    assert "response: <text>Good day to you!</text>" in out, out


def test_jsonl_intents(jsonl_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "123"},
        message={"text": "hello world"},
        intents=IntentsResult.resolve(
            [RecognizedIntent("i1", 0.98), RecognizedIntent("i2", 0.97)]
        ),
    )

    out = jsonl_journal(ctx)

    assert (
        '"intents": {"top": {"name": "i1", "confidence": 0.98}, '
        '"ranking": [{"name": "i1", "confidence": 0.98}, '
        '{"name": "i2", "confidence": 0.97}]}'
    ) in out


def test_yaml_intents(yaml_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "123"},
        message={"text": "hello world"},
        intents=IntentsResult.resolve(
            [RecognizedIntent("i1", 0.98), RecognizedIntent("i2", 0.97)]
        ),
    )

    out = yaml_journal(ctx)
    assert (
        "intents:\n"
        "  top:\n"
        "    name: i1\n"
        "    confidence: 0.98\n"
        "  ranking:\n"
        "  - name: i1\n"
        "    confidence: 0.98\n"
        "  - name: i2\n"
        "    confidence: 0.97"
    ) in out


def test_jsonl_intents_irrelevant(ctx, jsonl_journal):
    out = jsonl_journal(ctx)

    assert '"intents": {"top": null, "ranking": []}' in out


def test_yaml_intents_irrelevant(ctx, yaml_journal):
    out = yaml_journal(ctx)

    assert ("intents:\n" "  top: null\n" "  ranking: []") in out


def test_jsonl_entities(jsonl_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "123"},
        message={"text": "hello world"},
        entities=EntitiesResult.resolve(
            [
                RecognizedEntity("e1", "v1", "xx", 1, 11),
                RecognizedEntity("e2", "v2", "yy", 2, 22),
            ]
        ),
    )

    out = jsonl_journal(ctx)

    assert (
        '"entities": ['
        '{"name": "e1", "value": "v1", "literal": "xx", "start_char": 1, "end_char": 11}, '
        '{"name": "e2", "value": "v2", "literal": "yy", "start_char": 2, "end_char": 22}],'
    ) in out


def test_yaml_entities(yaml_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "123"},
        message={"text": "hello world"},
        entities=EntitiesResult.resolve(
            [
                RecognizedEntity("e1", "v1", "xx", 1, 11),
                RecognizedEntity("e2", "v2", "yy", 2, 22),
            ]
        ),
    )

    out = yaml_journal(ctx)

    assert (
        "entities:\n"
        "- name: e1\n"
        "  value: v1\n"
        "  literal: xx\n"
        "  start_char: 1\n"
        "  end_char: 11\n"
        "- name: e2\n"
        "  value: v2\n"
        "  literal: yy\n"
        "  start_char: 2\n"
        "  end_char: 22\n"
    ) in out


def test_jsonl_entities_value_int(jsonl_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "123"},
        message={"text": "hello world"},
        entities=EntitiesResult.resolve(
            [
                RecognizedEntity("e1", 1, "one", 2, 34),
            ]
        ),
    )

    out = jsonl_journal(ctx)

    assert (
        '"entities": '
        '[{"name": "e1", "value": 1, "literal": "one", "start_char": 2, "end_char": 34}]'
    ) in out


def test_yaml_entities_value_int(yaml_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "123"},
        message={"text": "hello world"},
        entities=EntitiesResult.resolve(
            [
                RecognizedEntity("e1", 1, "one", 2, 34),
            ]
        ),
    )

    out = yaml_journal(ctx)

    assert (
        "entities:\n"
        "- name: e1\n"
        "  value: 1\n"
        "  literal: one\n"
        "  start_char: 2\n"
        "  end_char: 34\n"
    ) in out


def test_json_entities_empty(ctx, jsonl_journal):
    out = jsonl_journal(ctx)

    assert '"entities": []' in out


def test_yaml_entities_empty(ctx, yaml_journal):
    out = yaml_journal(ctx)

    assert "entities: []" in out


def test_jsonl_logs(ctx, jsonl_journal):
    ctx.debug(("what is here?", {"xxx": "yyy"}))
    ctx.warning("something wrong")
    ctx.set_error(BotError("some error"))

    out = jsonl_journal(ctx)

    assert (
        '"events": ['
        '{"type": "log", "payload": {"level": "DEBUG", "message": ["what is here?", {"xxx": "yyy"}]}}, '
        '{"type": "log", "payload": {"level": "WARNING", "message": "something wrong"}}], '
        '"message": {"text": "hello world"}, "error": {"message": "some error"}}'
    ) in out


def test_yaml_logs(ctx, yaml_journal):
    ctx.debug(("what is here?", {"xxx": "yyy"}))
    ctx.warning("something wrong")
    ctx.set_error(BotError("some error"))

    out = yaml_journal(ctx)

    assert (
        "events:\n"
        "- type: log\n"
        "  payload:\n"
        "    level: DEBUG\n"
        "    message:\n"
        "    - what is here?\n"
        "    - xxx: yyy\n"
        "- type: log\n"
        "  payload:\n"
        "    level: WARNING\n"
        "    message: something wrong\n"
        "message:\n"
        "  text: hello world\n"
        "error:\n"
        "  message: some error"
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


def test_yaml_error_snippet(ctx, yaml_journal):
    class C(ResourceSchema):
        s = fields.String()

    data = C().loads("s: hello world")
    ctx.set_error(BotError("some error", YamlSnippet.from_data(data)))

    out = yaml_journal(ctx)

    assert (
        "error:\n"
        "  message: some error\n"
        "  snippets:\n"
        "  - |\n"
        '    in "<unicode string>", line 1, column 1:\n'
        "      s: hello world\n"
        "      ^^^\n"
    ) in out


def test_jsonl_rpc(jsonl_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "123"}, rpc=RpcContext(RpcRequest("say_hello"))
    )

    out = jsonl_journal(ctx)

    assert '"dialog": {"channel_name": "test", "user_id": "123"}' in out
    assert '"rpc": {"method": "say_hello", "params": {}}' in out


def test_yaml_rpc(yaml_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "123"}, rpc=RpcContext(RpcRequest("say_hello"))
    )

    out = yaml_journal(ctx)

    assert ("dialog:\n" "  channel_name: test\n" "  user_id: '123'") in out
    assert ("rpc:\n" "  method: say_hello\n" "  params: {}") in out


def test_jsonl_sep(ctx, jsonl_journal):
    out = jsonl_journal(ctx)

    assert out.endswith(os.linesep)


def test_yaml_sep(ctx, yaml_journal):
    out = yaml_journal(ctx)

    assert out.endswith("---" + os.linesep)


class Value:
    pass


def test_jsonl_journal_events(ctx, jsonl_journal):
    value = Value()
    ctx.journal_event("event1", None)
    ctx.journal_event("test", value)
    ctx.journal_event("event1", {"1": 1})

    out = jsonl_journal(ctx)

    assert (
        '"events": [{"type": "event1", "payload": null}, '
        '{"type": "test", "payload": "' + repr(value) + '"}, '
        '{"type": "event1", "payload": {"1": 1}}]'
    ) in out, out


def test_yaml_journal_events(ctx, yaml_journal):
    value = Value()
    ctx.journal_event("event1", None)
    ctx.journal_event("test", value)
    ctx.journal_event("event1", {"1": 1})

    out = yaml_journal(ctx)

    assert (
        "events:\n"
        "- type: event1\n"
        "  payload: null\n"
        "- type: test\n"
        f"  payload: {value!r}\n"
        "- type: event1\n"
        "  payload:\n"
        "    '1': 1\n"
    ) in out, out


def test_journal_chain():
    history = []
    journal = JournalChain([lambda ctx: history.append(1), lambda ctx: history.append(2)])
    journal(ctx=None)
    assert history == [1, 2]


def _file_journal(tmp_path, dumps):
    journal_file = tmp_path / "maxbot.journal"
    with journal_file.open("a") as f:
        journal = FileJournal(f, dumps)

        def call(ctx):
            journal(ctx)
            return journal_file.read_text()

        yield call
