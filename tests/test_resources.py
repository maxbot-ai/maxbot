import asyncio
import importlib
from platform import uname
from unittest.mock import Mock

import pytest
import yaml
from marshmallow import Schema, fields

from maxbot.errors import BotError
from maxbot.flows.dialog_tree import DialogNodeSchema, SubtreeSchema
from maxbot.nlu import EntitySchema, IntentSchema
from maxbot.resources import (
    DictResources,
    DirectoryResources,
    FileResources,
    InlineResources,
    PackageResources,
)
from maxbot.rpc import MethodSchema
from maxbot.schemas import ResourceSchema

DICT_RESOURCES = {
    "extensions": {"my_extension": {}},
    "channels": {"my_channel": {}},
    "intents": [
        {
            "name": "my_intent",
            "examples": [
                "example 1",
                "example 2",
            ],
        }
    ],
    "entities": [
        {
            "name": "my_entity",
            "values": [
                {
                    "name": "my_value",
                    "phrases": [
                        "phrase 1",
                        "phrase 2",
                    ],
                    "regexps": [],
                }
            ],
        }
    ],
    "rpc": [{"method": "my_method"}],
    "dialog": [
        {
            "condition": "my_condition",
            "response": "my_response",
        }
    ],
}

YAML_RESOURCES = yaml.safe_dump(DICT_RESOURCES)


class ExtensionsSchema(ResourceSchema):
    my_extension = fields.Nested(Schema)
    my_extension2 = fields.Nested(Schema)


class ChannelsSchema(ResourceSchema):
    my_channel = fields.Nested(Schema)
    my_channel2 = fields.Nested(Schema)


def assert_resources(rs, changes={}):
    expected = {**DICT_RESOURCES, **changes}
    assert expected.get("extensions", {}) == rs.load_extensions(ExtensionsSchema())
    assert expected.get("channels", {}) == rs.load_channels(ChannelsSchema())
    assert expected.get("intents", []) == rs.load_intents(IntentSchema(many=True))
    assert expected.get("entities", []) == rs.load_entities(EntitySchema(many=True))
    assert expected.get("rpc", []) == rs.load_rpc(MethodSchema(many=True))
    assert [n["condition"] for n in expected.get("dialog", [])] == [
        n["condition"].source for n in rs.load_dialog(DialogNodeSchema(many=True))
    ]
    assert expected.get("subtrees", []) == rs.load_dialog_subtrees(SubtreeSchema())


def test_dict_empty():
    assert_resources(
        DictResources.empty(),
        {
            "extensions": {},
            "channels": {},
            "intents": [],
            "entities": [],
            "rpc": [],
            "dialog": [],
        },
    )


def test_dict_load():
    assert_resources(
        DictResources(DICT_RESOURCES),
    )


def test_dict_error():
    with pytest.raises(BotError) as excinfo:
        DictResources({"XXX": "YYY"})
    assert "Unknown field 'XXX'" in excinfo.value.message


def test_inline_load():
    assert_resources(
        InlineResources(YAML_RESOURCES),
    )


def test_inline_error():
    with pytest.raises(BotError) as excinfo:
        InlineResources("XXX: YYY")
    assert "Unknown field 'XXX'" in excinfo.value.message


def test_file_load(tmp_path):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(YAML_RESOURCES)
    assert_resources(
        FileResources(botfile),
    )


def test_file_error(tmp_path):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text("XXX: YYY")
    with pytest.raises(BotError) as excinfo:
        FileResources(botfile)
    assert "Unknown field 'XXX'" in excinfo.value.message


def test_directory_load(tmp_path):
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    assert_resources(
        DirectoryResources(tmp_path),
    )


def test_directory_custom_botfile(tmp_path):
    (tmp_path / "mybot.yaml").write_text(YAML_RESOURCES)
    assert_resources(
        DirectoryResources(tmp_path, "mybot.yaml"),
    )


