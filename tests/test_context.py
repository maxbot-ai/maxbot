from dataclasses import fields

import pytest

from maxbot.context import (
    EntitiesProxy,
    EntitiesResult,
    IntentsResult,
    LogRecord,
    RecognizedEntity,
    RecognizedIntent,
    RpcContext,
    RpcRequest,
    TurnContext,
)


def test_intents_result():
    menu = RecognizedIntent(name="menu", confidence=0.3)
    bill = RecognizedIntent(name="bill", confidence=0.5)
    obj = IntentsResult.resolve((menu, bill))
    assert obj.ranking == (bill, menu)
    assert obj.top == bill
    assert obj.bill == bill
    assert obj.menu is None
    assert obj.irrelevant == False
    assert repr(obj) == (
        f"IntentsResult(top={bill!r}, bill=RecognizedIntent(...), "
        f"ranking=(RecognizedIntent(...), {menu!r}))"
    )


def test_intents_result_below_threshold():
    menu = RecognizedIntent(name="menu", confidence=0.3)
    bill = RecognizedIntent(name="bill", confidence=0.5)
    obj = IntentsResult.resolve((menu, bill), top_threshold=0.6)
    assert obj.ranking == (bill, menu)
    assert obj.top is None
    assert obj.bill is None
    assert obj.menu is None
    assert obj.xxx is None
    assert obj.irrelevant == True
    assert repr(obj) == f"IntentsResult(top=None, ranking=({bill!r}, {menu!r}))"


def test_intents_result_definitions():
    menu = RecognizedIntent(name="menu", confidence=0.3)
    bill = RecognizedIntent(name="bill", confidence=0.5)
    obj = IntentsResult.resolve((menu, bill), definitions={"menu": True, "bill": True})
    assert obj.bill == bill
    assert obj.menu is None
    with pytest.raises(ValueError, match="No such intent: 'xxx'"):
        assert obj.xxx


@pytest.fixture
def menu_entities():
    return (
        RecognizedEntity(
            name="menu", value="standard", literal="Standard", start_char=1, end_char=9
        ),
        RecognizedEntity(
            name="menu", value="vegetarian", literal="Vegetarian", start_char=12, end_char=22
        ),
        RecognizedEntity(
            name="menu", value="cake", literal="Cake shop", start_char=25, end_char=34
        ),
    )


@pytest.fixture
def menu_definition():
    return {
        "name": "menu",
        "values": [
            {
                "name": "standard",
                "phrases": [],
            },
            {
                "name": "vegetarian",
                "phrases": [],
            },
            {
                "name": "cake",
                "phrases": [],
            },
        ],
    }


def test_entities_proxy_phrases(menu_entities, menu_definition):
    standard, vegetarian, cake = menu_entities
    obj = EntitiesProxy((standard, vegetarian), menu_definition)
    assert obj.name == standard.name
    assert obj.value == standard.value
    assert obj.literal == standard.literal
    assert obj.start_char == standard.start_char
    assert obj.end_char == standard.end_char
    assert obj.standard == True
    assert obj.vegetarian == True
    assert obj.cake == False
    assert obj.all_values == (standard.value, vegetarian.value)
    assert obj.all_objects == (standard, vegetarian)
    with pytest.raises(AttributeError):
        assert obj.xxx
    assert repr(obj) == (
        "EntitiesProxy("
        "name='menu', "
        "value='standard', "
        "literal='Standard', "
        "start_char=1, "
        "end_char=9, "
        "standard=True, "
        "vegetarian=True, "
        "cake=False, "
        "all_values=('standard', 'vegetarian'), "
        "all_objects=(...)"
        ")"
    )


def test_entities_proxy_builtin():
    date = RecognizedEntity(
        name="date",
        value="2022-05-29",
        literal="on May 29, 2022 at 5pm",
        start_char=34,
        end_char=56,
    )
    obj = EntitiesProxy((date,))
    assert obj.name == date.name
    assert obj.value == date.value
    assert obj.literal == date.literal
    assert obj.start_char == date.start_char
    assert obj.end_char == date.end_char
    assert obj.all_values == (date.value,)
    assert obj.all_objects == (date,)
    with pytest.raises(AttributeError):
        assert obj.xxx
    assert repr(obj) == (
        "EntitiesProxy("
        "name='date', "
        "value='2022-05-29', "
        "literal='on May 29, 2022 at 5pm', "
        "start_char=34, "
        "end_char=56, "
        "all_values=('2022-05-29',), "
        "all_objects=(...)"
        ")"
    )


def test_entities_proxy_empty():
    obj = EntitiesProxy(tuple(), {"name": "datetime"})
    assert bool(obj) == False

    for f in fields(RecognizedEntity):
        with pytest.raises(AttributeError):
            getattr(obj, f.name)
    assert obj.all_values == tuple()
    assert obj.all_objects == tuple()
    assert repr(obj) == (
        "EntitiesProxy(" "name='datetime', " "all_values=(), " "all_objects=()" ")"
    )


def test_entities_result(menu_entities):
    standard, vegetarian, cake = menu_entities
    date = RecognizedEntity(
        name="date",
        value="2022-05-29",
        literal="on May 29, 2022 at 5pm",
        start_char=34,
        end_char=56,
    )
    obj = EntitiesResult.resolve((standard, vegetarian, cake, date))
    assert obj.all_objects == (standard, vegetarian, cake, date)
    assert obj.menu.all_objects == (standard, vegetarian, cake)
    assert obj.date.all_objects == (date,)
    with pytest.raises(AttributeError, match="No such entity: 'xxx'"):
        assert obj.xxx
    assert repr(obj) == (
        "EntitiesResult("
        f"all_objects=({standard!r}, {vegetarian!r}, {cake!r}, {date!r}), "
        "proxies={...}, "
        "menu=EntitiesProxy(...), "
        "date=EntitiesProxy(...)"
        ")"
    )


def test_entities_result_definitions(menu_entities):
    standard, vegetarian, cake = menu_entities
    obj = EntitiesResult.resolve((standard, vegetarian, cake), definitions={"menu": True})
    assert obj.menu
    with pytest.raises(AttributeError, match="No such entity: 'xxx'"):
        assert obj.xxx


def test_rpc_context():
    request = RpcRequest(method="say_hello", params={"name": "Bob"})
    obj = RpcContext(request)
    assert obj.method == "say_hello"
    assert obj.params == {"name": "Bob"}
    assert obj.request == request
    assert obj.say_hello == request
    assert bool(obj) == True
    with pytest.raises(AttributeError):
        assert obj.xxx
    assert (
        repr(obj)
        == "RpcContext(method='say_hello', params={'name': 'Bob'}, say_hello=RpcRequest(...), request=RpcRequest(...))"
    )


def test_rpc_context_empty():
    obj = RpcContext()
    assert obj.method is None
    assert obj.params is None
    assert obj.request is None
    assert bool(obj) == False
    with pytest.raises(AttributeError):
        assert obj.say_hello
    assert repr(obj) == "RpcContext(method=None, params=None, request=None)"


def test_log_debug():
    ctx = TurnContext(dialog=None, message={"text": "hello world"})
    ctx.debug("foo bar")
    assert ctx.logs == [LogRecord("DEBUG", "foo bar")]


def test_log_warning():
    ctx = TurnContext(dialog=None, message={"text": "hello world"})
    ctx.warning("foo bar")
    assert ctx.logs == [LogRecord("WARNING", "foo bar")]
