"""MaxBot stories engine."""
import pprint
from asyncio import new_event_loop
from datetime import timedelta, timezone
from uuid import uuid4

from ..context import get_utc_time_default
from ..maxml import Schema, ValidationError, fields, markup, pre_load, pretty, validates_schema
from ..rpc import RpcRequestSchema
from ..schemas import ResourceSchema


class Stories:
    """Load and run stories."""

    class MismatchError(Exception):
        """Run story mismatch error."""

        def __init__(self, message):
            """Create new instance."""
            super().__init__(message)

        @property
        def message(self):
            """Mismatch formatted message."""
            return self.args[0]

    def __init__(self, bot):
        """Create new instance.

        :param MaxBot bot: Bot instance.
        """
        self.bot = bot
        self.command_schema = self.bot.dialog_manager.CommandSchema(many=True)
        self.loop = new_event_loop()

        class _RpcRequestSchemaWithDesc(RpcRequestSchema):
            @validates_schema
            def validates_schema(self, data, **kwargs):
                params_schema = bot.rpc.get_params_schema(data["method"])
                if params_schema is None:
                    raise ValidationError("Method not found", field_name="method")
                errors = params_schema().validate(data.get("params", {}))
                if errors:
                    raise ValidationError(pprint.pformat(errors), field_name="params")

        class _TurnSchema(Schema):
            utc_time = fields.DateTime()
            message = fields.Nested(bot.dialog_manager.MessageSchema)
            rpc = fields.Nested(_RpcRequestSchemaWithDesc)
            response = fields.List(fields.Str(), required=True)

            @pre_load
            def response_short_syntax(self, data, **kwargs):
                response = data.get("response")
                if isinstance(response, str):
                    data.update(response=[response])
                return data

            @validates_schema
            def validates_schema(self, data, **kwargs):
                if ("message" in data) == ("rpc" in data):
                    raise ValidationError("Exactly one of 'message' or 'rpc' is required.")

        class _StorySchema(ResourceSchema):
            name = fields.Str(required=True)
            turns = fields.Nested(_TurnSchema, many=True, required=True)
            markers = fields.List(fields.Str(), load_default=list)

        self.schema = _StorySchema(many=True)

    def load(self, fspath):
        """Load stories from file.

        :param str fspath: Stories file path.
        :return list[dict]: Loaded stories.
        """
        return self.schema.load_file(fspath)

    def run(self, story):
        """Run one story."""
        self.loop.run_until_complete(self.arun(story))

    async def arun(self, story):
        """Run one story asynchronously."""
        original_comparator = markup.Value.COMPARATOR
        markup.Value.COMPARATOR = markup_value_rendered_comparator
        try:
            self.bot.dialog_manager.utc_time_provider = StoryUtcTimeProvider()
            dialog = {"channel_name": "stories", "user_id": str(uuid4())}

            for i, turn in enumerate(story["turns"]):
                self.bot.dialog_manager.utc_time_provider.tick(turn.get("utc_time"))

                with self.bot.persistence_manager(dialog) as tracker:
                    if "message" in turn:
                        response = await self.bot.dialog_manager.process_message(
                            turn["message"], dialog, tracker.get_state()
                        )
                    elif "rpc" in turn:
                        response = await self.bot.dialog_manager.process_rpc(
                            turn["rpc"], dialog, tracker.get_state()
                        )
                    else:
                        raise AssertionError()  # pragma: not covered

                for expected in turn["response"]:
                    if self.command_schema.loads(expected) == response:
                        break
                else:
                    expected = [self.command_schema.loads(r) for r in turn["response"]]
                    raise self.MismatchError(
                        _format_mismatch(i, expected, response, self.command_schema)
                    )
        finally:
            markup.Value.COMPARATOR = original_comparator


class StoryUtcTimeProvider:
    """Stories datetime."""

    def __init__(self):
        """Create new class instance."""
        self.value = None

    def tick(self, dt=None):
        """Calculate datetime for next step of story.

        :param datetime dt: Datetime from stry turn (optional).
        """
        if dt:
            if dt.tzinfo:
                self.value = dt.astimezone(timezone.utc)
            else:
                self.value = dt.replace(tzinfo=timezone.utc)
        elif self.value is not None:
            self.value += timedelta(seconds=10)

    def __call__(self):
        """Get current datetime."""
        return get_utc_time_default() if self.value is None else self.value


def markup_value_rendered_comparator(lhs, rhs):
    """Compare `markup.Value` by rendered value."""
    if isinstance(lhs, (markup.Value, str)) and isinstance(rhs, (markup.Value, str)):
        lhs_rendered = lhs if isinstance(lhs, str) else lhs.render()
        return lhs_rendered == (rhs if isinstance(rhs, str) else rhs.render())
    return False


def _format_mismatch(turn_index, expected, actual, command_schema):
    expected_str = "\n-or-\n".join(pretty.print_xml(e, command_schema) for e in expected)
    actual_str = pretty.print_xml(actual, command_schema)

    def _shift(s):
        return "\n".join(f"  {line}" for line in s.splitlines())

    return f"Mismatch at step [{turn_index}]\nExpected:\n{_shift(expected_str)}\nActual:\n{_shift(actual_str)}"
