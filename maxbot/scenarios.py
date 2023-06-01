"""NLG scenarios and templates."""
from dataclasses import dataclass, field

import jinja2

from .errors import BotError, YamlSnippet
from .jinja_env import create_jinja_env
from .maxml import ValidationError, fields
from .schemas import CommandSchema

# Default jinja environment for :class:`~Expression` and :class:`~Scenario'.
DEFAULT_JINJA_ENV = create_jinja_env()

# Scenario errors we turn into :class:`~BotError`.
JINJA_ERRORS = (
    TypeError,
    ValueError,
    LookupError,
    ArithmeticError,
    AttributeError,
    jinja2.TemplateError,
    jinja2.UndefinedError,
)

FRAME_ANCHOR = "66ef03f1-e601-4497-9891-00bbe4289ab3"


class ExpressionField(fields.Field):
    """:class:`~Expression` field.

    Jinja expressions used to build logical conditions and calculate values in dialog tree and
    slot filling flows. For example,

        dialog:
          - condition: intents.cancel_order and entities.order_number
            response: OK. The order is canceled.

    where logical conditions `intents.cancel_order and entities.order_number` determines when we need
    to cancel the order.

    `Jinja expression syntax <https://jinja.palletsprojects.com/en/3.1.x/templates/#expressions>`_ is
    very similar to how ordinary Python expressions work.

    Data types `str`, `bool`, `int`, `float` are allowed as field values.

    The following keys are expected in the field context:

        * 'jinja_env' - jinja environment used to compile an expression, default :var:`~DEFAULT_JINJA_ENV`.
    """

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, (str, bool, int, float)):
            return Expression(
                value,
                self.context.get("jinja_env", DEFAULT_JINJA_ENV),
            )
        raise ValidationError("Invalid expression. Must be one of: str, bool, number")


class ScenarioField(fields.String):
    """Scenario field.

    Scenario encapsulates an imperative logic applied against dialog turn context and used to get
    a list of commands.

    Implementation: :class:`~Template`. It uses jinja templates to apply custom logic to generated
    commands. Internally the field is represented by the dict that matches the :class:`~TemplateSchema`.

    The following keys are expected in the field context:

        * 'schema' - response commands schema, default :class:`~CommandSchema`,
        * 'jinja_env' - jinja environment used to compile template, default :var:`~DEFAULT_JINJA_ENV`.


    """

    def __init__(self, controls_schema=None, **kwargs):
        """Create new class instance.

        :param Schema controls_schema: Schema for control commands.
        :param bool many: Are we deserializing a list of objects?
        :param dict kwargs: Keyword arguments passed to underlying constructor.
        """
        super().__init__(**kwargs)
        self.controls_schema = controls_schema

    def _deserialize(self, value, attr, data, partial=None, **kwargs):
        schema_class = self.context.get("schema", CommandSchema)
        if self.controls_schema:
            schema_class = _union_commands(schema_class, self.controls_schema)
        if not isinstance(value, str):
            raise BotError("Scenario field should be a string", YamlSnippet.from_data(value))
        return Template(
            value,
            schema_class,
            self.context.get("jinja_env", DEFAULT_JINJA_ENV),
        )


def _union_commands(commands_class, controls_class):
    return type("Union" + controls_class.__name__, (controls_class, commands_class), {})


