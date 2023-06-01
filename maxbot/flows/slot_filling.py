"""Slot Filling Conversation Flow."""
import logging
from dataclasses import dataclass, field
from typing import Optional

from ..context import EntitiesProxy, RecognizedEntity, RecognizedIntent
from ..maxml import Schema, fields, post_load
from ..scenarios import ExpressionField, ScenarioField
from ..schemas import MaxmlSchema, ResourceSchema
from ._base import DigressionResult, FlowResult

logger = logging.getLogger(__name__)


class FoundCommands(MaxmlSchema):
    """Control commands for `found` scenarios."""

    # Move on to the next empty slot after displaying the response (default).
    move_on = fields.Nested(Schema)

    # Clear the current slot value and prompt for the correct value.
    prompt_again = fields.Nested(Schema)

    # Do not prompt for the slot and just wait for the user to respond.
    listen_again = fields.Nested(Schema)

    # Skip the remaining slots and go directly to the node-level response next.
    response = fields.Nested(Schema)


class NotFoundCommands(MaxmlSchema):
    """Control commands for `not_found` scenarios."""

    # Prompt for the correct slot value (default).
    prompt_again = fields.Nested(Schema)

    # Do not prompt for the slot and just wait for the user to respond.
    listen_again = fields.Nested(Schema)

    # Skip the remaining slots and go directly to the node-level response next.
    response = fields.Nested(Schema)


class PromptCommands(MaxmlSchema):
    """Control commands for `prompt` scenarios."""

    # Wait for the user to respond (default).
    listen_again = fields.Nested(Schema)

    # Skip the remaining slots and go directly to the node-level response next.
    response = fields.Nested(Schema)


class HandlerCommands(MaxmlSchema):
    """Control commands for `slot_handlers`."""

    # Move on to the next empty slot after displaying the response (default).
    move_on = fields.Nested(Schema)

    # Skip the remaining slots and go directly to the node-level response next.
    response = fields.Nested(Schema)


@dataclass(frozen=True)
class Slot:
    """Slot is used to gather a piace of information from the user input.

    See :class:`~SlotSchema` for more informaion.
    """

    name: str
    check_for: callable
    condition: Optional[callable] = None
    value: Optional[callable] = None
    prompt: Optional[callable] = None
    found: Optional[callable] = None
    not_found: Optional[callable] = None


class SlotSchema(ResourceSchema):
    """Slot is used to gather a piace of information from the user input."""

    # Provide a name for the slot in which to store the value of interest from the user input.
    name = fields.Str(required=True)

    # Identify an information you want to extract from the user input. The result will be saved as
    # a slot value.
    check_for = ExpressionField(required=True)

    # If provided, the result will be stored as a slot value instead of `check_for`.
    value = ExpressionField()

    # Makes the slot only be enabled under the specified condition.
    condition = ExpressionField()

    # Asks a piece of the information you need from the user.
    # To make a slot optional, add a slot without a prompt.
    prompt = ScenarioField(PromptCommands)

    # Executed after the user provides the expected information. Useful to validate the information provided.
    found = ScenarioField(FoundCommands)

    # Executed only if the information provided by the user is not understood, which means all of the following are true:
    #   * none of the active slots are filled successfully;
    #   * no slot handlers are understood;
    #   * nothing triggered as a digression from slot filling.
    not_found = ScenarioField(NotFoundCommands)

    @post_load(pass_original=True)
    def post_load(self, data, original_data, **kwargs):
        """Create a slot object and add YAML symbols for loaded data.

        :param dict data: Deserialized data.
        :param dict original_data: Original data before deserialization.
        :param dict kwargs: Ignored arguments.
        """
        super().post_load(data, original_data, **kwargs)
        return Slot(**data)


@dataclass(frozen=True)
class Handler:
    """Provide responses to questions users might ask that are tangential to the purpose of the slot filling.

    See :class:`~HandlerSchema` for more information.
    """

    condition: callable
    response: callable


class HandlerSchema(ResourceSchema):
    """Provide responses to questions users might ask that are tangential to the purpose of the slot filling.

    After responding to the off-topic question, the prompt associated with the current empty slot is displayed.
    """

    # Triggers slot handler based on user input provided any time during the slot filling.
    condition = ExpressionField(required=True)

    # Responds to the user when the slot handler is triggered.
    response = ScenarioField(HandlerCommands, required=True)

    @post_load(pass_original=True)
    def post_load(self, data, original_data, **kwargs):
        """Create a slot handler object and add YAML symbols for loaded data.

        :param dict data: Deserialized data.
        :param dict original_data: Original data before deserialization.
        :param dict kwargs: Ignored arguments.
        """
        super().post_load(data, original_data, **kwargs)
        return Handler(**data)


class SlotFilling:
    """Slot Filling Conversation Flow."""

    def __init__(self, slots, handlers):
        """Create new class instance.

        :param list slots: List of slots to fill.
        :param list handlers: List of slots to fill.
        """
        self.slots = slots
        self.handlers = handlers

    async def __call__(self, ctx, state, digression_result=None):
        """Make a turn in a slot filling flow.

        :param TurnContext ctx: Context of the turn.
        :param dict state: State of the flow model.
        :param DigressionResult digression_result: The result with which we return from digression.
        :return FlowResult: The result of the turn of the flow.
        """
        turn = Turn(self.slots, self.handlers, ctx, state, digression_result)
        return await turn()


