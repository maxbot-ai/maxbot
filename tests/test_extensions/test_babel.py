import datetime
from unittest.mock import Mock

import pytest

from maxbot.errors import BotError
from maxbot.extensions.babel import BabelExtension


@pytest.fixture(scope="session")
def utc_time():
    return datetime.datetime(2022, 1, 2, 12, 0, tzinfo=datetime.timezone.utc)


def test_init():
    assert _babel().keys() == {"format_datetime", "format_date", "format_time", "format_currency"}


@pytest.mark.parametrize(
    "filter_name, expected",
    (
        ("format_datetime", "Jan 2, 2022, 12:00:00\u202fPM"),
        ("format_date", "Jan 2, 2022"),
        ("format_time", "12:00:00\u202fPM"),
    ),
)
def test_format_locale_param(utc_time, filter_name, expected):
    assert _babel()[filter_name](utc_time, locale="en") == expected


@pytest.mark.parametrize(
    "filter_name, expected",
    (
        ("format_datetime", "2 janv. 2022, 12:00:00"),
        ("format_date", "2 janv. 2022"),
        ("format_time", "12:00:00"),
    ),
)
def test_format_locale_config(utc_time, filter_name, expected):
    assert _babel({"locale": "fr"})[filter_name](utc_time) == expected


@pytest.mark.parametrize(
    "filter_name, expected",
    (
        ("format_datetime", "02.01.2022, 12:00:00"),
        ("format_date", "02.01.2022"),
        ("format_time", "12:00:00"),
    ),
)
def test_format_locale_priority(utc_time, filter_name, expected):
    assert _babel({"locale": "fr"})[filter_name](utc_time, locale="de") == expected


@pytest.mark.parametrize("filter_name", ("format_datetime", "format_date", "format_time"))
def test_format_locale_not_set(utc_time, filter_name):
    # use LC_TIME
    assert _babel()[filter_name](utc_time)


def test_format_locale_not_set_format_currency():
    # use LC_NUMERIC
    assert _babel()["format_currency"](1, "USD")


@pytest.mark.parametrize("filter_name", ("format_datetime", "format_date", "format_time"))
def test_format_unknown_locale(utc_time, filter_name):
    with pytest.raises(BotError) as excinfo:
        _babel()[filter_name](utc_time, locale="xyz")
    assert str(excinfo.value) == "caused by babel.core.UnknownLocaleError: unknown locale 'xyz'"


def test_format_currency_unknown_locale():
    with pytest.raises(BotError) as excinfo:
        _babel()["format_currency"](1, "USD", locale="xyz")
    assert str(excinfo.value) == "caused by babel.core.UnknownLocaleError: unknown locale 'xyz'"


@pytest.mark.parametrize(
    "format, expected",
    (
        ("short", "1/2/22, 12:00\u202fPM"),
        ("medium", "Jan 2, 2022, 12:00:00\u202fPM"),
        ("long", "January 2, 2022, 12:00:00\u202fPM UTC"),
        ("full", "Sunday, January 2, 2022, 12:00:00\u202fPM Coordinated Universal Time"),
    ),
)
def test_format_datetime_format(utc_time, format, expected):
    assert _babel({"locale": "en"})["format_datetime"](utc_time, format=format) == expected


@pytest.mark.parametrize(
    "format, expected",
    (
        ("short", "1/2/22"),
        ("medium", "Jan 2, 2022"),
        ("long", "January 2, 2022"),
        ("full", "Sunday, January 2, 2022"),
    ),
)
def test_format_date_format(utc_time, format, expected):
    assert _babel({"locale": "en"})["format_date"](utc_time, format=format) == expected


@pytest.mark.parametrize(
    "format, expected",
    (
        ("short", "12:00\u202fPM"),
        ("medium", "12:00:00\u202fPM"),
        ("long", "12:00:00\u202fPM UTC"),
        ("full", "12:00:00\u202fPM Coordinated Universal Time"),
    ),
)
def test_format_time_format(utc_time, format, expected):
    assert _babel({"locale": "en"})["format_time"](utc_time, format=format) == expected


def test_format_currency_param():
    assert _babel({"locale": "en"})["format_currency"](1, "USD") == "$1.00"


def test_format_currency_config():
    assert _babel({"locale": "en", "currency": "EUR"})["format_currency"](1) == "€1.00"


def test_format_currency_proirity():
    assert _babel({"locale": "en", "currency": "EUR"})["format_currency"](1, "JPY") == "¥1"


def test_format_currency_rub():
    assert (
        _babel({"locale": "ru", "currency": "RUB"})["format_currency"](
            4096, format="#,##0\xa0¤", currency_digits=False
        )
        == "4\xa0096\xa0₽"
    )


def test_currency_not_set():
    with pytest.raises(BotError) as excinfo:
        _babel({"locale": "en"})["format_currency"](1)
    assert str(excinfo.value) == "`currency` is not set"


@pytest.mark.parametrize(
    "filter_name, expected",
    (
        ("format_datetime", "2 ene 2022 06:00:00"),
        ("format_time", "06:00:00"),
    ),
)
def test_format_tz_param(utc_time, filter_name, expected):
    assert _babel({"locale": "es_MX"})[filter_name](utc_time, tz="Mexico/General") == expected


@pytest.mark.parametrize(
    "filter_name, expected",
    (
        ("format_datetime", "2 ene 2022 06:00:00"),
        ("format_time", "06:00:00"),
    ),
)
def test_format_tz_config(utc_time, filter_name, expected):
    assert _babel({"locale": "es_MX", "tz": "Mexico/General"})[filter_name](utc_time) == expected


@pytest.mark.parametrize(
    "filter_name, expected",
    (
        ("format_datetime", "2 ene 2022 06:00:00"),
        ("format_time", "06:00:00"),
    ),
)
def test_format_tz_priority(utc_time, filter_name, expected):
    assert (
        _babel({"locale": "es_MX", "tz": "UTC"})[filter_name](utc_time, tz="Mexico/General")
        == expected
    )


@pytest.mark.parametrize(
    "filter_name, expected",
    (
        ("format_datetime", "2 ene 2022 12:00:00"),
        ("format_time", "12:00:00"),
    ),
)
def test_format_tz_not_set(utc_time, filter_name, expected):
    assert _babel({"locale": "es_MX"})[filter_name](utc_time) == expected


@pytest.mark.parametrize("filter_name", ("format_datetime", "format_time"))
def test_unknown_tz_param(utc_time, filter_name):
    with pytest.raises(BotError) as excinfo:
        _babel({"locale": "es_MX"})[filter_name](utc_time, tz="Europe/Unknown")

    assert (
        str(excinfo.value) == "caused by builtins.LookupError: unknown timezone 'Europe/Unknown'"
    )


@pytest.mark.parametrize("filter_name", ("format_datetime", "format_time"))
def test_unknown_tz_config(utc_time, filter_name):
    with pytest.raises(BotError) as excinfo:
        _babel({"locale": "es_MX", "tz": "Europe/Unknown"})[filter_name](utc_time)

    assert (
        str(excinfo.value) == "caused by builtins.LookupError: unknown timezone 'Europe/Unknown'"
    )


def _babel(config={}):
    builder = Mock()
    BabelExtension(builder, config)
    return {c[0][1]: c[0][0] for c in builder.add_template_filter.call_args_list}
