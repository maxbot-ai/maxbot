"""MaxBot stories pytest plugin.

See:
- https://docs.pytest.org/en/7.1.x/how-to/writing_plugins.html
- https://docs.pytest.org/en/7.1.x/reference/reference.html
- https://docs.pytest.org/en/7.1.x/example/nonpython.html
"""
import pytest
from dotenv import find_dotenv, load_dotenv

from ..resolver import BotResolver
from . import Stories

_STORIES = None
_CONFIG = None


def pytest_addoption(parser):
    """Add options to pytest command line."""
    group = parser.getgroup("maxbot")
    group.addoption(
        "--bot",
        action="store",
        dest="bot_spec",
        help=(
            "Path for bot file or directory or the Maxbot instance to load. "
            "The instance can be in the form 'module:name'. "
            "Module can be a dotted import. Name is not required if it is 'bot'."
        ),
    )


def pytest_configure(config):
    """Perform initial configuration."""
    bot_spec = config.getoption("bot_spec")
    if bot_spec:
        path = find_dotenv(".env", usecwd=True)
        if path:
            load_dotenv(path, encoding="utf-8")

        global _STORIES, _CONFIG  # pylint: disable=W0603
        _STORIES = Stories(BotResolver(bot_spec)())
        _CONFIG = config


def pytest_collect_file(file_path, parent):
    """Create collector of stories."""
    return StoriesFile.from_parent(parent, path=file_path) if _STORIES else None


class StoriesFile(pytest.File):
    """Stories YAML file."""

    def collect(self):
        """Collect stories from current file."""
        for story in _STORIES.load(self.fspath):
            item = StoryItem.from_parent(self, name=story["name"])
            item.user_properties.append(("maxbot_story", story))
            for mark in story["markers"]:
                _CONFIG.addinivalue_line("markers", mark)
                item.add_marker(mark)
            yield item


class StoryItem(pytest.Item):
    """One story pytest representation."""

    def runtest(self):
        """Run story."""
        _, story = next(pair for pair in self.user_properties if pair[0] == "maxbot_story")
        _STORIES.run(story)

    def repr_failure(self, excinfo, style=None):
        """Return a representation of a test failure."""
        if isinstance(excinfo.value, _STORIES.MismatchError):
            return excinfo.value.message
        return excinfo.getrepr(style="long" if _CONFIG.getoption("verbose") > 0 else "short")

    def reportinfo(self):
        """Get location information for this item for test reports."""
        return self.fspath, None, f"{self.name}"


def pytest_sessionfinish(session, exitstatus):
    """Cleanup pytest session."""
    if _STORIES:
        _STORIES.loop.close()
