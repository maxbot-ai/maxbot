from base64 import b64encode

import pytest
import respx

from maxbot.bot import MaxBot
from maxbot.errors import BotError


@pytest.mark.parametrize("method", ("get", "post", "put", "delete"))
def test_tag(method):
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% """
        + method.upper()
        + """ "http://127.0.0.1/endpoint" %}
            test
    """
    )
    _test_mock_common(bot, method)


def test_service_args():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1/endpoint
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call(service='my_service') %}
            test
    """
    )
    _test_mock_common(bot, "get")


def test_service_not_found():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call(service='my_service') %}
            test
    """
    )
    with pytest.raises(BotError) as excinfo:
        bot.process_message("hey bot")
    assert str(excinfo.value) == 'Unknown REST service "my_service"'


def test_service_in_url():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" %}
            test
    """
    )
    _test_mock_common(bot, "get")


def test_method_default_get():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call(url="http://127.0.0.1/endpoint") %}
            test
    """
    )
    _test_mock_common(bot, "get")


def test_method_default_post():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call(url="http://127.0.0.1/endpoint", body={"a": 1}) %}
            test
    """
    )
    _test_mock_common(bot, "post")


def test_method_service():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
              method: post
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call(url="my_service://endpoint") %}
            test
    """
    )
    _test_mock_common(bot, "post")


def test_method_args():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
              method: post
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call(url="my_service://endpoint", method="put") %}
            test
    """
    )
    _test_mock_common(bot, "put")


def test_url_and_base_url():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call(service="my_service", url="endpoint") %}
            test
    """
    )
    _test_mock_common(bot, "get")


def test_base_url():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1/endpoint
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call(service="my_service") %}
            test
    """
    )
    _test_mock_common(bot, "get")


def test_url():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call(url="http://127.0.0.1/endpoint") %}
            test
    """
    )
    _test_mock_common(bot, "get")


def test_url_not_specified():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% set _ = rest_call() %}
            test
    """
    )
    with pytest.raises(BotError) as excinfo:
        bot.process_message("hey bot")
    assert str(excinfo.value) == "URL is not specified"


def test_headers():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
              headers: {"a": "a", "b": "b"}
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" headers {"b": "2", "c": "3"} %}
            test
    """
    )

    def _match(request):
        assert request.headers["a"] == "a"
        assert request.headers["b"] == "2"
        assert request.headers["c"] == "3"
        return True

    _test_mock_common(bot, "get", additional_matcher=_match)


def test_parameters():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
              parameters: {"a": "a", "b": "b"}
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" parameters {"b": "2", "c": "3"} %}
            test
    """
    )

    def _match(request):
        assert request.url.query == b"a=a&b=2&c=3"
        return True

    _test_mock_common(bot, "get", additional_matcher=_match)


def test_timeout_default():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" %}
            test
    """
    )

    def _match(request):
        assert request.extensions["timeout"] == {"connect": 5, "pool": 5, "read": 5, "write": 5}
        return True

    _test_mock_common(bot, "get", additional_matcher=_match)


def test_timeout_service():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
              timeout: 6
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" %}
            test
    """
    )

    def _match(request):
        assert request.extensions["timeout"] == {"connect": 6, "pool": 6, "read": 6, "write": 6}
        return True

    _test_mock_common(bot, "get", additional_matcher=_match)


def test_timeout_args():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
              timeout: 6
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" timeout 7 %}
            test
    """
    )

    def _match(request):
        assert request.extensions["timeout"] == {"connect": 7, "pool": 7, "read": 7, "write": 7}
        return True

    _test_mock_common(bot, "get", additional_matcher=_match)


def test_auth_service():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
              auth:
                user: myuser
                password: mypassword
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" %}
            test
    """
    )

    def _match(request):
        assert request.headers["Authorization"] == "Basic " + b64encode(
            b"myuser:mypassword"
        ).decode("ascii")
        return True

    _test_mock_common(bot, "get", additional_matcher=_match)


def test_auth_args():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
              auth:
                user: myuser
                password: mypassword
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" auth {"user": "myuser2", "password": "mypassword2"} %}
            test
    """
    )

    def _match(request):
        assert request.headers["Authorization"] == "Basic " + b64encode(
            b"myuser2:mypassword2"
        ).decode("ascii")
        return True

    _test_mock_common(bot, "get", additional_matcher=_match)


def test_200_json():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% GET "http://127.0.0.1/endpoint" %}
            {{ rest.ok|tojson }}|{{ rest.status_code }}|{{ rest.json.success|tojson }}
    """
    )
    _test_mock_common(bot, "get", json=dict(success=1), text="true|200|1")


@pytest.mark.parametrize("on_error", ("", 'on_error "break_flow"'))
def test_server_error(on_error, respx_mock):
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% GET "http://127.0.0.1/endpoint" """
        + on_error
        + """ %}
            {{ rest.ok|tojson }}|{{ rest.status_code }}
    """
    )
    respx_mock.get("http://127.0.0.1/endpoint").respond(status_code=500)
    with pytest.raises(BotError) as excinfo:
        bot.process_message("hey bot")
    assert "REST call failed: Server error '500 Internal Server Error'" in str(excinfo.value)
    assert len(respx_mock.calls) == 1


def test_server_error_continue():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% GET "http://127.0.0.1/endpoint" on_error "continue" %}
            {{ rest.ok|tojson }}|{{ rest.status_code }}
    """
    )
    _test_mock_common(bot, "get", status_code=500, text="false|500")


def test_invalid_on_error():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% GET "http://127.0.0.1/endpoint" on_error "try_again" %}
            {{ rest.ok|tojson }}|{{ rest.status_code }}
    """
    )
    with pytest.raises(BotError) as excinfo:
        bot.process_message("hey bot")
    assert str(excinfo.value) == "on_error invalid value: try_again"


@respx.mock
def _test_mock_common(
    bot,
    method,
    additional_matcher=None,
    json=None,
    status_code=200,
    text="test",
):
    route = respx.request(method, "http://127.0.0.1/endpoint").respond(
        json=json, status_code=status_code
    )
    commands = bot.process_message("hey bot")
    assert commands == [{"text": text}]
    assert route.call_count == 1
    if additional_matcher is not None:
        additional_matcher(route.calls.last.request)
