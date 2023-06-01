"""Schemas for bot resources."""
import os
import re
import textwrap
from collections.abc import Hashable

import marshmallow.exceptions
import yaml

from .errors import BotError, XmlSnippet, YamlSnippet, YamlSymbols
from .maxml import Schema, fields, markup, post_load, pre_load
from .maxml.xml_parser import XmlParser


class LoaderFactory(yaml.BaseLoader):  # pylint: disable=R0901
    """Make yaml loader customizable.

    YAML loaders are customized at class level. We perform dynamic subclassing and use class-level
    customization methods to create different loaders with various capabilities.
    """

    @classmethod
    def new_loader(cls):
        """Create a dynamic subclass to customize it separately."""
        return type("ConcreteLoader", (cls,), {})

    @classmethod
    def load(cls, data):
        """Load yaml document."""
        try:
            # nosec note: actualy we derive a safe loader
            return yaml.load(data, Loader=cls)  # nosec B506
        except yaml.MarkedYAMLError as exc:
            raise YamlParsingError(exc) from exc

    @classmethod
    def register_unknown_tag_error(cls):
        """Raise `yaml.constructor.ConstructorError` on unknown tag."""

        def _raise_constructor_error(loader, node):
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"could not determine a constructor for the tag {node.tag!r}",
                node.start_mark,
            )

        cls.add_constructor(None, _raise_constructor_error)

    @classmethod
    def register_variable_substitution(cls):
        """Add capability to substitute special placeholders with environment variables.

        Variables are replaced in string scalars beginning with the `!ENV` tag. Default values
        provided after the colon `:`. Example:

            username: !ENV ${DB_USER:paws}
            password: !ENV ${DB_PASS}

        More complex example:

            database:
                url: !ENV postgresql://${DB_USER:paws}:${DB_PASS}@${DB_HOST}:${DB_PORT}/mydatabase
        """
        variable_re = re.compile(r".*?\$\{([^}{:]+)(:([^}]+))?\}.*?")

        def substitute_variables(loader, node):
            string = loader.construct_scalar(node)
            for name, with_colon, default in variable_re.findall(string):
                if with_colon:
                    value = os.environ.get(name, default)
                elif name not in os.environ:
                    raise BotError(
                        f"Missing required environment variable {name!r}",
                        YamlSnippet.at_mark(node.start_mark),
                    )
                else:
                    value = os.environ[name]
                string = string.replace(f"${{{name}{with_colon}}}", value, 1)
            return string

        cls.add_constructor("!ENV", substitute_variables)

    @classmethod
    def _register_default_constructors(cls):
        if hasattr(cls, "maxbot_pre_construct_handler"):
            assert hasattr(cls, "maxbot_post_construct_handler")
            return  # already registered

        assert not hasattr(cls, "maxbot_post_construct_handler")

        cls.maxbot_pre_construct_handler = {}
        cls.maxbot_post_construct_handler = {}

        def create_default_constructor(constructor_name):
            def default_constructor(loader, node):
                handler = loader.__class__.maxbot_pre_construct_handler.get(node.tag)
                if handler:
                    handler(loader, node)

                rv = getattr(loader, constructor_name)(node)

                handler = loader.__class__.maxbot_post_construct_handler.get(node.tag)
                if handler:
                    handler(rv, node)

                return rv

            return default_constructor

        cls.add_constructor(
            "tag:yaml.org,2002:map", create_default_constructor("construct_mapping")
        )
        cls.add_constructor(
            "tag:yaml.org,2002:seq", create_default_constructor("construct_sequence")
        )
        cls.add_constructor(
            "tag:yaml.org,2002:str", create_default_constructor("construct_scalar")
        )

    @classmethod
    def set_post_construct_debug_watcher(cls):
        """Add capabilities to debug loaded documents using :class:`~YamlSymbols`."""
        cls._register_default_constructors()

        cls.maxbot_post_construct_handler["tag:yaml.org,2002:map"] = YamlSymbols.add
        cls.maxbot_post_construct_handler["tag:yaml.org,2002:seq"] = YamlSymbols.add
        cls.maxbot_post_construct_handler["tag:yaml.org,2002:str"] = YamlSymbols.add

    @classmethod
    def set_pre_construct_strict_map_checker(cls):
        """Add a strict check that the maps do not contain duplicate keys."""
        cls._register_default_constructors()

        def check(loader, node):
            processed = set()
            for key_node, _ in node.value:
                key = loader.construct_object(key_node)
                if isinstance(key, Hashable):
                    if key in processed:
                        raise yaml.constructor.ConstructorError(
                            "While constructing a mapping",
                            node.start_mark,
                            f'found duplicate key: "{key}"',
                            key_node.start_mark,
                            None,
                        )
                    processed.add(key)

        cls.maxbot_pre_construct_handler["tag:yaml.org,2002:map"] = check


