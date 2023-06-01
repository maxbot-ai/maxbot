"""Rich library related stuff.

Rich library is heavy, we put all its stuf here and defer its load.

"""
import functools
import logging
from dataclasses import asdict
from datetime import datetime
from enum import IntEnum

from rich.console import Console
from rich.containers import Lines
from rich.logging import RichHandler
from rich.pretty import Pretty
from rich.progress import Progress as _Progress
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ..context import TurnContext
from ..errors import BotError, XmlSnippet, YamlSnippet
from ..maxml import markup, pretty
from ._yaml_dumper import yaml_frendly_dumps

STDOUT = Console()
STDERR = Console(stderr=True)
# Make sure the STDERR output displayed above the progress display.
Progress = functools.partial(_Progress, console=STDERR)


class PrettyJournal:
    """Pretty journal to console."""

    class VerbosityLevel(IntEnum):
        """Level of verbosity."""

        NLU = 1
        JOURNAL = 2

    def __init__(self, verbose=0, console=None):
        """Create class instance.

        :param int verbose: Output verbosity.
        :param Console|None console: Console to write.
        """
        self.verbose = verbose
        self.console = console or STDOUT

    def __call__(self, ctx):
        """Write turn context.

        :param TurnContext ctx: Context of the dialog turn.
        """
        self.console.line()
        self.print_dialog(ctx.dialog)
        if ctx.message:
            self.print_message(ctx.message)
        if ctx.rpc:
            self.print_rpc(asdict(ctx.rpc.request))
        if ctx.commands:
            self.print_commands(ctx.commands, ctx.command_schema)
        if self.verbose >= self.VerbosityLevel.NLU:
            self.print_intents(ctx.intents)
            if ctx.entities.all_objects:
                self.print_entities(ctx.entities)
        if ctx.journal_events:
            self.print_journal_events(ctx.journal_events)
        if ctx.error:
            self.print_error(ctx.error)

    def print_dialog(self, dialog):
        """Print dialog info.

        :param dict dialog: Dialog information.
        """
        turn_time = datetime.now().strftime("[%X]")
        self.console.print(
            f"{turn_time}, {dialog['channel_name']}#{dialog['user_id']}",
            style="dim",
            highlight=False,
        )

    def print_intents(self, intents):
        """Print recognized NLU intents.

        :param IntentsResult intents: Intents recognized from the message.
        """
        output = Table.grid(padding=(0, 1))
        output.title = "intents"
        output.title_justify = "left"
        output.expand = True
        output.add_column()
        output.add_column()
        output.add_column(ratio=1)

        def _print_intent(label, intent):
            output.add_row(Text.styled(label, "bold"), "name", Text.styled(intent.name, "yellow"))
            output.add_row("", "confidence", str(intent.confidence))

        if intents.top is None:
            output.add_row(Text.styled(".irrelevant", "bold"), "", "")
        else:
            _print_intent(".top", intents.top)
        for i, intent in enumerate(intents.ranking):
            label = f".ranking[{i}]"
            _print_intent(label, intent)
        self.console.print(output)

    def print_entities(self, entities):
        """Print recognized NLU entities.

        :param EntitiesResult entities: Entities recognized from the message.
        """
        output = Table.grid(padding=(0, 1))
        output.title = "entities"
        output.title_justify = "left"
        output.expand = True
        output.add_column()
        output.add_column()
        output.add_column(ratio=1)
        for i, entity in enumerate(entities.all_objects):
            label = f".all_objects[{i}]"
            output.add_row(Text.styled(label, "bold"), "name", Text.styled(entity.name, "yellow"))
            output.add_row("", "value", str(entity.value))
            output.add_row("", "literal", entity.literal)
            output.add_row("", "start_char", str(entity.start_char))
            output.add_row("", "end_char", str(entity.end_char))
        self.console.print(output)

    def print_message(self, message):
        """Print user message.

        :param dict message: User message.
        """
        if "text" in message and len(message) == 1:
            message = message["text"]
        self._print_speech("🧑", message)

    def print_rpc(self, rpc):
        """Print RPC request.

        :param RpcContext rpc: Context of RPC request.
        """
        self._print_speech("💡", rpc)

    def print_commands(self, commands, command_schema):
        """Print response commands.

        :param list[dict] commands: Response commands.
        :param Schema command_schema: Schema of commands.
        """
        simple_text = (
            len(commands) == 1
            and "text" in commands[0]
            and isinstance(commands[0]["text"], markup.Value)
        )
        if simple_text:
            commands = commands[0]["text"].render()
            lexer = None
        else:
            assert command_schema
            commands = pretty.print_xml(commands, command_schema)
            lexer = "XML"
        self._print_speech("🤖", commands, lexer=lexer)

    def print_journal_events(self, journal_events):
        """Print events from journal.

        :param list[dict] journal_events: Journal.
        """
        verbose_journal = self.verbose >= self.VerbosityLevel.JOURNAL
        output = Table.grid(padding=(0, 1))
        output.title = "journal_events" if verbose_journal else "logs"
        output.title_justify = "left"
        output.expand = True
        output.add_column()
        output.add_column(ratio=1)
        for event in journal_events:
            level, message = self._extract_log_event(event)
            if level:
                if not isinstance(message, str):
                    message = Pretty(message, indent_size=2, indent_guides=True)
                output.add_row(self._LOG_LEVELS[level.upper()], message)
            elif verbose_journal:
                output.add_row(
                    Text.styled(event.get("type", "?"), "yellow"),
                    _yaml_syntax(event.get("payload")),
                )
        self.console.print(output)

    def print_error(self, exc):
        """Print bot error.

        :param BotError exc: An error occured.
        """
        message = Lines()
        message.append(exc.message)
        for snippet in exc.snippets:
            message.extend(bot_error_snippet(snippet))
        self._print_log("ERROR", message)

    def _print_speech(self, speaker, data, lexer=None):
        output = Table.grid(padding=(0, 1))
        output.expand = True
        output.add_column()
        output.add_column(ratio=1, overflow="fold")

        if isinstance(data, str):
            speech = data if lexer is None else Syntax(data, lexer, background_color="default")
        else:
            speech = _yaml_syntax(data)

        output.add_row(speaker, speech)
        self.console.print(output)

    _LOG_LEVELS = {
        "DEBUG": Text.styled("ⓘ ", "blue"),
        "WARNING": Text.styled("⚠ ", "yellow"),
        "ERROR": Text.styled("✗ ", "red"),
    }

    def _print_log(self, level, message):
        output = Table.grid(padding=(0, 1))
        output.expand = True
        output.add_column()
        output.add_column(ratio=1, overflow="fold")
        output.add_row(self._LOG_LEVELS[level.upper()], message)
        self.console.print(output)

    def _extract_log_event(self, event):
        level, message = TurnContext.extract_log_event(event)
        return (level, message) if level in self._LOG_LEVELS else (None, None)


