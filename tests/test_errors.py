from textwrap import indent

import pytest
import yaml

from maxbot.errors import BotError, YamlSnippet, YamlSymbols
from maxbot.maxml import fields
from maxbot.schemas import ResourceSchema


def test_bot_error_simple():
    e = BotError("error message")
    assert str(e) == "error message"


def test_bot_error_cause():
    with pytest.raises(BotError) as excinfo:
        raise BotError("error message") from RuntimeError()
    assert str(excinfo.value) == "caused by builtins.RuntimeError: error message"


def make_node(name="xxx", buffer_="xxx\x00"):
    m = yaml.Mark(name, 0, 0, 0, buffer_, None)
    return yaml.ScalarNode("XXX", value="xxx", style=None, start_mark=m, end_mark=m)


def test_yaml_symbols_add_lookup():
    n = make_node()
    YamlSymbols.add("source", n)
    assert YamlSymbols.lookup("source") == n


def test_yaml_symbols_lookup_mismatch():
    n = make_node()
    YamlSymbols.add("source", n)
    # force the same string but with different allocation in memory
    assert YamlSymbols.lookup("sour" + "ce") is None


def test_yaml_symbols_skip_value():
    # skip values that does not have unique id
    n = make_node()
    YamlSymbols.add(True, n)
    assert YamlSymbols.lookup(True) is None


def test_yaml_symbols_cleanup_by_buffer():
    # skip values that does not have unique id
    n = make_node(buffer_="yyy\x00")
    YamlSymbols.add("source", n)
    assert YamlSymbols.lookup("source") == n
    YamlSymbols.cleanup("yyy")
    assert YamlSymbols.lookup("source") is None


def test_yaml_symbols_cleanup_by_name():
    # skip values that does not have unique id
    n = make_node(name="zzz", buffer_=None)
    YamlSymbols.add("source", n)
    assert YamlSymbols.lookup("source") == n
    YamlSymbols.cleanup("zzz")
    assert YamlSymbols.lookup("source") is None


def test_yaml_snippet_no_symbols():
    assert YamlSnippet.from_data("hello world") is None


def test_yaml_snippet_source():
    class C(ResourceSchema):
        s = fields.String()

    source = C().loads("s: hello world")
    assert YamlSnippet.from_data(source).format() == (
        'in "<unicode string>", line 1, column 1:\n' "  s: hello world\n" "  ^^^\n"
    )


def test_yaml_snippet_key_mapping():
    class C(ResourceSchema):
        s = fields.String()

    source = C().loads("s: hello world")
    assert YamlSnippet.from_data(source, key="s").format() == (
        'in "<unicode string>", line 1, column 4:\n' "  s: hello world\n" "     ^^^\n"
    )


def test_yaml_snippet_key_sequence():
    class C(ResourceSchema):
        s = fields.List(fields.String)

    source = C().loads("s: [hello world, goodbye world]")
    assert YamlSnippet.from_data(source["s"], key=1).format() == (
        'in "<unicode string>", line 1, column 18:\n'
        "  s: [hello world, goodbye world]\n"
        "                   ^^^\n"
    )


def test_yaml_snippet_line_block_scalar():
    class C(ResourceSchema):
        s = fields.String()

    source = C().loads(("s: >\n" "    hello world\n" "    bye bye\n"))
    assert YamlSnippet.from_data(source["s"], line=1).format() == (
        'in "<unicode string>", line 2:\n'
        "  s: >\n"
        "      hello world\n"
        "      ^^^\n"
        "      bye bye\n"
    )


def test_yaml_snippet_line_style_flow_scalar():
    class C(ResourceSchema):
        s = fields.String()

    source = C().loads(('s: "hello world\n' '    bye bye"\n'))
    assert YamlSnippet.from_data(source["s"], line=1).format() == (
        'in "<unicode string>", line 1:\n' '  s: "hello world\n' "     ^^^\n" '      bye bye"'
    )


