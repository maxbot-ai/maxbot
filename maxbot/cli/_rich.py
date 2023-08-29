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
Progress = functools.partial(
    _Progress, console=STDERR, redirect_stdout=False, redirect_stderr=False
)


class PrettyJournal:
    """Pretty journal to console."""

    class VerbosityLevel(IntEnum):
        """Level of verbosity."""

        INFO = 0
        NLU = 1
        VAR_DIFF = 1
        JOURNAL = 2
        VAR_FULL = 2

    def __init__(self, verbosity=0, console=None):
        """Create class instance.

        :param int verbosity: Output verbosity.
        :param Console|None console: Console to write.
        """
        self.verbosity = verbosity
        self.console = console or STDOUT

    def __call__(self, ctx):
        """Write turn context.

        :param TurnContext ctx: Context of the dialog turn.
        """
        if self.verbosity >= self.VerbosityLevel.INFO:
            self.console.line()
            self.print_dialog(ctx.dialog)
            if ctx.message:
                self.print_message(ctx.message)
            if ctx.rpc:
                self.print_rpc(asdict(ctx.rpc.request))
            if ctx.commands:
                self.print_commands(ctx.commands, ctx.command_schema)
            if self.verbosity >= self.VerbosityLevel.NLU:
                self.print_intents(ctx.intents)
                if ctx.entities.all_objects:
                    self.print_entities(ctx.entities)
            if ctx.journal_events:
                self.print_journal_events(ctx.journal_events)
            if ctx.error:
                self.print_error(ctx.error)
            if self.verbosity >= self.VerbosityLevel.VAR_FULL or (
                ctx.error and self.verbosity >= self.VerbosityLevel.VAR_DIFF
            ):
                self.print_var_full(ctx.state)
        elif ctx.error:
            self.console.line()
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
        extractors = [
            self._extract_log_event,
        ]
        if self.verbosity >= self.VerbosityLevel.VAR_DIFF:
            extractors.append(self._extract_user_diff)
            extractors.append(self._extract_slots_diff)
        if self.verbosity >= self.VerbosityLevel.JOURNAL:
            extractors.append(self._extract_journal_event)

        table = Table.grid(padding=(0, 1))
        table.title = "journal_events" if len(extractors) > 1 else "logs"
        table.title_justify = "left"
        table.expand = True
        table.add_column()
        table.add_column(ratio=1)

        table_is_empty = True
        for event in journal_events:
            for e in extractors:
                first, second = e(event)
                if first:
                    table.add_row(first, second)
                    table_is_empty = False
                    break

        if not table_is_empty:
            self.console.print(table)

    def print_error(self, exc):
        """Print bot error.

        :param BotError exc: An error occured.
        """
        message = Lines()
        message.append(exc.message)
        for snippet in exc.snippets:
            message.extend(bot_error_snippet(snippet))
        self._print_log("ERROR", message)

    def print_var_full(self, state):
        """Print snapshot of slots.* and user.*.

        :param StateVariables state: Container of variables.
        """
        self._print_full(state, "slots")
        self._print_full(state, "user")

    def _print_full(self, state, field_name):
        d = getattr(state, field_name)
        if d:
            table = Table.grid(padding=(0, 1))
            table.title = field_name
            table.title_justify = "left"
            table.expand = True
            table.add_column()
            table.add_column(ratio=1)

            for name, value in d.items():
                table.add_row(Text.styled(f".{name}", "bold"), _yaml_syntax(value))

            self.console.print(table)

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
        level = self._LOG_LEVELS.get(level.upper()) if isinstance(level, str) else None
        if not isinstance(message, str):
            message = Pretty(message, indent_size=2, indent_guides=True)
        return (level, message) if level else (None, None)

    def _extract_user_diff(self, event):
        return self._extract_diff(event, "user")

    def _extract_slots_diff(self, event):
        return self._extract_diff(event, "slots")

    def _extract_diff(self, event, kind):
        t, p = event.get("type"), event.get("payload")
        if isinstance(p, dict):
            if t == "assign":
                name, value = p.get(kind), p.get("value")
                if isinstance(name, str):
                    return Text.styled(f"{kind}.{name} =", "green"), Pretty(
                        value, indent_size=2, indent_guides=True
                    )
            elif t == "delete":
                name = p.get(kind)
                if isinstance(name, str):
                    return Text.styled("❌ delete", "red"), Text.styled(f"{kind}.{name}", "bold")
        return None, None

    def _extract_journal_event(self, event):
        return Text.styled(event.get("type", "?"), "yellow"), _yaml_syntax(event.get("payload"))


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
        self.setFormatter(logging.Formatter("%(asctime)s - %(processName)s - %(message)s"))

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
