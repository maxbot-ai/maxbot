"""Prepare bot for CLI."""
import click

from ..resolver import BotResolver


class _CliBotResolver(BotResolver):
    def on_bot_error(self, exc):
        raise click.Abort()

    def on_error(self, exc):
        raise click.Abort() from exc

    def on_unknown_source(self, pkg_error):
        raise click.BadParameter(
            f'file or directory not found, import causes error "{pkg_error}".', param_hint="--bot"
        )

    def on_invalid_type(self):
        raise click.BadParameter(
            f"a valid MaxBot instance was not obtained from {self.spec!r}.", param_hint="--bot"
        )


def resolve_bot(spec):
    """Create a bot object from the given specification.

    :param str spec: Path for bot file or directory or a name to an object.
    :raise click.BadParameter: Invalid specification provided.
    :raise click.Abort: An error occured while creating the object.
    :return MaxBot: Created object.
    """
    return _CliBotResolver(spec)()
