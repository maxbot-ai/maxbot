import os
from platform import uname
from time import sleep

import pytest
from sanic import Sanic

from maxbot.context import StateVariables
from maxbot.errors import YamlSymbols

Sanic.test_mode = True


@pytest.fixture(autouse=True)
def cleanup_yaml_symbols():
    YamlSymbols._stores.clear()


@pytest.fixture
def dialog_stub():
    return {"channel_name": "some_channel", "user_id": "123"}


@pytest.fixture
def state_stub():
    return StateVariables.empty()


@pytest.fixture(scope="session")
def mtime_workaround_func():
    if "microsoft-standard" in uname().release or os.environ.get("MTIME_WORKAROUND"):
        # Not enough granularity for mtime.
        return lambda: sleep(0.01)
    return lambda: None
