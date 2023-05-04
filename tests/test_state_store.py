import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from maxbot.state_store import DialogTable, SQLAlchemyStateStore


@pytest.fixture
def event():
    return {"channel_name": "test", "user_id": 123}


def test_create(event):
    state_store = SQLAlchemyStateStore()
    with state_store(event) as state:
        state.user["user1"] = "value1"
        state.slots["slot1"] = "value2"
        state.components["flow1"] = "value3"

    with Session(state_store.engine) as session:
        user = session.scalars(select(DialogTable)).one()
        assert user.dialog_id
        assert user.channel_name == "test"
        assert user.user_id == "123"
        v1, v2, v3 = user.variables
        assert v1.name == "user.user1"
        assert v1.value == "value1"
        assert v2.name == "slots.slot1"
        assert v2.value == "value2"
        assert v3.name == "components.flow1"
        assert v3.value == "value3"


def test_update(event):
    state_store = SQLAlchemyStateStore()
    with state_store(event) as state:
        state.user["user1"] = "value1"

    with state_store(event) as state:
        state.user["user1"] = "value2"

    with Session(state_store.engine) as session:
        user = session.scalars(select(DialogTable)).one()
        (v,) = user.variables
        assert v.name == "user.user1"
        assert v.value == "value2"


def test_update_inplace(event):
    state_store = SQLAlchemyStateStore()
    with state_store(event) as state:
        state.user["user1"] = {"key": "value1"}

    with state_store(event) as state:
        state.user["user1"]["key"] = "value2"

    with Session(state_store.engine) as session:
        user = session.scalars(select(DialogTable)).one()
        (v,) = user.variables
        assert v.name == "user.user1"
        assert v.value == {"key": "value2"}


def test_delete_using_del(event):
    state_store = SQLAlchemyStateStore()
    with state_store(event) as state:
        state.user["user1"] = "value1"

    with state_store(event) as state:
        del state.user["user1"]

    with Session(state_store.engine) as session:
        user = session.scalars(select(DialogTable)).one()
        assert len(user.variables) == 0


def test_keep_none(event):
    state_store = SQLAlchemyStateStore()
    with state_store(event) as state:
        state.user["user1"] = "value1"

    with state_store(event) as state:
        state.user["user1"] = None

    with Session(state_store.engine) as session:
        user = session.scalars(select(DialogTable)).one()
        (v,) = user.variables
        assert v.name == "user.user1"
        assert v.value is None


# def test_from_config():
#    services = Services().loads(
#        """
#        sqlalchemy:
#            url: sqlite://
#    """
#    )
#    state_store = SQLAlchemyStateStore(services.sqlalchemy)
#    assert state_store.engine
