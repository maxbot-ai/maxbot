"""Command Line Interface for a Bot."""
import click

from ._bot import resolve_bot
from ._journal import create_journal
from ._logging import configure_logging
from ._ngrok import ask_ngrok


@click.command(
    short_help="Run the bot",
    context_settings={
        # less is more readable, but make sure the contents fits on one page
        "max_content_width": 120
    },
)
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
    "--updater",
    type=click.Choice(choices=["webhooks", "polling"]),
    default=None,
    help=(
        "The way your bot geting updates from messaging platforms. "
        "The 'polling' updater is only available for telegram channel. "
        "By default, the most appropriate value is selected."
    ),
)
@click.option(
    "--host",
    type=str,
    default="localhost",
    show_default=True,
    help="Hostname or IP address on which to listen.",
)
@click.option(
    "--port",
    type=int,
    default=8080,
    show_default=True,
    help="TCP port on which to listen.",
)
@click.option(
    "--public-url",
    type=str,
    help=(
        "A URL that is forwarded to http://<host>:<port>/. "
        "This is used to register webhooks to get updates for the channels. "
        "If missing, no webhooks are registered and you have to register them yourself."
    ),
)
@click.option(
    "--ngrok",
    is_flag=True,
    default=False,
    help="Obtain host, port and public URL from ngrok.",
)
@click.option(
    "--ngrok-url",
    type=str,
    default="http://localhost:4040",
    show_default=True,
    help="An URL to ngrok's web interface.",
)
@click.option(
    "--reload/--no-reload",
    "autoreload",
    is_flag=True,
    default=True,
    help="Watch bot files and reload on changes.",
)
@click.option("-v", "--verbose", count=True, help="Set the verbosity level.")
@click.option(
    "--logger",
    type=str,
    default="console",
    show_default=True,
    help=(
        "Write the developer logs to console or file:/path/to/file.log. "
        "Use the --journal-file option to redirect the journal."
    ),
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Do not log to console.",
)
@click.option(
    "--journal-file",
    type=click.File(mode="a", encoding="utf8"),
    help="Write the journal to the file.",
)
@click.option(
    "--journal-output",
    type=click.Choice(choices=["json", "yaml"]),
    default="json",
    show_default=True,
    help="Journal file format",
)
@click.pass_context
def run(
    ctx,
    bot_spec,
    updater,
    host,
    port,
    public_url,
    ngrok,
    ngrok_url,
    autoreload,
    verbose,
    logger,
    quiet,
    journal_file,
    journal_output,
):
    """
    Run the bot.

    Examples:

    \b
    # load resources from single file
    maxbot run --bot bot.yaml

    \b
    # load resources from a directory
    maxbot run --bot mybot/

    \b
    # provide import spec to load the bot
    maxbot run --bot mybot:bot

    \b
    # force webhooks updater to be used
    maxbot run --bot bot.yaml --updater webhooks

    \b
    # bind webhooks updater to custom host and port
    maxbot run --bot bot.yaml --host 127.0.0.1 --port 8000

    \b
    # provide public URL to register webhooks to get updates for the channels
    maxbot run --bot bot.yaml --public-url https://example.com/webhooks/

    \b
    # obtain host, port and public URL from ngrok
    maxbot run --bot bot.yaml --ngrok

    \b
    # log to file
    maxbot run --bot bot.yaml --logger file:/var/log/maxbot.log

    \b
    # journal to file and to console
    maxbot run --bot bot.yaml --journal-file /var/log/maxbot.jsonl

    \b
    # journal to file only
    maxbot run --bot bot.yaml -q --journal-file /var/log/maxbot.jsonl
    """
    if not quiet:
        configure_logging(logger, verbose)

    from ._rich import Progress

    with Progress(transient=True) as progress:
        progress.add_task("Loading resources", total=None)

        bot = resolve_bot(bot_spec)
        bot.dialog_manager.journal(create_journal(verbose, quiet, journal_file, journal_output))

    polling_conflicts = [
        next(p.get_error_hint(ctx) for p in ctx.command.params if p.name == name)
        for name in ("host", "port", "public_url", "ngrok", "ngrok_url")
        if ctx.get_parameter_source(name) != click.core.ParameterSource.DEFAULT
    ]

    # resolve the default updater
    if updater is None:
        if bot.rpc or polling_conflicts:
            updater = "webhooks"
        elif bot.channels.names == {"telegram"}:
            updater = "polling"
        else:
            updater = "webhooks"

    # run the bot using updater
    if updater == "polling":
        if polling_conflicts:
            raise click.UsageError(
                f"Option '--updater=polling' conflicts with {', '.join(polling_conflicts)}."
            )
        bot.run_polling(autoreload=autoreload)
    elif updater == "webhooks":
        if ngrok or ctx.get_parameter_source("ngrok_url") != click.core.ParameterSource.DEFAULT:
            ngrok_conflicts = [
                next(p.get_error_hint(ctx) for p in ctx.command.params if p.name == name)
                for name in ("host", "port", "public_url")
                if ctx.get_parameter_source(name) != click.core.ParameterSource.DEFAULT
            ]
            if ngrok_conflicts:
                raise click.UsageError(
                    f"Option '--ngrok'/'--ngrok-url' conflicts with {', '.join(ngrok_conflicts)}."
                )
            host, port, public_url = ask_ngrok(ngrok_url)
        bot.run_webapp(host, port, public_url=public_url, autoreload=autoreload)
    else:
        raise AssertionError(f"Unexpected updater {updater}.")  # pragma: no cover
