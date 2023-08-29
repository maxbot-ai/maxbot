"""Command Line Interface for a Bot."""
from functools import partial

import click

from ..webapp import run_webapp
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
@click.option("-v", "--verbose", count=True, help="Increasing the level of verbosity.")
@click.option("-q", "--quiet", count=True, help="Decreasing the level of verbosity.")
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
@click.option(
    "--workers",
    type=int,
    default=1,
    show_default=True,
    help="Number of web application worker processes to spawn. Cannot be used with `fast`.",
)
@click.option(
    "--fast",
    is_flag=True,
    default=False,
    help="Set the number of web application workers to max allowed.",
)
@click.option(
    "--single-process",
    "single_process",
    is_flag=True,
    default=False,
    help="Run web application in a single process.",
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
    workers,
    fast,
    single_process,
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
    # verbose journal output and discard logger messages
    maxbot run --bot bot.yaml -vv --logger file:/dev/null

    \b
    # print to console (journal and logger) errors only
    maxbot run --bot bot.yaml -q
    """
    if quiet and verbose:
        raise click.UsageError("Options -q and -v are mutually exclusive.")

    verbosity = verbose if verbose else (0 - quiet)

    from ._rich import Progress

    init_logging = partial(configure_logging, logger, verbosity)
    init_logging()

    bot_factory = partial(create_bot, bot_spec, logger, verbosity, journal_file, journal_output)
    with Progress(transient=True) as progress:
        progress.add_task("Loading resources", total=None)

        bot = bot_factory()

    polling_conflicts = [
        next(p.get_error_hint(ctx) for p in ctx.command.params if p.name == name)
        for name in (
            "host",
            "port",
            "public_url",
            "ngrok",
            "ngrok_url",
            "workers",
            "fast",
            "single_process",
        )
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

        run_webapp(
            bot,
            bot_factory,
            host,
            port,
            init_logging=init_logging,
            public_url=public_url,
            autoreload=autoreload,
            workers=workers,
            fast=fast,
            single_process=single_process,
        )
    else:
        raise AssertionError(f"Unexpected updater {updater}.")  # pragma: no cover


def create_bot(bot_spec, logger, verbosity, journal_file, journal_output):
    """Create new instance of MaxBot."""
    bot = resolve_bot(bot_spec)
    bot.dialog_manager.journal(create_journal(verbosity, journal_file, journal_output))
    return bot
