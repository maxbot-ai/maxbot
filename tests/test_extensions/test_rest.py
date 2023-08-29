from base64 import b64encode
from datetime import timedelta

import httpx
import pytest
import respx

import maxbot.extensions.rest
from maxbot.bot import MaxBot
from maxbot.errors import BotError

_GB_TIMEOUT = (
    maxbot.extensions.rest.RestExtension.ConfigSchema()
    .load({})["garbage_collector_timeout"]
    .total_seconds()
)


@pytest.mark.parametrize("method", ("get", "post", "put", "delete", "patch"))
def test_tag(method):
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |
            {% """
        + method.upper()
        + """ "http://127.0.0.1/endpoint" %}
            test
    """
    )
    _test_mock_common(bot, method)


def test_duplicate_services():
    with pytest.raises(BotError) as excinfo:
        MaxBot.inline(
            """
            extensions:
              rest:
                services:
                - name: my_service
                  base_url: http://127.0.0.1/
                - name: My_Service
                  base_url: http://127.0.0.2/
            dialog:
            - condition: true
              response: |-
                {% set _ = rest_call(service='my_service') %}
                test
        """
        )
    assert str(excinfo.value) == (
        "Duplicate REST service names: 'My_Service' and 'my_service'\n  in"
        ' "<unicode string>", line 7, column 25:\n'
        "      base_url: http://127.0.0.1/\n"
        "    - name: My_Service\n"
        "            ^^^\n"
        "      base_url: http://127.0.0.2/"
    )


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
          response: |
            {% set _ = rest_call(service='my_service') %}
            test
    """
    )
    _test_mock_common(bot, "get")


def test_service_case_insensitive():
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
            {% set _ = rest_call(service='mY_seRVICe') %}
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
          response: |
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
          response: |
            {% GET "my_service://endpoint" %}
            test
    """
    )
    _test_mock_common(bot, "get")


def test_service_in_url_case_insensitive():
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
            {% GET "My_SERVICe://endpoint" %}
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
          response: |
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
          response: |
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
          response: |
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
          response: |
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
          response: |
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
          response: |
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
          response: |
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
          response: |
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
          response: |
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
          response: |
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
          response: |
            {% GET "my_service://endpoint" %}
            test
    """
    )

    def _match(request):
        assert request.extensions["timeout"] == {"connect": 5, "pool": 5, "read": 5, "write": 5}
        return True

    _test_mock_common(bot, "get", additional_matcher=_match)


def test_timeout_config():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
            timeout:
              default: 5.1
              pool: 1
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" %}
            test
    """
    )

    def _match(request):
        assert request.extensions["timeout"] == {
            "connect": 5.1,
            "pool": 1,
            "read": 5.1,
            "write": 5.1,
        }
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
            timeout: 5.5
        dialog:
        - condition: true
          response: |
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
            timeout: 5.5
        dialog:
        - condition: true
          response: |
            {% GET "my_service://endpoint" timeout 7 %}
            test
    """
    )

    def _match(request):
        assert request.extensions["timeout"] == {"connect": 7, "pool": 7, "read": 7, "write": 7}
        return True

    _test_mock_common(bot, "get", additional_matcher=_match)


def test_limits_config(monkeypatch):
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
            limits:
              max_keepalive_connections: 1
              max_connections: 2
              keepalive_expiry: 3
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" %}
            test
    """
    )
    limits = []
    httpx_AsyncClient_ctor = httpx.AsyncClient.__init__

    def hook_AsyncClient_ctor(self, *args, **kwargs):
        limits.append(kwargs.get("limits"))
        httpx_AsyncClient_ctor(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", hook_AsyncClient_ctor)

    _test_mock_common(bot, "get")
    assert limits == [
        httpx.Limits(max_connections=2, max_keepalive_connections=1, keepalive_expiry=3.0)
    ]


def test_limits_service(monkeypatch):
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service
              base_url: http://127.0.0.1
              limits:
                max_keepalive_connections: 4
                max_connections: 5
                keepalive_expiry: 6
            limits:
              max_keepalive_connections: 1
              max_connections: 2
              keepalive_expiry: 3
        dialog:
        - condition: true
          response: |-
            {% GET "my_service://endpoint" %}
            test
    """
    )
    limits = []
    httpx_AsyncClient_ctor = httpx.AsyncClient.__init__

    def hook_AsyncClient_ctor(self, *args, **kwargs):
        limits.append(kwargs.get("limits"))
        httpx_AsyncClient_ctor(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", hook_AsyncClient_ctor)

    _test_mock_common(bot, "get")
    assert limits == [
        httpx.Limits(max_connections=5, max_keepalive_connections=4, keepalive_expiry=6.0)
    ]


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
          response: |
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
          response: |
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
          response: |
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
          response: |
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
          response: |
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
          response: |
            {% GET "http://127.0.0.1/endpoint" on_error "try_again" %}
            {{ rest.ok|tojson }}|{{ rest.status_code }}
    """
    )
    with pytest.raises(BotError) as excinfo:
        bot.process_message("hey bot")
    assert str(excinfo.value) == "on_error invalid value: try_again"


def test_network_error_continue():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% GET "http://127.0.0.1/endpoint" on_error "continue" %}
            {{ rest.ok }}
    """
    )
    assert _test_mock_network_error(bot, error=httpx.ConnectError) == [{"text": "False"}]