@dataclass
class Expression:
    """An expression used in dialog tree to check conditions and calculate values."""

    # A source string to compile expression.
    source: str

    # Jinja environment used to compile expression.
    jinja_env: jinja2.Environment = field(default=DEFAULT_JINJA_ENV)

    # Compiled expression.
    expr: callable = field(init=False)

    def __post_init__(self):
        """Compile an expression."""
        if not hasattr(self.jinja_env, "sync_env"):
            self.jinja_env.extend(sync_env=self.jinja_env.overlay(enable_async=False))

        try:
            self.expr = self.jinja_env.sync_env.compile_expression(
                self.source, undefined_to_none=False
            )
        except jinja2.TemplateSyntaxError as exc:
            raise BotError(exc.message, YamlSnippet.from_data(self.source)) from exc

    def __call__(self, ctx, **params):
        """Evaluate an expression using scenario context.

        See :meth:`~TurnContext.create_scenario_context` for a list of evaluation params.

        :param TurnContext ctx: The turn context from which the scenario context is created.
        :param dict params: Additional params for scenario context.
        :return Any: Expression evaluation result.
        """
        try:
            value = self.expr(_create_scenario_context(ctx, params))
            bool(value)  # raise UndefinedError if StrictUndefined
            return value
        except JINJA_ERRORS as exc:
            # jinja always treats expressions as on line
            raise BotError(str(exc), YamlSnippet.from_data(self.source)) from exc

    def __repr__(self):
        """Represent expression as its source string."""
        return repr(self.source)


@dataclass
class Template:
    """Template scenario used to generate a list of commands.

    Template is evaluated in two steps.

    First, the :attr:`content` is rendered into the text document using :attr:`~jinja_env`.
    Rendering params described in :meth:`~TurnContext.create_scenario_context`.

    Second, the document is deserialized into the list of commands based on its :attr:`~syntax`
    and using its :attr:`~Schema`.

        * `raw` syntax - the document is a plain string that is deserialized to a list containing
        one text command, see :meth:`~CommandSchema.short_syntax_list`.
        * `yaml` syntax - the document is a YAML-string wich is deserialized as a list of commands.

    Commands are not interpreted by the scenario in any way. They are simply returned to the caller
    flow.
    """

    # The content, that is compiled into template.
    content: str

    # A schema that is used to deserialize commands from rendered document.
    Schema: type = field(default=CommandSchema)

    # Jinja environment used to compile template.
    jinja_env: jinja2.Environment = field(default=DEFAULT_JINJA_ENV)

    # Compiled template.
    tpl: callable = field(init=False)

    def __post_init__(self):
        """Compile a template."""
        try:
            self.tpl = self.jinja_env.from_string(self.content)
        except jinja2.TemplateSyntaxError as exc:
            raise BotError(
                exc.message, YamlSnippet.from_data(self.content, line=exc.lineno)
            ) from exc

    async def __call__(self, ctx, **params):
        """Render template using scenario context and deserialize commands.

        See :meth:`~TurnContext.create_scenario_context` for a list of rendering params.

        :param TurnContext ctx: The turn context from which the scenario context is created.
        :param dict params: Additional params for scenario context.
        :return list: A list of commands, that matches :class:`~CommandSchema`.
        """
        try:
            document = await self.tpl.render_async(_create_scenario_context(ctx, params))
        except jinja2.TemplateSyntaxError as exc:
            # TODO: using _extract_lineno we have lost the actual location of
            # the error in macros: exc.lineno, exc.filename ...
            raise BotError(
                exc.message, YamlSnippet.from_data(self.content, line=_extract_lineno(exc))
            ) from exc
        except JINJA_ERRORS as exc:
            raise BotError(
                str(exc), YamlSnippet.from_data(self.content, line=_extract_lineno(exc))
            ) from exc

        try:
            return self.Schema(many=True).loads(document)
        except BotError as exc:
            # wrap original error to include YAML snippet
            raise BotError(
                exc.message, YamlSnippet.from_data(self.content), *exc.snippets
            ) from exc


def _extract_lineno(exc):
    """Extract line where template error is occured assuming that traceback was rewritten by jinja.

    See jinja2.debug.rewrite_traceback_stack for more tech details.
    """
    tb = exc.__traceback__
    lineno = None
    while tb:
        if tb.tb_frame.f_code.co_filename == "<template>":
            if tb.tb_frame.f_locals.get("FRAME_ANCHOR") == FRAME_ANCHOR:
                lineno = tb.tb_lineno
        tb = tb.tb_next
    return lineno


def _create_scenario_context(ctx, params):
    result = ctx.create_scenario_context(params)
    result.update(FRAME_ANCHOR=FRAME_ANCHOR)
    return result
