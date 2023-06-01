"""Builtin MaxBot extension: date/time convertors."""
from datetime import date, datetime, time, timezone

from dateutil.parser import parse
from dateutil.tz import gettz

from ..errors import BotError


def tz_filter(name):
    """Retrieve a time zone object from a string representation.

    :param str name: A time zone name.
    :return tzinfo:
    """
    tz = gettz(name)
    if tz is None:
        raise BotError(f"Unknown timezone: {name!r}")
    return tz


def datetime_filter(value):
    """Convert input value to `datetime` object.

    :param datetime|date|time|int|float|str value: input value.
    :raise BotError: Could not convert input value to `datetime`.
    :return datetime:
    """
    result = _datetime_filter_impl(value)
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def _datetime_filter_impl(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, time):
        return datetime.combine(datetime.now(value.tzinfo), value)
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        return parse(value)
    except (OverflowError, ValueError) as error:
        raise BotError(f"Could not convert {value!r} to datetime: {error}") from error


def date_filter(value):
    """Convert input value to `date` object.

    :param datetime|date|int|float|str value: input value.
    :raise BotError: Could not convert input value to `date`.
    :return date:
    """
    if not isinstance(value, datetime):
        if isinstance(value, date):
            return value
        if isinstance(value, time):
            raise BotError(f"Could not convert {value!r} to date")
    return datetime_filter(value).date()


def time_filter(value):
    """Convert input value to `time` object.

    :param datetime|time|int|float|str value: input value.
    :raise BotError: Could not convert input value to `time`.
    :return time:
    """
    if not isinstance(value, datetime):
        if isinstance(value, time):
            return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        if isinstance(value, date):
            raise BotError(f"Could not convert {value!r} to time")
    return datetime_filter(value).timetz()


class DatetimeExtension:
    """Extension class."""

    def __init__(self, builder, config):
        """Extension entry point.

        :param BotBuilder builder: MaxBot builder.
        :param dict config: Extension configuration.
        """
        builder.add_template_filter(tz_filter, "tz")
        builder.add_template_filter(datetime_filter, "datetime")
        builder.add_template_filter(date_filter, "date")
        builder.add_template_filter(time_filter, "time")
