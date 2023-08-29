# rest extension

The `rest` extension is designed to perform HTTP requests, the input and output of which are described by JSON objects.
This extension provides global function `rest_call` and Jinja tags for every possible HTTP method:
`GET`, `POST`, `PUT`, `DELETE` and `PATCH`.

## Extension configuration

| Name                        | Type                                            | Description                       |
| --------------------------- | ----------------------------------------------- | --------------------------------- |
| `services`                  | Sequence (list) of [Service](#service)          | Pre-configured remote server data |
| `timeout`                   | [Timeout](/design-reference/timeout.md)         | Default HTTP request timeout      |
| `limits`                    | [Pool limits](/design-reference/pool-limits.md) | HTTP pool limits configuration    |
| `garbage_collector_timeout` | [Time delta](/design-reference/timedelta.md)    | Garbage collector timeout         |

Value `garbage_collector_timeout` sets the time interval not more often than garbage collector will be triggered.
Garbage collector removes cached results older than `garbage_collector_timeout`.
Default value: 1 hour.

### `Service`

Each `Service` object has the following format:

| Field name   | Type                                            | Description                                                    |
| ------------ | ----------------------------------------------- | -------------------------------------------------------------- |
| `name`\*     | [String](/design-reference/strings.md)          | Unique name (case-insensitive)                                 |
| `method`     | [String](/design-reference/strings.md)          | HTTP request method: `get`, `post`, `put`, `delete` or `patch` |
| `base_url`   | [String](/design-reference/strings.md)          | Basic part of the URL                                          |
| `auth`       | [Auth](#auth)                                   | Authentication data                                            |
| `headers`    | [Dictionary](/design-reference/dictionaries.md) | HTTP headers                                                   |
| `parameters` | [Dictionary](/design-reference/dictionaries.md) | URL parameters                                                 |
| `timeout`    | [Timeout](/design-reference/timeout.md)         | Default HTTP request timeout                                   |
| `limits`     | [Pool limits](/design-reference/pool-limits.md) | HTTP pool limits configuration                                 |
| `cache`      | [Time delta](/design-reference/timedelta.md)    | Time for which a successful requests is cached                 |

If `limits` field is not specified, the value of the `limits` will be taken from [extension configuration](#extension-configuration).
If both values are missing, the default values will be used (see [Pool limits](/design-reference/pool-limits.md)).

If `cache` field is specified, the all results of a successful HTTP requests for this serivce will be cached.
Be careful with this feature. We **recommend to cache only** `GET` requests.

### `Auth`

`Auth` object has the following format:

| Field name   | Type                                   | Description   |
| ------------ | -------------------------------------- | ------------- |
| `user`\*     | [String](/design-reference/strings.md) | User name     |
| `password`\* | [String](/design-reference/strings.md) | User password |

## `rest_call` function

Arguments of function `rest_call`:

| Name         | Type                                   | Description |
| ------------ | -------------------------------------- | ----------- |
| `service`    | [String](/design-reference/strings.md) | Unique name of [service](#service) from configuration (case-insensitive) |
| `url`        | [String](/design-reference/strings.md) | URL |
| `method`     | [String](/design-reference/strings.md) | HTTP request method: `get`, `post`, `put`, `delete` or `patch` |
| `auth`       | [Auth](#auth)                          | Authentication data  |
| `body`       | [Dictionary](/design-reference/dictionaries.md) or [String](/design-reference/strings.md) | HTTP request body |
| `headers`    | [Dictionary](/design-reference/dictionaries.md) | HTTP headers |
| `parameters` | [Dictionary](/design-reference/dictionaries.md) | URL parameters |
| `timeout`    | [Integer](/design-reference/numbers.md)         | Request timeout in seconds |
| `on_error`   | [String](/design-reference/strings.md) | Function behavior when an error occurs: `continue` or `break_flow` |
| `cache`      | [Integer](/design-reference/numbers.md) | Time (in seconds) for which a successful request is cached |

The `rest_call` function returns an dictionary:

| Field name      | Type                                     | Description               |
| --------------- | ---------------------------------------- | ------------------------- |
| `ok`\*          | [Boolean](/design-reference/booleans.md) | Request success flag      |
| `status_code`\* | [Integer](/design-reference/numbers.md)  | HTTP response status code |
| `json`\*        | Any                                      | Response data             |


### Arguments `service` and `url`

When calling `rest_call` function, there are two ways to refer to a service:
* specify argument `service`
* specify argument `url` in the format `service://[url]"`

For example, the following bot responds to the user with a link to the latest release from GitHub.
```yaml
extensions:
  rest:
    services:
    - name: api_github
      base_url: https://api.github.com/
dialog:
- condition: true
  response: |
    {% set rest = rest_call(method="get", url="api_github://repos/maxbot-ai/maxbot/releases/latest") %}
    {{ rest.json.html_url }}
```

We can make the same call by explicitly referring to the service by name:
```
    {% set rest = rest_call(method="get", service="api_github", url="repos/maxbot-ai/maxbot/releases/latest") %}
```

Or not use extension configuration at all:
```yaml
extensions:
  rest: {}
dialog:
- condition: true
  response: |
    {% set rest = rest_call(method="get", url="https://api.github.com/repos/maxbot-ai/maxbot/releases/latest") %}
    {{ rest.json.html_url }}
```

### Argument `method`

HTTP request method: `get`, `post`, `put`, `delete` or `patch`.
Default value: `post` if argument `body` is given, otherwise `get`

### Argument `auth`

Authentication data.
If no argument is passed, then the value is taken from the service.
If the value is not set anywhere, then the request is made without authentication.

### Argument `body`

If value of `body` is a [string](/design-reference/strings.md), it is passed to body of HTTP request as is.

If value of `body` is a [dictionary](/design-reference/dictionaries.md):
* if `Content-Type` is explicitly specified in `headers` by `application/x-www-form-urlencoded`, the `body` will be URL-encoded;
* in the opposite case, the `body` will be JSON-encoded.

### Argument `headers`

HTTP request headers.
The dictionary passed in function argument is merged with dictionary from the service.
Values from function argument have higher precedence.

### Argument `parameters`

URL parameters.
The dictionary passed in function argument is merged with dictionary from the service.
Values from function argument have higher precedence.


### Argument `timeout`

Request timeout in seconds. Value 0 is ignored.
If no argument is passed, then the value is taken from the service or from extension configuration.
If the value is not set anywhere, then the request is executed with a timeout of 5 seconds.

### Argument `on_error`

This argument controls the behavior of the function in case of an error in the execution of an HTTP request:
* `continue`: function will return control.
  The error signal is the `ok` field, which has the value `False` on the returned dictionary.
* `break_flow` (default value): function will throw an exception `BotError`.

### Argument `cache`

If `cache` argument (or the corresponding setting in [Service](#service)) is given, the result of a successful HTTP request will be cached.
Be careful with this feature. We **recommend to cache only** `GET` requests.

## Using Jinja tags

You can use Jinja tags instead of `rest_call` function: `GET`, `POST`, `PUT`, `DELETE` or `PATCH`.
These tags correspond to the available HTTP request methods.

As a result of the tag operation, a local variable `rest` will be created.
It will be filled with the return value of function `rest_call`.

Let's rewrite the example where the bot replies to the user with a link to the latest release from GitHub.
```yaml
extensions:
  rest:
    services:
    - name: api_github
      base_url: https://api.github.com/
dialog:
- condition: true
  response: |
    {% GET "api_github://repos/maxbot-ai/maxbot/releases/latest" %}
    {{ rest.json.html_url }}
```

The tag is followed by a string with the [value of the URL](#arguments-service-and-url).
The remaining arguments of `rest_call` function can be specified further in pairs: `argument_name` (unquoted), `value`.

For example, increasing the timeout to 15 seconds looks like this:
```
    {% GET "api_github://repos/maxbot-ai/maxbot/releases/latest" timeout 15 %}
```
