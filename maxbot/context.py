"""The context of the dialog turns."""
import logging
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from operator import attrgetter
from types import SimpleNamespace
from typing import Optional, Union

from .errors import BotError
from .jinja_env import StateNamespace
from .maxml import Schema

logger = logging.getLogger(__name__)


class _ReprAsIs:
    """Help to get string representation without quotes.

    For comparison:

        $ print (repr('XXX'))
        'XXX'

        $ print (repr(_ReprAsIs('XXX')))
        XXX
    """

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value


def _from_rich_repr(obj):
    """Create dataclass-like object representation using its 'rich repr protocol'.

    The protocol is not fully supported, just what we need.

    See https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol for more info.
    """
    items = [f"{k}={v!r}" for k, v in obj.__rich_repr__()]
    return "{}({})".format(  # pylint: disable=consider-using-f-string
        type(obj).__qualname__, ", ".join(items)
    )


@dataclass(frozen=True)
class RecognizedIntent:
    """An intent recognized from the user utterance."""

    # The name of the intent.
    name: str

    # A rating provided by NLU model that shows how confident it is that an intent is the correct
    # intent. Should be in the range 0.0 < confidence <= 1.0.
    confidence: float


@dataclass(frozen=True)
class IntentsResult:
    """The result of intent recognition in the user utterance."""

    @classmethod
    def resolve(cls, intents, top_threshold=0.5, definitions=None):
        """Create a class instance from the list of recognized intents.

        :param list intents: A list of intents recognized from the user utterance.
        :param float top_threshold: The minimum value of the confidence score for the `top` intent.
        :param dict definitions: Definitions of all available intents.
        :return IntentsResult:
        """
        ranking = tuple(sorted(intents, key=attrgetter("confidence"), reverse=True))
        for intent in ranking:
            logger.debug("%s", intent)
        top = ranking[0] if ranking else None
        if top and top.confidence < top_threshold:
            top = None
        return cls(top, ranking, definitions)

    # A recognized intent with the highest confidence score, greater than `top_threshold`.
    top: Optional[RecognizedIntent] = field(default=None)

    # All recognized intents are sorted in descending order of confidence score.
    ranking: tuple[RecognizedIntent] = field(default_factory=tuple)

    # Definitions of all available intents
    definitions: Optional[dict] = field(default=None)

    @property
    def irrelevant(self):
        """Return True if no intent is recognized."""
        return not self.top

    def __getattr__(self, name):
        """Return the top intent if it matched the given name.

        This is a convenient way to check the top intent for scenarios. Instead of

            intents.top == 'my_intent'

        you can just write

            intents.my_intent

        :param str name: The name of the intent you want to check.
        :return RecognizedIntent|None: The top intent if it matches the given name.
        """
        if self.definitions is not None:
            if name not in self.definitions:
                # this kind of errors does not lead to undefined in jinja
                raise ValueError(f"No such intent: {name!r}.")
        if self.top and self.top.name == name:
            return self.top
        return None

    def __repr__(self):
        """Create representation replacing repeated objects with placeholders."""
        return _from_rich_repr(self)

    def __rich_repr__(self):
        """Support for 'rich repr protocol'."""
        yield "top", self.top
        ranking = self.ranking
        if self.top:
            if self.top.name.isidentifier():
                yield self.top.name, _ReprAsIs("RecognizedIntent(...)")
            ranking = (_ReprAsIs("RecognizedIntent(...)"),) + self.ranking[1:]
        yield "ranking", ranking


@dataclass(frozen=True)
class RecognizedEntity:
    """An entity recognized from the user utterance."""

    # The name of the entity.
    name: str

    # The value of the entity.
    value: Union[str, int]

    # How exactly the entity was present in the utterance.
    literal: str

    # An index of the first char of the literal value in the utterance.
    start_char: int

    # An index of the last char of the literal value in the utterance.
    end_char: int

    @classmethod
    def from_span(cls, span, name=None, value=None):
        """Create a class instance from spacy's span.

        :param spacy.tokens.Span span: The spacy's span.
        :param str name: The name of the entity.
        :param any value: The value of the entity.
        :return RecognizedEntity:
        """
        if value is None:
            value = span.text
        return cls(name or span.label_, value, span.text, span.start_char, span.end_char)


