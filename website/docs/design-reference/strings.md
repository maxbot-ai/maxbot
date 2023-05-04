# Strings

Strings are sequences of unicode characters. Their methods and filters help you work with text. String-specific operators, tests, filters, and methods are described below. Since strings are also [sequences](lists.md#lists-tuples-and-more), you can apply any sequence [operators](lists.md#operators), [tests](lists.md#tests), and [filters](lists.md#filters) to strings. We duplicate the most important of them on this page.

## Literals

### "Hello World" {#new-string}

String literals are surrounded by either single quotation marks, or double quotation marks.

```
{{ "hello" }}
-> hello

{{ 'hello' }}
-> hello
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#literals).

## Constructors

### `any|string` {#filter-string}

Convert an object to a string if it isn’t already.

```
{{ true|string|upper }}
-> TRUE
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.string).

## Operators

### `string[start:stop]` {#operator-slice}

Gets a substring with the character at *start* and the last character set to index before *stop*. Indexes *start* and *stop* can be omitted which means that the result includes characters from the beginning or end of the string.

```
{% set input = "This is a text." %}

{{ input[5:15] }}
-> "is a text."

{{ input[5:] }}
-> "is a text."

{{ input[:15] }}
-> "This is a text."
```

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#typesseq-common), [In-depth Tutorial on DigitalOcean](https://www.digitalocean.com/community/tutorials/python-slice-string).

### `string % x` {#operator-modulo}

Given `string % x`, instances of `%` in string are replaced with zero or more elements of values. This operation is commonly known as string interpolation.

```
{% set greeting = "Hello" %}
{% set name = "John" %}

{{ "%s, %s!" % (greeting, name) }}
-> Hello, John!
```

