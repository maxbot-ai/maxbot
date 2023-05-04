"""Builtin MaxBot extension: internationalization and localization using "Babel" library."""
import babel.dates
import babel.numbers
from marshmallow import Schema, fields

from ..errors import BotError
from .datetime import date_filter, datetime_filter, time_filter


class FormatExtension:
    """Extension class."""

    class ConfigSchema(Schema):
        """Extension configuration schema."""

        locale = fields.Str()
        currency = fields.Str()

    def __init__(self, builder, config):
        """Extension entry point.

        :param BotBuilder builder: MaxBot builder.
        :param dict config: Extension configuration.
        """
        self.locale = config.get("locale")
        self.currency = config.get("currency")

        builder.add_template_filter(self._format_datetime, "format_datetime")
        builder.add_template_filter(self._format_date, "format_date")
        builder.add_template_filter(self._format_time, "format_time")

        builder.add_template_filter(self._format_currency, "format_currency")

    def _format_datetime(
        self, value, format="medium", locale=None
    ):  # pylint: disable=redefined-builtin
        return babel.dates.format_datetime(
            datetime_filter(value), format=format, locale=self._get_locale(locale)
        )

    def _format_date(
        self, value, format="medium", locale=None
    ):  # pylint: disable=redefined-builtin
        return babel.dates.format_date(
            date_filter(value), format=format, locale=self._get_locale(locale)
        )

    def _format_time(
        self, value, format="medium", locale=None
    ):  # pylint: disable=redefined-builtin
        return babel.dates.format_time(
            time_filter(value), format=format, locale=self._get_locale(locale)
        )

    def _format_currency(
        self, value, currency=None, format=None, locale=None, currency_digits=True
    ):  # pylint: disable=redefined-builtin
        return babel.numbers.format_currency(
            value,
            self._get_currency(currency),
            format=format,
            locale=self._get_locale(locale),
            currency_digits=currency_digits,
        )

    def _get_locale(self, locale=None):
        if locale:
            return locale
        if self.locale:
            return self.locale
        raise BotError("`locale` is not set")

    def _get_currency(self, currency=None):
        if currency:
            return currency
        if self.currency:
            return self.currency
        raise BotError("`currency` is not set")
