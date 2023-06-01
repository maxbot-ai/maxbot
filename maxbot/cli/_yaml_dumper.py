"""Dump to YAML."""

from yaml import SafeDumper, dump


class YamlFrendlyDumper(SafeDumper):
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


YamlFrendlyDumper.add_representer(str, YamlFrendlyDumper.represent_str_literal)
YamlFrendlyDumper.add_representer(None, YamlFrendlyDumper.represent_undefined_to_repr)


def yaml_frendly_dumps(data):
    """Dump object to YAML string (human-friendly).

    Dump all unknown objects as repr-string.

    :param any data: Object to dump.
    """
    return dump(data, Dumper=YamlFrendlyDumper, sort_keys=False)
