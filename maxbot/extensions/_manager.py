"""Extension Manager."""
import importlib.metadata
import pkgutil
from abc import abstractmethod

from ..maxml import Schema, fields
from ..schemas import ResourceSchema

BUILTIN_EXTENSIONS = {
    "rest": "maxbot.extensions.rest.RestExtension",
    "datetime": "maxbot.extensions.datetime.DatetimeExtension",
    "babel": "maxbot.extensions.babel.BabelExtension",
    "rasa": "maxbot.extensions.rasa.RasaExtension",
    "strict_undefined": "maxbot.extensions.strict_undefined.StrictUndefinedExtension",
    "jinja_loader": "maxbot.extensions.jinja_loader.jinja_loader",
}


class _ExtensionProxy:
    """A proxy that delays loading the wrapped extension.

    An actual extension is loaded only when declared in resources.
    """

    def __init__(self, name):
        self.name = name
        self.loaded = None

    @abstractmethod
    def load(self):
        """Load the wrapped extension."""

    def get(self):
        """Get the wrapped extension."""
        if self.loaded is None:
            self.loaded = self.load()
        return self.loaded

    def config_schema(self):
        """Config schema for the wrapped extension.

        The method is passed as a callable for the fields.Nested, which allows lazy loading.
        """
        config_class = getattr(self.get(), "ConfigSchema", Schema)
        return config_class()

    def apply(self, builder, config):
        """Apply the wrapped extension."""
        extension = self.get()
        extension(builder, config)


class _BuiltinProxy(_ExtensionProxy):
    """A proxy for builtin extensions."""

    def __init__(self, name, import_spec):
        super().__init__(name)
        self.import_spec = import_spec

    def load(self):
        return pkgutil.resolve_name(self.import_spec)


class _EntryPointProxy(_ExtensionProxy):
    """A proxy for extensions from entry point."""

    def __init__(self, entry_point):
        super().__init__(entry_point.name)
        self.entry_point = entry_point

    def load(self):
        return self.entry_point.load()


class _LoadedProxy(_ExtensionProxy):
    """A proxy for extensions that already loaded."""

    def __init__(self, name, extension):
        super().__init__(name)
        self.extension = extension

    def load(self):
        return self.extension


class ExtensionManager:
    """A manager that loads, configures and applies extensions."""

    def __init__(self):
        """Create new class instance."""
        self.proxies = self._discover_extensions()

    def _discover_extensions(self):
        proxies = []
        proxies.extend(_BuiltinProxy(name, spec) for name, spec in BUILTIN_EXTENSIONS.items())
        proxies.extend(_EntryPointProxy(entry_point) for entry_point in self._get_entry_points())
        return {p.name: p for p in proxies}

    _ENTRY_POINTS = []

    @classmethod
    def _get_entry_points(cls):
        """Cache entry points for performance reasons."""
        if not cls._ENTRY_POINTS:
            cls._ENTRY_POINTS = importlib.metadata.entry_points().get("maxbot_extensions", [])
        return cls._ENTRY_POINTS

    def add_extensions(self, extensions):
        """Add more extensions.

        :param dict extensions: Extensions in the form name->callable.
        """
        if extensions:
            self.proxies.update(
                {name: _LoadedProxy(name, extension) for name, extension in extensions.items()}
            )

    def apply_extensions(self, builder, resources):
        """Load, configure and apply extensions to the given builder.

        :param BotBuilder builder: A builder for the bot we need to extend.
        :param Resources resources: Resources to load extension configurations.
        """
        schema_class = ResourceSchema.from_dict(
            {
                proxy.name: fields.Nested(
                    proxy.config_schema
                )  # config_schema will be called later
                for proxy in self.proxies.values()
            },
            name="ExtensionsSchema",
        )
        configs = resources.load_extensions(schema_class())

        for name, config in configs.items():
            self.proxies[name].apply(builder, config)
