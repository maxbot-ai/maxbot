import os

import pytest

from maxbot import MaxBot
from maxbot.errors import BotError


def test_include_text(tmp_path):
    include_file = tmp_path / "hello.yaml"
    include_file.write_text("hello world")

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% include """
        + repr(str(include_file))
        + """%}
    """
    )
    commands = bot.process_message("say hello")
    assert commands == [dict(text="hello world")]


def test_include_maxml(tmp_path):
    include_file = tmp_path / "hello.yaml"
    include_file.write_text(
        """
<text>
    hello world
</text>
    """
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% include """
        + repr(str(include_file))
        + """%}
    """
    )
    commands = bot.process_message("say hello")
    assert commands == [dict(text="hello world")]


def test_macro_maxml(tmp_path):
    include_file = tmp_path / "hello.yaml"
    include_file.write_text(
        """
{% macro hello(name) %}
<text>
    hello {{ name }}
</text>
{% endmacro %}
    """
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |
            {% from """
        + repr(str(include_file))
        + """ import hello%}
            {{ hello('world') }}
    """
    )
    commands = bot.process_message("say hello")
    assert commands == [dict(text="hello world")]


def test_use_macro(tmp_path):
    include_file = tmp_path / "hello.yaml"
    include_file.write_text(
        """
        {%- macro do(who) -%}
            hello {{ who }}
        {%- endmacro %}
    """
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as hello %}
            {{ hello.do('world') }}
    """
    )
    commands = bot.process_message("say hello")
    assert commands == [dict(text="hello world")]


def test_indent(tmp_path):
    include_file = tmp_path / "test.yaml"
    include_file.write_text(
        """
{%- macro do() -%}
Hello!
I am MaxBot.
{%- endmacro -%}
"""
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as test %}
            {{ test.do()|indent }}
    """
    )
    commands = bot.process_message("say hello")
    assert commands == [dict(text="Hello! I am MaxBot.")]


def test_import_import(tmp_path):
    include_file2 = tmp_path / "test2.yaml"
    include_file2.write_text("{%- macro do() -%}MaxBot{%- endmacro -%}")

    include_file = tmp_path / "test.yaml"
    include_file.write_text(
        """
{% import "test2.yaml" as test2 %}
{%- macro do() -%}
Hello!
I am {{ test2.do() }}.
{%- endmacro -%}
"""
    )

    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import 'test.yaml' as test %}
            {{ test.do() }}
    """
    )

    bot = MaxBot.from_file(bot_file)

    commands = bot.process_message("say hello")
    assert commands == [dict(text="Hello! I am MaxBot.")]


def test_use_slots_with_context(tmp_path):
    include_file = tmp_path / "test.yaml"
    include_file.write_text(
        """
{%- macro do() -%}
Hello!
I am {{ slots.name }}.
{%- endmacro -%}
"""
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as test with context %}
            {% set slots.name = 'MaxBot' %}
            {{ test.do()|indent }}
    """
    )
    commands = bot.process_message("say hello")
    assert commands == [dict(text="Hello! I am MaxBot.")]


def test_use_slots_as_argument(tmp_path):
    include_file = tmp_path / "test.yaml"
    include_file.write_text(
        """
{%- macro do(name) -%}
Hello!
I am {{ name }}.
{%- endmacro -%}
"""
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as test %}
            {% set slots.name = 'MaxBot' %}
            {{ test.do(slots.name)|indent }}
    """
    )
    commands = bot.process_message("say hello")
    assert commands == [dict(text="Hello! I am MaxBot.")]


def test_clear_slot(tmp_path):
    include_file = tmp_path / "test.yaml"
    include_file.write_text(
        """
{% macro do() %}
{% delete slots.name %}
{% endmacro %}
"""
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as test with context %}
            {% set slots.name = 'failed' %}
            {{ test.do() }}
            Hello!
            I am {{ slots.name|default('MaxBot', true) }}.
    """
    )
    commands = bot.process_message("say hello")
    assert commands == [dict(text="Hello! I am MaxBot.")]


def test_return_slot(tmp_path):
    include_file = tmp_path / "test.yaml"
    include_file.write_text(
        """
{% macro do() %}
{% set slots.name = 'MaxBot' %}
{% endmacro %}
"""
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as test with context %}
            {% set slots.name = 'failed' %}
            {{ test.do() }}
            Hello!
            I am {{ slots.name }}.
    """
    )
    commands = bot.process_message("say hello")
    assert commands == [dict(text="Hello! I am MaxBot.")]