class ConsoleLogHandler(RichHandler):
    """Customize rich log handler."""

    _level_text = {
        logging.DEBUG: "ⓘ ",
        logging.INFO: "✓",
        logging.WARNING: "⚠ ",
        logging.ERROR: "✗",
        logging.CRITICAL: "✗",
    }

    _level_style = {
        logging.DEBUG: Style(dim=True),
        logging.INFO: Style(color="green"),
        logging.WARNING: Style(color="yellow"),
        logging.ERROR: Style(color="red", bold=False),
        logging.CRITICAL: Style(color="red", bold=True),
    }

    def __init__(self):
        """Create new class instance."""
        super().__init__(console=STDERR, show_time=False, show_path=False)
        self.setFormatter(logging.Formatter("%(message)s"))

    def get_level_text(self, record):
        """Render the level prefix for log record.

        :param LogRecod record: Logging record.
        :return Text: Rendered prefix.
        """
        level_text = Text.styled(
            self._level_text[record.levelno], self._level_style[record.levelno]
        )
        return level_text

    def render_message(self, record, message):
        """Render message text in to Text.

        BotError must be logged as the first argument so that it can be nicely formatted.

        :param LogRecod record: Logging record.
        :param str message: String containing log message.
        :return ConsoleRenderable: Renderable to display log message.
        """
        if record.args and isinstance(record.args, tuple) and isinstance(record.args[0], BotError):
            return self.render_bot_error(record, record.args[0])
        return Text.styled(message, self._level_style[record.levelno])

    def render_bot_error(self, record, exc):
        """Render a BotError with a snippet.

        :param LogRecod record: Logging record.
        :param BotError exc: The error to print.
        """
        # we replace the actual message with a message without a snippet
        record.args = (exc.message,) + record.args[1:]
        # possible formatter is ignored for simplicity, because actually we are not using it
        message = record.getMessage()

        lines = Lines()
        lines.append(Text.styled(message, self._level_style[record.levelno]))
        # attach the formatted snippets
        for snippet in exc.snippets:
            lines.extend(bot_error_snippet(snippet))
        return lines


def bot_error_snippet(snippet):
    """Format YAML snippet to output to console."""
    assert isinstance(snippet, (XmlSnippet, YamlSnippet))
    lexer = "XML" if isinstance(snippet, XmlSnippet) else "YAML+Jinja"
    yield Text(snippet.format_location(), style="dim")
    yield Syntax(
        snippet.code,
        lexer,
        line_numbers=True,
        line_range=(snippet.line, snippet.line + 2),
        highlight_lines={snippet.line + 1},
    )


def _yaml_syntax(data):
    return Syntax(yaml_frendly_dumps(data).rstrip("\n"), "YAML", background_color="default")
