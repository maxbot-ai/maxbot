from unittest.mock import Mock

import pytest

import maxbot.stories.pytest


@pytest.fixture(autouse=True)
def mock_resolve_bot(monkeypatch):
    monkeypatch.setattr(maxbot.stories.pytest, "BotResolver", Mock())


def test_file(testdir, monkeypatch):
    stories_file = testdir.tmpdir / "stories.yaml"
    stories_file.write_text("", encoding="utf8")

    stories = Mock()
    stories.load = Mock(return_value=[{"name": f"story{i}", "markers": []} for i in range(2)])
    monkeypatch.setattr(maxbot.stories.pytest, "Stories", Mock(return_value=stories))

    result = testdir.runpytest("-p", "maxbot_stories", "--bot", "my_bot", stories_file)
    result.stdout.fnmatch_lines(["*2 passed*"])


def test_directory(testdir, monkeypatch):
    stories_dir = testdir.tmpdir / "stories"
    stories_dir.mkdir()
    for i in range(3):
        (stories_dir / f"{i}.yaml").write_text("", encoding="utf8")

    stories = Mock()
    stories.load = Mock(return_value=[{"name": f"story{i}", "markers": []} for i in range(2)])
    monkeypatch.setattr(maxbot.stories.pytest, "Stories", Mock(return_value=stories))

    result = testdir.runpytest("-p", "maxbot_stories", "--bot", "my_bot", stories_dir)
    result.stdout.fnmatch_lines(["*6 passed*"])


def test_fail(testdir, monkeypatch):
    stories_file = testdir.tmpdir / "stories.yaml"
    stories_file.write_text("", encoding="utf8")

    stories = Mock()
    stories.load = Mock(return_value=[{"name": "story1", "markers": []}])
    stories.run = Mock(side_effect=RuntimeError())

    class _MismatchError(Exception):
        pass

    stories.MismatchError = _MismatchError
    monkeypatch.setattr(maxbot.stories.pytest, "Stories", Mock(return_value=stories))

    result = testdir.runpytest("-p", "maxbot_stories", "--bot", "my_bot", stories_file)
    result.stdout.fnmatch_lines(
        [
            "*FAILED stories.yaml::story1 - RuntimeError*",
            "*1 failed*",
        ]
    )


def test_xfail(testdir, monkeypatch):
    stories_file = testdir.tmpdir / "stories.yaml"
    stories_file.write_text("", encoding="utf8")

    stories = Mock()
    stories.load = Mock(return_value=[{"name": "story1", "markers": ["xfail"]}])
    stories.run = Mock(side_effect=RuntimeError())

    class _MismatchError(Exception):
        pass

    stories.MismatchError = _MismatchError
    monkeypatch.setattr(maxbot.stories.pytest, "Stories", Mock(return_value=stories))

    result = testdir.runpytest("-p", "maxbot_stories", "--bot", "my_bot", stories_file)
    result.stdout.no_fnmatch_line("*FAILED stories.yaml::story1 - RuntimeError*")
    result.stdout.fnmatch_lines(["*1 xfailed*"])


def test_mismatch(testdir, monkeypatch):
    stories_file = testdir.tmpdir / "stories.yaml"
    stories_file.write_text("", encoding="utf8")

    stories = Mock()
    stories.load = Mock(return_value=[{"name": "story1", "markers": []}])

    class _MismatchError(Exception):
        message = "XyZ"

    stories.MismatchError = _MismatchError
    stories.run = Mock(side_effect=_MismatchError())
    monkeypatch.setattr(maxbot.stories.pytest, "Stories", Mock(return_value=stories))

    result = testdir.runpytest("-p", "maxbot_stories", "--bot", "my_bot", stories_file)
    result.stdout.fnmatch_lines(
        [
            "*XyZ*",
            "*1 failed*",
        ]
    )
