"""Builtin MaxBot extension: "Babel" library (https://babel.pocoo.org/) frontend."""
from datetime import datetime

import babel.core
import babel.dates
import babel.numbers

from ..errors import BotError
from ..maxml import Schema, fields
from .datetime import date_filter, datetime_filter, time_filter


class BabelExtension:
    """Extension class."""

    class ConfigSchema(Schema):
        """Extension configuration schema."""

        locale = fields.Str()
        currency = fields.Str()
        tz = fields.Str()

    def __init__(self, builder, config):
        """Extension entry point.

        :param BotBuilder builder: MaxBot builder.
        :param dict config: Extension configuration.
        """
        self.locale = config.get("locale")
        self.currency = config.get("currency")

        tz = config.get("tz")
        self.timezone = _get_timezone_from_babel(tz) if tz else None

        self.default_locale_time = babel.core.default_locale("LC_TIME")
        self.default_locale_numeric = babel.core.default_locale("LC_NUMERIC")

        builder.add_template_filter(self._format_datetime, "format_datetime")
        builder.add_template_filter(self._format_date, "format_date")
        builder.add_template_filter(self._format_time, "format_time")

        builder.add_template_filter(self._format_currency, "format_currency")

    def _format_datetime(
        self, value, format="medium", locale=None, tz=None
    ):  # pylint: disable=redefined-builtin
        return _wrap_unknown_locale(
            babel.dates.format_datetime,
            datetime_filter(value),
            format=format,
            locale=self._get_locale(locale) or self.default_locale_time,
            tzinfo=self._get_tzinfo(tz),
        )

    def _format_date(
        self, value, format="medium", locale=None
    ):  # pylint: disable=redefined-builtin
        return _wrap_unknown_locale(
            babel.dates.format_date,
            date_filter(value),
            format=format,
            locale=self._get_locale(locale) or self.default_locale_time,
        )

    def _format_time(
        self, value, format="medium", locale=None, tz=None
    ):  # pylint: disable=redefined-builtin
        if not isinstance(value, datetime):
            value = time_filter(value)
        return _wrap_unknown_locale(
            babel.dates.format_time,
            value,
            format=format,
            locale=self._get_locale(locale) or self.default_locale_time,
            tzinfo=self._get_tzinfo(tz),
        )

    def _format_currency(
        self, value, currency=None, format=None, locale=None, currency_digits=True
    ):  # pylint: disable=redefined-builtin
        return _wrap_unknown_locale(
            babel.numbers.format_currency,
            value,
            self._get_currency(currency),
            format=format,
            locale=self._get_locale(locale) or self.default_locale_numeric,
            currency_digits=currency_digits,
        )

    def _get_locale(self, locale):
        return locale if locale else self.locale

    def _get_currency(self, currency=None):
        if currency:
            return currency
        if self.currency:
            return self.currency
        raise BotError("`currency` is not set")

    def _get_tzinfo(self, tz):
        try:
            return _get_timezone_from_babel(tz) if tz else self.timezone
        except LookupError as err:
            raise BotError(f"unknown timezone {tz!r}") from err


def _get_timezone_from_babel(tz):
    try:
        return babel.dates.get_timezone(tz)
    except LookupError as err:
        raise BotError(f"unknown timezone {tz!r}") from err


def _wrap_unknown_locale(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except babel.core.UnknownLocaleError as err:
        raise BotError(f"unknown locale {err.identifier!r}") from err
