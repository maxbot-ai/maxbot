"""Maxbot Markup."""
from dataclasses import dataclass, field
from typing import Optional

from ..errors import BotError
from . import fields


class Field(fields.Field):
    """Markup field schema."""

    #: Default error messages.
    default_error_messages = {"invalid": "Not a MarkupValue."}

    def __init__(self, **kwargs):
        """Create new class instance."""
        super().__init__(**kwargs)
        value = self.metadata.get("maxml")
        if value not in {None, "element", "content"}:
            raise BotError(f"Unexpected `maxml` value: {value!r}")

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, Value):
            raise self.make_error("invalid")
        return value


START_TAG = "start_tag"
END_TAG = "end_tag"
TEXT = "text"


@dataclass(frozen=True)
class Item:
    """Item of loaded markup value."""

    # Kind of item: START_TAG, END_TAG or TEXT
    kind: str

    # Value of a item
    value: str

    # Optional value of a item
    optional: Optional[dict] = field(default=None)


class PlainTextRenderer:
    """Simple renderer.

    + Whitespace normalization
    + Tag `br` to new line ("\n")
    + Ignore all unknown tags
    """

    KNOWN_START_TAGS = {"br": "\n"}
    KNOWN_END_TAGS = {}

    def __init__(self, items):
        """Create new class instance.

        :param list[Item] items: Loaded items.
        """
        self.items = items

    def __call__(self):
        """Return rendered string."""
        chunks = []
        for item in self.items:
            if item.kind == START_TAG:
                chunks.append(self.KNOWN_START_TAGS.get(item.value, ""))
            elif item.kind == END_TAG:
                chunks.append(self.KNOWN_END_TAGS.get(item.value, ""))
            else:
                assert item.kind == TEXT
                chunks.append(" ".join(item.value.split()))

        # special case: "begin <unsupported />end"
        for i, item in enumerate(self.items):
            if item.kind == TEXT:
                if item.value and item.value[-1].isspace():
                    for j in range(i + 1, len(self.items)):
                        if self.items[j].kind != TEXT and not chunks[j]:
                            continue
                        if self.items[j].kind == TEXT and chunks[j]:
                            chunks[i] = chunks[i] + " "
                        break

        return "".join(chunks)


def default_value_comparator(lhs, rhs):
    """Check: two `Value` objects are equal."""
    if isinstance(lhs, Value) and isinstance(rhs, str):
        return lhs.render() == rhs
    return lhs.items == rhs.items if isinstance(lhs, Value) and isinstance(rhs, Value) else False


class Value:
    """Loaded markup value."""

    COMPARATOR = default_value_comparator

    def __init__(self, items=None):
        """Create new class instance.

        :param list[Item] items: Loaded items.
        """
        self.items = items or []

    def render(self, renderer_class=None):
        """Render loaded value.

        :param type renderer_class: Custom renderer class.
        """
        renderer_class = renderer_class or PlainTextRenderer
        return renderer_class(self.items)()

    def __repr__(self):
        """Create representation string."""
        return f"<maxml.markup.Value{self.render()!r}>"

    def __eq__(self, rhs):
        """Check equal."""
        return self.COMPARATOR(rhs)
