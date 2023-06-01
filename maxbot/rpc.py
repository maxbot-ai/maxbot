"""MaxBot RPC."""

from .errors import BotError, YamlSnippet
from .maxml import Schema, ValidationError, fields
from .resources import InlineResources
from .schemas import ResourceSchema


class RpcManager:
    """Handle RPC calls."""

    def __init__(self):
        """Create new class instance."""
        self._schemas = {}

    def __bool__(self):
        """Check if any rpc methods configured."""
        return bool(self._schemas)

    def load_resources(self, resources):
        """Load RPC resources.

        :param Resources resources: Bot resources.
        """
        self._schemas = {}
        for d in resources.load_rpc(MethodSchema(many=True)):
            method = d["method"]
            if method in self._schemas:
                raise BotError(f"Duplicate method {method!r}", YamlSnippet.from_data(method))
            self._schemas[method] = Schema.from_dict(
                {p["name"]: fields.Raw(required=p.get("required")) for p in d.get("params", [])}
            )

    def load_inline_resources(self, source):
        """Load dialog resources from YAML-string.

        :param str source: A YAML-string with resources.
        """
        self.load_resources(InlineResources(source))

    def get_params_schema(self, method):
        """Get the schame to validate method arguments."""
        return self._schemas.get(method)

    def parse_request(self, request_data):
        """Parse incoming request data.

        :param dict request_data: Incoming request data.
        :return: Parsed request data.
        """
        try:
            request = RpcRequestSchema().load(request_data)
        except ValidationError as exc:
            raise RpcError("Invalid Request", -32600, exc.normalized_messages()) from exc

        params_schema = self.get_params_schema(request["method"])
        if params_schema is None:
            raise RpcError("Method not found", -32601, request["method"])
        errors = params_schema().validate(request.get("params", {}))
        if errors:
            raise RpcError("Invalid params", -32602, errors)

        return request

    def blueprint(self, channels, callback):
        """Create web application blueprint to receive incoming updates.

        :param ChannelCollection channels: Channels to respond.
        :param callable callback: a callback for received messages.
        :return Blueprint: Blueprint for sanic app.
        """
        # lazy import to speed up load time
        from sanic import Blueprint
        from sanic.response import json

        bp = Blueprint("rpc")

        @bp.post("/rpc/<channel_name>/<user_id>")
        async def endpoint(request, channel_name, user_id):
            """Process RPC requests with sanic.

            :param sanic.request.Request request: Sanic request.
            :param str channel_name: The name of the channel in which the conversation is taking place.
            :param str user_id: The ID of the user with whom the conversation is taking place.
            :return dict: Flask accepted RPC response
            """
            try:
                channel = channels.get(channel_name)
                if channel is None:
                    raise RpcError("Unknown channel", -32100, channel_name)
                await callback(request.json, channel, user_id)
            except RpcError as exc:
                return json(
                    {"error": {"code": exc.code, "message": exc.message, "data": exc.data}}
                )
            return json({"result": None})

        return bp


class RpcError(RuntimeError):
    """An error occured during RPC request processing."""

    def __init__(self, message, code, data):
        """Create new class instance.

        :param str message: Error message.
        :param int code: Error code.
        :param any data: Error details.
        """
        self.message, self.code, self.data = message, code, data


class RpcRequestSchema(Schema):
    """Deserialize and validate RPC Request Object."""

    # The name of the method to be invoked.
    method = fields.String(required=True)

    # Parameter values to be used during the invocation of the method.
    # Will be validated later depending of the method.
    params = fields.Dict(fields.String(), fields.Raw())


class ParamSchema(Schema):
    """RPC formal parameter definition."""

    # The name of the parameter.
    name = fields.String(required=True)

    # Whether the parameter is required.
    required = fields.Boolean()


class MethodSchema(ResourceSchema):
    """JSON-RPC method definition."""

    # Method name.
    method = fields.String(required=True)

    # Formal parameters of the method.
    params = fields.Nested(ParamSchema, many=True)
