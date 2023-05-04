"""CLI logging output."""
import logging
import logging.handlers

import click


def configure_logging(target, verbosity):
    """Configure CLI logging.

    :param str target: The name of the logger and its arguments.
    :param int verbosity: Output verbosity.
    """
    _configure_libs(verbosity)

    if target == "console":
        from ._rich import ConsoleLogHandler  # speed up loading time

        handler = ConsoleLogHandler()
    elif target.startswith("file:"):
        handler = _create_file_handler(filename=target.removeprefix("file:"))
    else:
        raise click.BadParameter(f"unknown logger {target!r}.", param_hint="--logger")

    loglevel = [logging.INFO, logging.DEBUG][min(verbosity, 1)]
    handler.setLevel(loglevel)

    logging.basicConfig(level="NOTSET", handlers=[handler])
    logging.debug(f"Verbosity: {verbosity}")


def _configure_libs(verbosity):
    loglevel = [logging.WARNING, logging.INFO, logging.DEBUG][min(verbosity, 2)]
    libs = [
        "asyncio",
        "httpx",
        "telegram",
        "apscheduler",
        "hpack",
        "sanic",
    ]
    for lib in libs:
        logging.getLogger(lib).setLevel(loglevel)
    # its especially noisy
    logging.getLogger("hpack").setLevel(logging.INFO)


def _create_file_handler(filename):
    try:
        handler = logging.handlers.WatchedFileHandler(filename, encoding="utf8")
    except IOError as e:
        raise click.BadParameter(
            f"could not log to the {filename!r}: {e!r}", param_hint="--logger"
        )
    handler.setFormatter(logging.Formatter("%(asctime)s -  %(levelname)s - %(message)s"))
    return handler