@dataclass
class Turn:
    """A turn of the slot filling flow."""

    # List of slots.
    slots: list[Slot]

    # List of slot handlers.
    handlers: list[Handler]

    # Context of the turn.
    ctx: object

    # State of the flow.
    state: dict

    # The result with which we return from digression.
    digression_result: DigressionResult

    # Slot that where elicited during the turn.
    found_slots: list = field(default_factory=list)

    # Slots for which we were asked to skip the prompt.
    skip_prompt: list = field(default_factory=list)

    # Whenever we were asked to skip slot filling and give the final response.
    want_response: bool = False

    @property
    def enabled_slots(self):
        """Access only slots for which :attr:`~SlotSchema.condition` is `True`.

        Note that slot conditions are lazily evaluated.
        """
        for slot in self.slots:
            if slot.condition is None or slot.condition(self.ctx):
                yield slot

    def elicit(self, slot):
        """Capture and store slot value from the user input.

        :param Slot slot: A slot to elicit.
        """
        value = slot.check_for(
            self.ctx, slot_in_focus=(self.state.get("slot_in_focus") == slot.name)
        )
        if not value:
            return
        if slot.value:
            value = slot.value(self.ctx)
        if isinstance(value, (EntitiesProxy, RecognizedEntity)):
            value = value.value
        if isinstance(value, RecognizedIntent):
            value = True
        logger.debug("elicit slot %r value %r", slot.name, value)
        previous_value = self.ctx.state.slots.get(slot.name)
        self.ctx.state.slots[slot.name] = value
        self.found_slots.append((slot, {"previous_value": previous_value, "current_value": value}))

    def clear_slot(self, slot):
        """Clear slot value.

        :param Slot slot: A slot to clear.
        """
        self.ctx.state.slots.pop(slot.name, None)

    def listen_again(self, slot):
        """Do not prompt for the given slot during the turn.

        :param Slot slot: A slot to not to prompt.
        """
        self.skip_prompt.append(slot)

    async def found(self, slot, params):
        """Execute the `found` scenario and its control commands.

        :param Slot slot: A slot for which execute the scenario.
        :param dict params: Extra params to pass to the scenario.
        """
        payload = self.ctx.journal_event("found", {"slot": slot.name})
        for command in await slot.found(self.ctx, **params):
            if "response" in command:
                self.want_response = True
                payload.update(control_command="response")
                break
            if "prompt_again" in command:
                payload.update(control_command="prompt_again")
                self.clear_slot(slot)
                break
            if "listen_again" in command:
                payload.update(control_command="listen_again")
                self.clear_slot(slot)
                self.listen_again(slot)
                break
            if "move_on" in command:
                payload.update(control_command="move_on")
                break
            self.ctx.commands.append(command)

    async def not_found(self, slot):
        """Execute the `not_found` scenario and its control commands.

        :param Slot slot: A slot for which execute the scenario.
        """
        payload = self.ctx.journal_event("not_found", {"slot": slot.name})
        for command in await slot.not_found(self.ctx):
            if "response" in command:
                self.want_response = True
                payload.update(control_command="response")
                break
            if "prompt_again" in command:
                payload.update(control_command="prompt_again")
                break
            if "listen_again" in command:
                self.listen_again(slot)
                payload.update(control_command="listen_again")
                break
            self.ctx.commands.append(command)
        else:
            self.listen_again(slot)

    async def prompt(self, slot):
        """Execute the `prompt` scenario and its control commands.

        :param Slot slot: A slot for which execute the scenario.
        """
        payload = self.ctx.journal_event("prompt", {"slot": slot.name})
        for command in await slot.prompt(self.ctx):
            if "response" in command:
                self.want_response = True
                payload.update(control_command="response")
                break
            if "listen_again" in command:
                self.listen_again(slot)
                payload.update(control_command="listen_again")
                break
            self.ctx.commands.append(command)
        else:
            self.listen_again(slot)

    async def handler(self, handler):
        """Execute the `handler.response` scenario and its control commands.

        :param Handler handler: A handler for which execute the scenario.
        """
        payload = self.ctx.journal_event("slot_handler", {"condition": handler.condition.source})
        for command in await handler.response(self.ctx):
            if "response" in command:
                self.want_response = True
                payload.update(control_command="response")
                break
            if "move_on" in command:
                payload.update(control_command="move_on")
                break
            self.ctx.commands.append(command)

    async def __call__(self):
        """Make a turn in a slot filling flow.

        :return FlowResult: The result of the turn of the flow.
        """
        # elicit
        for slot in self.enabled_slots:
            self.elicit(slot)
        # found
        for slot, params in self.found_slots:
            self.ctx.journal_event(
                "slot_filling", {"slot": slot.name, "value": params["current_value"]}
            )
            if slot.found:
                await self.found(slot, params)
        if self.state.get("slot_in_focus") and not self.found_slots:
            # perform the following operations in order until the first one succeeds
            # * slot handlers
            # * digression
            # * not found response

            if self.digression_result is None:
                # slot handlers
                for handler in self.handlers:
                    if handler.condition(self.ctx):
                        await self.handler(handler)
                        break
                else:
                    return FlowResult.DIGRESS

            if self.digression_result == DigressionResult.NOT_FOUND:
                # not found
                catalog = {s.name: s for s in self.enabled_slots}
                slot = catalog.get(self.state.get("slot_in_focus"))
                if slot and slot.not_found:
                    await self.not_found(slot)

        if not self.want_response:
            # prompt
            for slot in self.enabled_slots:
                if slot.prompt and self.ctx.state.slots.get(slot.name) is None:
                    self.state["slot_in_focus"] = slot.name
                    if slot not in self.skip_prompt:
                        await self.prompt(slot)
                    break
            else:
                self.state["slot_in_focus"] = None
        # result
        if self.want_response:
            self.state["slot_in_focus"] = None
        if self.state.get("slot_in_focus") is None:
            return FlowResult.DONE
        return FlowResult.LISTEN
