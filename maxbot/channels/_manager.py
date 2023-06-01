"""Channels Manager."""

import asyncio
import inspect
import pkgutil
from abc import ABC, abstractmethod

from ..maxml import Schema, fields
from ..schemas import ResourceSchema

BUILTIN_CHANNELS = {
    "telegram": "maxbot.channels.telegram:TelegramChannel",
    "viber": "maxbot.channels.viber:ViberChannel",
    "facebook": "maxbot.channels.facebook:FacebookChannel",
    "vk": "maxbot.channels.vk:VkChannel",
}


class Channel(ABC):
    """Channel base class."""

    def __init__(self, name, config):
        """Create a new class instance.

        :param str name: Channel name.
        :param dict config: Channel configuration.
        """
        self.name = name
        self.config = config
        self._receive_hooks = list(self._discover_member_hooks("receive_"))
        self._send_hooks = list(self._discover_member_hooks("send_"))

    def _discover_member_hooks(self, prefix):
        """Discover hooks from the object methods.

        :param str prefix: Methods prefix.
        :return: An iterable of message type and hook.
        """
        prefix_len = len(prefix)
        for name, hook in inspect.getmembers(self, asyncio.iscoroutinefunction):
            if name.startswith(prefix):
                yield name[prefix_len:], hook

    @abstractmethod
    async def create_dialog(self, data):
        """Extract dialog information from incoming data.

        :param dict data: Channel-dependent incoming data.
        :return dict: A dialog information that matches the :class:`~maxbot.schemas.DialogSchema`.
        """

    @abstractmethod
    async def receive_text(self, data):
        """Receive a text message from the channel.

        :param dict data: Channel-dependent incoming data.
        :return dict: Text message.
        """

    @abstractmethod
    async def send_text(self, command, dialog):
        """Send a text command to the channel.

        :param dict command: A command to be sent.
        :param dict dialog: A dialog we respond in.
        """

    async def call_receivers(self, data):
        """Transform channel arguments to a message.

        :param dict data: Channel-dependent incoming data.
        """
        for _, hook in self._receive_hooks:
            message = await hook(data)
            if message is not None:
                return message
        return None

    async def call_senders(self, command, dialog):
        """Send command to the user as a response.

        :param dict command: A command to be sent.
        :param dict dialog: A dialog we respond in.
        :raise ValueError: There is no suitable sender.
        """
        for name, hook in self._send_hooks:
            if name in command:
                await hook(command, dialog)
                break
        else:
            raise ValueError(f"Could not execute command {command!r}")


class ChannelsCollection:
    """A collection of bot channels."""

    @classmethod
    def empty(cls):
        """Create an empty collection."""
        return cls([])

    def __init__(self, channels):
        """Create new class instance.

        :param list channels: List of channel objects.
        """
        self._channels = {c.name: c for c in channels}

    def __iter__(self):
        """Iterate over channel objects."""
        return iter(self._channels.values())

    @property
    def names(self):
        """Get a set of channel names.

        :return set: A set of channel names.
        """
        return set(self._channels.keys())

    def get(self, name):
        """Get a channel by its name.

        :param str name: Channel name.
        :return Channel|None: Channel object.
        """
        return self._channels.get(name)

    def __getattr__(self, name):
        """Access channel objects.

        :param str name: Channel name.
        :return Channel: Channel object.
        :raise AttributeError: There is no channel with this name in the collection.
        """
        try:
            return self._channels[name]
        except KeyError as exc:
            raise AttributeError(f"Unknown channel {name!r}") from exc

    def __bool__(self):
        """Check if the collection contains channels."""
        return bool(self._channels)


class ChannelFactory:
    """Create a channel from the list of mixins."""

    def __init__(self, name):
        """Create new class instance.

        :param str name: The name of the channel.
        """
        self.name = name
        self.loaded = None
        self._mixins = []

    def _resolve_mixins(self):
        rv = []
        for m in self._mixins:
            if isinstance(m, str):
                m = pkgutil.resolve_name(m)
            rv.append(m)
        return rv

    def add_mixin(self, mixin):
        """Add a mixin class for the channel.

        :param type mixin: Mixin class for the channel.
        :return ChannelFactory: To allow chained calls.
        """
        self._mixins.append(mixin)
        return self

    def create_class(self):
        """Create channel class.

        :return type: Channel class.
        """
        class_name = "".join(w.capitalize() or "_" for w in self.name.split("_"))
        mixins = self._resolve_mixins()
        return type(class_name, tuple(reversed(mixins)) + (Channel,), {})

    def get_class(self):
        """Get class for a channel.

        :return type: Channel class.
        """
        if self.loaded is None:
            self.loaded = self.create_class()
        return self.loaded

    def config_schema(self):
        """Config schema for the channel.

        The method is passed as a callable for the fields.Nested, which allows lazy loading.
        """
        schema_class = getattr(self.get_class(), "ConfigSchema", Schema)
        return schema_class()

    def create_instance(self, config=None):
        """Create channel instance.

        :param dict config: Channel configuration.
        :return Channel: Channel instance.
        """
        channel_class = self.get_class()
        return channel_class(self.name, config or {})


class ChannelManager:
    """Create and configure channels for a bot."""

    def __init__(self):
        """Create new class instance."""
        self.factories = {}
        self._register_builtin_channels()

    def _register_builtin_channels(self):
        for name, import_spec in BUILTIN_CHANNELS.items():
            self.add_mixin(import_spec, name)

    def add_mixin(self, mixin, name):
        """Add mixin class for the channel.

        :param type mixin: Mixin class.
        :param str name: Channel name.
        :return ChannelManager: To allow chained calls.
        """
        self.factories.setdefault(name, ChannelFactory(name)).add_mixin(mixin)
        return self

    def create_channels(self, resources):
        """Create channels with configurations defined by resources.

        :param Resources resources: Resources to get configuration.
        :return ChannelsCollection: Created channels.
        """
        schema_class = ResourceSchema.from_dict(
            {
                factory.name: fields.Nested(
                    factory.config_schema
                )  # config_schema will be called later
                for factory in self.factories.values()
            },
            name="ChannelsSchema",
        )
        configs = resources.load_channels(schema_class())
        return ChannelsCollection(
            self.factories[name].create_instance(config) for name, config in configs.items()
        )
