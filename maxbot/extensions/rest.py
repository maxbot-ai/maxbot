"""Builtin MaxBot extension: REST calls from jinja scenarios."""
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import httpx
from jinja2 import nodes
from jinja2.ext import Extension

from ..errors import BotError, YamlSnippet
from ..maxml import PoolLimitSchema, Schema, TimeDeltaSchema, TimeoutSchema, fields, validate

logger = logging.getLogger(__name__)


class _JinjaExtension(Extension):
    tags = {
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
    }

    def parse(self, parser):
        method = parser.stream.current.value.lower()
        lineno = next(parser.stream).lineno
        kwargs = [
            nodes.Keyword("method", nodes.Const(method)),
        ]
        url = parser.parse_expression()
        kwargs.append(nodes.Keyword("url", url))

        while parser.stream.current.type == "name":
            name = parser.stream.expect("name")
            value = parser.parse_expression()
            kwargs.append(nodes.Keyword(name.value, value))

        restcall = nodes.Call(nodes.Name("rest_call", "load"), [], kwargs, None, None)

        target = nodes.Name("rest", "store")
        # {% set rest = rest_call(method=..., ...) %}
        return nodes.Assign(target, restcall).set_lineno(lineno)


def _now():
    return datetime.now(timezone.utc)


class _ServiceAuth(Schema):
    user = fields.Str(required=True)
    password = fields.Str(required=True)


class _Service(Schema):
    name = fields.Str(required=True)
    method = fields.Str(
        validate=validate.OneOf(
            [
                "get",
                "post",
                "put",
                "delete",
                "patch",
            ]
        )
    )
    auth = fields.Nested(_ServiceAuth())
    headers = fields.Dict(keys=fields.Str(), values=fields.Str(), load_default=dict)
    parameters = fields.Dict(keys=fields.Str(), values=fields.Str(), load_default=dict)
    timeout = fields.Nested(TimeoutSchema())
    base_url = fields.Url()
    limits = fields.Nested(PoolLimitSchema())
    cache = fields.Nested(TimeDeltaSchema())


