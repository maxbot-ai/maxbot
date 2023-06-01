"""Command `stories` of bots."""
import pprint
from datetime import timedelta, timezone
from pathlib import Path
from uuid import uuid4

import click
from marshmallow import Schema, ValidationError, fields, pre_load, validates_schema
from rich.console import Console

from ..context import get_utc_time_default
from ..maxml import markup, pretty
from ..rpc import RpcRequestSchema
from ..schemas import ResourceSchema
from ._bot import resolve_bot


@click.command(short_help="Run bot stories")
@click.option(
    "--bot",
    "-B",
    "bot_spec",
    required=True,
    help=(
        "Path for bot file or directory or the Maxbot instance to load. The instance can be in "
        "the form 'module:name'. Module can be a dotted import. Name is not required if it is 'bot'."
    ),
)
@click.option(
    "--stories",
    "-S",
    "stories_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to YAML file with stories",
)
def stories(bot_spec, stories_file):
    """Run bot stories."""
    bot = resolve_bot(bot_spec)

    original_comparator = markup.Value.COMPARATOR
    try:
        markup.Value.COMPARATOR = markup_value_rendered_comparator
        if stories_file:
            return _stories_impl(bot, stories_file)
        return _stories_impl(bot, Path(bot.resources.base_directory) / "stories.yaml")
    finally:
        markup.Value.COMPARATOR = original_comparator


def _stories_impl(bot, stories_file):
    console = Console()
    command_schema = bot.dialog_manager.CommandSchema(many=True)
    bot.dialog_manager.utc_time_provider = StoryUtcTimeProvider()

    for story in create_story_schema(bot).load_file(stories_file):
        console.print(story["name"], end=" ")
        dialog = {"channel_name": "stories", "user_id": str(uuid4())}
        bot.dialog_manager.utc_time_provider.on_start_new_story()

        for i, turn in enumerate(story["turns"]):
            bot.dialog_manager.utc_time_provider.tick(turn.get("utc_time"))

            if "message" in turn:
                response = bot.process_message(turn["message"], dialog)
            elif "rpc" in turn:
                response = bot.process_rpc(turn["rpc"], dialog)
            else:
                raise AssertionError("Either message or rpc must be provided.")

            for expected in turn["response"]:
                if command_schema.loads(expected) == response:
                    break
            else:
                status = "XFAIL" if story["xfail"] else "FAILED"
                expected = [command_schema.loads(r) for r in turn["response"]]
                console.print(_format_mismatch(status, i, expected, response, command_schema))
                if not story["xfail"]:
                    raise click.Abort()
                break
        else:
            console.print("OK")
    return 0


class StoryUtcTimeProvider:
    """Stories datetime."""

    def __init__(self):
        """Create new class instance."""
        self.value = None

    def on_start_new_story(self):
        """Reset value for new story."""
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


def create_story_schema(bot):
    """Create marshmallow schema of story objects.

    :param MaxBot bot: Created bot.
    :return ResourceSchema: Created schema.
    """

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
        xfail = fields.Bool(load_default=False)
        name = fields.Str(required=True)
        turns = fields.Nested(_TurnSchema, many=True, required=True)

    return _StorySchema(many=True)


def markup_value_rendered_comparator(lhs, rhs):
    """Compare `markup.Value` by rendered value."""
    if isinstance(lhs, (markup.Value, str)) and isinstance(rhs, (markup.Value, str)):
        lhs_rendered = lhs if isinstance(lhs, str) else lhs.render()
        return lhs_rendered == (rhs if isinstance(rhs, str) else rhs.render())
    return False


def _format_mismatch(status, turn_index, expected, actual, command_schema):
    expected_str = "\n-or-\n".join(pretty.print_xml(e, command_schema) for e in expected)
    actual_str = pretty.print_xml(actual, command_schema)

    def _shift(s):
        return "\n".join(f"  {line}" for line in s.splitlines())

    return f"{status} at step [{turn_index}]\nExpected:\n{_shift(expected_str)}\nActual:\n{_shift(actual_str)}"
