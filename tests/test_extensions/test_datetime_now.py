from datetime import datetime

import pytest
from pytz import UnknownTimeZoneError, timezone, utc

from maxbot.bot import MaxBot


def test_default():
    bot = MaxBot.inline(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: |
            {{ now.isoformat() }}
    """
    )

    (command,) = bot.process_message("hey bot")
    delta = datetime.now() - datetime.fromisoformat(command["text"])

    assert delta.total_seconds() >= 0
    assert delta.total_seconds() < 1


def test_sydney():
    bot = MaxBot.inline(
        """
        extensions:
            datetime:
                tz: Australia/Sydney
        dialog:
        - condition: true
          response: |
            {{ now.isoformat() }}
    """
    )

    (command,) = bot.process_message("hey bot")
    delta = datetime.now(timezone("Australia/Sydney")) - datetime.fromisoformat(command["text"])

    assert delta.total_seconds() >= 0
    assert delta.total_seconds() < 1


def test_utc():
    bot = MaxBot.inline(
        """
        extensions:
            datetime:
                tz: UTC
        dialog:
        - condition: true
          response: |
            {{ now.isoformat() }}
    """
    )

    (command,) = bot.process_message("hey bot")
    delta = datetime.now(utc) - datetime.fromisoformat(command["text"])

    assert delta.total_seconds() >= 0
    assert delta.total_seconds() < 1


def test_unknown_timezone():
    with pytest.raises(UnknownTimeZoneError) as excinfo:
        MaxBot.inline(
            """
            extensions:
                datetime:
                    tz: Europe/Unknown
            dialog:
            - condition: true
              response: |
                {{ now.isoformat() }}
        """
        )
    assert "Europe/Unknown" in str(excinfo.value)


def test_today():
    bot = MaxBot.inline(
        """
        extensions:
            datetime: {}
        dialog:
        - condition: true
          response: !jinja |-
            {{ today.isoformat() }}
    """
    )

    (command,) = bot.process_message("hey bot")
    assert datetime.fromisoformat(command["text"]).date() == datetime.today().date()
