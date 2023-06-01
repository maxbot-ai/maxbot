"""Bot error handling and debugging."""
import pathlib
import textwrap

import yaml


class BotError(RuntimeError):
    """An error caused by any problem in bot resources or during scenarios execution."""

    def __init__(self, message, *snippets):
        """Create new class instance.

        :param str message: An error message.
        :param nippet snippets: A snippent (zero or more) of the resource file or string that caused an error.
        """
        super().__init__(message)
        self.snippets = [s for s in snippets if s]

    @property
    def message(self):
        """Get the error message including information about the cause error."""
        message = self.args[0]
        cause = self.__cause__ or self.__context__
        if cause is not None and not isinstance(cause, self.__class__):
            klass = cause.__class__
            return f"caused by {klass.__module__}.{klass.__qualname__}: {message}"
        return message

    def __str__(self):
        """Detailed description of an error including error cause and a snippet."""
        lines = [
            self.message,
        ]
        lines += [textwrap.indent(s.format(), "  ") for s in self.snippets]
        return "\n".join(lines)


class YamlSymbols:
    """Maps resource data fragments to the YAML nodes from which they were obtained.

    Note, that the data is identified by the result of Python's `id` function. So, sclars like
    `int`, `float`, `bool` are not mapped. It's not critical because scalars almost never
    cause errors.

    Tracks YAML-documents for the YAML nodes to cleanup symbols for dynamically generated documents.
    This avoids memory leaks. Documents are identified by the file name or content string (for
    dynamic docs).
    """

    _stores = {}

    @classmethod
    def cleanup(cls, document):
        """Remove YAML-nodes for the passed document.

        :param string document: The file name or content string of the YAML-document.
        """
        cls._stores.pop(document, None)

    @classmethod
    def add(cls, data, node):
        """Map the resource data to its YAML-node.

        :param Any data: The resource data.
        :param yaml.Node node: The YAML-node.
        """
        if isinstance(data, (int, float, bool)):
            return
        if node.start_mark.buffer is not None:
            key = node.start_mark.buffer.rstrip("\0")
        else:
            key = node.start_mark.name
        store = cls._stores.setdefault(key, {})
        store[id(data)] = node

    @classmethod
    def lookup(cls, data):
        """Get for YAML-node by its resource data.

        :param Any data: The resource data.
        :return yaml.Node: The YAML-node from wich the data was obtained.
        """
        id_ = id(data)
        for store in cls._stores.values():
            if id_ in store:
                return store[id_]
        return None

    @classmethod
    def reference(cls, derived, original):
        """Map the derived resource data to the YAML-node of the original resource.

        If the original resource is not mapped yet then nothing happens.

        :param Any derived: The derived resource data.
        :param Any original: The original resource data.
        """
        node = cls.lookup(original)
        if node:
            cls.add(derived, node)


class Snippet:
    """Snippet base class."""

    def __init__(self, name, lines, line, column, exact_column, frame=None):
        """Create new class instance.

        :param str name: Document name.
        :param list[str] lines: Lines with the source code.
        :param int line: A line number to point to.
        :param int column: A column number to point to.
        :param bool exact_column: Are we pointing exactly to the specified column or
                                  to the whole line?
        :param tuple(int, int) frame: Range of important lines
        """
        self.name = name
        self._lines = lines
        self.line = line
        self.column = column
        self.exact_column = exact_column
        self.frame = frame

    @property
    def code(self):
        """Get whole source code."""
        return "\n".join(self._lines)

    def format_location(self):
        """Build a string description of the pointer."""
        if self.exact_column:
            return f'in "{self.name}", line {self.line + 1}, column {self.column + 1}'
        return f'in "{self.name}", line {self.line + 1}'

    def format_code(self, pointer="^^^", max_lines=1, max_chars=80):
        """Build a code snippet with a pointer.

        :param str pointer: String representation of the pointer.
        :param int max_lines: Maximum number of lines above/below selected line.
        :param int max_chars: Maximum number of chars in the lines above/below selected line.
        :return str:
        """
        if self.frame:
            frame_start_line, frame_end_line = self.frame
            if frame_end_line - frame_start_line > 6:
                start_line = max(self.line - max_lines, frame_start_line)
                delta = max(max_lines - (start_line - frame_start_line), 0)
                end_line = min(self.line + max_lines + delta + 1, len(self._lines))
            else:
                max_chars = max(max_chars, 80 * 3)
                start_line, end_line = frame_start_line, frame_end_line
        else:
            start_line = max(self.line - max_lines, 0)
            end_line = min(self.line + max_lines + 1, len(self._lines))
        if start_line == end_line:
            end_line += 1

        head = "\n".join(self._lines[start_line : self.line])  # noqa: E203
        if len(head) > max_chars:
            head = "..." + head[-max_chars:]  # noqa: E203

        tail = "\n".join(self._lines[self.line + 1 : end_line])  # noqa: E203
        if len(tail) > max_chars:
            tail = tail[:max_chars] + "..."

        pointer = " " * self.column + pointer
        code = "\n".join(([head] if head else []) + [self._lines[self.line], pointer, tail])
        code = textwrap.dedent(code)
        return code

    def format(self):
        """Build a string description and a code snippet with a pointer."""
        location = self.format_location()
        code = textwrap.indent(self.format_code(), "  ")
        return f"{location}:\n{code}"

    def __str__(self):
        """Get string representation of the object."""
        return self.format()


