import datetime

import pytest

from maxbot.bot import MaxBot
from maxbot.errors import BotError


@pytest.fixture
def builder():
    return MaxBot.builder()


@pytest.fixture
def now(builder):
    now = datetime.datetime.now()
    builder.add_template_global(now, "now_mock")
    return now


def test_datetime_datetime(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ (now_mock|datetime).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert now == datetime.datetime.fromisoformat(command["text"])


def test_datetime_date(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ (now_mock.date()|datetime).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    value = datetime.datetime.fromisoformat(command["text"])
    assert now.date() == value.date()
    assert datetime.datetime.min.time() == value.time()


def test_datetime_time(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ (now_mock.time()|datetime).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert now == datetime.datetime.fromisoformat(command["text"])


def test_datetime_int(builder):
    ts = int(datetime.datetime.now().timestamp())
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ ("""
        + str(ts)
        + """|datetime).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert datetime.datetime.fromisoformat(command["text"]) == datetime.datetime.fromtimestamp(ts)


def test_datetime_float(builder):
    now = datetime.datetime.now()
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ ("""
        + str(now.timestamp())
        + """|datetime).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert datetime.datetime.fromisoformat(command["text"]) == now


def test_datetime_str(builder):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ ("January 1, 2047 at 8:21:00AM"|datetime).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert datetime.datetime.fromisoformat(command["text"]) == datetime.datetime(2047, 1, 1, 8, 21)


def test_datetime_str_error(builder):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ "xyz"|datetime }}
    """
    )

    with pytest.raises(BotError) as excinfo:
        builder.build().process_message("hey bot")
    assert str(excinfo.value).endswith(
        "ParserError: Could not convert 'xyz' to datetime: Unknown string format: xyz"
    )


def test_date_datetime(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ (now_mock|date).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert now.date() == datetime.date.fromisoformat(command["text"])


def test_date_date(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ (now_mock.date()|date).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert now.date() == datetime.date.fromisoformat(command["text"])


def test_date_time_error(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ now_mock.time()|date }}
    """
    )

    with pytest.raises(BotError) as excinfo:
        builder.build().process_message("hey bot")
    assert str(excinfo.value).startswith("Could not convert datetime.time(")
    assert str(excinfo.value).endswith(") to date")


def test_date_str(builder):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ ("January 1, 2047"|date).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert datetime.date.fromisoformat(command["text"]) == datetime.date(2047, 1, 1)


def test_time_datetime(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ (now_mock|time).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert now.time() == datetime.time.fromisoformat(command["text"])


def test_time_time(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ (now_mock.time()|time).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert now.time() == datetime.time.fromisoformat(command["text"])


def test_time_date_error(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ now_mock.date()|time }}
    """
    )

    with pytest.raises(BotError) as excinfo:
        builder.build().process_message("hey bot")
    assert str(excinfo.value).startswith("Could not convert datetime.date(")
    assert str(excinfo.value).endswith(") to time")


def test_time_str(builder):
    builder.use_inline_resources(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ ("8:21:00AM"|time).isoformat() }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert datetime.time.fromisoformat(command["text"]) == datetime.time(8, 21)
