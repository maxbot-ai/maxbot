# HTTP pool limit

With the pool limit object, you can control the size of the connection pool.
We use the `Limits` from the [httpx](https://www.python-httpx.org/) library as the value.

## Fields

| Name                        | Type                                    | Description                                          | Default value |
| --------------------------- | --------------------------------------- | ---------------------------------------------------- | ------------- |
| `max_keepalive_connections` | [Integer](/design-reference/numbers.md) | Number of allowable keep-alive connections           | 20            |
| `max_connections`           | [Integer](/design-reference/numbers.md) | Maximum number of allowable connections              | 100           |
| `keepalive_expiry`          | [Float](/design-reference/numbers.md)   | Time limit on idle keep-alive connections in seconds | 5.0           |

