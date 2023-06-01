"""Bot journals."""
import json
import os
from dataclasses import asdict

from ..maxml import pretty
from ._yaml_dumper import yaml_frendly_dumps


def create_journal(verbose, quiet, journal_file, journal_output):
    """Create bot journal from provided specification.

    :param int verbose: Verbose level.
    :param bool quiet: Do not log to console.
    :param file journal_file: Logging to the file.
    :param str journal_output: File journal output format ("json" or "yaml").
    """
    journal = JournalChain()
    if not quiet:
        from ._rich import PrettyJournal  # speed up loading time

        journal.chain.append(PrettyJournal(verbose))
    if journal_file:
        journal.chain.append(
            FileJournal(
                journal_file,
                {"json": Dumper.json_line, "yaml": Dumper.yaml_triple_dash}[journal_output],
            )
        )
    return journal


class JournalChain:
    """Sequentially call several journals."""

    def __init__(self, chain=None):
        """Create class instance."""
        self.chain = chain or []

    def __call__(self, ctx):
        """Process turn context.

        :param TurnContext ctx: Context of the dialog turn.
        """
        for journal in self.chain:
            journal(ctx)


class FileJournal:
    """A journal that write to file."""

    def __init__(self, f, dumps):
        """Create class instance.

        :param file f: Target file to write.
        :dump callable dumps: Dump object to string.
        """
        self.f = f
        self.dumps = dumps

    def __call__(self, ctx):
        """Write turn context.

        :param TurnContext ctx: Context of the dialog turn.
        """
        record = {
            "time": str(ctx.utc_time),
            "dialog": ctx.dialog,
            "intents": {
                "top": None if ctx.intents.top is None else asdict(ctx.intents.top),
                "ranking": [asdict(i) for i in ctx.intents.ranking],
            },
            "entities": [asdict(e) for e in ctx.entities.all_objects],
            "events": ctx.journal_events,
        }
        if ctx.message:
            record["message"] = ctx.message
        if ctx.rpc:
            record["rpc"] = asdict(ctx.rpc.request)
        if ctx.commands:
            record["response"] = pretty.print_xml(ctx.commands, ctx.command_schema)
        if ctx.error:
            record["error"] = {"message": ctx.error.message}
            if ctx.error.snippets:
                record["error"]["snippets"] = [s.format() for s in ctx.error.snippets]
        self.f.write(self.dumps(record))
        self.f.flush()


class Dumper:
    """Dumpers for FileJournal (`dumps` in ctor)."""

    @staticmethod
    def json_line(data):
        """Dump objects to JSON line."""

        def default(o):
            return repr(o)

        return json.dumps(data, default=default) + os.linesep

    @staticmethod
    def yaml_triple_dash(data):
        """Dump object to YAML with three dashes (`---`) at end."""
        return yaml_frendly_dumps(data) + "---" + os.linesep
