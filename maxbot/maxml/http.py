"""HTTPX library (https://www.python-httpx.org/) configuration."""
import httpx
from marshmallow import Schema, fields, post_load, pre_load  # noqa: F401


class TimeoutSchema(Schema):
    """HTTP request timeout schema.

    @see https://www.python-httpx.org/advanced/#timeout-configuration
    """

    default = fields.Float(load_default=5.0)
    connect = fields.Float()
    read = fields.Float()
    write = fields.Float()
    pool = fields.Float()

    @pre_load
    def short_syntax(self, data, **kwargs):
        """Short syntax is available.

        timeout: 1.2
        -> httpx.Timeout(connect=1.2, read=1.2, write=1.2, pool=1.2)
        """
        if isinstance(
            data,
            (
                float,
                int,
                str,
            ),
        ):
            try:
                return {"default": float(data)}
            except ValueError:
                pass
        return data

    @post_load
    def return_httpx_timeout(self, data, **kwargs):
        """Create and return httpx.Timeout by loaded data."""
        return httpx.Timeout(
            connect=data.get("connect", data["default"]),
            read=data.get("read", data["default"]),
            write=data.get("write", data["default"]),
            pool=data.get("pool", data["default"]),
        )

    DEFAULT = httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)


class PoolLimitSchema(Schema):
    """HTTP pool limit schema.

    @see https://www.python-httpx.org/advanced/#pool-limit-configuration
    """

    max_keepalive_connections = fields.Int(load_default=20)
    max_connections = fields.Int(load_default=100)
    keepalive_expiry = fields.Float(load_default=5.0)

    @post_load
    def return_httpx_limits(self, data, **kwargs):
        """Create and return httpx.Timeout by loaded data."""
        return httpx.Limits(
            max_keepalive_connections=data["max_keepalive_connections"],
            max_connections=data["max_connections"],
            keepalive_expiry=data["keepalive_expiry"],
        )

    DEFAULT = httpx.Limits(max_keepalive_connections=20, max_connections=100, keepalive_expiry=5.0)