class YamlSnippet(Snippet):
    """A snippet of YAML-document with pointer to specific line and column."""

    @classmethod
    def from_data(cls, data, *, key=None, line=None):
        """Build a snippet for a resource data fragment.

        If the :param:`~key` parameter passed we extract the nested YAML-node with this key.

        It is possible to take into account a specific :param:`~line` inside YAML-node that is multiline scalar.
        This is useful when poining to a line in multiline string such as jinja templates.

        :param str|int|None key: The key in the resource data.
        :param int|None line: The line in multiline scalar to move the pointer to.
        :return str|None: Created snippet or `None` if resource data if not found in the :class:`~YamlSymbols`.
        """
        node = YamlSymbols.lookup(data)
        if node is not None:
            if key is not None:
                node = cls._node_get(node, key)
            if line is None:
                return cls.at_mark(node.start_mark)
            return cls.with_offset(node, line)
        return None

    @staticmethod
    def _node_get(node, key):
        if isinstance(node, yaml.MappingNode):
            mapping = dict((k.value, v) for k, v in node.value)
            return mapping.get(key, node)
        if isinstance(node, yaml.SequenceNode):
            return node.value[key]
        return node

    @classmethod
    def at_mark(cls, mark):
        """Build the snippet with a pointer exactly on the mark.

        :param yaml.Mark mark: The mark to build snippet around.
        :return str:
        """
        return cls(mark.name, cls._read_lines(mark), mark.line, mark.column, exact_column=True)

    @classmethod
    def with_offset(cls, node, line):
        """Build the snippet around the node with a line pointer at the speficied offset.

        This method is useful when poining to a line in multiline string such as jinja templates.
        A column pointer is always at the beginning of the line.

        :param yaml.Node node: The node to build snippet around.
        :param int line: The offeset of the line pointer.
        :return str:
        """
        mark = node.start_mark
        lines = cls._read_lines(mark)
        if line < 1:
            raise ValueError("The line number must be positive.")
        line += mark.line  # get the line in the whole document
        if node.style in {None, "'", '"'}:  # plain, single-quoted, double-quoted
            line -= 1  # flow-strings share their first line with parent key
            column = mark.column
            frame = None
        else:  # literal ('|'), folded ('>')
            s = lines[line]
            column = len(s) - len(s.lstrip(" "))
            frame = frame = (mark.line, node.end_mark.line + 1)
        return cls(mark.name, lines, line, column, exact_column=False, frame=frame)

    @staticmethod
    def _read_lines(mark):
        if mark.buffer is not None:
            code = mark.buffer.rstrip("\0")
        else:
            code = pathlib.Path(mark.name).read_text(encoding="utf8")
        # do not use splitlines, because terminal line break should result in an extra line
        return code.split("\n")


class XmlSnippet(Snippet):
    """A snippet of XML document with pointer to specific line and column."""

    def __init__(self, lines, lineno, column):
        """Create new class instance.

        :param list[str] lines: Lines with the source code.
        :param int lineno: A line number to point to.
        :param int column: Number of comunt.
        """
        super().__init__("<Xml document>", lines, lineno, column, exact_column=True)

    def format(self):
        """Build a string description and a code snippet with a pointer."""
        location = self.format_location()
        code = textwrap.indent(self.format_code(max_lines=3), "  ")
        return f"{location}:\n{code}"
