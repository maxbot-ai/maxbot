# `timedelta` object representation

A [timedelta](https://docs.python.org/3/library/datetime.html#timedelta-objects) object represents a duration, the difference between two dates or times.

## Feilds

`timedelta` object is defined as a set of fields:
* weeks
* days
* hours
* minutes
* seconds
* microseconds
* milliseconds

All fields are of type [integer](/design-reference/numbers.md) and default to `0`.

## How to set a value

Let's look at the ways of setting a value using the example of [rest](/extensions/rest.md) extension configuration.

You can use a short syntax to specify a value in seconds:
```yaml
extensions:
  rest:
    services:
      name: my_server
      cache: 10
```
For the above example, values of successful HTTP requests will be cached for 10 seconds.
It's equivalent to the following:
```yaml
extensions:
  rest:
    services:
      name: my_server
      cache:
        seconds: 10
```

If we want to cache results for 90 minutes (5400 seconds), we can set it like this:
```yaml
extensions:
  rest:
    services:
      name: my_server
      cache:
        hours: 1
        minutes: 30
```
Or like this:
```yaml
extensions:
  rest:
    services:
      name: my_server
      cache:
        minutes: 90
```