@pytest.mark.xfail(reason="expecting a snippet of macro here, see MAX-5237")
def test_error_on_import(tmp_path):
    include_file = tmp_path / "test.yaml"
    include_file.write_text(
        """
{%- macro do() -%}
{{ @! }}
{%- endmacro -%}
"""
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as test %}
    """
    )
    with pytest.raises(BotError) as excinfo:
        bot.process_message("say hello")

    assert str(excinfo.value) == ("unexpected char '@' at 23")


@pytest.mark.parametrize(
    "file_name",
    (
        "not_exist_file.yaml",
        "not_exist_dir/file.yaml",
        "@",
        "!",
        "<",
        ">",
        "/",
        ".",
    ),
)
def test_not_exist_file(file_name):
    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(file_name)
        + """ as text %}
    """
    )
    with pytest.raises(BotError) as excinfo:
        bot.process_message("say hello")

    assert file_name in str(excinfo.value)
    assert "TemplateNotFound" in str(excinfo.value)


def test_error_render(tmp_path):
    include_file = tmp_path / "test.yaml"
    include_file.write_text(
        """
{% macro do() %}
{{ abc.cba + 1 }}
{% endmacro %}
"""
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as test %}
            {{ test.do() }}
    """
    )
    with pytest.raises(BotError) as excinfo:
        bot.process_message("say hello")
    assert "caused by jinja2.exceptions.UndefinedError: 'abc' is undefined" in str(excinfo.value)


def test_error_render_oob(tmp_path):
    include_file = tmp_path / "test.yaml"
    include_file.write_text(
        """
{% macro do() %}
test-test-test
{% macro m0() %}{{ abc.cba + 1 }}{% endmacro %}
{% macro m1() %}{{ m0() }}{% endmacro %}
{% macro m2() %}{{ m1() }}{% endmacro %}
{% macro m3() %}{{ m2() }}{% endmacro %}
{% macro m4() %}{{ m3() }}{% endmacro %}
{% macro m5() %}{{ m4() }}{% endmacro %}
{% macro m6() %}{{ m5() }}{% endmacro %}
{% macro m7() %}{{ m6() }}{% endmacro %}
{% macro m8() %}{{ m7() }}{% endmacro %}
{% macro m9() %}{{ m8() }}{% endmacro %}
{{ m9() }}
{% endmacro %}
"""
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as test %}
            {% macro m0() %}{{ test.do() }}{% endmacro %}
            {% macro m1() %}{{ m0() }}{% endmacro %}
            {% macro m2() %}{{ m1() }}{% endmacro %}
            {{ m2() }}
    """
    )
    with pytest.raises(BotError) as excinfo:
        bot.process_message("say hello")
    assert "caused by jinja2.exceptions.UndefinedError: 'abc' is undefined" in str(excinfo.value)


def from_file(bot_file):
    return MaxBot.from_file(bot_file)


def from_directory(bot_file):
    dir_path, _ = os.path.split(bot_file)
    return MaxBot.from_directory(dir_path)


@pytest.mark.parametrize("build_fn", (from_file, from_directory))
def test_relative_path(tmp_path, build_fn):
    include_file = tmp_path / "hello.yaml"
    include_file.write_text("{% set name = 'world' %}")

    bot_file = tmp_path / "bot.yaml"
    bot_file.write_text(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import 'hello.yaml' as hello %}
            hello {{ hello.name }}
    """
    )

    bot = build_fn(bot_file)
    commands = bot.process_message("say hello")
    assert commands == [dict(text="hello world")]


def test_import_reload(tmp_path):
    include_file = tmp_path / "hello.yaml"
    include_file.write_text(
        """
        {%- macro do() -%}
            step1
        {%- endmacro %}
    """
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% import """
        + repr(str(include_file))
        + """ as hello %}
            {{ hello.do() }}
    """
    )
    commands = bot.process_message("bla bla bla")
    assert commands == [dict(text="step1")]

    include_file.write_text(
        """
        {%- macro do() -%}
            step2
        {%- endmacro %}
    """
    )

    commands = bot.process_message("bla bla bla")
    assert commands == [dict(text="step2")]


def test_include_reload(tmp_path):
    include_file = tmp_path / "hello.yaml"
    include_file.write_text(
        """
        step1
    """
    )

    bot = MaxBot.inline(
        """
        extensions:
          jinja_loader: {}
        dialog:
        - condition: true
          response: |-
            {% include """
        + repr(str(include_file))
        + """ %}
    """
    )
    commands = bot.process_message("bla bla bla")
    assert commands == [dict(text="step1")]

    include_file.write_text(
        """
        step2
    """
    )

    commands = bot.process_message("bla bla bla")
    assert commands == [dict(text="step2")]
