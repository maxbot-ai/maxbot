import importlib.metadata
import sys
from importlib.metadata import EntryPoint
from importlib.util import module_from_spec, spec_from_loader
from unittest.mock import Mock, sentinel

import pytest
from marshmallow import Schema, fields

import maxbot.extensions._manager
from maxbot.extensions import ExtensionManager
from maxbot.resources import InlineResources


@pytest.fixture
def extension_mock():
    class ConfigSchema(Schema):
        x = fields.String()

    mock = Mock()
    mock.ConfigSchema = ConfigSchema
    return mock


def _apply_and_assert_extension(em, extension_mock):
    assert not em.proxies["my_extension"].loaded  # check for lazy loading

    # extension not configured
    em.apply_extensions(sentinel.builder, InlineResources("extensions: {}"))
    assert not extension_mock.called
    assert not em.proxies["my_extension"].loaded  # check for lazy loading

    # extension configured
    em.apply_extensions(sentinel.builder, InlineResources("extensions: {my_extension: {x: y}}"))
    extension_mock.assert_called_once_with(sentinel.builder, {"x": "y"})
    assert em.proxies["my_extension"].loaded


def test_builtin_extensions(monkeypatch, extension_mock):
    global MyExtension
    MyExtension = extension_mock
    monkeypatch.setattr(
        maxbot.extensions._manager,
        "BUILTIN_EXTENSIONS",
        {"my_extension": f"{__name__}.MyExtension"},
    )
    _apply_and_assert_extension(ExtensionManager(), extension_mock)


def test_add_extensions(extension_mock):
    em = ExtensionManager()
    em.add_extensions({"my_extension": extension_mock})

    _apply_and_assert_extension(em, extension_mock)


def test_entry_point_extensions(extension_mock, monkeypatch):
    # Create a new EntryPoint object by pretending we have a setup.cfg and
    # use generted module to provide extension
    module = module_from_spec(spec_from_loader("xxx", loader=None))
    module.__dict__["MyExtension"] = extension_mock
    monkeypatch.setitem(sys.modules, "xxx", module)
    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        Mock(
            return_value={
                "maxbot_extensions": EntryPoint._from_text(
                    "[options.entry_points]maxbot_extensions\n    my_extension = xxx:MyExtension"
                ),
            }
        ),
    )

    _apply_and_assert_extension(ExtensionManager(), extension_mock)
