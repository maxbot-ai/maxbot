import pytest

from maxbot.errors import BotError
from maxbot.maxml import PoolLimitSchema, TimeoutSchema, fields
from maxbot.schemas import ResourceSchema


class Config(ResourceSchema):
    timeout = fields.Nested(TimeoutSchema())
    limits = fields.Nested(PoolLimitSchema())


def test_timeout_empty():
    data = Config().loads(
        """
      timeout: {}
    """
    )
    assert data["timeout"].connect == 5.0
    assert data["timeout"].read == 5.0
    assert data["timeout"].write == 5.0
    assert data["timeout"].pool == 5.0


def test_timeout_short_syntax():
    data = Config().loads(
        """
      timeout: 1.2
    """
    )
    assert data["timeout"].connect == 1.2
    assert data["timeout"].read == 1.2
    assert data["timeout"].write == 1.2
    assert data["timeout"].pool == 1.2


def test_timeout_error():
    with pytest.raises(BotError) as excinfo:
        Config().loads(
            """
          timeout: abc
        """
        )
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Invalid input type.\n"
        '  in "<unicode string>", line 2, column 20:\n'
        "    timeout: abc\n"
        "             ^^^\n"
    )


def test_timeout_default():
    data = Config().loads(
        """
      timeout:
        default: 3.6
    """
    )
    assert data["timeout"].connect == 3.6
    assert data["timeout"].read == 3.6
    assert data["timeout"].write == 3.6
    assert data["timeout"].pool == 3.6


def test_timeout_default_connect_pool():
    data = Config().loads(
        """
      timeout:
        default: 3.6
        connect: 10.0
        pool: 1.0
    """
    )
    assert data["timeout"].connect == 10.0
    assert data["timeout"].read == 3.6
    assert data["timeout"].write == 3.6
    assert data["timeout"].pool == 1.0


def test_timeout_connect_read_write_pool():
    data = Config().loads(
        """
      timeout:
        connect: 1.0
        read: 2.0
        write: 3.0
        pool: 4.0
    """
    )
    assert data["timeout"].connect == 1.0
    assert data["timeout"].read == 2.0
    assert data["timeout"].write == 3.0
    assert data["timeout"].pool == 4.0


def test_limits_empty():
    data = Config().loads(
        """
        limits: {}
    """
    )
    assert data["limits"].max_keepalive_connections == 20
    assert data["limits"].max_connections == 100
    assert data["limits"].keepalive_expiry == 5.0


def test_limits():
    data = Config().loads(
        """
        limits:
          max_keepalive_connections: 1
          max_connections: 2
          keepalive_expiry: 3
    """
    )
    assert data["limits"].max_keepalive_connections == 1
    assert data["limits"].max_connections == 2
    assert data["limits"].keepalive_expiry == 3.0
