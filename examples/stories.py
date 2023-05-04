import asyncio
import logging
import pprint
import random
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from marshmallow import Schema, ValidationError, fields, pre_load, validates_schema

from maxbot.bot import MaxBot
from maxbot.rpc import RpcRequestSchema
from maxbot.schemas import ResourceSchema

if len(sys.argv) < 2:
    print("Please, provide project dir")
    print(f"{sys.argv[0]} <dirname>")
    sys.exit(1)

project_dir = Path(sys.argv[1])
bot = MaxBot.from_file(project_dir / "bot.yaml")
RESPONSE_SCHEMA = bot.dialog_manager.dialog_flow._context["schema"](many=True)


class RpcRequestSchemaWithDesc(RpcRequestSchema):
    @validates_schema
    def validates_schema(self, data, **kwargs):
        params_schema = bot.rpc.get_params_schema(data["method"])
        if params_schema is None:
            raise ValidationError("Method not found", field_name="method")
        errors = params_schema().validate(data.get("params", {}))
        if errors:
            raise ValidationError(pprint.pformat(errors), field_name="params")


class TurnSchema(Schema):
    message = fields.Nested(bot.dialog_manager.MessageSchema)
    rpc = fields.Nested(RpcRequestSchemaWithDesc)
    response = fields.Str(required=True)

    @validates_schema
    def validates_schema(self, data, **kwargs):
        if ("message" in data) == ("rpc" in data):
            raise ValidationError("Exactly one of 'message' or 'rpc' is required.")


class StorySchema(ResourceSchema):
    name = fields.Str(required=True)
    turns = fields.Nested(TurnSchema, many=True, required=True)


def main():
    for story in StorySchema(many=True).loads((project_dir / "stories.yaml").read_text()):
        print(story["name"], end=" ")
        dialog = {"channel_name": "stories", "user_id": str(random.randrange(sys.maxsize))}
        for turn in story["turns"]:
            if "message" in turn:
                response = bot.process_message(turn["message"], dialog)
            elif "rpc" in turn:
                response = bot.process_rpc(turn["rpc"], dialog)
            else:
                assert False, "Either message or rpc must be provided."

            expected = RESPONSE_SCHEMA.loads(turn["response"])
            if expected != response:
                print("FAILED\nExpected:\n%s\nActual:\n%s" % (expected, response))
                sys.exit(1)
        print("OK")


main()
