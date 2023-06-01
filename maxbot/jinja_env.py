"""Jinja environment for NLG templates."""
import logging

import jinja2
from jinja2 import nodes
from jinja2.exceptions import TemplateRuntimeError, UndefinedError
from jinja2.ext import Extension
from jinja2.utils import Namespace, missing
from markupsafe import Markup

logger = logging.getLogger(__name__)


def create_jinja_env(options=None):
    """Create Jinja environment with the passes options.

    The `autoescape` option defaults to `True`.

    The function and filter `mandatory` is added to the environment.

    Using :class:`EnclosedUndefined` avoids throwing an :class:`~jinja2.UndefinedError`
    to expresions like `{% if entities.menu.standard %}` in cases where `entities.menu` is
    not recognized and returns `undefined`.
    This undefined type cannot be formatted into a string or put into a user variable/slot using
    the Jinja-tag `user` or `slot` (an exception will be thrown).

    :param dict|None options: An options for the Jinja environment.
    :return jinja2.Environment:
    """
    options = dict(options) if options else {}
    # nosec note: autoescape is not actual when rendering yaml
    options.setdefault("extensions", []).extend(
        [
            "jinja2.ext.loopcontrols",
            "jinja2.ext.do",
            StateDeleteExtension,
            LoggingExtension,
        ]
    )
    options.setdefault("undefined", EnclosedUndefined)
    options.setdefault("trim_blocks", True)
    options.setdefault("lstrip_blocks", True)
    options.setdefault("autoescape", True)
    env = jinja2.Environment(enable_async=True, **options)  # nosec: B701
    env.filters.update(mandatory=mandatory)
    env.filters.update(nl2br=nl2br)
    env.globals.update(mandatory=mandatory)
    return env


class StateNamespace(Namespace):
    """Wraps a dictionary of state variables to allow modifications via jinja assignments.

    Inheritance is required because jinja only allows attribute assignments for its :class:`jinja2.utils.Namespace` class.

    Examples:

        {% set user.name = 'John' %}
        {% set slots.couner = 0 %}

    Assigning undefined and none is not allowed.
    """

    def __init__(self, variables):
        """Create new class instance.

        The original constructor copies the passed dictionary, but we keep a reference to get changes back.
        """
        super().__init__()
        self._Namespace__attrs = variables

    def __setitem__(self, name, value):
        """Set variable value.

        Does not allow undefined values.

        :param str name: Variable name.
        :param Any value: Variable value.
        """
        # do not allow undefined values
        value = mandatory(value)
        if value is None:
            raise ValueError("could not assign none to state variable.")
        super().__setitem__(name, value)

    def __delitem__(self, name):
        """Delete variable.

        :param str name: Variable name.
        """
        del self._Namespace__attrs[name]

    def __repr__(self) -> str:
        """View variables."""
        return repr(self._Namespace__attrs)


class StateDeleteExtension(Extension):
    """Jinja extension for custom tag `delete` to delete state variables.

    Examples:

        {% delete user.name %}
        {% delete slots.counter %}
    """

    tags = {"delete"}

    def parse(self, parser):
        """Transform our custom statement into delete call.

        This method is called by Jinja environment.

        :param jinja.parser.Parser parser: Jinja parser.
        :return jinja.nodes.Node: Jinja node.
        """
        lineno = next(parser.stream).lineno  # tag "delete"

        target = parser.stream.expect("name")
        parser.stream.expect("dot")
        attr = parser.stream.expect("name")

        node = nodes.ExprStmt(lineno=lineno)
        node.node = self.call_method(
            "_delete_variable",
            [nodes.ContextReference(), nodes.Const(target.value), nodes.Const(attr.value)],
            lineno=lineno,
        )
        return node

    def _delete_variable(self, context, target, attr):
        obj = context.resolve_or_missing(target)
        if obj is missing:
            raise UndefinedError(f"'{target}' is undefined")
        if not isinstance(obj, StateNamespace):
            raise TemplateRuntimeError(
                f"can only delete user and slots variables, given {type(obj).__name__!r}"
            )
        if hasattr(obj, attr):
            del obj[attr]


class LoggingExtension(Extension):
    """Jinja extension for custom tags `debug` and `warning` used to logging."""

    tags = {"debug", "warning"}

    def parse(self, parser):
        """Transform our custom statements into logging hooks calls.

        This method is called by Jinja environment.

        :param jinja.parser.Parser parser: Jinja parser.
        :return jinja.nodes.Node: Jinja node.
        """
        level = parser.stream.current.value
        lineno = next(parser.stream).lineno
        objects = parser.parse_tuple()
        node = nodes.ExprStmt(lineno=lineno)
        node.node = self.call_method(
            "_call_logger",
            [nodes.ContextReference(), nodes.Const(level.upper()), objects],
            lineno=lineno,
        )
        return node

    def _call_logger(self, context, level, objects):
        turn_context = context.get("_turn_context")
        if turn_context:
            turn_context.log(level, objects)
        else:
            logger.log(getattr(logging, level, "DEBUG"), repr(objects))
        return objects


class EnclosedUndefined(jinja2.Undefined):
    """Child class from :class:`~jinja2.Undefined`.

    Example of cast to bool:
        >>> jinja2.Environment(undefined=EnclosedUndefined).from_string("{% if xxx %}defined{% else %}undefined{% endif %}").render()
        'undefined'

    Example of cast to string:
        >>> jinja2.Environment(undefined=EnclosedUndefined).from_string("{{ xxx }}").render()
          File "<template>", line 1, in top-level template code
        jinja2.exceptions.UndefinedError: 'xxx' is undefined
    """

    __str__ = jinja2.Undefined._fail_with_undefined_error  # pylint: disable=W0212


def mandatory(o):
    """Throws an :class:`~UndefinedError` exception if the argument is undefined otherwise returns it.

    :raise UndefinedError: The argument is undefined.
    :param any o: Any object.
    :return any: Input argument.
    """
    if isinstance(o, jinja2.Undefined):
        o._fail_with_undefined_error()  # pylint: disable=protected-access
    return o


def nl2br(text):
    """Convert newlines to <br /> element."""
    return Markup("<br />".join(text.splitlines()))
