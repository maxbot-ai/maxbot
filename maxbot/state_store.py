"""Default implementation for state tracker based on sqlalchemy."""
import copy
from contextlib import contextmanager

from sqlalchemy import (
    JSON,
    Column,
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

Base = declarative_base()


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

    __table_args__ = (UniqueConstraint("channel_name", "user_id"),)


class VariableTable(Base):
    """Stores the state of a conversation."""

    __tablename__ = "variable"

    variable_id = Column(Integer, primary_key=True)
    dialog_id = Column(Integer, ForeignKey("dialog.dialog_id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    value = Column(JSON, nullable=False)

    __table_args__ = (UniqueConstraint("dialog_id", "name"),)


class SQLAlchemyStateStore:
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
            self._set_engine(
                create_engine(
                    "sqlite://",
                    future=True,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                )
            )
        return self._engine

    @engine.setter
    def engine(self, value):
        self._set_engine(value)

    def _set_engine(self, value):
        self._engine = value
        Base.metadata.create_all(self._engine, checkfirst=True)

    @contextmanager
    def __call__(self, dialog):
        """Load and save state variables.

        :param dict dialog: A dialog for which the state is being loaded, with the schema :class:`~maxbot.schemas.DialogSchema`.
        :return StateVariables: A container for state variables.
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

            # make a deep copy to allow sqlalchemy track changes by
            # comparing with original values
            kv_pairs = [(v.name, copy.deepcopy(v.value)) for v in user.variables]
            variables = StateVariables.from_kv_pairs(kv_pairs)
            yield variables
            existing = {v.name: v for v in user.variables}
            for name, value in variables.to_kv_pairs():
                if name in existing:
                    var = existing.pop(name)
                    var.value = value
                else:
                    var = VariableTable(name=name, value=value)
                    user.variables.append(var)
            # variables that not in kv_pairs anymore must be deleted
            for var in existing.values():
                user.variables.remove(var)
            session.commit()
