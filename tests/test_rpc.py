from unittest.mock import AsyncMock, sentinel

import pytest

from maxbot import MaxBot
from maxbot.errors import BotError
from maxbot.rpc import RpcError, RpcManager


@pytest.fixture
def rpc():
    rpc = RpcManager()
    rpc.load_inline_resources(
        """
        rpc:
         - method: say_hello
    """
    )
    return rpc


def test_rpc_load(rpc):
    assert bool(rpc) == True
    rpc.load_inline_resources("{}")
    assert bool(rpc) == False


def test_parse_request(rpc):
    request = rpc.parse_request({"method": "say_hello"})
    assert request["method"] == "say_hello"


def test_duplicate_method(rpc):
    with pytest.raises(BotError) as excinfo:
        rpc.load_inline_resources(
            """
            rpc:
              - method: say_hello
              - method: say_hello
        """
        )
    assert "Duplicate method" in str(excinfo)


def test_invalid_method(rpc):
    with pytest.raises(RpcError) as excinfo:
        rpc.parse_request({"method": "say_goodbye"})
    assert excinfo.value.message == "Method not found"
    assert excinfo.value.data == "say_goodbye"


def test_params(rpc):
    rpc.load_inline_resources(
        """
        rpc:
         - method: say_hello
           params:
             - name: user_name
               required: true
    """
    )
    request = rpc.parse_request({"method": "say_hello", "params": {"user_name": "Bob"}})
    assert request["method"] == "say_hello"
    assert request["params"] == {"user_name": "Bob"}


def test_params_missing_required(rpc):
    rpc.load_inline_resources(
        """
        rpc:
         - method: say_hello
           params:
             - name: user_name
               required: true
    """
    )
    with pytest.raises(RpcError) as excinfo:
        rpc.parse_request({"method": "say_hello"})
    assert excinfo.value.message == "Invalid params"
    assert excinfo.value.data == {"user_name": ["Missing data for required field."]}


def test_params_missing_optional(rpc):
    rpc.load_inline_resources(
        """
        rpc:
         - method: say_hello
           params:
             - name: user_name
    """
    )
    request = rpc.parse_request({"method": "say_hello"})
    assert request["method"] == "say_hello"
    assert "params" not in request


def test_params_undeclared(rpc):
    with pytest.raises(RpcError) as excinfo:
        rpc.parse_request({"method": "say_hello", "params": {"user_name": "Bob"}})
    assert excinfo.value.message == "Invalid params"
    assert excinfo.value.data == {"user_name": ["Unknown field."]}


def test_invalid_request(rpc):
    with pytest.raises(RpcError) as excinfo:
        rpc.parse_request({"xxx": "say_hello"})
    assert excinfo.value.message == "Invalid Request"
    assert excinfo.value.data == {
        "method": ["Missing data for required field."],
        "xxx": ["Unknown field."],
    }


# def test_parse_error(rpc):
#    with pytest.raises(RpcError) as excinfo:
#        rpc.parse_request("XXX")
#    assert excinfo.value.message == "Parse error"
#    assert excinfo.value.data == "Expecting value: line 1 column 1 (char 0)"


def test_endpoint_success(rpc):
    callback = AsyncMock()

    from sanic import Sanic

    app = Sanic(__name__)
    app.blueprint(rpc.blueprint({"my_channel": sentinel.my_channel}, callback))
    request, response = app.test_client.post("/rpc/my_channel/123", json={"method": "say_hello"})

    assert response.status_code == 200, response.text
    assert response.json == {"result": None}

    request, channel, user_id = callback.call_args.args
    assert request["method"] == "say_hello"
    assert not "params" in request
    assert channel == sentinel.my_channel
    assert user_id == "123"


def test_endpoint_error(rpc):
    callback = AsyncMock()

    from sanic import Sanic

    app = Sanic(__name__)
    app.blueprint(rpc.blueprint({}, callback))
    request, response = app.test_client.post("/rpc/my_channel/123", json={"method": "say_hello"})

    assert response.status_code == 200, response.text
    assert response.json == {
        "error": {"code": -32100, "data": "my_channel", "message": "Unknown channel"},
    }
    assert not callback.called
