"""MaxBot resources."""
import importlib
import importlib.resources
import logging
from pathlib import Path

from .errors import BotError
from .maxml import fields
from .schemas import ResourceSchema

logger = logging.getLogger(__name__)


class BotSchema(ResourceSchema):
    """A schema for resources used to create a bot.

    Fields has a raw type because actual nested schemas are
    generated/configured at run time with the :class:`~DictResources`
    and similar classes.
    """

    # Extensions used to customize a bot.
    # See :class:`~ExtensionsSchema`.
    extensions = fields.Raw()

    # Channels used to communicate with the user.
    # See :class:`~ChannelsSchema`.
    channels = fields.Raw()

    # User intents.
    # See :class:`~IntentSchema`.
    intents = fields.Raw()

    # User entities.
    # See :class:`~EntitySchema`.
    entities = fields.Raw()

    # Dialog tree containing conversational logic.
    # See :class:`~DialogNodeSchema`.
    dialog = fields.Raw()

    rpc = fields.Raw()


class Resources:
    """Resources base class."""

    @classmethod
    def empty(cls):
        """Create an object without resources."""
        return cls({})

    def __init__(self, data):
        """Create new class instance.

        :param dict data: A dictionary with resources.
        """
        self._data = data

    def load_extensions(self, schema):
        """Load extensions used to customize a bot.

        :param ExtensionsSchema schema: The schema used to deserialize the data.
        """
        return schema.load(self._data.get("extensions", {}))

    def load_channels(self, schema):
        """Load channels used to communicate with the user.

        :param ChannelsSchema schema: The schema used to deserialize the data.
        """
        return schema.load(self._data.get("channels", {}))

    def load_intents(self, schema):
        """Load user intents.

        :param IntentSchema schema: The schema used to deserialize the data.
        """
        return schema.load(self._data.get("intents", []))

    def load_entities(self, schema):
        """Load user entities.

        :param EntitySchema schema: The schema used to deserialize the data.
        """
        return schema.load(self._data.get("entities", []))

    def load_dialog(self, schema):
        """Load dialog tree containing conversational logic.

        :param DialogNodeSchema schema: The schema used to deserialize the data.
        """
        return schema.load(self._data.get("dialog", []))

    def load_dialog_subtrees(self, schema):
        """Load dialog's subtrees: parts of the overall dialogue tree.

        :param SubtreeSchema schema: The schema used to deserialize the data.
        """
        return []

    def load_rpc(self, schema):
        """Load dialog endpoints.

        :param MethodSchema schema: The schema used to deserialize the data.
        """
        return schema.load(self._data.get("rpc", []))


class DictResources(Resources):
    """Load resources from a Python dict."""

    def __init__(self, data):
        """Create new class instance.

        :param dict data: A dictionary with resources.
        """
        super().__init__(BotSchema().load(data))


class InlineResources(Resources):
    """Load resources from a YAML-string."""

    def __init__(self, source):
        """Create new class instance.

        :param str source: A YAML-string with resources.
        """
        super().__init__(BotSchema().loads(source))


class FileResources(Resources):
    """Load resources from a YAML-file."""

    def __init__(self, path):
        """Create new class instance.

        :param str|Path path: A path to a file with resources.
        """
        self.base_directory = path.parent
        self._botfile = path
        self._watchlist = []
        super().__init__(self._load_botfile())

    def _load_botfile(self):
        self._watch(self._botfile, "bot")
        return BotSchema().load_file(self._botfile)

    def _watch(self, path, label):
        """Register a file to watch.

        :param str path: A path to a file.
        """
        try:
            mtime = path.stat().st_mtime
        except OSError as exc:
            raise BotError(f"Could not acces file {path!r}: {exc}") from exc

        logger.debug(f"load {label} from {path}")
        self._watchlist.append((path, label, mtime))
        return path

    def poll(self, error_recovery=False):
        """Poll for change in resources.

        :param bool error_recovery: Return changes even if the actual data hasn't changed.
        :return set: Changed resource types.
        """
        for path, label, old_mtime in self._watchlist:
            try:
                new_mtime = path.stat().st_mtime
            except OSError as exc:
                logger.debug(f"file {path} access problem: {exc}")
            else:
                if new_mtime <= old_mtime:
                    continue
                logger.debug(
                    f"file {path} changed, modification time: {old_mtime} -> {new_mtime}."
                )
            self._watchlist = []
            data = self._load_botfile()
            changes = self._botfile_changes(self._data, data)
            if label != "bot" or error_recovery:
                changes.add(label)
            self._data = data
            logger.debug("got resource changes %s", changes)
            return changes
        return set()

    def _botfile_changes(self, old_data, new_data):
        changes = set()
        changes.update(lbl for lbl in new_data if new_data[lbl] != old_data.get(lbl))
        changes.update(set(old_data) - set(new_data))
        return changes


