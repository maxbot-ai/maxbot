"""MaxBot CLI."""
import click
import dotenv

from .info import info as info_command
from .run import run as run_command


@click.group()
def main():
    """Execute the cli script for MaxBot applications.

    Provides commands to run bots and etc.
    """
    path = dotenv.find_dotenv(".env", usecwd=True)
    if path:
        dotenv.load_dotenv(path, encoding="utf-8")


main.add_command(run_command)
main.add_command(info_command)

__all__ = ("main",)
