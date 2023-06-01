# datetime extension

This extension provides template filters to convert input value to date/time.
The filters throw an exception (`BotError`) if the conversion is not possible.

## `tz` filter {#tz}

Retrieve a time zone object from a string representation. An empty string is interpreted as local time.

Usage example: getting local time in `Asia/Dubai` timezone.
```yaml
extensions:
  datetime: {}
dialog:
- condition: true
  response: |
    {{ utc_time.astimezone("Asia/Dubai"|tz).isoformat() }}
```
```
🧑 hello
🤖 2023-05-29T20:28:40.864665+04:00
```

The set of supported time zones depends on your system.
A well-known list of timezones can be found on [Wikipedia](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) (`TZ identifier` column).

If the timezone is not recognized, an error will occur:
```yaml
extensions:
  datetime: {}
dialog:
- condition: true
  response: |
    {{ "XYZ"|tz }}
```
```
🧑 hello
logs
✗  Unknown timezone: 'XYZ'
```

## `datetime` filter {#datetime}

Convert input value to [datetime](https://docs.python.org/3/library/datetime.html#datetime-objects).
The input value can be of the following types: [datetime](https://docs.python.org/3/library/datetime.html#datetime-objects), [date](https://docs.python.org/3/library/datetime.html#date-objects), [time](https://docs.python.org/3/library/datetime.html#time-objects), [int](/design-reference/numbers.md), [float](/design-reference/numbers.md), [str](/design-reference/strings.md).

In the following example, we convert the ISO 8601 format string into a [datetime](https://docs.python.org/3/library/datetime.html#datetime-objects) value and
print string representing this date and time.

```yaml
extensions:
  datetime: {}
dialog:
- condition: true
  response: |
    {{ ("2023-05-24T10:00:00+00:00"|datetime).ctime() }}
```
```
🧑 hello
🤖 Wed May 24 10:00:00 2023
```

## `date` filter {#date}

Convert input value to [date](https://docs.python.org/3/library/datetime.html#date-objects).
The input value can be of the following types: [datetime](https://docs.python.org/3/library/datetime.html#datetime-objects), [date](https://docs.python.org/3/library/datetime.html#date-objects), [int](/design-reference/numbers.md), [float](/design-reference/numbers.md), [str](/design-reference/strings.md)

In the following example, we convert integer into a [date](https://docs.python.org/3/library/datetime.html#date-objects) value and
print day of the week.
```yaml
extensions:
  datetime: {}
dialog:
- condition: true
  response: |
    {{ ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
        "Sunday"][(1684922400|date).weekday()] }}
```
```
🧑 hello
🤖 Wednesday
```

## `time` filter {#time}

Convert input value to [time](https://docs.python.org/3/library/datetime.html#time-objects).
The input value can be of the following types: [datetime](https://docs.python.org/3/library/datetime.html#datetime-objects), [time](https://docs.python.org/3/library/datetime.html#time-objects), [int](/design-reference/numbers.md), [float](/design-reference/numbers.md), [str](/design-reference/strings.md)

In the following example, we convert float into a [time](https://docs.python.org/3/library/datetime.html#time-objects) value and
print time value in ISO 8601 format.
```yaml
extensions:
  datetime: {}
dialog:
- condition: true
  response: |
    {{ (1684922400.0|time).isoformat() }}
```
```
🧑 hello
🤖 10:00:00+00:00
```