def test_directory_intents(tmp_path):
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    (tmp_path / "intents.yaml").write_text(
        """
        - name: my_intent_1
          examples:
              - example 11
              - example 12
    """
    )
    (tmp_path / "intents").mkdir()
    (tmp_path / "intents/my_intents.yaml").write_text(
        """
        - name: my_intent_2
          examples:
              - example 21
              - example 22
    """
    )

    rs = DirectoryResources(tmp_path)
    assert [
        {"name": "my_intent", "examples": ["example 1", "example 2"]},
        {"name": "my_intent_1", "examples": ["example 11", "example 12"]},
        {"name": "my_intent_2", "examples": ["example 21", "example 22"]},
    ] == rs.load_intents(IntentSchema(many=True))


def test_directory_entities(tmp_path):
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    (tmp_path / "entities.yaml").write_text(
        """
        - name: my_entity_1
          values:
            - name: my_value_1
              phrases:
                - phrase 11
                - phrase 12
    """
    )
    (tmp_path / "entities").mkdir()
    (tmp_path / "entities/my_entities.yaml").write_text(
        """
        - name: my_entity_2
          values:
            - name: my_value_2
              phrases:
                - phrase 21
                - phrase 22
    """
    )

    rs = DirectoryResources(tmp_path)
    assert [
        {
            "name": "my_entity",
            "values": [{"name": "my_value", "phrases": ["phrase 1", "phrase 2"], "regexps": []}],
        },
        {
            "name": "my_entity_1",
            "values": [
                {"name": "my_value_1", "phrases": ["phrase 11", "phrase 12"], "regexps": []}
            ],
        },
        {
            "name": "my_entity_2",
            "values": [
                {"name": "my_value_2", "phrases": ["phrase 21", "phrase 22"], "regexps": []}
            ],
        },
    ] == rs.load_entities(EntitySchema(many=True))


def test_directory_dialog(tmp_path):
    (tmp_path / "bot.yaml").write_text("{}")
    (tmp_path / "dialog.yaml").write_text(
        """
        - condition: my_condition_1
          response: my_response_1
    """
    )

    rs = DirectoryResources(tmp_path)
    (node,) = rs.load_dialog(DialogNodeSchema(many=True))
    assert node["condition"].source == "my_condition_1"


def test_directory_dialog_split(tmp_path):
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    (tmp_path / "dialog.yaml").write_text(
        """
        - condition: my_condition_1
          response: my_response_1
    """
    )

    rs = DirectoryResources(tmp_path)
    with pytest.raises(BotError) as excinfo:
        assert_resources(rs)

    assert (
        "It is not allowed to split dialog tree between " "bot.yaml and dialog.yaml."
    ) in excinfo.value.message


def test_directory_rpc(tmp_path):
    (tmp_path / "bot.yaml").write_text("{}")
    (tmp_path / "rpc.yaml").write_text(
        """
      - method: my_method_1
    """
    )

    rs = DirectoryResources(tmp_path)
    assert [{"method": "my_method_1"}] == rs.load_rpc(MethodSchema(many=True))


def test_directory_rpc_split(tmp_path):
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    (tmp_path / "rpc.yaml").write_text("{}")

    rs = DirectoryResources(tmp_path)
    with pytest.raises(BotError) as excinfo:
        assert_resources(rs)

    assert (
        "It is not allowed to split RPC between " "bot.yaml and rpc.yaml."
    ) in excinfo.value.message


def test_directory_subtree(tmp_path):
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    (tmp_path / "dialog").mkdir()
    (tmp_path / "dialog" / "mysubtree.yaml").write_text(
        """
        name: my_subtree
        nodes: []
    """
    )
    assert_resources(
        DirectoryResources(tmp_path), {"subtrees": [{"name": "my_subtree", "nodes": []}]}
    )


