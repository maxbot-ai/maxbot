import pytest

from maxbot.resolver import BotResolver, pkgutil


def test_raise_unknown_source():
    with pytest.raises(RuntimeError) as excinfo:
        BotResolver("XyZ")()
    assert str(excinfo.value) == (
        "'XyZ' file or directory not found, "
        """import causes error ModuleNotFoundError("No module named 'XyZ'")"""
    )


def test_raise_invalid_type(monkeypatch):
    monkeypatch.setattr(pkgutil, "resolve_name", lambda spec: 1)
    with pytest.raises(RuntimeError) as excinfo:
        BotResolver("XyZ")()
    assert str(excinfo.value) == "A valid MaxBot instance was not obtained from 'XyZ'"
