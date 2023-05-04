"""Bot journals."""
import atexit
import json
import os
from dataclasses import asdict
from datetime import datetime

import click


def create_journal(target):
    """Create bot journal from provided specification.

    :param str target: The name of the journal and its arguments.
    """
    if target == "console":
        from ._rich import PrettyJournal  # speed up loading time

        return PrettyJournal()
    if target.startswith("file:"):
        return JsonLineJournal(filename=target.removeprefix("file:"))
    raise click.BadParameter(f"unknown journal {target!r}.", param_hint="--journal")


class JsonLineJournal:
    """A journal that writes JSON lines into a file."""

    def __init__(self, filename):
        """Create class instance.

        :param str filename: The name of the file to write.
        """
        try:
            f = open(filename, mode="a", encoding="utf8")  # pylint: disable=consider-using-with
        except IOError as e:
            raise click.BadParameter(f"could not open {filename!r}: {e!r}", param_hint="--journal")
        atexit.register(f.close)
        self.f = f

    def __call__(self, ctx):
        """Write turn context.

        :param TurnContext ctx: Context of the dialog turn.
        """
        record = {
            "time": str(datetime.now()),
            "dialog": ctx.dialog,
        }
        if ctx.message:
            record["message"] = ctx.message
        if ctx.rpc:
            record["rpc"] = asdict(ctx.rpc.request)
        if ctx.commands:
            record["response"] = ctx.commands
        for log in ctx.logs:
            message = log.message if isinstance(log.message, str) else repr(log.message)
            record.setdefault("logs", []).append({"level": log.level, "message": message})
        if ctx.error:
            record["error"] = {"message": ctx.error.message}
            if ctx.error.snippets:
                record["error"]["snippets"] = [s.format() for s in ctx.error.snippets]
        self.f.write(json.dumps(record) + os.linesep)
        self.f.flush()