@dataclass(frozen=True)
class EntitiesProxy:
    """All entities with the same name recognized from the user utterance."""

    # All entities.
    all_objects: tuple[RecognizedEntity]

    # Entity definition
    definition: Optional[dict] = field(default=None)

    @property
    def all_values(self):
        """Return a tuple of all entities values.

        :return tuple:
        """
        return tuple(e.value for e in self.all_objects)

    @property
    def first(self):
        """Return the first recognized value.

        :return RecognizedEntity:
        """
        return self.all_objects[0] if self.all_objects else None

    def __getattr__(self, name):
        """Access the proxied entities in a convenient way.

        First, often you need attributes of the first entity only, so use

            entities.menu.value
            entities.menu.literal

        instead of equal but longer version

            entities.menu.all_objects[0].value
            entities.menu.all_objects[0].literal

        Second, the most common task is to check that the value is present in the collection.
        You can use

            entities.menu.vegetarian

        which is equal to more bulky

            'vegetarian' in entities.menu.all_values

        :param str name: The name of an entity attribute of checked entity value.
        :return any: The value of an entity attribute of boolean entity value presense flag.
        """
        if self.first and hasattr(self.first, name):
            return getattr(self.first, name)
        if name in self.all_values:
            return True
        if self.definition and any(name == v["name"] for v in self.definition.get("values", [])):
            # the value is defined but not recognized
            return False
        raise AttributeError

    def __bool__(self):
        """Determine if the entity is recognized or not."""
        return bool(self.all_objects)

    def __repr__(self):
        """Create representation replacing repeated objects with placeholders."""
        return _from_rich_repr(self)

    def __rich_repr__(self):
        """Support for 'rich repr protocol'."""
        if self.first:
            for f in fields(self.first):
                yield f.name, getattr(self.first, f.name)
        elif self.definition:
            yield "name", self.definition["name"]

        if self.definition:
            for v in self.definition.get("values", []):
                v = v["name"]
                yield v, v in self.all_values
        yield "all_values", self.all_values
        yield "all_objects", _ReprAsIs("(...)") if self.all_objects else tuple()


@dataclass(frozen=True)
class EntitiesResult:
    """The result of entity recognition in the user utterance."""

    @classmethod
    def resolve(cls, entities, definitions=None):
        """Create a class instance from the list of recognized entities.

        :param List[RecognizedEntity] entities: A list of recognized entities in the order they
                                                are appear in the utterance.
        :param dict definitions: Definitions of all available intents.
        :return EntitiesResult:
        """
        mapping = {}
        for entity in entities:
            logger.debug("%s", entity)
            mapping.setdefault(entity.name, []).append(entity)
        proxies = {}
        for name, objects in mapping.items():
            proxies[name] = EntitiesProxy(
                tuple(objects), definitions.get(name) if definitions else None
            )
        if definitions:
            for name in definitions:
                if name not in proxies:
                    proxies[name] = EntitiesProxy(tuple(), definitions[name])
        return cls(proxies, tuple(entities))

    # Maps entity names to proxies with corresponding entities.
    proxies: dict[str, EntitiesProxy] = field(default_factory=dict)

    # A tuple of all recognized entities in the order they are appear in the utterance.
    all_objects: tuple[RecognizedEntity] = field(default_factory=tuple)

    def __getattr__(self, name):
        """Return a proxy with the entities that matched the name.

        Convenient access to entity proxies. Simply use

            entities.menu

        instead of

            entities.proxies['menu']

        :param str name: The name of the entity.
        :return EntitiesProxy: A proxy with the entities that matched the name.
        """
        if name in self.proxies:
            return self.proxies[name]
        # this kind of errors does not lead to undefined in jinja
        raise AttributeError(f"No such entity: {name!r}.")

    def __repr__(self):
        """Create representation replacing repeated objects with placeholders."""
        return _from_rich_repr(self)

    def __rich_repr__(self):
        """Support for 'rich repr protocol'."""
        yield "all_objects", self.all_objects
        yield "proxies", _ReprAsIs("{...}")
        for name in self.proxies:
            if name.isidentifier():
                yield name, _ReprAsIs("EntitiesProxy(...)")


