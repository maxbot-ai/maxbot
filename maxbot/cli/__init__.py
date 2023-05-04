"""MaxBot CLI."""
import click
import dotenv

from .run import run


@click.group()
def main():
    """Execute the cli script for MaxBot applications.

    Provides commands to run bots, test them with stories etc.
    """
    path = dotenv.find_dotenv(".env", usecwd=True)
    if path:
        dotenv.load_dotenv(path, encoding="utf-8")


main.add_command(run)

__all__ = ("main",)
