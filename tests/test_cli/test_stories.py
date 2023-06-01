from datetime import datetime, timezone
from pathlib import Path

import pytest

import maxbot.cli.stories
from maxbot.builder import BotBuilder
from maxbot.cli import main
from maxbot.errors import BotError
from maxbot.maxml import markup


def test_minimal(runner, tmp_path):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text("{}")

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text("[]")

    result = runner.invoke(main, ["stories", "--bot", bot_file], catch_exceptions=False)
    assert result.exit_code == 0, result.output


def test_minimal_explicit(runner, tmp_path):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text("{}")

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text("[]")

    result = runner.invoke(
        main, ["stories", "--bot", tmp_path, "--stories", stories_file], catch_exceptions=False
    )
    assert result.exit_code == 0, result.output


def _iter_examples():
    for dir_path in (Path(__file__).parents[2] / "examples").iterdir():
        if dir_path.is_dir():
            if (dir_path / "stories.yaml").is_file():
                if (dir_path / "bot.yaml").is_file():
                    yield str(dir_path)


@pytest.mark.parametrize("project_dir", tuple(_iter_examples()))
def test_examples(runner, project_dir):
    result = runner.invoke(main, ["stories", "--bot", project_dir], catch_exceptions=False)
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    "utc_time", ("2023-04-10T19:15:58.104144", "2023-04-10T18:15:58.104144-01:00")
)
def test_utc_time_template(runner, tmp_path, utc_time):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text(
        """
    extensions:
        datetime: {}
    dialog:
    - condition: true
      response: |
        {{ utc_time.isoformat() }}
    """
    )

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        f"""
    - name: test
      turns:
        - utc_time: "{utc_time}"
          message: hello
          response: "2023-04-10T19:15:58.104144+00:00"
    """
    )

    result = runner.invoke(main, ["stories", "--bot", tmp_path], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "test OK" in result.output, result.output


def test_utc_time_entitites(runner, tmp_path):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text(
        """
    entities:
    - name: date
    dialog:
    - condition: entities.date
      response: |
        {{ entities.date.value }}
    """
    )

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
    - name: test
      turns:
        - utc_time: '2021-01-01T19:15:58.104144'
          message: today
          response: '2021-01-01'
    """
    )

    result = runner.invoke(main, ["stories", "--bot", tmp_path], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "test OK" in result.output, result.output


def test_fail(runner, tmp_path):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text(
        """
    dialog:
    - condition: true
      response: |
        {{ message.text }}
    """
    )

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
    - name: test
      turns:
        - message: hello
          response: HELLO
    """
    )

    result = runner.invoke(main, ["stories", "--bot", tmp_path], catch_exceptions=False)
    assert result.exit_code == 1, result.output
    assert result.output.startswith(
        (
            "test FAILED at step [0]\n"
            "Expected:\n"
            "  <text>HELLO</text>\n"
            "Actual:\n"
            "  <text>hello</text>\n"
        )
    ), result.output


def test_fail_list(runner, tmp_path):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text(
        """
    dialog:
    - condition: true
      response: |
        {{ message.text }}
    """
    )

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
    - name: test
      turns:
        - message: hello
          response:
          - hello1
          - hello2
    """
    )

    result = runner.invoke(main, ["stories", "--bot", tmp_path], catch_exceptions=False)
    assert result.exit_code == 1, result.output
    assert result.output.startswith(
        (
            "test FAILED at step [0]\n"
            "Expected:\n"
            "  <text>hello1</text>\n"
            "  -or-\n"
            "  <text>hello2</text>\n"
            "Actual:\n"
            "  <text>hello</text>\n"
        )
    ), result.output


def test_xfail(runner, tmp_path):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text(
        """
    dialog:
    - condition: true
      response: |
        {{ message.text }}
    """
    )

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
    - xfail: true
      name: test
      turns:
        - message: hello
          response: HELLO
    """
    )

    result = runner.invoke(main, ["stories", "--bot", tmp_path], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "test XFAIL" in result.output, result.output


def test_assert_no_message_and_no_rpc(runner, tmp_path, monkeypatch):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text("{}")

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text("[]")

    class _StorySchema:
        def load_file(self, *args, **kwargs):
            return [{"name": "test", "turns": [{"response": ""}]}]

    monkeypatch.setattr(maxbot.cli.stories, "create_story_schema", lambda bot: _StorySchema())

    with pytest.raises(AssertionError) as excinfo:
        runner.invoke(main, ["stories", "--bot", bot_file], catch_exceptions=False)
    assert str(excinfo.value) == "Either message or rpc must be provided."


def test_utc_time_tick_10sec():
    provider = maxbot.cli.stories.StoryUtcTimeProvider()
    provider.tick(datetime(2020, 1, 1, 0, 0))
    provider.tick()
    assert datetime(2020, 1, 1, 0, 0, 10, tzinfo=timezone.utc) == provider()


def test_rpc_method_validation_error():
    schema = maxbot.cli.stories.create_story_schema(BotBuilder().build())
    with pytest.raises(BotError) as excinfo:
        schema.loads(
            """
        - name: test
          turns:
          - rpc: { method: nonexistent }
            response: ""
        """
        )
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Method not found\n"
        '  in "<unicode string>", line 4, column 28:\n'
        "    turns:\n"
        "    - rpc: { method: nonexistent }\n"
        "                     ^^^\n"
        '      response: ""'
    )


def test_rpc_params_validation_error():
    builder = BotBuilder()
    builder.use_inline_resources(
        """
    rpc:
    - method: with_params
      params:
      - name: required_param
        required: true
    """
    )
    schema = maxbot.cli.stories.create_story_schema(builder.build())
    with pytest.raises(BotError) as excinfo:
        schema.loads(
            """
        - name: test
          turns:
          - rpc: { method: with_params }
            response: ""
        """
        )
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: {'required_param': "
        "['Missing data for required field.']}\n"
        '  in "<unicode string>", line 4, column 18:\n'
        "    turns:\n"
        "    - rpc: { method: with_params }\n"
        "           ^^^\n"
        '      response: ""'
    )


def test_turn_no_message_and_no_rpc():
    schema = maxbot.cli.stories.create_story_schema(BotBuilder().build())
    with pytest.raises(BotError) as excinfo:
        schema.loads(
            """
        - name: test
          turns:
          - response: ""
        """
        )
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: "
        "Exactly one of 'message' or 'rpc' is required.\n"
        '  in "<unicode string>", line 4, column 13:\n'
        "    turns:\n"
        '    - response: ""\n'
        "      ^^^\n"
    )


def test_match_first(runner, tmp_path):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text(
        """
    dialog:
    - condition: true
      response: |
        {{ message.text }}
    """
    )

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
    - name: test
      turns:
        - message: hello
          response:
          - hello
          - hello2
    """
    )

    result = runner.invoke(main, ["stories", "--bot", tmp_path], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "test OK" in result.output, result.output


def test_match_second(runner, tmp_path):
    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text(
        """
    dialog:
    - condition: true
      response: |
        {{ message.text }}
    """
    )

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
    - name: test
      turns:
        - message: hello
          response:
          - hello1
          - hello
    """
    )

    result = runner.invoke(main, ["stories", "--bot", tmp_path], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "test OK" in result.output, result.output


def test_markup_value_rendered_comparator_false():
    assert not maxbot.cli.stories.markup_value_rendered_comparator(markup.Value(), 1)