def test_directory_subtree_subfolders(tmp_path):
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    (tmp_path / "dialog").mkdir()
    (tmp_path / "dialog" / "file.yaml").write_text(
        """
        name: my_subtree_1
        nodes: []
    """
    )
    (tmp_path / "dialog" / "subdir1").mkdir()
    (tmp_path / "dialog" / "subdir1" / "file.yaml").write_text(
        """
        name: my_subtree_2
        nodes: []
    """
    )
    (tmp_path / "dialog" / "subdir1" / "subdir2").mkdir()
    (tmp_path / "dialog" / "subdir1" / "subdir2" / "file1.yaml").write_text(
        """
        name: my_subtree_3
        nodes: []
    """
    )
    assert_resources(
        DirectoryResources(tmp_path),
        {
            "subtrees": [
                {"name": "my_subtree_1", "nodes": []},
                {"name": "my_subtree_2", "nodes": []},
                {"name": "my_subtree_3", "nodes": []},
            ]
        },
    )


def test_directory_not_found(tmp_path):
    tmp_path = tmp_path / "mybot"
    with pytest.raises(BotError) as excinfo:
        assert_resources(
            DirectoryResources(tmp_path),
        )
    assert "No such file or directory" in excinfo.value.message


def test_package_load(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path.parent))
    (tmp_path / "__init__.py").touch()
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    assert_resources(
        PackageResources(tmp_path.name),
    )


def test_package_from_module(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path.parent))
    (tmp_path / "__init__.py").touch()
    (tmp_path / "somemodule.py").touch()
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    assert_resources(
        PackageResources(f"{tmp_path.name}.somemodule"),
    )


DICT_CHANGES = {
    "extensions": {"my_extension2": {}},
    "channels": {"my_channel2": {}},
    "intents": [
        {
            "name": "my_intent2",
            "examples": [
                "example 3",
                "example 4",
            ],
        }
    ],
    "entities": [
        {
            "name": "my_entity2",
            "values": [
                {
                    "name": "my_value2",
                    "phrases": [
                        "phrase 3",
                        "phrase 4",
                    ],
                    "regexps": [],
                }
            ],
        }
    ],
    "rpc": [{"method": "my_method2"}],
    "dialog": [
        {
            "condition": "my_condition2",
            "response": "my_response",
        }
    ],
}


YAML_CHANGES = yaml.safe_dump(DICT_CHANGES)


def test_poll_botfile(tmp_path, mtime_workaround_func):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(YAML_RESOURCES)
    rs = FileResources(botfile)

    assert not rs.poll()
    mtime_workaround_func()
    botfile.write_text(YAML_CHANGES)
    assert rs.poll() == {"extensions", "channels", "intents", "entities", "dialog", "rpc"}
    assert_resources(rs, DICT_CHANGES)


def test_poll_error_unlink(tmp_path):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(YAML_RESOURCES)
    rs = FileResources(botfile)

    assert not rs.poll()
    botfile.unlink()
    with pytest.raises(BotError):
        rs.poll()


def test_poll_error_invalid(tmp_path, mtime_workaround_func):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(YAML_RESOURCES)
    rs = FileResources(botfile)

    assert not rs.poll()
    mtime_workaround_func()
    botfile.write_text("XXX: YYY")
    with pytest.raises(BotError):
        rs.poll()

    mtime_workaround_func()
    botfile.write_text(YAML_RESOURCES)
    assert rs.poll(error_recovery=True) == {"bot"}


def test_poll_intents(tmp_path, mtime_workaround_func):
    (tmp_path / "bot.yaml").write_text(YAML_RESOURCES)
    (tmp_path / "intents.yaml").write_text(
        """
        - name: my_intent_1
          examples:
              - example 11
              - example 12
    """
    )
    rs = DirectoryResources(tmp_path)
    # make sure intent files are watched
    rs.load_intents(IntentSchema(many=True))

    mtime_workaround_func()
    (tmp_path / "intents.yaml").write_text(
        """
        - name: my_intent_2
          examples:
              - example 21
              - example 22
    """
    )
    assert rs.poll() == {"intents"}