@dataclass(frozen=True)
class StateVariables:
    """A container for state variables loaded by state tracker."""

    # User variables that live forever.
    user: dict = field(default_factory=dict)

    # Skill variables that live during discussing a topic.
    slots: dict = field(default_factory=dict)

    # Private variables used by **maxbot** internal components.
    components: dict = field(default_factory=dict)

    @classmethod
    def empty(cls):
        """Create empty state."""
        return StateVariables()

    @classmethod
    def from_kv_pairs(cls, kv_pairs):
        """Create a class instance from a flat list of key-value pairs.

        Expecting the list in the following form:

            [
                (user<name_1>, <value_1>),
                ...
                (slots<name_1>, <value_1>),
                ...
                (components<name_1>, <value_1>),
                ...
            ]

        where keys are of string type.

        :param list kv_pairs: A list of key-value pairs described above.
        :return StateVariables:
        :raise ValueError: Meet unknown namespace.
        """
        data = {f.name: {} for f in fields(cls)}
        for name, value in kv_pairs:
            ns, name = name.split(".", 1)
            if ns not in data:
                raise ValueError(f"Unknown ns {ns}")
            data[ns][name] = value
        return cls(**data)

    def to_kv_pairs(self):
        """Convert an instance to the format described in :meth:`~from_kv_pairs`."""
        for f in fields(self):
            for name, value in getattr(self, f.name).items():
                name = f"{f.name}.{name}"
                yield name, value


@dataclass(frozen=True)
class RpcRequest:
    """RPC request."""

    # Requested method.
    method: str

    # Actual parameters.
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RpcContext:
    """The context of the RPC request being processed."""

    # RPC request.
    request: RpcRequest = None

    @property
    def method(self):
        """Return RPC method if request is present otherwise return None."""
        return self.request.method if self.request else None

    @property
    def params(self):
        """Return RPC params if request is present otherwise return None."""
        return self.request.params if self.request else None

    def __getattr__(self, name):
        """Return rpc request is its called.

        This is a convenient way to check the called rpc request in scenarios. Instead of

            rpc.request.method == 'my_method'

        you can just write

            rp.my_method

        :param str name: RPC method you want to check.
        :return RpcRequest|None: RPC request if it matches the given method.
        """
        if self.request and self.request.method == name:
            return self.request
        raise AttributeError(f"{name!r} is not a called rpc method.")

    def __bool__(self):
        """Check if we are processing the request.

        The `rpc` object is falsy when there no actual rpc request.
        This makes it more obvious to use it in scenarios.

        :return bool: Do we have an actual rpc request.
        """
        return bool(self.request)

    def __repr__(self):
        """Create representation replacing repeated objects with placeholders."""
        return _from_rich_repr(self)

    def __rich_repr__(self):
        """Support for 'rich repr protocol'."""
        yield "method", self.method
        yield "params", self.params
        if self.request:
            yield self.request.method, _ReprAsIs("RpcRequest(...)")
            yield "request", _ReprAsIs("RpcRequest(...)")
        else:
            yield "request", self.request


