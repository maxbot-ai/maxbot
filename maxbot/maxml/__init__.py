"""MAXbot Markup Language."""

from marshmallow import (  # noqa: F401
    Schema,
    ValidationError,
    fields,
    post_load,
    pre_load,
    validate,
)
