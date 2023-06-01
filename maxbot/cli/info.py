"""Command `info` of bots."""
import importlib.metadata
import platform
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table


@click.command(short_help="Show installation info")
def info():
    """Maxbot installation info."""
    console = Console()

    output = Table().grid(padding=(0, 4))
    output.expand = True
    output.add_column()
    output.add_column(overflow="fold", style="green")

    for k, v in maxbot_info().items():
        output.add_row(k, v)

    console.print(output)


def maxbot_info():
    """Generate info about the current Maxbot intallation.

    :return dict: The maxbot info.
    """
    package = (__package__).split(".", maxsplit=1)[0]
    return {
        "Maxbot version": _get_package_version(package),
        "Python version": platform.python_version(),
        "Platform": platform.platform(),
        "Location": str(Path(__file__).parent.parent.parent),
    }


def _get_package_version(name: str):
    """Get the version of an installed package.

    :param str: The name of the installed Python package.
    :return str: The version or None if package not installed.
    """
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None