class RestExtension:
    """Extension class."""

    class ConfigSchema(Schema):
        """Extension configuration schema."""

        services = fields.List(fields.Nested(_Service()), load_default=list)
        timeout = fields.Nested(TimeoutSchema())
        limits = fields.Nested(PoolLimitSchema())
        garbage_collector_timeout = fields.Nested(
            TimeDeltaSchema(), load_default=TimeDeltaSchema.VALUE_TYPE(hours=1)
        )

    @dataclass(frozen=True)
    class _CacheValue:
        return_value: dict
        created: datetime = field(default_factory=_now, init=False)

    def __init__(self, builder, config):
        """Extension entry point.

        :param BotBuilder builder: MaxBot builder.
        :param dict config: Extension configuration.
        """
        self.services = {}
        for service in config.get("services", []):
            service_name = service["name"].lower()
            if service_name in self.services:
                raise BotError(
                    f"Duplicate REST service names: {service['name']!r} and "
                    f"{self.services[service_name]['name']!r}",
                    YamlSnippet.from_data(service["name"]),
                )
            self.services[service_name] = service
        self.allowed_schemes = frozenset({"http", "https"} | set(self.services.keys()))
        self.timeout = config.get("timeout", TimeoutSchema.DEFAULT)
        self.limits = config.get("limits", PoolLimitSchema.DEFAULT)
        self.garbage_collector_timeout = config["garbage_collector_timeout"]
        builder.add_template_global(self._rest_call, "rest_call")
        builder.jinja_env.add_extension(_JinjaExtension)
        self.cache_container = {}
        self.cache_container_garbage_collector_ts = _now()

    async def _rest_call(self, **args):
        args = dict(args)
        service = self._prepare_service(args)

        method = _prepare_method(args, service)
        url = _prepare_url(args, service)
        logger.debug("%s %s", method.upper(), url)

        headers = _prepare_headers(args, service)
        params = _prepare_params(args, service)
        body = args.get("body")
        auth = _prepare_auth(args, service)

        cache_key, return_value = None, None
        cache_timeout = _prepare_cache_timeout(args, service)
        if cache_timeout:
            cache_key = _create_cache_key(method, url, headers, params, body, auth)

        now = _now()
        if now > (self.cache_container_garbage_collector_ts + self.garbage_collector_timeout):
            # ⚔️ garbage collection time
            self.cache_container_garbage_collector_ts = now
            garbage = []
            for key, value in self.cache_container.items():
                if cache_key == key and now <= (value.created + cache_timeout):
                    return_value = value.return_value
                elif now >= (value.created + self.garbage_collector_timeout):
                    garbage.append(key)
            for key in garbage:
                self.cache_container.pop(key, None)
        else:
            value = self.cache_container.get(cache_key)
            if value and now <= (value.created + cache_timeout):
                return_value = value.return_value

        if return_value:
            logger.debug("cache hit: %s", return_value)
            return return_value

        on_error = _prepare_on_error(args)

        session = service["session"]
        kwargs = {}
        headers = _prepare_headers(args, service)
        body = args.get("body")
        if isinstance(body, Mapping):
            _, content_type = next(
                iter([(k, v) for k, v in headers.items() if k.lower() == "content-type"]),
                (None, "application/json"),
            )
            if content_type.lower().strip().startswith("application/x-www-form-urlencoded"):
                kwargs.update(data=body)
            else:
                kwargs.update(json=body)
        else:
            kwargs.update(content=body)

        try:
            resp = await session.request(
                method,
                url,
                headers=headers,
                params=params,
                auth=auth,
                timeout=self._prepare_timeout(args, service),
                **kwargs,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as error:
            result = {"ok": False, "status_code": resp.status_code, "json": {}}
            return _on_request_exception(on_error, error, result)
        except httpx.HTTPError as error:
            return _on_request_exception(on_error, error, result={"ok": False})

        try:
            return_value = {"ok": True, "status_code": resp.status_code, "json": resp.json()}
        except ValueError as error:
            logger.exception(
                "\n".join(
                    [
                        "JSON deserialisation error",
                        "Content-Type: " + resp.headers.get("Content-Type", ""),
                        "Response: " + resp.text,
                        str(error),
                    ]
                )
            )
            return {"ok": True, "status_code": resp.status_code, "json": {}}
        if cache_timeout:
            self.cache_container[cache_key] = self._CacheValue(return_value)
        return return_value

    def _prepare_service(self, args):
        service_name = args.get("service")
        if service_name:
            service = self.services.get(service_name.lower())
            if service is None:
                _raise(f'Unknown REST service "{service_name}"')
        else:
            splitted = args.get("url", "").split("://", 1)
            service = {}
            if len(splitted) == 2:
                scheme = splitted[0].lower()
                service = self.services.get(scheme, {})
                if service:
                    args["url"] = splitted[1]
                elif scheme not in self.allowed_schemes:
                    one_of = ["http", "https"] + list(self.services.keys())
                    raise BotError(
                        (
                            f"Unknown schema ({splitted[0]!r}) in URL {args['url']!r}\n"
                            f"Must be one of: {', '.join(one_of)}"
                        )
                    )
            else:
                service = {}

        if "session" not in service:
            service["session"] = httpx.AsyncClient(limits=service.get("limits", self.limits))

        return service

    def _prepare_timeout(self, args, service):
        return args.get("timeout") or service.get("timeout") or self.timeout


def _prepare_on_error(args):
    on_error = args.get("on_error", "break_flow")
    if on_error not in ["break_flow", "continue"]:
        _raise(f"on_error invalid value: {on_error}")
    return on_error


def _prepare_method(args, service):
    default = "post" if "body" in args else "get"
    return args.get("method") or service.get("method") or default


def _prepare_url(args, service):
    base_url = service.get("base_url")
    url = args.get("url") or args.get("path")
    if base_url and url:
        return urljoin(base_url, url)
    return base_url or url or _raise("URL is not specified")


def _prepare_headers(args, service):
    return {**service.get("headers", {}), **args.get("headers", {})}


def _prepare_params(args, service):
    return {**service.get("parameters", {}), **args.get("parameters", {})}


def _prepare_auth(args, service):
    auth = args.get("auth") or service.get("auth")
    return (auth["user"], auth["password"]) if auth else None


def _prepare_cache_timeout(args, service):
    cache_timeout = args.get("cache")
    if cache_timeout is None:
        cache_timeout = service.get("cache")
    if isinstance(cache_timeout, timedelta):
        return cache_timeout
    return None if cache_timeout is None else timedelta(seconds=cache_timeout)


def _create_cache_key(method, url, headers, params, body, auth):
    return json.dumps(
        {"m": method, "u": url, "h": headers, "p": params, "b": body, "a": auth}, sort_keys=True
    )


def _raise(message):
    raise BotError(message)


def _on_request_exception(on_error, error, result):
    message = "REST call failed: " + str(error)
    logger.exception(message)
    if on_error == "continue":
        return result
    assert on_error == "break_flow"
    return _raise(message)
