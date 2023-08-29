"""`datetime.timedelta` representation."""
from datetime import timedelta

from marshmallow import Schema, fields, post_load, pre_load  # noqa: F401


class TimeDeltaSchema(Schema):
    """Time shift value representation.

    @see https://docs.python.org/3/library/datetime.html#timedelta-objects
    """

    VALUE_TYPE = timedelta

    days = fields.Int(load_default=0)
    seconds = fields.Int(load_default=0)
    microseconds = fields.Int(load_default=0)
    milliseconds = fields.Int(load_default=0)
    minutes = fields.Int(load_default=0)
    hours = fields.Int(load_default=0)
    weeks = fields.Int(load_default=0)

    @pre_load
    def short_syntax(self, data, **kwargs):
        """Short syntax is available.

        my_time: 5
        -> timedelta(seconds=5)
        """
        if isinstance(data, (int, str)):
            try:
                return {"seconds": int(data)}
            except ValueError:
                pass
        return data

    @post_load
    def return_httpx_timeout(self, data, **kwargs):
        """Create and return datetime.timedelta by loaded data."""
        return self.VALUE_TYPE(
            days=data["days"],
            seconds=data["seconds"],
            microseconds=data["microseconds"],
            milliseconds=data["milliseconds"],
            minutes=data["minutes"],
            hours=data["hours"],
            weeks=data["weeks"],
        )
