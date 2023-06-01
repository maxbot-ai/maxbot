"""Builtin MaxBot extension: REST calls from jinja scenarios."""
import logging
from urllib.parse import urljoin

import httpx
from jinja2 import nodes
from jinja2.ext import Extension

from ..errors import BotError
from ..maxml import Schema, fields, validate

logger = logging.getLogger(__name__)


class _ServiceAuth(Schema):
    user = fields.Str(required=True)
    password = fields.Str(required=True)


class _Service(Schema):
    name = fields.Str(required=True)
    method = fields.Str(validate=validate.OneOf(["get", "post", "put", "delete"]))
    auth = fields.Nested(_ServiceAuth())
    headers = fields.Dict(keys=fields.Str(), values=fields.Str(), load_default=dict)
    parameters = fields.Dict(keys=fields.Str(), values=fields.Str(), load_default=dict)
    timeout = fields.Int()
    base_url = fields.Url()


class _JinjaExtension(Extension):
    tags = {"GET", "POST", "PUT", "DELETE"}

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


class RestExtension:
    """Extension class."""

    class ConfigSchema(Schema):
        """Extension configuration schema."""

        services = fields.List(fields.Nested(_Service()), load_default=list)

    def __init__(self, builder, config):
        """Extension entry point.

        :param BotBuilder builder: MaxBot builder.
        :param dict config: Extension configuration.
        """
        self.services = {s["name"]: s for s in config.get("services", [])}
        builder.add_template_global(self._rest_call, "rest_call")
        builder.jinja_env.add_extension(_JinjaExtension)

    async def _rest_call(self, **args):
        args = dict(args)
        service = self._prepare_service(args)

        method = _prepare_method(args, service)
        url = _prepare_url(args, service)
        logger.debug("%s %s", method.upper(), url)

        on_error = _prepare_on_error(args)

        session = service["session"]
        resp = await session.request(
            method,
            url,
            headers=_prepare_headers(args, service),
            params=_prepare_params(args, service),
            timeout=_prepare_timeout(args, service),
            json=args.get("body"),
            auth=_prepare_auth(args, service),
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPError as error:
            message = "REST call failed: " + str(error)

            logger.exception(message)
            if on_error == "continue":
                return {"ok": False, "status_code": resp.status_code, "json": {}}

            assert on_error == "break_flow"
            _raise(message)

        try:
            return {"ok": True, "status_code": resp.status_code, "json": resp.json()}
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

    def _prepare_service(self, args):
        service_name = args.get("service")
        if service_name:
            service = self.services.get(service_name)
            if service is None:
                _raise(f'Unknown REST service "{service_name}"')
        else:
            splitted = args.get("url", "").split("://")
            service = self.services.get(splitted[0], {}) if len(splitted) == 2 else {}
            if service:
                args["url"] = splitted[1]

        if "session" not in service:
            service["session"] = httpx.AsyncClient()

        return service


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


def _prepare_timeout(args, service):
    return args.get("timeout") or service.get("timeout") or 5


def _prepare_auth(args, service):
    auth = args.get("auth") or service.get("auth")
    return (auth["user"], auth["password"]) if auth else None


def _raise(message):
    raise BotError(message)
