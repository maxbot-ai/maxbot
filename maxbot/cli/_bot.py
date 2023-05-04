"""Prepare bot for CLI."""
import logging
import pkgutil
from pathlib import Path
from types import ModuleType

import click

from ..bot import MaxBot
from ..errors import BotError

logger = logging.getLogger(__name__)


def resolve_bot(spec):
    """Create a bot object from the given specification.

    :param str spec: Path for bot file or directory or a name to an object.
    :raise click.BadParameter: Invalid specification provided.
    :raise click.Abort: An error occured while creating the object.
    :return MaxBot: Created object.
    """
    pkg_error = None
    try:
        rv = pkgutil.resolve_name(spec)
    except (
        ValueError,  # invalid spec
        ModuleNotFoundError,  # module from spec is not found
    ) as exc:
        # we have to leave "except" block
        pkg_error = exc
    except BotError as exc:
        logger.critical("Bot Error %s", exc)
        raise click.Abort()
    except Exception as exc:
        logger.exception(f"While loading {spec!r}, an exception was raised")
        raise click.Abort() from exc
    if pkg_error:
        # fallback to paths
        path = Path(spec)
        try:
            if path.is_file():
                builder = MaxBot.builder()
                builder.use_directory_resources(path.parent, path.name)
                return builder.build()
            if path.is_dir():
                return MaxBot.from_directory(path)
        except BotError as exc:
            logger.critical("Bot Error %s", exc)
            raise click.Abort()
        raise click.BadParameter(
            f'file or directory not found, import causes error "{pkg_error}".', param_hint="--bot"
        )

    # if attribute name is not provided, use the default one.
    if isinstance(rv, ModuleType) and hasattr(rv, "bot"):
        rv = rv.bot
    if not isinstance(rv, MaxBot):
        raise click.BadParameter(
            f"a valid MaxBot instance was not obtained from {spec!r}.", param_hint="--bot"
        )
    return rv
