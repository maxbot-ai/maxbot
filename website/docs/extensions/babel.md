# babel extension

This extension is [Babel library](https://babel.pocoo.org/) frontend. It provides filters for date/time and currency formatting.

## Extension configuration {#config}

| Name       | Type                                   | Description           | Applies to |
| ---------- | -------------------------------------- | --------------------- | ---------- |
| `locale`   | [String](/design-reference/strings.md) | [Locale identifier](#locale). | **All** filters. |
| `tz`       | [String](/design-reference/strings.md) | [Time zone identifier](#timezone). | [format\_datetime](#format_datetime), [format\_time](#format_time) |
| `currency` | [String](/design-reference/strings.md) | [Currency code](#currency).        | [format\_currency](#format_currency) |

All values in the extension configuration are optional and can be overwritten by filter parameters.
For example: format local time using [format\_time](#format_time) filter.
The filter arguments (`locale` and `tz`) **override** the specified extension settings:
```yaml
extensions:
  babel:
    locale: de_DE
    tz: Europe/Berlin
dialog:
- condition: true
  response: |
    {{ utc_time|format_time(format="full", locale="en_US", tz="America/Chicago") }}
```
```
🧑 hello
🤖 10:10:09 AM Central Daylight Time
```

### Locale

Locale identifier is defined in this format: `language[_territory]`.
It consists of two identifiers: a language code and a territory code.
The territory code is optional.

Language codes are defined in ISO 639.
You can find them on [Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes).

Territory codes are defined in ISO 3166.
You can find them on [Wikipedia](https://en.wikipedia.org/wiki/ISO_3166-2#Current_codes).

For example `en_US`: `en` is the language code (English) and `US` is the country code (United States of America).

If an unknown locale is specified, an error will occur:
```yaml
extensions:
  babel:
    locale: xyz
dialog:
- condition: true
  response: |
    {{ utc_time|format_datetime }}
```
```
🧑 hello
logs
✗  caused by babel.core.UnknownLocaleError: unknown locale 'xyz'
```

### Time zone {#timezone}

The set of supported time zones depends on your system.
A well-known list of timezones can be found on [Wikipedia](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) (`TZ identifier` column).

If an unknown timezone is specified, an error will occur:
```yaml
extensions:
  babel: {}
dialog:
- condition: true
  response: |
    {{ utc_time|format_datetime(tz="xyz") }}
```
```
🧑 hello
logs
✗  caused by builtins.LookupError: unknown timezone 'xyz'
```

### Currency

The currency code is defined in ISO 4217.
A well-known list of currency codes can be found on [Wikipedia](https://en.wikipedia.org/wiki/ISO_4217#List_of_ISO_4217_currency_codes) (`Code` column).


## `format_datetime` filter {#format_datetime}

Filter `format_datetime` return a date and time formatted according to the given pattern.

Parameters:

| Name     | Default value | Description | Note |
| -------- | ------------- | ----------- | ---- |
| `value`  |               | Input value. | Any type suitable for the input value of filter [datetime](/extensions/datetime.md#datetime) |
| `format` | `"medium"`    | One of "full", "long", "medium", or "short", or a custom date/time pattern. | |
| `locale` |               | [Locale identifier](#locale). | If the parameter is not set, the value is taken from the extension configuration. If the value is not specified anywhere, `LC_TIME` value from your system is used. |
| `tz`     |               | [Time zone identifier](#timezone). | If the parameter is not set, the value is taken from the extension configuration. |

The filter is implemented by calling function [babel.dates.format\_datetime](https://babel.pocoo.org/en/latest/api/dates.html#babel.dates.format_datetime).

Usage example: format local date and time for Costa Rica (all formatting options are passed through filter arguments).

```yaml
extensions:
  babel: {}
dialog:
- condition: true
  response: |
    {{ utc_time|format_datetime(format="full", locale="es_CR", tz="America/Costa_Rica") }}
```
```
🧑 hello
🤖 martes, 30 de mayo de 2023, 08:58:46 hora estándar central
```

An custom pattern can be set in the value of `format`.
The syntax of the pattern is described in [documentation of babel library](https://babel.pocoo.org/en/latest/dates.html#pattern-syntax).
For example:

```yaml
extensions:
  babel: {}
dialog:
- condition: true
  response: |
    {{ utc_time|format_datetime(format="yyyy.MM.dd G 'at' HH:mm:ss zzz",
                                locale="en", tz="America/Costa_Rica") }}
```
```
🧑 hello
🤖 2023.05.30 d.C. at 09:27:49 -0600
```

## `format_date` filter {#format_date}

Filter `format_date` return a date formatted according to the given pattern.

Parameters:

| Name     | Default value | Description | Note |
| -------- | ------------- | ----------- | ---- |
| `value`  |               | Input value. | Any type suitable for the input value of filter [date](/extensions/datetime.md#date) |
| `format` | `"medium"`    | One of "full", "long", "medium", or "short", or a custom date pattern. | |
| `locale` |               | [Locale identifier](#locale). | If the parameter is not set, the value is taken from the extension configuration. If the value is not specified anywhere, `LC_TIME` value from your system is used. |

The filter is implemented by calling function [babel.dates.format\_date](https://babel.pocoo.org/en/latest/api/dates.html#babel.dates.format_date).

Usage example: format local date. Locale (Germany) is set in the extension settings. To get the local time (Berlin), [tz filter from datetime extension](/extensions/datetime.md#tz) is used.

```yaml
extensions:
  babel:
    locale: de_DE
  datetime: {}
dialog:
- condition: true
  response: |
    {{ utc_time.astimezone("Europe/Berlin"|tz)|format_date(format="full") }}
```
```
🧑 hello
🤖 Dienstag, 30. Mai 2023
```

An custom pattern can be set in the value of `format`.
The syntax of the pattern is described in [documentation of babel library](https://babel.pocoo.org/en/latest/dates.html#pattern-syntax).
For example:

```yaml
extensions:
  babel:
    locale: de_DE
  datetime: {}
dialog:
- condition: true
  response: |
    {{ utc_time.astimezone("Europe/Berlin"|tz)|format_date(format="EEE, MMM d, ''y") }}
```
```
🧑 hello
🤖 Di., Mai 30, '2023
```

## `format_time` filter {#format_time}

Filter `format_time` return a time formatted according to the given pattern.

Parameters:

| Name     | Default value | Description | Note |
| -------- | ------------- | ----------- | ---- |
| `value`  |               | Input value. | Any type suitable for the input value of filter [time](/extensions/datetime.md#time) |
| `format` | `"medium"`    | One of "full", "long", "medium", or "short", or a custom time pattern. | |
| `locale` |               | [Locale identifier](#locale). | If the parameter is not set, the value is taken from the extension configuration. If the value is not specified anywhere, `LC_TIME` value from your system is used. |
| `tz`     |               | [Time zone identifier](#timezone). | If the parameter is not set, the value is taken from the extension configuration. |

The filter is implemented by calling function [babel.dates.format\_time](https://babel.pocoo.org/en/latest/api/dates.html#babel.dates.format_time).

Usage example: format local time. Locale (`en_US`) and time zone (`America/Chicago`) are set in the extension settings.
```yaml
extensions:
  babel:
    locale: en_US
    tz: America/Chicago
dialog:
- condition: true
  response: |
    {{ utc_time|format_time(format="full") }}
```
```
🧑 hello
🤖 10:10:09 AM Central Daylight Time
```

An custom pattern can be set in the value of `format`.
The syntax of the pattern is described in [documentation of babel library](https://babel.pocoo.org/en/latest/dates.html#pattern-syntax).
For example:

```yaml
extensions:
  babel:
    locale: en_US
    tz: America/Chicago
dialog:
- condition: true
  response: |
    {{ utc_time|format_time(format="hh 'o''clock' a, zzzz") }}
```
```
🧑 hello
🤖 10 o'clock AM, Central Daylight Time
```

## `format_currency` filter {#format_currency}

Filter `format_currency` return formatted currency value.

| Name       | Description        | Note |
| ---------- | ------------------ | ---- |
| `value`    | Input value.       | Type is a [Number](/design-reference/numbers.md) |
| `currency` | [Currency code](#currency).     | If the parameter is not set, the value is taken from the extension configuration. |
| `format`   | Format string.     | |
| `locale`   | [Locale identifier](#locale). | If the parameter is not set, the value is taken from the extension configuration. If the value is not specified anywhere, `LC_NUMERIC` value from your system is used. |

The filter is implemented by calling function [babel.dates.format\_currency](https://babel.pocoo.org/en/latest/api/numbers.html#babel.numbers.format_currency).

Usage example: currency formatting (one Japanese yen). Locale (Japan) and currency (yen) are set in the extension settings.
```yaml
extensions:
  babel:
    locale: ja_JP
    currency: JPY
dialog:
- condition: true
  response: |
    {{ 1|format_currency }}
```
```
🧑 hello
🤖 ￥1
```

The format can also be specified explicitly.
The syntax of the pattern is described in [documentation of babel library](https://babel.pocoo.org/en/latest/numbers.html#pattern-syntax).
For example:
```yaml
extensions:
  babel:
    locale: en
dialog:
- condition: true
  response: |
    {{ 1099.98|format_currency(currency='EUR', format='#,##0.00 ¤¤¤') }}
```
```
🧑 hello
🤖 1,099.98 euros
```


If the `currency` value is not specified anywhere, an `BotError` exception will be raised:
```yaml
extensions:
  babel: {}
dialog:
- condition: true
  response: |
    {{ 1|format_currency }}
```
```
🧑 hello
logs
✗  `currency` is not set
```