class DirectoryResources(FileResources):
    """Load resources from a directory of YAML-files.

    Assuming the following directory structure:

        mybot/
            intents/
                core-intents.yaml
                faq-intents.yaml
                ...
            entities/
                core-entities.yaml
                products-entities.yaml
                ...
            bot.yaml
            dialog.yaml
    """

    def __init__(self, base_directory, botfile=None):
        """Create new class instance.

        :param str|Path base_directory: A path to a directory with resources.
        :param str botfile: bot filename, default=bot.yaml.
        """
        botfile = botfile or "bot.yaml"
        super().__init__(Path(base_directory) / botfile)

    def load_intents(self, schema):
        """Load user intents.

        Intents are searched for and loaded from the following files.

            * 'intents' section in the bot.yaml
            * intents.yaml
            * intents/*.yaml

        :param IntentSchema schema: The schema used to deserialize the data.
        """
        intents = super().load_intents(schema)
        path = self.base_directory / "intents.yaml"
        if path.exists():
            self._watch(path, "intents")
            intents.extend(schema.load_file(path))
        dir_path = self.base_directory / "intents"
        for path in dir_path.glob("*.yaml"):
            self._watch(path, "intents")
            intents.extend(schema.load_file(path))
        return intents

    def load_entities(self, schema):
        """Load user entities.

        Entities are searched for and loaded from the following files.

            * 'entities' section in the bot.yaml
            * entities.yaml
            * entities/*.yaml

        :param EntitySchema schema: The schema used to deserialize the data.
        """
        entities = super().load_entities(schema)
        path = self.base_directory / "entities.yaml"
        if path.exists():
            self._watch(path, "entities")
            entities.extend(schema.load_file(path))
        dir_path = self.base_directory / "entities"
        for path in dir_path.glob("*.yaml"):
            self._watch(path, "entities")
            entities.extend(schema.load_file(path))
        return entities

    def load_dialog(self, schema):
        """Load dialog tree containing conversational logic.

        Dialog tree is searched for and loaded from one and only one the following files.

            * 'dialog' section in the bot.yaml
            * dialog.yaml

        We do not split dialog tree into multiple file because we are planing to use skills
        for that purpose.

        :param DialogNodeSchema schema: The schema used to deserialize the data.
        :raise BotError: The dialog tree is splitted among several files.
        """
        dialog = super().load_dialog(schema)
        path = self.base_directory / "dialog.yaml"
        if path.exists():
            if dialog:
                raise BotError(
                    "It is not allowed to split dialog tree between bot.yaml and dialog.yaml."
                )
            self._watch(path, "dialog")
            return schema.load_file(path)
        return dialog

    def load_dialog_subtrees(self, schema):
        """Load dialog's subtrees: parts of the overall dialogue tree.

        Load `dialog/**/*.yaml` files. Each subtree is located in a separate file.

        :param SubtreeSchema schema: The schema used to deserialize the data.
        :return list: Subtree specifications.
        """
        dialog_dir = self.base_directory / "dialog"
        rv = []
        if dialog_dir.is_dir():
            for path in dialog_dir.glob("**/*.yaml"):
                self._watch(path, "dialog")
                rv.append(schema.load_file(path))
        return rv

    def load_rpc(self, schema):
        """Load dialog endpoints.

        :param MethodSchema schema: The schema used to deserialize the data.
        :raise BotError: The rpc is splitted among several files.
        """
        rv = super().load_rpc(schema)
        path = self.base_directory / "rpc.yaml"
        if path.exists():
            if rv:
                raise BotError("It is not allowed to split RPC between bot.yaml and rpc.yaml.")
            self._watch(path, "rpc")
            rv = schema.load_file(path)
        return rv


class PackageResources(DirectoryResources):
    """Load resources from a directory contained in the Python package resources."""

    def __init__(self, package, botfile=None):
        """Create new class instance.

        :param importlib.resources.Package package: A module object or a module name as a string.
        :param str botfile: bot filename, default=bot.yaml.
        """
        if isinstance(package, str):
            package = importlib.import_module(package)
        package_name = package.__spec__.name
        if package.__spec__.submodule_search_locations is None:
            package_name = ".".join(package_name.split(".")[:-1])
        super().__init__(importlib.resources.files(package_name), botfile)
