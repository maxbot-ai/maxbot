"""MaxBot CLI."""
import click
import dotenv

from .info import info as info_command
from .run import run
from .stories import stories as stories_command


@click.group()
def main():
    """Execute the cli script for MaxBot applications.

    Provides commands to run bots, test them with stories etc.
    """
    path = dotenv.find_dotenv(".env", usecwd=True)
    if path:
        dotenv.load_dotenv(path, encoding="utf-8")


main.add_command(run)
main.add_command(stories_command)
main.add_command(info_command)

__all__ = ("main",)
