import logging
from unittest.mock import Mock

import jinja2
import pytest
from jinja2.exceptions import TemplateRuntimeError, TemplateSyntaxError, UndefinedError

from maxbot.context import EntitiesResult, RecognizedEntity
from maxbot.jinja_env import StateNamespace, create_jinja_env
from maxbot.markdown import _SPECIAL_SYMBOLS


@pytest.fixture
def jinja_env():
    return create_jinja_env()


def test_slots_set(jinja_env):
    t = jinja_env.from_string("{% set slots.xxx = 'yyy' %}")
    slots = {}
    t.render(slots=StateNamespace(slots))
    assert slots["xxx"] == "yyy"


def test_slots_delete(jinja_env):
    t = jinja_env.from_string("{% delete slots.xxx %}")
    slots = {"xxx": "yyy"}
    t.render(slots=StateNamespace(slots))
    assert "xxx" not in slots


def test_slots_delete_missing(jinja_env):
    t = jinja_env.from_string("{% delete slots.xxx %}")
    slots = {}
    t.render(slots=StateNamespace(slots))
    assert slots == {}


def test_user_set(jinja_env):
    t = jinja_env.from_string("{% set user.xxx = 'yyy' %}")
    user = {}
    t.render(user=StateNamespace(user))
    assert user["xxx"] == "yyy"


def test_user_delete(jinja_env):
    t = jinja_env.from_string("{% delete user.xxx %}")
    user = {"xxx": "yyy"}
    t.render(user=StateNamespace(user))
    assert "xxx" not in user


def test_user_delete_missing(jinja_env):
    t = jinja_env.from_string("{% delete user.xxx %}")
    user = {}
    t.render(user=StateNamespace(user))
    assert user == {}


@pytest.mark.parametrize("level", ["debug", "warning"])
def test_logging_default(jinja_env, level, caplog):
    t = jinja_env.from_string(f"{{% {level} 'xxx', 'yyy' %}}")
    with caplog.at_level(logging.DEBUG):
        t.render()
    assert repr(("xxx", "yyy")) in caplog.text


@pytest.mark.parametrize("level", ["debug", "warning"])
def test_logging_with_handler(jinja_env, level):
    t = jinja_env.from_string(f"{{% {level} 'xxx', 'yyy' %}}")

    ctx = Mock()
    t.render(_turn_context=ctx)
    ctx.log.assert_called_with(level.upper(), ("xxx", "yyy"))


def test_mandatory_raise(jinja_env):
    with pytest.raises(jinja2.UndefinedError) as excinfo:
        jinja_env.from_string("{{ {}.test|mandatory }}").render()
    assert str(excinfo.value) == "'dict object' has no attribute 'test'"


@pytest.mark.parametrize(
    "case",
    (jinja2.Undefined, jinja2.ChainableUndefined, jinja2.DebugUndefined, jinja2.StrictUndefined),
)
def test_mandatory_raise_jinja2(jinja_env, case):
    with pytest.raises(jinja2.UndefinedError) as excinfo:
        jinja_env.from_string("{{ case|mandatory }}").render(case=case(name="test"))
    assert str(excinfo.value) == "'test' is undefined"


@pytest.mark.parametrize("case", (None, 0, 1, "", "a", False, True))
def test_mandatory_return(jinja_env, case):
    res = jinja_env.from_string("{{ case|mandatory }}").render(case=case)
    assert res == str(case)


def test_undefined_to_str(jinja_env):
    with pytest.raises(jinja2.UndefinedError) as excinfo:
        jinja_env.from_string("{{ {}.test }}").render()
    assert str(excinfo.value) == "'dict object' has no attribute 'test'"


def test_undefined_if(jinja_env):
    res = jinja_env.from_string("{% if {}.text %}fail{% else %}success{% endif %}").render()
    assert res == "success"


def test_undefined_entitites_to_str(jinja_env):
    e = RecognizedEntity("test", "value", "value", 0, 6)
    with pytest.raises(jinja2.UndefinedError) as excinfo:
        jinja_env.from_string("{{ entities.xxx.literal }}").render(
            entities=EntitiesResult(tuple([e]))
        )
    assert str(excinfo.value) == "'maxbot.context.EntitiesResult object' has no attribute 'xxx'"


def test_undefined_entitites_if(jinja_env):
    e = RecognizedEntity("test", "value", "value", 0, 6)
    res = jinja_env.from_string("{% if entities.xxx %}fail{% else %}success{% endif %}").render(
        entities=EntitiesResult(tuple([e]))
    )
    assert res == "success"


@pytest.mark.parametrize(
    "value, expected",
    (
        ("", ""),
        ("line", "line"),
        ("line 1\nline 2", "line 1<br />line 2"),
        ("line 1\nline 2\nline 3", "line 1<br />line 2<br />line 3"),
    ),
)
def test_nl2br(jinja_env, value, expected):
    res = jinja_env.from_string("{{ value|nl2br }}").render(value=value)
    assert res == expected


def test_autoescape_markdown(jinja_env):
    value = _SPECIAL_SYMBOLS
    res = jinja_env.from_string("{{ value }}").render(value=value)
    assert res == "".join(f"&#{ord(ch)};" for ch in value)


def test_double_scape(jinja_env):
    value = _SPECIAL_SYMBOLS
    res = jinja_env.from_string("{{ value|escape|escape }}").render(value=value)
    assert res == "".join(f"&#{ord(ch)};" for ch in value)


def test_url_attr(jinja_env):
    value = "https://api.telegram.org/file/botXXX:YYYYYYYY/photos/file_0.jpg"
    res = jinja_env.from_string('<image url="{{ value }}" />').render(value=value)
    assert res == (
        '<image url="https&#58;&#47;&#47;api&#46;telegram&#46;org'
        '&#47;file&#47;botXXX&#58;YYYYYYYY&#47;photos&#47;file&#95;0&#46;jpg" />'
    )


def test_xmlattr(jinja_env):
    value = "https://api.telegram.org/file/botXXX:YYYYYYYY/photos/file_0.jpg"
    res = jinja_env.from_string('<image{{ {"url": value}|xmlattr }} />').render(value=value)
    assert res == '<image url="https://api.telegram.org/file/botXXX:YYYYYYYY/photos/file_0.jpg" />'


def test_macro_maxml(jinja_env):
    res = jinja_env.from_string(
        (
            "{%- macro hello(name) -%}\n"
            "<text>Hello, {{ name }}</text>\n"
            "{%- endmacro -%}\n"
            '{{ hello("World") }}'
        )
    ).render()
    assert res == "<text>Hello, World</text>"
