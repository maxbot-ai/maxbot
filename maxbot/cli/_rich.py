"""Rich library related stuff.

Rich library is heavy, we put all its stuf here and defer its load.

"""
import functools
import logging
from dataclasses import asdict
from datetime import datetime

import yaml
from rich.console import Console
from rich.containers import Lines
from rich.logging import RichHandler
from rich.pretty import Pretty
from rich.progress import Progress as _Progress
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ..errors import BotError

STDOUT = Console()
STDERR = Console(stderr=True)
# Make sure the STDERR output displayed above the progress display.
Progress = functools.partial(_Progress, console=STDERR)


class PrettyJournal:
    """Pretty journal to console."""

    def __init__(self, console=None):
        """Create class instance.

        :param Console|None console: Console to write.
        """
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
            self.print_commands(ctx.commands)
        if ctx.logs:
            self.print_logs(ctx.logs)
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

    def print_commands(self, commands):
        """Print response commands.

        :param list[dict] commands: Response commands.
        """
        if len(commands) == 1:
            cmd = commands[0]
            if "text" in cmd and len(cmd) == 1:
                commands = cmd["text"]
        self._print_speech("🤖", commands)

    def print_logs(self, logs):
        """Print logs.

        :param list[LogRecord] logs: Log records.
        """
        for record in logs:
            if isinstance(record.message, str):
                self._print_log(record.level, record.message)
            else:
                self._print_log(
                    record.level, Pretty(record.message, indent_size=2, indent_guides=True)
                )

    def print_error(self, exc):
        """Print bot error.

        :param BotError exc: An error occured.
        """
        message = Lines()
        message.append(exc.message)
        for snippet in exc.snippets:
            message.extend(bot_error_snippet(snippet))
        self._print_log("ERROR", message)

    def _print_speech(self, speaker, data):
        output = Table.grid(padding=(0, 1))
        output.expand = True
        output.add_column()
        output.add_column(ratio=1, overflow="fold")

        if isinstance(data, str):
            speech = data
        else:
            string = yaml.dump(data, Dumper=_YAMLDumper).rstrip("\n")
            speech = Syntax(string, "YAML", background_color="default")

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
    yield Text(snippet.format_location(), style="dim")
    yield Syntax(
        snippet.code,
        "YAML+Jinja",
        line_numbers=True,
        line_range=(snippet.line, snippet.line + 2),
        highlight_lines={snippet.line + 1},
    )


class _YAMLDumper(yaml.SafeDumper):
    """Console friendly dumps."""

    @staticmethod
    def represent_str_literal(dumper, data):
        """Represent multiline strings using literal style."""
        data = str(data)
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_str(data)


_YAMLDumper.add_representer(str, _YAMLDumper.represent_str_literal)
