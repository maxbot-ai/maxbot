"""MaxBot dialog."""
import logging

from .context import RpcContext, RpcRequest, TurnContext
from .flows.dialog_flow import DialogFlow
from .resources import InlineResources
from .rpc import RpcManager
from .schemas import CommandSchema, DialogSchema, MessageSchema

logger = logging.getLogger(__name__)


class DialogManager:
    """Orchestrates the flow of the conversation."""

    def __init__(
        self,
        nlu=None,
        dialog_flow=None,
        rpc=None,
        dialog_schema=None,
        message_schema=None,
        command_schema=None,
    ):
        """Create new class instance.

        :param Nlu nlu: NLU component.
        :param jinja2.Environment jinja_env: Jinja environment.
        :param RpcManager rpc: RPC manager.
        :param type dialog_schema: A schema class for dialog informatin.
        :param type message_schema: A schema class for user message.
        :param type command_schema: A schema class for response commands.
        """
        self.DialogSchema = dialog_schema or DialogSchema
        self.MessageSchema = message_schema or MessageSchema
        self.CommandSchema = command_schema or CommandSchema
        self._nlu = nlu  # the default value is initialized lazily
        self.dialog_flow = dialog_flow or DialogFlow(context={"schema": self.CommandSchema})
        self.rpc = rpc or RpcManager()
        self._journal_logger = logging.getLogger("maxbot.journal")
        self._journal = self.default_journal
        self._dialog_is_ready = False

    @property
    def nlu(self):
        """NLU component used to recognize intent and entities from user's utterance."""
        if self._nlu is None:
            # lazy import to speed up load time
            from .nlu import Nlu

            self._nlu = Nlu()
        return self._nlu

    def load_resources(self, resources):
        """Load dialog resources.

        :param Resources resources: Bot resources.
        """
        self._dialog_is_ready = False
        self.rpc.load_resources(resources)
        self.dialog_flow.load_resources(resources)
        if hasattr(self.nlu, "load_resources"):
            self.nlu.load_resources(resources)
        self._dialog_is_ready = True

    def load_inline_resources(self, source):
        """Load dialog resources from YAML-string.

        :param str source: A YAML-string with resources.
        """
        self.load_resources(InlineResources(source))

    async def process_message(self, message, dialog, state):
        """Process user message.

        :param dict message: A message received from the user.
        :param dict dialog: Information about the dialog from which the message was received.
        :param StateVariables state: A container for state variables.
        :raise BotError: Something went wrong with the bot.
        :return List[dict]: A list of commands to respond to the user.
        """
        if not self._dialog_is_ready:
            logger.warning(
                "The dialog is not ready, messages is skipped until you load the resources."
            )
            return []
        logger.debug("process message %s, %s", message, dialog)
        message = self.MessageSchema().load(message)
        dialog = self.DialogSchema().load(dialog)
        intents, entities = await self.nlu(message)
        ctx = TurnContext(dialog, state, message=message, intents=intents, entities=entities)
        await self.dialog_flow.turn(ctx)
        self._journal(ctx)
        return ctx.commands

    async def process_rpc(self, request, dialog, state):
        """Process RPC request.

        :param dict request: A request received from the RPC client.
        :param dict dialog: Information about the dialog from which the message was received.
        :param StateVariables state: A container for state variables (optional).
        :raise BotError: Something went wrong with the bot.
        :return List[dict]: A list of commands to send to the user.
        """
        if not self._dialog_is_ready:
            logger.warning(
                "The dialog is not ready, rpc requests is skipped until you load the resources."
            )
            return []
        logger.debug("process rpc %s, %s", request, dialog)
        dialog = self.DialogSchema().load(dialog)
        request = self.rpc.parse_request(request)
        ctx = TurnContext(dialog, state, rpc=RpcContext(RpcRequest(**request)))
        await self.dialog_flow.turn(ctx)
        self._journal(ctx)
        return ctx.commands

    def default_journal(self, ctx):
        """Get the default implementaton of journal.

        :param TurnContext ctx: Turn context.
        """
        for record in ctx.logs:
            level = getattr(logging, record.level)
            if self._journal_logger.isEnabledFor(level):
                self._journal_logger.log(level, record.message)
        if ctx.error:
            raise ctx.error

    def journal(self, fn):
        """Register the journal callback.

        :param callable fn: The journal callback.
        """
        self._journal = fn
        return fn
