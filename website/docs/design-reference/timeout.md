# HTTP request timeout

The timeout object is used to control the maximum time to wait for an HTTP request to complete.
We use the `Timeout` from the `httpx` library as the value.
More details on the use of timeout can be found in the [documentation for the httpx library](https://www.python-httpx.org/advanced/#timeout-configuration).


## Fields

There are four different types of timeouts that may occur. These are `connect`, `read`, `write`, and `pool` timeouts.

* The `connect` timeout specifies the maximum amount of time to wait until a socket connection to the requested host is established.
* The `read` timeout specifies the maximum duration to wait for a chunk of data to be received (for example, a chunk of the response body).
* The `write` timeout specifies the maximum duration to wait for a chunk of data to be sent (for example, a chunk of the request body).
* The `pool` timeout specifies the maximum duration to wait for acquiring a connection from the connection pool.

All fields are of type [float](/design-reference/numbers.md) and contain values in seconds.

## How to set a value

Let's look at the ways of setting a value using the example of [rest](/extensions/rest.md) extension configuration.

If no value is set:
```yaml
extensions:
  rest: {}
```
5 seconds timeout will be applied by default:
```python
httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)
```

You can use a short syntax to fill the values of all fields with the same value:
```yaml
extensions:
  rest:
    timeout: 6.5
```
So the value of all fields will be filled with the value of 6.5 seconds
```python
httpx.Timeout(connect=6.5, read=6.5, write=6.5, pool=6.5)
```

You can fill the value of selected fields:
```yaml
extensions:
  rest:
    timeout:
      read: 1.0
      write: 1.0
```
The values of the other fields will be filled in by default:
```python
httpx.Timeout(connect=5.0, read=1.0, write=1.0, pool=5.0)
```

The default value can also be changed:
```yaml
extensions:
  rest:
    timeout:
      connect: 3.5
      default: 2.0
```
For the above example, we obtain the following value:
```python
httpx.Timeout(connect=3.5, read=2.0, write=2.0, pool=2.0)
```
