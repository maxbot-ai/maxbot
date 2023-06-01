"""MaxBot creation."""
from functools import cached_property, partial

from ._hooks import HookWrapper
from .bot import MaxBot
from .channels import ChannelManager
from .dialog_manager import DialogManager
from .extensions import ExtensionManager
from .flows.dialog_flow import DialogFlow
from .jinja_env import create_jinja_env
from .maxml import fields
from .resources import (
    DirectoryResources,
    FileResources,
    InlineResources,
    PackageResources,
    Resources,
)
from .rpc import RpcManager
from .schemas import CommandSchema, DialogSchema, MessageSchema
from .user_locks import AsyncioLocks


class BotBuilder:
    """This class is used to customize components and load resources while building a bot."""

    # Options that are passed to the Jinja environment in :attr:`jinja_env`. Changing these options
    # after the environment is created (accessing :attr:`jinja_env`) will have no effect.
    jinja_options = {}

    def __init__(self, *, available_extensions=None):
        """Create new class instance.

        :param dict available_extensions: A dictionary of available extensions.
        """
        self._extension_manager = ExtensionManager()
        self._extension_manager.add_extensions(available_extensions)
        self._channel_manager = ChannelManager()
        self._bot_created = False
        self.resources = Resources.empty()
        self._user_locks = None
        self._state_store = None
        self._nlu = None
        self._message_schemas = {}
        self._command_schemas = {}
        self._before_turn_hooks = []
        self._after_turn_hooks = []
        self._middlewares = []

    def add_message(self, schema, name):
        """Register a custom message.

        Example::

            class LocationMessage(Schema):
                longitude = fields.Float()
                latitude = fields.Float()

            builder.add_message(LocationMessage, 'location')

        :param type schema: Message schema.
        :param str name: Message name.
        """
        self._message_schemas[name] = schema
        return schema

    def message(self, name):
        """Register a custom message.

        Example::

            @builder.message('location')
            class LocationMessage(Schema):
                longitude = fields.Float()
                latitude = fields.Float()

        :param str name: Message name.
        """
        return partial(self.add_message, name=name)

    def _create_message_schema(self):
        return MessageSchema.from_dict(
            {n: fields.Nested(s) for n, s in self._message_schemas.items()}
        )

    def add_command(self, schema, name):
        """Register a custom command.

        Example::

            class PollCommand(Schema):
                question = fields.String()
                options = fields.List(fields.String)

            builder.add_message(PollCommand, 'poll')

        :param type schema: Command schema.
        :param str name: Command name.
        """
        self._command_schemas[name] = schema
        return schema

    def command(self, name):
        """Register a custom command.

        Example::

            @builder.command('poll')
            class PollCommand(Schema):
                question = fields.String()
                options = fields.List(fields.String)

        :param str name: Command name.
        """
        return partial(self.add_command, name=name)

    def _create_command_schema(self):
        return CommandSchema.from_dict(
            {n: fields.Nested(s) for n, s in self._command_schemas.items()}
        )

    def add_channel_mixin(self, mixin, name):
        """Register a mixin for a channel.

        :param type mixin: A mixin to be registered.
        :param str name: Channel name.
        :return type: Registered mixin.
        """
        self._channel_manager.add_mixin(mixin, name)
        return mixin

    def channel_mixin(self, name):
        """Register a mixin for a channel.

        :param str name: Channel name.
        :return type: Registered mixin.
        """
        return partial(self.add_channel_mixin, name=name)

    @property
    def user_locks(self):
        """User locks service.

        See default implementation :class:`~maxbot.user_locks.AsyncioLocks` for more information.
        """
        if self._user_locks is None:
            self._user_locks = AsyncioLocks()
        return self._user_locks

    @user_locks.setter
    def user_locks(self, value):
        self._user_locks = value

    @property
    def state_store(self):
        """State store used to maintain state variables.

        See default implementation :class:`~maxbot.state_store.SQLAlchemyStateStore` for more information.
        You can use this property to configure default state tracker::

            builder.state_store.engine = sqlalchemy.create_engine(...)

        or set your own implementation::

            class CustomStateStore:
                @contextmanager
                def __call__(self, dialog):
                    # load variables...
                    yield StateVariables(...)
                    # save variables...

            builder.state_store = CustomStateStore()
        """
        if self._state_store is None:
            # lazy import to speed up load time
            from .state_store import SQLAlchemyStateStore

            self._state_store = SQLAlchemyStateStore()
        return self._state_store

    @state_store.setter
    def state_store(self, value):
        self._state_store = value

    @property
    def nlu(self):
        """NLU component used to recognize intent and entities from user's utterance.

        See default implementation :class:`~maxbot.nlu.NLU` for more information.
        You can use this property to configure nlu component:

            builder.nlu.threshold = 0.6

        or set your own implementation:

            class CustomNlu:
                def load(self, intents, entities):
                    ...

                def __call__(self, message):
                    ...
                    return NluResult(...)

            builder.nlu = CustomNlu()
        """
        if self._nlu is None:
            # lazy import to speed up load time
            from .nlu import Nlu

            self._nlu = Nlu()
        return self._nlu

    @nlu.setter
    def nlu(self, nlu):
        self._nlu = nlu

    @cached_property
    def jinja_env(self):
        """Access jinja environment used to render templates.

        You can use this property to configure the environment::

            builder.jinja_env.add_extension(MyJinjaExtension)

        Also you can use convenient bot methods to add filters, tests and globals to the environment.
        The environment is created the first time this property is accessed. Changing :attr:`jinja_options` after that
        will have no effect.
        """
        return create_jinja_env(self.jinja_options)

    def add_template_filter(self, f, name=None):
        """Register a custom jinja template filter.

        Example::

            builder.add_template_filter(lambda s: s[::-1], 'reverse')

        :param callable f: A filter function.
        :param str name: An optional name of the filter, otherwise the function name will be used.
        """
        self.jinja_env.filters[name or f.__name__] = f
        return f

    def template_filter(self, name=None):
        """Register a custom jinja template filter.

        Example::

            @builder.template_filter()
            def reverse(s):
                return s[::-1]

        :param str name: An optional name of the filter, otherwise the function name will be used.
        """
        return partial(self.add_template_filter, name=name)

    def add_template_test(self, f, name=None):
        """Register a custom jinja template test.

        Example::

            def greeting(s):
                return any(h in s for h in ["hello", "hey"])

            builder.add_template_test(greeting)

        :param callable f: A test function.
        :param str name: An optional name of the test, otherwise the function name will be used.
        """
        self.jinja_env.tests[name or f.__name__] = f
        return f

    def template_test(self, name=None):
        """Register a custom jinja template test.

        Example::

            @builder.template_test()
            def greeting(s):
                return any(h in s for h in ["hello", "hey"])

        :param str name: An optional name of the test, otherwise the function name will be used.
        """
        return partial(self.add_template_test, name=name)

    def add_template_global(self, f, name=None):
        """Register a custom function in the jinja template global namespace.

        Example::

            def say_hello(name):
                return f"Hello, {name}!"

            builder.add_template_global(say_hello, 'hello')

        :param callable f: A function to be registered.
        :param str name: An optional name in the global namespace, otherwise the function name will be used.
        """
        self.jinja_env.globals[name or f.__name__] = f
        return f

    def template_global(self, name=None):
        """Register a custom function in the jinja template global namespace.

        Example::

            @builder.template_global('hello')
            def say_hello(name):
                return f"Hello, {name}!"

        :param str name: An optional name in the global namespace, otherwise the function name will be used.
        """
        return partial(self.add_template_global, name=name)

    def before_turn(self, f):
        """Register a function to run before each dialog turn.

        The function is called with one argument of type :class:`~maxbot.context.TurnContext`
        with information about the current turn.

        For example, this can be used to provide custom user profile to scenario context.

            @builder.before_turn
            def load_profile(ctx):
                resp = requests.get('http://example.com/profile/' + ctx.dialog.user_id)
                ctx.scenario.profile=resp.json()

        :param callable f: A hook function.
        """
        self._before_turn_hooks.append(HookWrapper(f))
        return f

    def after_turn(self, f):
        """Register a function to run after each dialog turn.

        The function is called with two arguments

            * :class:`~maxbot.context.TurnContext` - information about the current turn;
            * bool - whether the bot is waiting for the user's response.

        For example, this can be used to journal all the conversation messages::

            @builder.after_turn
            def journal_conversation(ctx):
                requests.post('http://example.com/journal/, json_data={
                    'user_id': ctx.dialog.user_id,
                    'message': ctx.message,
                    'commands': ctx.commands,
                })

        :param callable f: A hook function.
        """
        self._after_turn_hooks.append(HookWrapper(f))
        return f

    def add_middleware(self, middleware):
        """Add Middleware for dialog step.

        Example::
            class MyLogMiddleware:
                def __call__(self, take_turn):
                    def _take_turn(dialog, state=None, **kwargs):
                        print(dialog)
                        return take_turn(dialog, state=state, **kwargs)
                    return _take_turn

            builder.add_middleware(MyLogMiddleware())

        :param callable middleware: A middleware.
        """
        self._middlewares.append(middleware)

    def use_file_resources(self, path):
        """Set a YAML-file as a source of resources.

        :param str|Path path: A path to a file with resources.
        """
        self.use_resources(FileResources(path))

    def use_directory_resources(self, base_dir, botfile=None):
        """Set a directory of YAML-files as s source of resources.

        :param str base_dir: A path (str or Path) to a directory with resources.
        :param str botfile: bot filename, default=bot.yaml.
        """
        self.use_resources(DirectoryResources(base_dir, botfile))

    def use_inline_resources(self, source):
        """Set a YAML-string as a source of resources.

        :param str source: A YAML-string with resources.
        """
        self.use_resources(InlineResources(source))

    def use_package_resources(self, package, botfile=None):
        """Set a directory contained in the Python package as a source of resources.

        :param importlib.resources.Package package: A module object or a module name as a string.
        :param str botfile: Bot file name.
        """
        self.use_resources(PackageResources(package, botfile))

    def use_resources(self, resources):
        """Set a source of resources.

        :param object resources: A source of resources.
        """
        self.resources = resources

    def _create_dialog_manager(self):
        message_schema = self._create_message_schema()
        command_schema = self._create_command_schema()
        dm = DialogManager(
            self._nlu,
            DialogFlow(
                self._before_turn_hooks,
                self._after_turn_hooks,
                context={
                    "schema": command_schema,
                    "jinja_env": self.jinja_env,
                },
            ),
            RpcManager(),
            DialogSchema,
            message_schema,
            command_schema,
        )
        for mw in self._middlewares:
            if hasattr(mw, "process_message"):
                dm.process_message = mw.process_message(dm.process_message)
            if hasattr(mw, "process_rpc"):
                dm.process_rpc = mw.process_rpc(dm.process_rpc)
        dm.load_resources(self.resources)
        return dm

    def build(self):
        """Build a customized bot.

        This is a final call after that the builder is not usable anymore.

        :return MaxBot: A customized bot.
        """
        if self._bot_created:
            raise RuntimeError("Bot already created")
        self._bot_created = True

        self._extension_manager.apply_extensions(self, self.resources)
        channels = self._channel_manager.create_channels(self.resources)
        return MaxBot(
            self._create_dialog_manager(),
            channels,
            self.user_locks,
            self._state_store,
            self.resources,
        )
