"""Resolve bot from command line argument."""
import logging
import pkgutil
from pathlib import Path
from types import ModuleType

from .bot import MaxBot
from .errors import BotError

logger = logging.getLogger(__name__)


class BotResolver:
    """Create a bot object from the given specification.

    You can override .on_* handlers to generate your own errors.
    """

    def __init__(self, spec):
        """Create new instance.

        :param str spec: Path for bot file or directory or a name to an object.
        """
        self.spec = spec

    def __call__(self):
        """Create a bot object from the given specification.

        :return MaxBot: Created object.
        """
        pkg_error = None
        try:
            rv = pkgutil.resolve_name(self.spec)
        except (
            ValueError,  # invalid spec
            ModuleNotFoundError,  # module from spec is not found
        ) as exc:
            # we have to leave "except" block
            pkg_error = exc
        except BotError as exc:
            logger.critical("Bot Error %s", exc)
            self.on_bot_error(exc)
            raise exc
        except Exception as exc:
            logger.exception(f"While loading {self.spec!r}, an exception was raised")
            self.on_error(exc)
            raise exc
        if pkg_error:
            # fallback to paths
            path = Path(self.spec)
            try:
                if path.is_file():
                    builder = MaxBot.builder()
                    builder.use_directory_resources(path.parent, path.name)
                    return builder.build()
                if path.is_dir():
                    return MaxBot.from_directory(path)
            except BotError as exc:
                logger.critical("Bot Error %s", exc)
                self.on_bot_error(exc)
                raise exc
            self.on_unknown_source(pkg_error)
            raise RuntimeError(
                f"{self.spec!r} file or directory not found, import causes error {pkg_error!r}"
            )

        # if attribute name is not provided, use the default one.
        if isinstance(rv, ModuleType) and hasattr(rv, "bot"):
            rv = rv.bot
        if not isinstance(rv, MaxBot):
            self.on_invalid_type()
            raise RuntimeError(f"A valid MaxBot instance was not obtained from {self.spec!r}")
        return rv

    def on_bot_error(self, exc):
        """Handle a BotError that occurred when the bot was loaded."""

    def on_error(self, exc):
        """Raise exception (not a BotError) that occurred when the bot was loaded."""

    def on_unknown_source(self, pkg_error):
        """Handle a situation where `spec` is not a file, directory, or package."""

    def on_invalid_type(self):
        """Handle a situation where the resolved bot is of type other than MaxBot."""
