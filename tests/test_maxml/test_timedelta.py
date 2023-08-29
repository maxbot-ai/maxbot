import pytest

from maxbot.errors import BotError
from maxbot.maxml import TimeDeltaSchema, fields
from maxbot.schemas import ResourceSchema


class Config(ResourceSchema):
    timedelta = fields.Nested(TimeDeltaSchema())


def test_empty():
    data = Config().loads("timedelta: {}")
    assert data["timedelta"].total_seconds() == 0


def test_short():
    data = Config().loads("timedelta: 5")
    assert data["timedelta"].total_seconds() == 5


def test_short_error():
    with pytest.raises(BotError) as excinfo:
        Config().loads("timedelta: x")
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Invalid input type.\n"
        '  in "<unicode string>", line 1, column 12:\n'
        "    timedelta: x\n"
        "               ^^^\n"
    )


def test_all():
    data = Config().loads(
        """
        timedelta:
          weeks: 1
          days: 2
          hours: 3
          minutes: 4
          seconds: 5
          microseconds: 6
          milliseconds: 7
    """
    )
    assert data["timedelta"].total_seconds() == 788645.007006


def test_default():
    class Config(ResourceSchema):
        timedelta = fields.Nested(
            TimeDeltaSchema(), load_default=TimeDeltaSchema.VALUE_TYPE(seconds=5)
        )

    data = Config().loads("{}")
    assert data["timedelta"].total_seconds() == 5
