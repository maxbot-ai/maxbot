"""Dump to YAML."""

from yaml import SafeDumper, dump


def _create_dumper(aliases_allowed):
    class _Dumper(SafeDumper):
        """Human friendly dumps."""

        @staticmethod
        def represent_str_literal(dumper, data):
            """Represent multiline strings using literal style."""
            data = str(data)
            if "\n" in data:
                return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
            return dumper.represent_str(data)

        @staticmethod
        def represent_undefined_to_repr(dumper, data):
            """Represetn all unknown objects as repr-string."""
            return dumper.represent_str(repr(data))

        def ignore_aliases(self, data):
            """Check for aliase allowed."""
            return True if not aliases_allowed else super().ignore_aliases(data)

    _Dumper.add_representer(str, _Dumper.represent_str_literal)
    _Dumper.add_representer(None, _Dumper.represent_undefined_to_repr)
    return _Dumper


Dumper = _create_dumper(aliases_allowed=True)
DumperNoAliases = _create_dumper(aliases_allowed=False)


def yaml_frendly_dumps(data, aliases_allowed=True):
    """Dump object to YAML string (human-friendly).

    Dump all unknown objects as repr-string.

    :param any data: Object to dump.
    :param bool aliases_allowed: Enable/disable anchors and aliases usage.
    :return str: Dumped YAML string.
    """
    return dump(
        data,
        Dumper=Dumper if aliases_allowed else DumperNoAliases,
        sort_keys=False,
        allow_unicode=True,
    )
