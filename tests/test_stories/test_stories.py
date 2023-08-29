from datetime import datetime, timezone

import pytest

from maxbot import MaxBot
from maxbot.errors import BotError
from maxbot.maxml import markup
from maxbot.stories import Stories, StoryUtcTimeProvider, markup_value_rendered_comparator


@pytest.mark.parametrize(
    "utc_time", ("2023-04-10T19:15:58.104144", "2023-04-10T18:15:58.104144-01:00")
)
def test_utc_time_template(tmp_path, utc_time):
    stories = Stories(
        MaxBot.inline(
            """
        dialog:
        - condition: true
          response: "{{ utc_time.isoformat() }}"
        """
        )
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
    (s,) = stories.load(stories_file)
    stories.run(s)


def test_utc_time_entitites(tmp_path):
    stories = Stories(
        MaxBot.inline(
            """
        entities:
        - name: date
        dialog:
        - condition: entities.date
          response: "{{ entities.date.value }}"
        """
        )
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
    (s,) = stories.load(stories_file)
    stories.run(s)


def test_fail(tmp_path):
    stories = Stories(
        MaxBot.inline(
            """
        dialog:
        - condition: true
          response: "{{ message.text }}"
        """
        )
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

    (s,) = stories.load(stories_file)
    with pytest.raises(stories.MismatchError) as exinfo:
        stories.run(s)

    assert (
        "Mismatch at step [0]\n"
        "Expected:\n"
        "  <text>HELLO</text>\n"
        "Actual:\n"
        "  <text>hello</text>"
    ) == exinfo.value.message


def test_fail_list(tmp_path):
    stories = Stories(
        MaxBot.inline(
            """
        dialog:
        - condition: true
          response: "{{ message.text }}"
        """
        )
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

    (s,) = stories.load(stories_file)
    with pytest.raises(stories.MismatchError) as exinfo:
        stories.run(s)

    assert (
        "Mismatch at step [0]\n"
        "Expected:\n"
        "  <text>hello1</text>\n"
        "  -or-\n"
        "  <text>hello2</text>\n"
        "Actual:\n"
        "  <text>hello</text>"
    ) == exinfo.value.message


def test_utc_time_tick_10sec():
    provider = StoryUtcTimeProvider()
    provider.tick(datetime(2020, 1, 1, 0, 0))
    provider.tick()
    assert datetime(2020, 1, 1, 0, 0, 10, tzinfo=timezone.utc) == provider()


def test_rpc_method_validation_error(tmp_path):
    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
        - name: test
          turns:
          - rpc: { method: nonexistent }
            response: ""
    """
    )

    with pytest.raises(BotError) as excinfo:
        Stories(MaxBot.builder().build()).load(stories_file)

    lines = str(excinfo.value).splitlines()
    assert lines[0] == "caused by marshmallow.exceptions.ValidationError: Method not found"
    assert lines[1].endswith(", line 4, column 28:")
    assert lines[2:] == [
        "    turns:",
        "    - rpc: { method: nonexistent }",
        "                     ^^^",
        '      response: ""',
    ]


def test_rpc_params_validation_error(tmp_path):
    bot = MaxBot.inline(
        """
    rpc:
    - method: with_params
      params:
      - name: required_param
        required: true
    """
    )

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
        - name: test
          turns:
          - rpc: { method: with_params }
            response: ""
        """
    )

    with pytest.raises(BotError) as excinfo:
        Stories(bot).load(stories_file)

    lines = str(excinfo.value).splitlines()
    assert lines[0] == (
        "caused by marshmallow.exceptions.ValidationError: {'required_param': "
        "['Missing data for required field.']}"
    )
    assert lines[1].endswith(", line 4, column 18:")
    assert lines[2:] == [
        "    turns:",
        "    - rpc: { method: with_params }",
        "           ^^^",
        '      response: ""',
    ]


def test_turn_no_message_and_no_rpc(tmp_path):
    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
        - name: test
          turns:
          - response: ""
    """
    )

    with pytest.raises(BotError) as excinfo:
        Stories(MaxBot.builder().build()).load(stories_file)

    lines = str(excinfo.value).splitlines()
    assert lines[0] == (
        "caused by marshmallow.exceptions.ValidationError: "
        "Exactly one of 'message' or 'rpc' is required."
    )
    assert lines[1].endswith(", line 4, column 13:")
    assert lines[2:] == [
        "    turns:",
        '    - response: ""',
        "      ^^^",
    ]


def test_match_first(tmp_path):
    stories = Stories(
        MaxBot.inline(
            """
        dialog:
        - condition: true
          response: |
            {{ message.text }}
        """
        )
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

    (s,) = stories.load(stories_file)
    stories.run(s)


def test_match_second(tmp_path):
    stories = Stories(
        MaxBot.inline(
            """
        dialog:
        - condition: true
          response: |
            {{ message.text }}
        """
        )
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

    (s,) = stories.load(stories_file)
    stories.run(s)


def test_rpc(tmp_path):
    stories = Stories(
        MaxBot.inline(
            """
        rpc:
        - method: test
        dialog:
        - condition: rpc.test
          response: success
        """
        )
    )

    stories_file = tmp_path / "stories.yaml"
    stories_file.write_text(
        """
        - name: test
          turns:
          - rpc: { method: test }
            response: success
        """
    )

    (s,) = stories.load(stories_file)
    stories.run(s)


def test_markup_value_rendered_comparator_false():
    assert not markup_value_rendered_comparator(markup.Value(), 1)
