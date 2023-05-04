import datetime

import pytest

from maxbot.bot import MaxBot
from maxbot.errors import BotError


@pytest.fixture
def builder():
    return MaxBot.builder()


@pytest.fixture
def now(builder):
    now = datetime.datetime(2022, 1, 2, 12, 0)
    builder.add_template_global(now, "now")
    return now


@pytest.mark.parametrize(
    "filter, expected",
    (
        ("format_datetime", "Jan 2, 2022, 12:00:00 PM"),
        ("format_date", "Jan 2, 2022"),
        ("format_time", "12:00:00 PM"),
    ),
)
def test_format_locale_param(builder, now, filter, expected):
    builder.use_inline_resources(
        """
        extensions:
            format: {}
        dialog:
        - condition: true
          response: |
            {{ now|"""
        + filter
        + """ (locale='en') }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == expected


@pytest.mark.parametrize(
    "filter, expected",
    (
        ("format_datetime", "2 janv. 2022, 12:00:00"),
        ("format_date", "2 janv. 2022"),
        ("format_time", "12:00:00"),
    ),
)
def test_format_locale_config(builder, now, filter, expected):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: 'fr'
        dialog:
        - condition: true
          response: |
            {{ now|"""
        + filter
        + """ }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == expected


@pytest.mark.parametrize(
    "filter, expected",
    (
        ("format_datetime", "02.01.2022, 12:00:00"),
        ("format_date", "02.01.2022"),
        ("format_time", "12:00:00"),
    ),
)
def test_format_locale_priority(builder, now, filter, expected):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: 'fr'
        dialog:
        - condition: true
          response: |
            {{ now|"""
        + filter
        + """(locale='de') }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == expected


@pytest.mark.parametrize(
    "filter",
    ("format_datetime", "format_date", "format_time", "format_currency(1, 'RUB')"),
)
def test_format_locale_not_set(builder, now, filter):
    builder.use_inline_resources(
        """
        extensions:
            format: {}
        dialog:
        - condition: true
          response: |
            {{ now|"""
        + filter
        + """ }}
    """
    )
    with pytest.raises(BotError) as excinfo:
        builder.build().process_message("hey bot")
    assert str(excinfo.value) == "`locale` is not set"


@pytest.mark.parametrize(
    "format, expected",
    (
        ("short", "1/2/22, 12:00 PM"),
        ("medium", "Jan 2, 2022, 12:00:00 PM"),
        ("long", "January 2, 2022, 12:00:00 PM UTC"),
        ("full", "Sunday, January 2, 2022, 12:00:00 PM Coordinated Universal Time"),
    ),
)
def test_format_datetime_format(builder, now, format, expected):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: 'en'
        dialog:
        - condition: true
          response: |
            {{ now|format_datetime(format="""
        + repr(format)
        + """) }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == expected


@pytest.mark.parametrize(
    "format, expected",
    (
        ("short", "1/2/22"),
        ("medium", "Jan 2, 2022"),
        ("long", "January 2, 2022"),
        ("full", "Sunday, January 2, 2022"),
    ),
)
def test_format_date_format(builder, now, format, expected):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: 'en'
        dialog:
        - condition: true
          response: |
            {{ now|format_date(format="""
        + repr(format)
        + """) }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == expected


@pytest.mark.parametrize(
    "format, expected",
    (
        ("short", "12:00 PM"),
        ("medium", "12:00:00 PM"),
        ("long", "12:00:00 PM UTC"),
        ("full", "12:00:00 PM Coordinated Universal Time"),
    ),
)
def test_format_time_format(builder, now, format, expected):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: 'en'
        dialog:
        - condition: true
          response: |
            {{ now|format_time(format="""
        + repr(format)
        + """) }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == expected


def test_format_currency_param(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: en
        dialog:
        - condition: true
          response: |
            {{ 1|format_currency('USD') }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == "$1.00"


def test_format_currency_config(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: en
                currency: EUR
        dialog:
        - condition: true
          response: |
            {{ 1|format_currency }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == "€1.00"


def test_format_currency_proirity(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: en
                currency: EUR
        dialog:
        - condition: true
          response: |
            {{ 1|format_currency('JPY') }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == "¥1"


def test_format_currency_rub(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: ru
                currency: RUB
        dialog:
        - condition: true
          response: |
            {{ 4096|format_currency(format='#,##0\xa0¤', currency_digits=false) }}
    """
    )

    (command,) = builder.build().process_message("hey bot")
    assert command["text"] == "4 096 ₽"


def test_currency_not_set(builder, now):
    builder.use_inline_resources(
        """
        extensions:
            format:
                locale: ru
        dialog:
        - condition: true
          response: |
            {{ 1|format_currency }}"""
    )
    with pytest.raises(BotError) as excinfo:
        builder.build().process_message("hey bot")
    assert str(excinfo.value) == "`currency` is not set"
