import datetime
from unittest.mock import Mock, call

import pytest
from babel.dates import get_timezone

from maxbot.errors import BotError
from maxbot.extensions.datetime import (
    DatetimeExtension,
    date_filter,
    datetime_filter,
    time_filter,
    tz_filter,
)


def test_init():
    builder = Mock()
    DatetimeExtension(builder, {})
    expected = [
        call(tz_filter, "tz"),
        call(datetime_filter, "datetime"),
        call(date_filter, "date"),
        call(time_filter, "time"),
    ]
    builder.add_template_filter.assert_has_calls(expected, any_order=True)


def test_datetime_datetime():
    value = datetime.datetime.now()
    assert datetime_filter(value) == value.replace(tzinfo=datetime.timezone.utc)


def test_datetime_datetime_utc():
    value = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    assert datetime_filter(value) == value


def test_datetime_datetime_tz():
    tzinfo = get_timezone("Japan")
    value = datetime.datetime.now(tzinfo)
    assert datetime_filter(value) == value


def test_datetime_date():
    value = datetime.datetime.now(datetime.timezone.utc).date()
    assert datetime_filter(value) == datetime.datetime(
        value.year, value.month, value.day, tzinfo=datetime.timezone.utc
    )


def test_datetime_time():
    value = datetime.datetime.now()
    assert datetime_filter(value.time()) == datetime.datetime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        tzinfo=datetime.timezone.utc,
    )


def test_datetime_time_utc():
    value = datetime.datetime.now(datetime.timezone.utc)
    assert datetime_filter(value.timetz()) == datetime.datetime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        tzinfo=datetime.timezone.utc,
    )


def test_datetime_time_tz():
    tzinfo = datetime.timezone(datetime.timedelta(hours=-1))
    value = datetime.time(10, 30, tzinfo=tzinfo)
    turn_date = datetime.datetime.now(datetime.timezone.utc).date()
    assert datetime_filter(value) == datetime.datetime(
        turn_date.year, turn_date.month, turn_date.day, 10, 30, tzinfo=tzinfo
    )


def test_datetime_int():
    value = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    assert datetime_filter(value) == datetime.datetime.fromtimestamp(
        value, tz=datetime.timezone.utc
    )


def test_datetime_float():
    value = datetime.datetime.now(datetime.timezone.utc)
    assert datetime_filter(value.timestamp()) == value


def test_datetime_str():
    value = "January 1, 2047 at 8:21:00AM"
    assert datetime_filter(value) == datetime.datetime(
        2047, 1, 1, 8, 21, tzinfo=datetime.timezone.utc
    )


def test_datetime_str_tz():
    value = "2047-01-01T08:21:00+09:00"
    assert datetime_filter(value) == datetime.datetime(
        2047, 1, 1, 8, 21, tzinfo=datetime.timezone(datetime.timedelta(hours=9))
    )


def test_datetime_str_error():
    with pytest.raises(BotError) as excinfo:
        datetime_filter("xyz")
    assert str(excinfo.value).endswith(
        "ParserError: Could not convert 'xyz' to datetime: Unknown string format: xyz"
    )


def test_date_datetime():
    value = datetime.datetime.now(datetime.timezone.utc)
    assert date_filter(value) == value.date()


def test_date_date():
    value = datetime.datetime.now(datetime.timezone.utc).date()
    assert date_filter(value) == value


def test_date_time_error():
    with pytest.raises(BotError) as excinfo:
        date_filter(datetime.time(1, 0))
    assert str(excinfo.value) == "Could not convert datetime.time(1, 0) to date"


def test_date_int():
    value = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    assert (
        date_filter(value)
        == datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc).date()
    )


def test_date_float():
    value = datetime.datetime.now(datetime.timezone.utc)
    assert date_filter(value.timestamp()) == value.date()


def test_date_str():
    assert date_filter("January 1, 2047") == datetime.date(2047, 1, 1)


def test_time_datetime():
    value = datetime.datetime.now()
    assert time_filter(value) == value.time().replace(tzinfo=datetime.timezone.utc)


def test_time_datetime_utc():
    value = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    assert time_filter(value) == value.timetz()


def test_time_datetime_tz():
    tzinfo = get_timezone("Japan")
    value = datetime.datetime.now(tzinfo)
    assert time_filter(value) == value.timetz()


def test_time_date_error():
    with pytest.raises(BotError) as excinfo:
        time_filter(datetime.date(2001, 1, 2))
    assert str(excinfo.value) == "Could not convert datetime.date(2001, 1, 2) to time"


def test_time_time():
    value = datetime.datetime.now().time()
    assert time_filter(value) == value.replace(tzinfo=datetime.timezone.utc)


def test_time_time_utc():
    value = datetime.time(1, 2, 3, tzinfo=datetime.timezone.utc)
    assert time_filter(value) == value


def test_time_time_tz():
    tzinfo = get_timezone("Japan")
    value = datetime.datetime.now(tzinfo).timetz()
    assert time_filter(value) == value


def test_time_int():
    value = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    assert (
        time_filter(value)
        == datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc).timetz()
    )


def test_time_float():
    value = datetime.datetime.now(datetime.timezone.utc)
    assert time_filter(value.timestamp()) == value.timetz()


def test_time_str():
    assert time_filter("8:21:00AM") == datetime.time(8, 21, tzinfo=datetime.timezone.utc)


def test_time_str_tz():
    assert time_filter("11:00:00+09:00") == datetime.time(
        11, tzinfo=datetime.timezone(datetime.timedelta(hours=9))
    )


@pytest.mark.parametrize("value", (1000000000000000, 1000000000000000.0))
@pytest.mark.parametrize("filter_fn", (datetime_filter, date_filter, time_filter))
def test_datetime_overflow_error(value, filter_fn):
    with pytest.raises(BotError) as excinfo:
        filter_fn(value)
    assert f"Could not convert {value!r} to " in str(excinfo.value)


def test_tz():
    v = datetime.datetime.fromisoformat("2023-05-23T13:00:00+00:00")
    assert v.astimezone(tz_filter("Asia/Saigon")).isoformat() == "2023-05-23T20:00:00+07:00"


def test_tz_unknown():
    with pytest.raises(BotError) as excinfo:
        tz_filter("Unknown123")
    assert str(excinfo.value) == "Unknown timezone: 'Unknown123'"