class YamlParsingError(BotError):
    """An error in YAML markup with a nice formatting."""

    def __init__(self, exc):
        """Create new class instance.

        :param yaml.MarkedYAMLError exc: An original YAML error.
        """
        lines = []
        if exc.context:
            lines.append(exc.context)
        if exc.context_mark:
            snippet = YamlSnippet.at_mark(exc.context_mark).format()
            snippet = textwrap.indent(snippet, "  ")
            lines.append(snippet)
        if exc.problem:
            lines.append(exc.problem)
        if exc.problem_mark:
            snippet = YamlSnippet.at_mark(exc.problem_mark).format()
            snippet = textwrap.indent(snippet, "  ")
            lines.append(snippet)
        if exc.note:
            lines.append(exc.note)
        super().__init__("\n".join(lines))


class RenderConfig:
    """Module to load YAML documents using the :meth:`~Schema.loads`.

    Uses customized loader with the following apabilities:

        * :meth:`~LoaderFactory.register_variable_substitution`.
        * :meth:`~LoaderFactory.set_pre_construct_strict_map_checker`.
        * :meth:`~LoaderFactory.set_post_construct_debug_watcher`.
    """

    def __init__(self):
        """Create new class instance."""
        self.Loader = LoaderFactory.new_loader()
        self.Loader.register_variable_substitution()
        self.Loader.register_unknown_tag_error()
        self.Loader.set_pre_construct_strict_map_checker()
        self.Loader.set_post_construct_debug_watcher()

    def loads(self, data):
        """Deserialize a YAML data structure to an object defined by this Schema's fields.

        :param str data: A YAML string of the data to deserialize.
        """
        return self.Loader.load(data)


class MarshmallowSchema(Schema):
    """Base schema for marshmallow schemas."""

    def _create_error(self, message, data, key=None):
        raise AssertionError("Method is abstract")

    def handle_error(self, error, data, **kwargs):
        """Wrap ValidationError with a :class:`~BotError` that contains user friendly snippet.

        This is an implementation for custom error handler function for the schema.

        Raise only the first error with corresponding source data from marshmallow's normalized
        error messages.

        Contains some workarounds for the correct output of the snippet.

        :param ValidationError error: The ValidationError raised during (de)serialization.
        :param dict data: The original input data.
        :param dict kwargs: Ignored arguments.
        :raise BotError:
        """

        def first_error(errors, source):
            field, messages = next(iter(errors.items()))
            if isinstance(messages, dict):
                # go deeper, an error occured in nested schema
                return first_error(messages, source[field])
            if isinstance(messages, list):
                # several messages for one field
                messages = "\n".join(messages)
            if field == marshmallow.exceptions.SCHEMA:
                # actualy not a field in schema but schema itself
                field = None
            if messages == fields.Field.default_error_messages["required"]:
                # add missing field name
                messages = f"Missing required field {field!r}."
            if messages == self.error_messages["unknown"]:
                # add missing field name
                messages = f"Unknown field {field!r}."
                # point to the field itself, not to its value
                source = field
                field = None
            return self._create_error(messages, source, key=field)

        raise first_error(error.normalized_messages(), data) from error


class ResourceSchema(MarshmallowSchema):
    """Base schema for resource schemas."""

    class Meta:
        """Options object for a Schema."""

        render_module = RenderConfig()

    def _create_error(self, message, data, key=None):
        return BotError(message, YamlSnippet.from_data(data, key=key))

    def load_file(self, path, **kwargs):
        """Load YAML files in a convenient way.

        :param str path: A path to a file.
        :param dict kwargs: Keyword arguments passed to :meth`~Schema.loads`.
        """
        try:
            with open(path, encoding="utf8") as f:
                return self.loads(f, **kwargs)
        except OSError as exc:
            raise BotError(f"Could not load file {path}: {exc}") from exc

    @post_load(pass_original=True)
    def post_load(self, data, original_data, **kwargs):
        """Add yaml symbols for loaded data.

        :param dict data: Deserialized data.
        :param dict original_data: Original data before deserialization.
        :param dict kwargs: Ignored arguments.
        """
        for name in self._declared_fields:
            if name in data and isinstance(original_data, dict) and name in original_data:
                YamlSymbols.reference(data[name], original_data[name])
        YamlSymbols.reference(data, original_data)
        return data


class DialogSchema(ResourceSchema):
    """General information about the current conversation.

    Includes information that does not change or rarely changes during a conversation.
    """

    # The name of the channel in which the conversation is taking place.
    channel_name = fields.String(required=True)

    # The ID of the user with whom the conversation is taking place.
    # This ID is unique within the channel.
    user_id = fields.String(required=True)


class ImageMessage(Schema):
    """An image message payload."""

    # Image URL. You can use this URL to get the image file.
    # Download it ASAP because URL lifetime not guaranteed.
    url = fields.Url(required=True)

    # Image size in bytes.
    size = fields.Integer()

    # Caption as defined by the user.
    caption = fields.Str()