def test_network_error_break():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% GET "http://127.0.0.1/endpoint" %}
            {{ rest.ok }}
    """
    )
    with pytest.raises(BotError) as excinfo:
        _test_mock_network_error(bot, error=httpx.TimeoutException)
    assert str(excinfo.value) == "caused by httpx.TimeoutException: REST call failed: Mock Error"


def test_cache_args():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 %}
    """
    )
    _test_cache(bot)


def test_cache_service():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: localhost
              cache: 1
              base_url: http://127.0.0.1/
        dialog:
        - condition: true
          response: |
            {% GET "localhost://endpoint" %}
    """
    )
    _test_cache(bot)


def test_cache_expired_args(monkeypatch):
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 %}
    """
    )
    mock = {"now": maxbot.extensions.rest._now()}
    monkeypatch.setattr(maxbot.extensions.rest, "_now", lambda: mock["now"])

    _test_cache(
        bot,
        cached_successfully=False,
        between_calls=lambda: mock.update(now=mock["now"] + timedelta(seconds=2)),
    )


def test_cache_expired_service(monkeypatch):
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: localhost
              cache: 1
              base_url: http://127.0.0.1/
        dialog:
        - condition: true
          response: |
            {% GET "localhost://endpoint" %}
    """
    )
    mock = {"now": maxbot.extensions.rest._now()}
    monkeypatch.setattr(maxbot.extensions.rest, "_now", lambda: mock["now"])

    _test_cache(
        bot,
        cached_successfully=False,
        between_calls=lambda: mock.update(now=mock["now"] + timedelta(seconds=2)),
    )


def test_cache_garbage_collector_ignored(monkeypatch):
    bot = MaxBot.inline(
        f"""
        extensions:
          rest: {{}}
        dialog:
        - condition: true
          response: |
            {{% GET "http://127.0.0.1/endpoint" cache {_GB_TIMEOUT + 2}  %}}
    """
    )
    mock = {"now": maxbot.extensions.rest._now()}
    monkeypatch.setattr(maxbot.extensions.rest, "_now", lambda: mock["now"])

    _test_cache(
        bot,
        between_calls=lambda: mock.update(now=mock["now"] + timedelta(seconds=_GB_TIMEOUT + 1)),
    )


def test_cache_garbage_collector_expired(monkeypatch):
    bot = MaxBot.inline(
        f"""
        extensions:
          rest: {{}}
        dialog:
        - condition: true
          response: |
            {{% GET "http://127.0.0.1/endpoint" cache 1  %}}
    """
    )
    mock = {"now": maxbot.extensions.rest._now()}
    monkeypatch.setattr(maxbot.extensions.rest, "_now", lambda: mock["now"])

    _test_cache(
        bot,
        cached_successfully=False,
        between_calls=lambda: mock.update(now=mock["now"] + timedelta(seconds=_GB_TIMEOUT + 1)),
    )


def test_cache_garbage_collector_time(monkeypatch):
    mock = {"now": maxbot.extensions.rest._now()}
    monkeypatch.setattr(maxbot.extensions.rest, "_now", lambda: mock["now"])
    bot = MaxBot.inline(
        f"""
        extensions:
          rest: {{}}
        dialog:
        - condition: true
          response: |
            {{% GET "http://127.0.0.1/endpoint" cache {_GB_TIMEOUT + 1}  %}}
    """
    )

    mock.update(now=mock["now"] - timedelta(seconds=_GB_TIMEOUT + 3))
    _test_cache(
        bot,
        between_calls=lambda: mock.update(now=mock["now"] + timedelta(seconds=_GB_TIMEOUT)),
    )


@pytest.mark.parametrize(
    "field",
    (
        "headers",
        "parameters",
        "body",
        "auth",
    ),
)
def test_cache_dict_reorder(field):
    bot = MaxBot.inline(
        f"""
        extensions:
          rest: {{}}
        dialog:
        - condition: message.text == "1"
          response: |
            {{% GET "http://127.0.0.1/endpoint" cache 1 {field} {{"user": "v1", "password": "v2"}} %}}
        - condition: message.text == "2"
          response: |
            {{% GET "http://127.0.0.1/endpoint" cache 1 {field} {{"password": "v2", "user": "v1"}} %}}
    """
    )
    _test_cache(bot)


@pytest.mark.parametrize(
    "field",
    (
        "headers",
        "parameters",
        "body",
        "auth",
    ),
)
def test_cache_dict_mismatch(field):
    bot = MaxBot.inline(
        f"""
        extensions:
          rest: {{}}
        dialog:
        - condition: message.text == "1"
          response: |
            {{% GET "http://127.0.0.1/endpoint" cache 1 {field} {{"user": "v1", "password": "v2"}} %}}
        - condition: message.text == "2"
          response: |
            {{% GET "http://127.0.0.1/endpoint" cache 1 {field} {{"user": "v1", "password": "MISMATCH"}} %}}
    """
    )
    _test_cache(bot, cached_successfully=False)


def test_cache_url_service_match():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: localhost
              cache: 1
              base_url: http://127.0.0.1/
        dialog:
        - condition: message.text == "1"
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 %}
        - condition: message.text == "2"
          response: |
            {% GET "localhost://endpoint" %}
    """
    )
    _test_cache(bot)


