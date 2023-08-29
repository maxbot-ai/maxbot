import pytest
from sqlalchemy import select
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from maxbot.maxml import markup
from maxbot.persistence_manager import DialogTable, RequestType, SQLAlchemyManager
from maxbot.webapp import Factory


@pytest.fixture
def event():
    return {"channel_name": "test", "user_id": 123}


def test_state_create(event):
    persistence_manager = SQLAlchemyManager()
    with persistence_manager(event) as tracker:
        tracker.get_state().user["user1"] = "value1"
        tracker.get_state().slots["slot1"] = "value2"
        tracker.get_state().components["flow1"] = "value3"

    with Session(persistence_manager.engine) as session:
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


def test_state_update(event):
    persistence_manager = SQLAlchemyManager()
    with persistence_manager(event) as tracker:
        tracker.get_state().user["user1"] = "value1"

    with persistence_manager(event) as tracker:
        tracker.get_state().user["user1"] = "value2"

    with Session(persistence_manager.engine) as session:
        user = session.scalars(select(DialogTable)).one()
        (v,) = user.variables
        assert v.name == "user.user1"
        assert v.value == "value2"


def test_state_update_inplace(event):
    persistence_manager = SQLAlchemyManager()
    with persistence_manager(event) as tracker:
        tracker.get_state().user["user1"] = {"key": "value1"}

    with persistence_manager(event) as tracker:
        tracker.get_state().user["user1"]["key"] = "value2"

    with Session(persistence_manager.engine) as session:
        user = session.scalars(select(DialogTable)).one()
        (v,) = user.variables
        assert v.name == "user.user1"
        assert v.value == {"key": "value2"}


def test_state_delete_using_del(event):
    persistence_manager = SQLAlchemyManager()
    with persistence_manager(event) as tracker:
        tracker.get_state().user["user1"] = "value1"

    with persistence_manager(event) as tracker:
        del tracker.get_state().user["user1"]

    with Session(persistence_manager.engine) as session:
        user = session.scalars(select(DialogTable)).one()
        assert len(user.variables) == 0


def test_state_keep_none(event):
    persistence_manager = SQLAlchemyManager()
    with persistence_manager(event) as tracker:
        tracker.get_state().user["user1"] = "value1"

    with persistence_manager(event) as tracker:
        tracker.get_state().user["user1"] = None

    with Session(persistence_manager.engine) as session:
        user = session.scalars(select(DialogTable)).one()
        (v,) = user.variables
        assert v.name == "user.user1"
        assert v.value is None


def test_history_message(event):
    persistence_manager = SQLAlchemyManager()
    with persistence_manager(event) as tracker:
        tracker.set_message_history({}, [])

    with persistence_manager(event) as tracker:
        (turn,) = tracker.user.history
        assert turn.request_date
        assert turn.request_type == RequestType.message
        assert turn.request == {}
        assert turn.response == []


def test_history_rpc(event):
    persistence_manager = SQLAlchemyManager()
    with persistence_manager(event) as tracker:
        tracker.set_rpc_history({}, [])

    with persistence_manager(event) as tracker:
        (turn,) = tracker.user.history
        assert turn.request_date
        assert turn.request_type == RequestType.rpc
        assert turn.request == {}
        assert turn.response == []


def _default(tmp_path):
    return SQLAlchemyManager()


def _default_mp(tmp_path):
    persistence_manager = Factory._create_default_mp_persistence_manager(tmp_path / "pytest.db")
    persistence_manager.create_tables()
    return persistence_manager


@pytest.mark.parametrize("factory", [_default, _default_mp])
def test_history_maxml(event, factory, tmp_path):
    v = markup.Value(
        [
            markup.Item(markup.TEXT, "line 1"),
            markup.Item(markup.START_TAG, "br"),
            markup.Item(markup.END_TAG, "br"),
            markup.Item(markup.TEXT, "line 2"),
        ]
    )
    persistence_manager = factory(tmp_path)
    with persistence_manager(event) as tracker:
        tracker.set_rpc_history({}, [{"text": v}])

    with persistence_manager(event) as tracker:
        (turn,) = tracker.user.history
        assert turn.request_date
        assert turn.request_type == RequestType.rpc
        assert turn.request == {}
        assert turn.response == [{"text": "line 1<br />line 2"}]


@pytest.mark.parametrize("factory", [_default, _default_mp])
def test_history_json_not_serializable(event, factory, tmp_path):
    class Value:
        pass

    persistence_manager = factory(tmp_path)
    with pytest.raises(StatementError) as excinfo:
        with persistence_manager(event) as tracker:
            tracker.set_rpc_history({}, [{"custom": Value()}])

    assert "Object of type Value is not JSON serializable" in str(excinfo.value)