class MessageSchema(ResourceSchema):
    """Message received by the user.

    This schema is implemented as an envelope for a different message types. The schema field
    represents a message of particular type. The field name is the name of the message type. The
    field type is the payload for the message of that type. Typically, only one field is
    populated for the message. Examples;

        MessageSchema().loads('''
            text: Hello world!
        ''')
        # {'text': 'Hello world!'}

        MessageSchema().loads('''
            image:
                url: http://example.com/hello.png
                caption: Hello world!
        ''')
        # {'image': {'url': 'http://example.com/hello.png', 'caption': 'Hello world!'}}

    The schema supports most widely used message types in a platform-independent way. You can
    customize the schema by adding new types and overriding existing types. For example, given
    the payload for new message type 'location':

        class LocationMessage(Schema):
            longitude = fields.Float()
            latitude = fields.Float()

    we can extend our message schema by declaring a subclass

        class MyMessageSchema(MessageSchema):
            location = fields.Nested(LocationMessage)

    or generating subclass using :meth:`~Schema.from_dict`

        MyMessageSchema = MessageSchema.from_dict(
            {
                'location': fields.Nested(LocationMessage)
            }
        )

    Next, we can use the resulting schema to load our custom message:

        MyMessageSchema().loads('''
            location:
                latitude: 40.7580
                longitude: -73.9855
        ''')
        # {'location': {'latitude': 40.7580, 'longitude': 40.7580}}
    """

    # Text message.
    text = fields.String()

    # Image message.
    image = fields.Nested(ImageMessage)

    @pre_load
    def short_syntax(self, data, **kwargs):
        """Short syntax for text message.

        You can write

            message: Hello world

        instead of

            message:
                text: Hello world

        Useful mostly for writing stories.

        :param dict data: Deserialized data.
        :param dict kwargs: Ignored arguments.
        """
        if isinstance(data, str):
            data = {"text": data}
        return data


class MaxmlSchema(MarshmallowSchema):
    """Base schema for MAXML commands."""

    class Meta:
        """Options object for a Schema."""

        render_module = XmlParser()

    class _Error(Exception):
        def __init__(self, message, data, key):
            self.message = message
            self.data = data
            self.key = key

    def _create_error(self, message, data, key=None):
        return self._Error(message, data, key)

    def loads(self, json_data, **kwargs):
        """Load commands from headless XML document."""
        symbols = {}
        unvalidated = self.opts.render_module.loads(
            json_data, maxml_command_schema=self, maxml_symbols=symbols
        )

        try:
            return self.load(unvalidated, **kwargs)
        except self._Error as exc:
            ptr = None
            if isinstance(exc.data, dict) and exc.key is not None:
                ptr = symbols.get(id(exc.data.get(exc.key)))
            if ptr is None:
                ptr = symbols.get(id(exc.data))
            snippet = XmlSnippet(json_data.splitlines(), ptr.lineno, ptr.column) if ptr else None
            # chain with original marshmallow.exceptions.ValidationError
            raise BotError(exc.message, snippet) from exc.__cause__


class ImageCommand(Schema):
    """An image command payload."""

    # HTTP URL to get a file from the Internet.
    url = fields.Url(required=True)

    # Caption of the image to be sent.
    caption = markup.Field()


class CommandSchema(MaxmlSchema):
    """Command to send to user.

    This schema is implemented as an envelope for a different command types. The schema field
    represents a command of particular type. The field name is the name of the command type. The
    field type is the payload for the command of that type. Typically, only one field is
    populated for the command and commands are loaded in whole lists. For example, a list of
    two commands:

        CommandSchema(many=True).loads('''
            Hello world!
            <image url="http://example.com/hello.png" />
        ''')
        # [{'text': <maxml.markup.Value'Hello world!'>}, {'image': {'url': 'http://example.com/hello.png'}}]

    The schema supports most widely used command types in a platform-independent way. You can
    customize the schema by adding new types and overriding existing types. For example, given
    the payload for new command type 'location':

        class LocationCommand(Schema):
            longitude = fields.Float()
            latitude = fields.Float()

    we can extend our command schema by declaring a subclass

        class MyCommandSchema(CommandSchema):
            location = fields.Nested(LocationCommand)

    or generating subclass using :meth:`~Schema.from_dict`

        MyCommandSchema = CommandSchema.from_dict(
            {
                'location': fields.Nested(LocationCommand)
            }
        )

    Next, we can use the resulting schema to load our custom message:

        MyCommandSchema(many=True).loads('''
            Here is my location.
            <location latitude="40.7580" longitude="-73.9855" />
        ''')
        # [{'text': 'Here is my location.'}, {'location': {'latitude': 40.7580, 'longitude': 40.7580}}]
    """

    # Text message.
    text = markup.Field()

    # Image message.
    image = fields.Nested(ImageCommand)