def get_utc_time_default():
    """Return current time in UTC (default factory for TurnContext.utc_time)."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TurnContext:
    """The context used by the bot when processing the user message."""

    # An information about the dialog.
    dialog: dict

    # State variables of the dialog.
    state: StateVariables = field(default_factory=StateVariables)

    # Date and time of turn (in UTC)
    utc_time: datetime = field(default_factory=get_utc_time_default)

    # User message processed by the bot.
    message: dict = field(default_factory=dict)

    # The context of the RPC request processed by the bot.
    rpc: RpcContext = field(default_factory=RpcContext)

    # Intents recognized from the message.
    intents: IntentsResult = field(default_factory=IntentsResult)

    # Entities recognized from the message.
    entities: EntitiesResult = field(default_factory=EntitiesResult)

    # Additional variables for the scenario context.
    scenario: dict = field(default_factory=SimpleNamespace, init=False)

    # Process user message journal
    journal_events: list[dict] = field(default_factory=list, init=False)

    # Commands to respond to the user.
    commands: list[dict] = field(default_factory=list, init=False)

    # Schema of `.commands`
    command_schema: Optional[Schema] = field(default=None)

    # An error occured.
    error: Optional[BotError] = field(default=None, init=False)

    def __post_init__(self):
        """Make sure that turn is either foreground or background which is mutually exclusive."""
        assert bool(self.message) != bool(self.rpc)

    def get_state_variable(self, key):
        """Get state variable for the component.

        :param str key: The key used by the component to store its variable.
        :return Any:
        """
        return self.state.components.get(key)

    def set_state_variable(self, key, value):
        """Set state variable for the component.

        :param str key: The key used by the component to store its variable.
        :param any value: A json-serializable value to store.
        """
        self.state.components[key] = value

    def clear_state_variables(self):
        """Clear state variables for all components."""
        self.state.components.clear()
        self.state.slots.clear()

    def create_scenario_context(self, params):
        """Create the scenario context corresponding to the turn context.

        Variables are included to the scenario context in the following order
        (later ones overwrite earlier ones).

            * Variables from the :attr:`~scenario_context`.
            * Variables passed in :param:`~params`.
            * Built-in variables.

        Built-in variables passed to the scenario context.

        =====    =====                                          ======
        Name     Type                                           Description
        =====    =====                                          ======
        message   dict (:class:`~maxbot.schemas.MessageSchema`) A message processed by the bot.
        dialog    dict (:class:`~maxbot.schemas.DialogSchema`)  An information about the dialog.
        intents   IntentsResult                                 Intents recognized from the message.
        entities  EntitiesResult                                Entities recognized from the message.
        user      dict                                          User variables that live forever.
        slots     dict                                          Skill variables that live during discussing a topic.
        =====    =====                                          ======

        :param dict params: A dict of variables to include to the result.
        :return dict: The scenario context.
        """
        rv = {}
        rv.update(self.scenario.__dict__)
        rv.update(params)
        rv.update(
            {
                "message": self.message,
                "dialog": self.dialog,
                "intents": self.intents,
                "entities": self.entities,
                "user": StateNamespace(self.state.user),
                "slots": StateNamespace(self.state.slots),
                "rpc": self.rpc,
                "params": self.rpc.request.params if self.rpc.request else {},
                "utc_time": self.utc_time,
                "utc_today": self.utc_time.date(),
                "_turn_context": self,
            }
        )
        return rv

    def extend(self, **attributes):
        """Add the attributes to the instance of the context if they do not exist yet.

        This is used by extensions to pass data between hooks.
        """
        for key, value in attributes.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    def journal_event(self, event_type, payload):
        """Add new journal event.

        :param str event_type: Type of the event.
        :param any payload: Payload of the event.
        :return any: Payload of inserted event.
        """
        logger.debug("%s %s", event_type, payload)
        event = {"type": event_type, "payload": payload}
        self.journal_events.append(event)
        return event["payload"]

    def log(self, level, message):
        """Log the message.

        :param str level: Log level.
        :param any message: Log message.
        """
        self.journal_event("log", {"level": level, "message": message})

    def debug(self, message):
        """Log the message with level DEBUG.

        :param any message: Log message.
        """
        self.log("DEBUG", message)

    def warning(self, message):
        """Log the message with level WARNING.

        :param any message: Log message.
        """
        self.log("WARNING", message)

    def set_error(self, error):
        """Set the error occured during context processing.

        :param BotError error
        """
        object.__setattr__(self, "error", error)

    @staticmethod
    def extract_log_event(event):
        """Try to extract level and message from journal event.

        :param dict event: Event from TrunContext.journal_events.
        :return tuple: Extracted level and message or (None, None)
        """
        if event.get("type") == "log":
            payload = event.get("payload")
            if isinstance(payload, dict):
                return payload.get("level"), payload.get("message")
        return None, None