def test_cache_url_mismatch():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: message.text == "1"
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 %}
        - condition: message.text == "2"
          response: |
            {% GET "http://127.0.0.1/endpoinX" cache 1 %}
    """
    )
    with respx.mock:
        route2 = respx.get("http://127.0.0.1/endpoinX").respond(json={})
        _test_cache(bot, cached_successfully=False, route2=route2)


def test_cache_on_error_ignore():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: message.text == "1"
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 on_error "continue" %}
        - condition: message.text == "2"
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 on_error "break_flow" %}
    """
    )
    _test_cache(bot)


def test_cache_method_mismatch():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: message.text == "1"
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 %}
        - condition: message.text == "2"
          response: |
            {% POST "http://127.0.0.1/endpoint" cache 1 %}
    """
    )
    with respx.mock:
        route2 = respx.post("http://127.0.0.1/endpoint").respond(json={})
        _test_cache(bot, cached_successfully=False, route2=route2)


def test_cache_timeout_ignore():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: message.text == "1"
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 timeout 1 %}
        - condition: message.text == "2"
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 timeout 2 %}
    """
    )
    _test_cache(bot)


def test_cache_error():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |
            {% GET "http://127.0.0.1/endpoint" cache 1 on_error "continue" %}
    """
    )
    with respx.mock:
        route = respx.get("http://127.0.0.1/endpoint").respond(status_code=500)
        _test_cache_mocked(bot, route, cached_successfully=False)


def test_misprint_service_name():
    bot = MaxBot.inline(
        """
        extensions:
          rest:
            services:
            - name: my_service1
              base_url: http://127.0.0.1
        dialog:
        - condition: true
          response: |-
            {% GET "my_service2://endpoint" %}
            {{ rest.ok }}
    """
    )
    with pytest.raises(BotError) as excinfo:
        bot.process_message("hey bot")
    assert str(excinfo.value) == (
        "Unknown schema ('my_service2') in URL 'my_service2://endpoint'\n"
        "Must be one of: http, https, my_service1"
    )


def test_request_body_urlencoded():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% POST "http://127.0.0.1/endpoint"
                body {"k": "v"}|urlencode
            %}
            test
    """
    )

    def _match(request):
        assert b"".join(b for b in request.stream) == b"k=v"
        return True

    _test_mock_common(bot, "post", additional_matcher=_match)


def test_request_body_urlencoded_content_type():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% POST "http://127.0.0.1/endpoint"
                body {"k": "v"}
                headers {'Content-Type': 'application/x-www-form-urlencoded'}
            %}
            test
    """
    )

    def _match(request):
        assert b"".join(b for b in request.stream) == b"k=v"
        return True

    _test_mock_common(bot, "post", additional_matcher=_match)


def test_request_body_json():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% POST "http://127.0.0.1/endpoint"
                body {"k": "v"}
            %}
            test
    """
    )

    def _match(request):
        assert b"".join(b for b in request.stream) == b'{"k": "v"}'
        return True

    _test_mock_common(bot, "post", additional_matcher=_match)


def test_request_body_raw():
    bot = MaxBot.inline(
        """
        extensions:
          rest: {}
        dialog:
        - condition: true
          response: |-
            {% POST "http://127.0.0.1/endpoint"
                body "k|v"
            %}
            test
    """
    )

    def _match(request):
        assert b"".join(b for b in request.stream) == b"k|v"
        return True

    _test_mock_common(bot, "post", additional_matcher=_match)


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


@respx.mock
def _test_cache(bot, **kwargs):
    route = respx.get("http://127.0.0.1/endpoint").respond(json={})
    _test_cache_mocked(bot, route, **kwargs)


def _test_cache_mocked(
    bot, route, cached_successfully=True, between_calls=lambda: None, route2=None
):
    bot.process_message("1")
    assert route.call_count == 1
    between_calls()
    bot.process_message("2")
    call_count = route.call_count + (route2.call_count if route2 else 0)
    assert call_count == (1 if cached_successfully else 2)


@respx.mock
def _test_mock_network_error(bot, error):
    route = respx.request("GET", "http://127.0.0.1/endpoint").mock(side_effect=error)
    commands = bot.process_message("hey bot")
    assert route.call_count == 1
    return commands
