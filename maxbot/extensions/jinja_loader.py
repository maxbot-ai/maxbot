"""Builtin MaxBot extension: load jinja-files relative to the skill base directory."""
import os.path

from jinja2 import BaseLoader, TemplateNotFound


class _JinjaLoader(BaseLoader):
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir

    def get_source(self, environment, template):
        file_name = template
        if self.base_dir and not os.path.isabs(file_name):
            file_name = os.path.join(self.base_dir, file_name)

        if not os.path.isfile(file_name):
            raise TemplateNotFound(template)

        mtime = os.path.getmtime(file_name)
        with open(file_name, encoding="utf-8") as f:
            source = f.read()
        return source, file_name, lambda: mtime == os.path.getmtime(file_name)


def jinja_loader(builder, config):
    """Extension entry point.

    :param BotBuilder builder: MaxBot builder.
    :param dict config: Extension configuration.
    """
    builder.jinja_env.loader = _JinjaLoader(getattr(builder.resources, "base_directory", None))