LIPSUM = (
    "Sed ut perspiciatis, unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem "
    "aperiam eaque ipsa, quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt, explicabo.\n"
    "Nemo enim ipsam voluptatem, quia voluptas sit, aspernatur aut odit aut fugit, sed quia consequuntur magni dolores "
    "eos, qui ratione voluptatem sequi nesciunt, neque porro quisquam est, qui dolorem ipsum, quia dolor sit, amet, "
    "consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt, ut labore et dolore magnam aliquam "
    "quaerat voluptatem.\n"
    "Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, "
    "nisi ut aliquid ex ea commodi consequatur?\n"
    "Quis autem vel eum iure reprehenderit, qui in ea voluptate velit esse, quam nihil molestiae consequatur, "
    "vel illum, qui dolorem eum fugiat, quo voluptas nulla pariatur?\n"
    "At vero eos et accusamus et iusto odio dignissimos ducimus, qui blanditiis praesentium voluptatum deleniti "
    "atque corrupti, quos dolores et quas molestias excepturi sint, obcaecati cupiditate non provident, similique "
    "sunt in culpa, qui officia deserunt mollitia animi, id est laborum et dolorum fuga.\n"
    "Et harum quidem rerum facilis est et expedita distinctio.\n"
    "Nam libero tempore, cum soluta nobis est eligendi optio, cumque nihil impedit, quo minus id, quod maxime placeat, "
    "facere possimus, omnis voluptas assumenda est, omnis dolor repellendus.\n"
    "Temporibus autem quibusdam et aut officiis debitis aut rerum necessitatibus saepe eveniet, "
    "ut et voluptates repudiandae sint et molestiae non recusandae.\n"
    "Itaque earum rerum hic tenetur a sapiente delectus, ut aut reiciendis voluptatibus maiores alias "
    "consequatur aut perferendis doloribus asperiores repellat."
)


def test_yaml_snippet_max_chars():
    class C(ResourceSchema):
        s = fields.String()

    lipsum = indent(LIPSUM, "  ")
    source = C().loads(f"s: >\n{lipsum}")
    assert YamlSnippet.from_data(source["s"], line=2).format() == (
        'in "<unicode string>", line 3:\n'
        "  ...illo inventore veritatis et quasi architecto beatae vitae dicta sunt, explicabo.\n"
        "    Nemo enim ipsam voluptatem, quia voluptas sit, aspernatur aut odit aut fugit, sed quia "
        "consequuntur magni dolores eos, qui ratione voluptatem sequi nesciunt, neque porro quisquam est, "
        "qui dolorem ipsum, quia dolor sit, amet, consectetur, adipisci velit, sed quia non numquam eius "
        "modi tempora incidunt, ut labore et dolore magnam aliquam quaerat voluptatem.\n"
        "    ^^^\n"
        "    Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit ..."
    )


def test_yaml_snippet_frame():
    class C(ResourceSchema):
        s1 = fields.String()
        s2 = fields.String()
        s3 = fields.String()

    source = C().loads(
        """
        s1: String 1
        s2: |
            Line 1
            Line 2
            Line 3
            Line 4
        s3: |
            String 3"""
    )
    assert YamlSnippet.from_data(source["s2"], line=1).format() == (
        'in "<unicode string>", line 4:\n'
        "  s2: |\n"
        "      Line 1\n"
        "      ^^^\n"
        "      Line 2\n"
        "      Line 3\n"
        "      Line 4\n"
        "  s3: |"
    )


def test_yaml_snippet_frame_without_nl():
    class C(ResourceSchema):
        s1 = fields.String()
        s2 = fields.String()

    source = C().loads(
        """
        s1: String 1
        s2: |
            Line 1"""
    )
    assert YamlSnippet.from_data(source["s2"], line=1).format() == (
        'in "<unicode string>", line 4:\n' "  s2: |\n" "      Line 1\n" "      ^^^\n"
    )


def test_yaml_snippet_frame_with_nl():
    class C(ResourceSchema):
        s1 = fields.String()
        s2 = fields.String()

    source = C().loads(
        """
        s1: String 1
        s2: |
            Line 1
"""
    )
    assert YamlSnippet.from_data(source["s2"], line=1).format() == (
        'in "<unicode string>", line 4:\n' "  s2: |\n" "      Line 1\n" "      ^^^\n"
    )


def test_yaml_snippet_frame_delta():
    class C(ResourceSchema):
        s1 = fields.String()
        s2 = fields.String()
        s3 = fields.String()

    source = C().loads(
        """
        s1: String 1
        s2: |
            Line 1
            Line 2
            Line 3
            Line 4
            Line 5
            Line 6
        s3: |
            String 3"""
    )
    assert YamlSnippet.from_data(source["s2"], line=1).format() == (
        'in "<unicode string>", line 4:\n'
        "  s2: |\n"
        "      Line 1\n"
        "      ^^^\n"
        "      Line 2\n"
        "      Line 3"
    )