In most cases it should be more convenient and efficient to use the  [`str.format()`](#method-format):

```
{{ "{}, {}!".format(greeting, name) }}
-> Hello, John!
```

**See also**: [Python Docs](https://docs.python.org/3/tutorial/inputoutput.html#old-string-formatting), [printf-style String Formatting](https://docs.python.org/3/library/stdtypes.html#old-string-formatting), [`str|format`](#filter-format), [`str.format()`](#method-format).

### `x in string` {#operator-in}

Return true if the right string contains the left substring.

```
{% set input = "I said yes!" %}

{{ "yes" in input }}
-> true # because the input string contains substring "yes"
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#other-operators).

### `x not in string` {#operator-not-in}

Return true if the right string does not contain the left substring.

```
{% set input = "I said no!" %}

{{ "yes" in input }}
-> false # because the input string does not contain substring "yes"
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#logic).

### `string1 ~ string2` {#operator-concatenate}

Converts all operands into strings and concatenates them.

```
{% set name = "John" %}

{{ "Hello " ~ name ~ "!" }}
-> Hello John!
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#other-operators).

### `string * number` {#operator-multiply}

Repeat a string multiple times.

```
{{ "=" * 8 }}
-> ========
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#math).

## Tests

### `x is in string` {#test-in}

Check if *x* is in *string*. Typicallty you need to use operator [`x in string`](#operator-in) instead of a test. Use a test when you need filter a list of possible substrings.

```
{% set input = "I said yes!" %}

{{ "yes" is in input }}
-> true

{{ ["yes", "yep", "ok"]|select("in", input)|list }}
-> ["yes"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.in), [`x in string`](#operator-in), [`list|select`](lists.md#filter-select), [`iterable|list`](lists.md#filter-list).

### `x is lower` {#test-lower}

Return true if *x* is lowercased.

```
{{ "onion" is lower }}
-> true

{{ ["onion", "olives", "HAM"]|select("lower")|list }}
-> ["onion", "olives"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.lower), [`list|select`](lists.md#filter-select), [`iterable|list`](lists.md#filter-list), [Methods: Character Case](#methods-character-case).

### `x is string` {#test-string}

Return true if *x* is a string.

```
{{ "hello world" is string }}
-> true

{{ [true, "hello world", 12]|select("string")|list }}
-> ["hello world"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.string), [`list|select`](lists.md#filter-select), [`iterable|list`](lists.md#filter-list).

### `x is upper` {#test-upper}

Return true if *x* is uppercased.

```
{{ "HAM" is upper }}
-> true

{{ ["onion", "olives", "HAM"]|select("upper")|list }}
-> ["HAM"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.upper), [`list|select`](lists.md#filter-select), [`iterable|list`](lists.md#filter-list), [Methods: Character Case](#methods-character-case).

## Filters

### `str|capitalize` {#filter-capitalize}

Capitalize a value. The first character will be uppercase, all others lowercase.

```
{% set input = "hello world!" %}

{{ input|capitalize }}
-> Hello world!
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.capitalize), [Methods: Character Case](#methods-character-case).

### `str|format` {#filter-format}

Apply the given values to a [printf-style](https://docs.python.org/library/stdtypes.html#printf-style-string-formatting) format string, like string % values.

```
{{ "%s, %s!"|format(greeting, name) }}
Hello, World!
```

In most cases it should be more convenient and efficient to use the  [`str.format()`](#method-format):

```
{{ "{}, {}!".format(greeting, name) }}
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.format), [`string % x`](#operator-modulo),  [Methods: Formatting](#methods-formatting).

### `str|indent` {#filter-indent}

Return a copy of the string with each line indented by 4 spaces. The first line and blank lines are not indented by default.

#### Parameters

* `width` – Number of spaces, or a string, to indent by.
* `first` – Don’t skip indenting the first line.
* `blank` – Don’t skip indenting empty lines.

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.indent), [Methods: Formatting](#methods-formatting).

### `str|length` {#filter-length}

Return the number of characters in a string.

```
{% set input = "Hello" %}

{{ input|length }}
-> 5
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.length).

### `str|lower` {#filter-lower}

Convert a string to a lowercase.

```
{% set input = "This is A DOG!" %}

{{ input|lower }}
-> this is a dog!
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.lower), [Methods: Character Case](#methods-character-case).

### `str|replace` {#filter-replace}

Return a copy of the value with all occurrences of a substring replaced with a new one.

#### Parameters

* `old*` - The substring that should be replaced.
* `new*`- The replacement string.
* `count` - If givven, only the first *count* occurrences are replaced.

#### Examples

```
{{ "Hello World"|replace("Hello", "Goodbye") }}
-> Goodbye World

{{ "AAA"|replace("A", "B", 2) }}
-> BBA
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.replcae), [Methods: Replacing](#methods-replacing).

### `str|title` {#filter-title}

Return a titlecased version of the value. I.e. words will start with uppercase letters, all remaining characters are lowercase.

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.title), [Methods: Character Case](#methods-character-case).

### `str|trim` {#filter-trim}

Strip leading and trailing characters, by default whitespace.

#### Parameters

* `chars` - A string containing characters to strip.

#### Examples

```
{% set input = "   something is here    " %}

Result: "{{ input|trim }}".
-> Result: "something is here".
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.trim), [Methods: Stripping](#methods-stripping).

### `str|truncate` {#filter-truncate}

Return a truncated copy of the string.

Strings that only exceed the length by the tolerance margin given in the fourth parameter will not be truncated.

#### Parameters

* `length` - The maximum length of the string to keep on (default=255).
* `killwords` - If true, the cut the text at length, otherwise discard the last word (default=false).
* `end` - A string to append if the text is in fact truncated (default="...").
* `leeway ` - Strings that only exceed the length by the tolerance margin given will not be truncated (default=5).

#### Examples

```
{{ "foo bar baz qux"|truncate(9) }}
-> "foo..."

{{ "foo bar baz qux"|truncate(9, true) }}
-> "foo ba..."

{{ "foo bar baz qux"|truncate(11) }}
-> "foo bar baz qux"

{{ "foo bar baz qux"|truncate(11, false, '...', 0) }}
-> "foo bar..."
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.truncate), [Methods: Formatting](#methods-formatting).

### `str|upper` {#filter-upper}

Convert a string to uppercase.

```
{% set input = "hi there" %}

{{ input|upper }}
-> HI THERE
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.upper), [Methods: Character Case](#methods-character-case).

### `str|wordcount` {#filter-wordcount}

Count the words in that string.

```
{% set input = "Hello, world!" %}

{{ input|wordcount }}
-> 2
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.wordcount).

## Methods {#methods}

## Methods: Replace {#methods-replacing}

### `str.replace(old, new)` {#method-replace}

Return a copy of the string with all occurrences of substring old replaced by new. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.replace).

## Methods: Prefixes, Suffixes {#methods-prefixes-and-suffixes}

### `str.startswith(prefix)` {#method-startswith}

Return true if string starts with the prefix, otherwise return false.

```
{% set input = "What is your name?" %}

{{ input.startswith("What") }}
-> true
```

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.startswith).

### `str.endswith(suffix, ...)` {#method-endswith}

Return true if the string ends with the specified suffix, otherwise return false.

```
{% set input = "What is your name?" %}

{{ input.endswith("?") }}
-> true
```

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.endswith).

### `str.removeprefix(prefix)` {#method-removeprefix}

Return a copy of the string without the prefix. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.removeprefix).

### `str.removesuffix(suffix)` {#method-removesuffix}

Return a copy of the string without the suffix. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.removesuffix).

## Methods: Strip {#methods-stripping}

### `str.strip([chars], ...)` {#method-strip}

Return a copy of the string with the leading and trailing characters removed. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.strip).

### `str.lstrip([chars])` {#method-lstrip}

Return a copy of the string with leading characters removed. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.lstrip).

### `str.rstrip([chars])` {#method-rstrip}

Return a copy of the string with trailing characters removed. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.rstrip).

## Methods: Split {#methods-splitting}

### `str.partition(sep)` {#method-partition}

Split the string at the *first occurrence* of sep, and return a 3-tuple containing the part before the separator, the separator itself, and the part after the separator. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.partition).

### `str.rpartition(sep)` {#method-rpartition}

Split the string at the *last occurrence* of sep, and return a 3-tuple containing the part before the separator, the separator itself, and the part after the separator. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.rpartition).

### `str.rsplit(sep)` {#method-rsplit}

Return a list of the words in the string, using sep as the delimiter string. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.rsplit).

### `str.split(sep, ...)` {#method-split}

Return a list of the words in the string, using sep as the delimiter string. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.split).

### `str.splitlines(...)` {#method-splitlines}

Return a list of the lines in the string, breaking at line boundaries. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.splitlines).

## Methods: Format {#methods-formatting}

### `str.format(...)` {#method-format}

Perform a string formatting operation. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.format).

```
{{ "The sum of 1 + 2 is {0}".format(1+2) }}
-> The sum of 1 + 2 is 3
```

See also: [Format String Syntax](https://docs.python.org/3/library/string.html#formatstrings), [`str|format`](#filter-format), [`string % x`](#operator-modulo).

### `str.join(iterable)` {#method-join}

Return a string which is the concatenation of the strings in iterable. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.join).

**See also**: [`list|join`](lists.md#filter-join).

### `str.center(width, ...)` {#method-center}

Return centered in a string of length width. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.center).

### `str.expandtabs(...)` {#method-expandtabs}

Return a copy of the string where all tab characters are replaced by one or more spaces, depending on the current column and the given tab size. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.expandtabs).

### `str.ljust(width)` {#method-ljust}

Return the string left justified in a string of length width. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.ljust).

### `str.rjust(width)` {#method-rjust}

Return the string right justified in a string of length width. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.rjust).

### `str.zfill(width)` {#method-zfill}

Return a copy of the string left filled with ASCII '0' digits to make a string of length width. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.zfill).

## Methods: Character Case {#methods-character-case}

### `str.capitalize()` {#method-capitalize}

Return a copy of the string with its first character capitalized and the rest lowercased. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.capitalize).

### `str.casefold()` {#method-casefold}

Return a casefolded copy of the string. Casefolded strings may be used for caseless matching. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.casefold).

### `str.upper()` {#method-upper}

Return a copy of the string with all the cased characters 4 converted to uppercase. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.upper).

### `str.lower()` {#method-lower}

Return a copy of the string with all the cased characters converted to lowercase. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.lower).

### `str.title()` {#method-title}

Return a titlecased version of the string where words start with an uppercase character and the remaining characters are lowercase. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.title).

### `str.swapcase()` {#method-swapcase}

Return a copy of the string with uppercase characters converted to lowercase and vice versa. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.swapcase).

## Methods: Predicates {#methods-predicates}

### `str.isalnum()` {#method-isalnum}

Return true if all characters in the string are alphanumeric and there is at least one character, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.isalnum).

### `str.isalpha()` {#method-isalpha}

Return true if all characters in the string are alphabetic and there is at least one character, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.isalpha).

### `str.isascii()` {#method-isascii}

Return true if the string is empty or all characters in the string are ASCII, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.isascii).

### `str.isdecimal()` {#method-isdecimal}

Return true if all characters in the string are decimal characters and there is at least one character, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.isdecimal).

### `str.isdigit()` {#method-isdigit}

Return true if all characters in the string are digits and there is at least one character, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.isdigit).

### `str.islower()` {#method-islower}

Return true if all cased characters in the string are lowercase and there is at least one cased character, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.islower).

### `str.isnumeric()` {#method-isnumeric}

Return true if all characters in the string are numeric characters, and there is at least one character, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.isnumeric).

### `str.isprintable()` {#method-isprintable}

Return true if all characters in the string are printable or the string is empty, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.isprintable).

### `str.isspace()` {#method-isspace}

Return true if there are only whitespace characters in the string and there is at least one character, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.isspace).

### `str.istitle()` {#method-istitle}

Return true if the string is a titlecased string and there is at least one character. Return false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.istitle).

### `str.isupper()` {#method-isupper}

Return true if all cased characters in the string are uppercase and there is at least one cased character, false otherwise. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.isupper).

## Methods: Substrings {#methods-substrings}

### `str.find(sub, ...)` {#method-find}

Return the *lowest index* in the string where substring **sub** is found. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.find).

### `str.index(sub, ...)` {#method-index}

Like [str.find()](#method-find), but raise an errors when the substring is not found. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.index).

### `str.rfind(sub, ...)` {#method-rfind}

Return the *highest index* in the string where substring **sub** is found. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.rfind).

### `str.rindex(sub, ...)` {#method-rindex}

Like [str.rfind()](#method-rfind), but raise an errors when the substring is not found. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.rindex).

### `str.count(sub, ...)` {#method-count}

Return the number of non-overlapping occurrences of substring *sub*. See [Python Docs](https://docs.python.org/3/library/stdtypes.html#str.count).
