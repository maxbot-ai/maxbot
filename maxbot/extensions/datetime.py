"""Builtin MaxBot extension: date/time utils and `now` global variable."""
from datetime import date, datetime, time

import dateutil.parser
from marshmallow import Schema, fields
from pytz import timezone

from ..errors import BotError


def datetime_filter(value):
    """Convert input value to `datetime` object.

    :param datetime|date|time|int|float|str value: input value.
    :raise BotError: Could not convert input value to `datetime`.
    :return datetime:
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, time):
        return datetime.combine(datetime.now(), value)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    try:
        return dateutil.parser.parse(value)
    except (dateutil.parser.ParserError, OverflowError) as error:
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
            return value
        if isinstance(value, date):
            raise BotError(f"Could not convert {value!r} to time")
    return datetime_filter(value).time()


class DatetimeExtension:
    """Extension class."""

    class ConfigSchema(Schema):
        """Extension configuration schema."""

        tz = fields.Str()

    def __init__(self, builder, config):
        """Extension entry point.

        :param BotBuilder builder: MaxBot builder.
        :param dict config: Extension configuration.
        """
        tz = config.get("tz")
        self.timezone = timezone(tz) if tz else None
        builder.before_turn(self._before_turn)
        builder.add_template_filter(datetime_filter, "datetime")
        builder.add_template_filter(date_filter, "date")
        builder.add_template_filter(time_filter, "time")

    def _before_turn(self, ctx):
        dt = datetime.now(self.timezone)
        ctx.scenario.now = dt
        ctx.scenario.today = dt.date()
