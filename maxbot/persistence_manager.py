"""Default implementation for state tracker based on sqlalchemy."""
import copy
import enum
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import Session, declarative_base, relationship
from sqlalchemy.pool import StaticPool

from .context import StateVariables
from .maxml import markup, pretty

logger = logging.getLogger(__name__)
Base = declarative_base()


def create_json_serializer(default_serializers=None):
    """Create JSON serializer.

    https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.JSON
    (see "Customizing the JSON Serializer")

    :param list[tuple] default_serializers: Pairs: object type, object serializier.
    :return callable: Value for json_serializer argument of create_engine.
    """
    default_serializers = list(default_serializers) if default_serializers else []
    default_serializers.append((markup.Value, lambda o: "\n".join(pretty.markup_to_lines(o))))

    def _default(o):
        for type_, serializer in default_serializers:
            if isinstance(o, type_):
                return serializer(o)
        raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

    return lambda o: json.dumps(o, default=_default)


class DialogTable(Base):
    """Stores the information about a conversation channel and user."""

    __tablename__ = "dialog"

    dialog_id = Column(Integer, primary_key=True)
    channel_name = Column(String, nullable=False)
    user_id = Column(String, nullable=False)

    variables = relationship(
        lambda: VariableTable,
        backref="user",
        cascade="all, delete-orphan",
        order_by=lambda: VariableTable.variable_id,
    )

    history = relationship(
        lambda: HistoryTable,
        cascade="all, delete-orphan",
        order_by=lambda: HistoryTable.history_id,
    )

    __table_args__ = (UniqueConstraint("channel_name", "user_id"),)


class VariableTable(Base):
    """Stores the state of a conversation."""

    __tablename__ = "variable"

    variable_id = Column(Integer, primary_key=True)
    dialog_id = Column(Integer, ForeignKey("dialog.dialog_id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    value = Column(JSON, nullable=False)

    __table_args__ = (UniqueConstraint("dialog_id", "name"),)


class RequestType(enum.Enum):
    """Type of request source."""

    # Message from user
    message = 1

    # RPC message
    rpc = 2


class HistoryTable(Base):
    """Stores the dialog turn history."""

    __tablename__ = "history"

    history_id = Column(Integer, primary_key=True)
    dialog_id = Column(Integer, ForeignKey("dialog.dialog_id", ondelete="CASCADE"), nullable=False)
    request_date = Column(DateTime(timezone=True), nullable=False)
    request_type = Column(Enum(RequestType), nullable=False)
    request = Column(JSON, nullable=False)
    response = Column(JSON, nullable=False)


class PersistenceTracker:
    """Dialog turn persistence tracker."""

    def __init__(self, user):
        """Create new class instance.

        :param DialogTable user: Current dialog with user.
        """
        self.user = user

        # make a deep copy to allow sqlalchemy track changes by
        # comparing with original values
        kv_pairs = [(v.name, copy.deepcopy(v.value)) for v in self.user.variables]
        self.variables = StateVariables.from_kv_pairs(kv_pairs)

    def get_state(self):
        """Return state variables."""
        return self.variables

    def set_message_history(self, message, commands):
        """Track incoming user message.

        :param any message: JSON-serializable object of user message.
        :param list commands: List of JSON-serializable objects of response commands.
        """
        self.user.history.append(
            HistoryTable(
                request_date=datetime.now(timezone.utc),
                request_type=RequestType.message,
                request=message,
                response=commands,
            )
        )

    def set_rpc_history(self, rpc, commands):
        """Track RPC.

        :param any rpc: JSON-serializable object of RPC.
        :param list commands: List of JSON-serializable objects of response commands.
        """
        self.user.history.append(
            HistoryTable(
                request_date=datetime.now(timezone.utc),
                request_type=RequestType.rpc,
                request=rpc,
                response=commands,
            )
        )

    @contextmanager
    def __call__(self):
        """Wrap dialog turn."""
        yield self

        existing = {v.name: v for v in self.user.variables}
        for name, value in self.variables.to_kv_pairs():
            if name in existing:
                var = existing.pop(name)
                var.value = value
            else:
                var = VariableTable(name=name, value=value)
                self.user.variables.append(var)
        # variables that not in kv_pairs anymore must be deleted
        for var in existing.values():
            self.user.variables.remove(var)


class SQLAlchemyManager:
    """Load and save the state during the conversation."""

    def __init__(self):
        """Create new class instance."""
        self._engine = None

    @property
    def engine(self):
        """Sqlalchemy engine.

        You can set your own engine, for example,

            from sqlalchemy import create_engine

            state_tracker.engine = create_engine("postgresql://scott:tiger@localhost:5432/mydatabase")

        All necessary tables are created immediately after your set engine.

        Default: in-memory sqlite db that supports multithreading.
        """
        if self._engine is None:
            self._engine = self._create_default_engine()
            self._create_tables(self._engine)
        return self._engine

    @engine.setter
    def engine(self, value):
        self._engine = value

    def create_tables(self):
        """Create storage schema."""
        if self._engine is None:
            self._engine = self._create_default_engine()
        self._create_tables(self.engine)

    @staticmethod
    def _create_default_engine():
        return create_engine(
            "sqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            json_serializer=create_json_serializer(),
        )

    @staticmethod
    def _create_tables(engine):
        Base.metadata.create_all(engine, checkfirst=True)

    @contextmanager
    def __call__(self, dialog):
        """Load and save persistence state.

        :param dict dialog: A dialog for which the state is being loaded, with the schema :class:`~maxbot.schemas.DialogSchema`.
        :return PersistenceTracker: Persistence tracker of current dialog turn.
        """
        with Session(self.engine) as session:
            stmt = (
                select(DialogTable)
                .where(DialogTable.channel_name == dialog["channel_name"])
                .where(DialogTable.user_id == str(dialog["user_id"]))
                .with_for_update()
            )
            user = session.scalars(stmt).one_or_none()
            if user is None:
                user = DialogTable(channel_name=dialog["channel_name"], user_id=dialog["user_id"])
                session.add(user)

            tracker = PersistenceTracker(user)
            with tracker():
                yield tracker

            session.commit()
