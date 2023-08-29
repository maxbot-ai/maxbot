"""CLI logging output."""
import logging
import logging.handlers
import sys

import click


def configure_logging(target, verbosity):
    """Configure CLI logging.

    :param str target: The name of the logger and its arguments.
    :param int verbosity: Output verbosity.
    """
    if verbosity < -1:
        logging.disable()
        return

    _configure_libs(verbosity)

    if target == "console":
        if _stderr_is_non_interactive():
            handler = _create_stderr_handler()
        else:
            from ._rich import ConsoleLogHandler  # speed up loading time

            handler = ConsoleLogHandler()
    elif target.startswith("file:"):
        handler = _create_file_handler(filename=target.removeprefix("file:"))
    else:
        raise click.BadParameter(f"unknown logger {target!r}.", param_hint="--logger")

    loglevel = logging.DEBUG if verbosity >= 1 else logging.INFO
    handler.setLevel(loglevel)

    logging.basicConfig(level="NOTSET", handlers=[handler])
    logging.debug(f"Verbosity: {verbosity}")


def _configure_libs(verbosity):
    loglevel = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG][min(verbosity + 1, 3)]
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


def _create_stderr_handler():
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s -  %(processName)s - %(name)s - %(levelname)s - %(message)s"
        )
    )
    return handler


def _stderr_is_non_interactive():
    return not sys.stderr.isatty()
