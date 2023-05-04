# Numbers

There are two numeric types: integer and float.

## Literals

### `42` {#new-int}

Integers are whole numbers without a decimal part. The `_` character can be used to separate groups for legibility.

```
{{ 42 / 123_456 }}
```

### `42.1e2` {#new-float}

Floating point numbers can be written using a `.` as a decimal mark. They can also be written in scientific notation with an upper or lower case `e` to indicate the exponent part. The `_` character can be used to separate groups for legibility, but cannot be used in the exponent part.

```
{{ 42.23 / 42.1e2 / 123_456.789 }}
```

## Constructors

### `any|int` {#filter-int}

Convert the value into an integer.

#### Parameters

* `default` - The value to return when conversion doesn’t work (default=0).
* `base` - Overrides the default base (10), which handles input with prefixes such as 0b, 0o and 0x for bases 2, 8 and 16 respectively.

#### Examples

```
{{ "2"|int + 2 }}
-> 4

{{ "0xFF"|int(base = 16) }}
255
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.int).

### `any|float` {#filter-float}

Convert the value into a floating point number.

#### Parameters

* `default` - The value to return when conversion doesn’t work (default=0.0).

#### Examples

```
{{ "1.1"|float + "0.5"|float }}
-> 1.6
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.float).

## Operators:

### `+` `-` `*` `/` `//` `%` `*` `**` {#math}

* `{{ 1 + 1 }} -> 2` - Add two numbers.
* `{{ 3 - 2 }} -> 1` - Subtract the second number from the first one.
* `{{ 1 / 2 }} -> 0.5` - Divide two numbers. The return value will be a floating point number.
* `{{ 20 // 7 }} -> 2` - Divide two numbers and return the truncated integer result.
* `{{ 11 % 7 }} -> 4` - Calculate the remainder of an integer division.
* `{{ 2 * 2 }} -> 4` - Multiply the left operand with the right one.
* `{{ 2**3 }} -> 8` - Raise the left operand to the power of the right operand.

## Tests

### `x is divisibleby` {#test-divisibleby}

Check if a variable is divisible by a number.

#### Parameters

* `num` - The number by which we divide.

#### Examples

```
{{ 12 is divisibleby 4 }}
-> true

{{ 11 is divisibleby 3 }}
-> false
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-test.divisibleby).

### `x is even` {#test-even}

Return true if the variable is even.

#### Examples

```
{{ 12 is even}}
-> true

{{ 11 is even }}
-> false
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.even).

### `x is float` {#test-float}

Return true if the object is a float.

#### Examples

```
{{ 12 is float}}
-> false

{{ 12.0 is float }}
-> true
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.float).

### `x is integer` {#test-integer}

Return true if the object is a integer.

#### Examples

```
{{ 12 is integer}}
-> true

{{ 12.0 is integer }}
-> false
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.integer).

### `x is number` {#test-number}

Return true if the object is a number.

#### Examples

```
{{ 12 is number}}
-> true

{{ 12.0 is number }}
-> true

{{ "12" is number }}
-> false
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.number).

### `x is odd` {#test-odd}

Return true if the number is odd.

#### Examples

```
{{ 11 is odd}}
-> true

{{ 12 is odd }}
-> false
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.odd).

## Filters

### `number|abs` {#filter-abs}

Return the absolute value of the argument.

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.abs).

### `number|filesizeformat` {#filter-filesizeformat}

Format the value like a ‘human-readable’ file size (i.e. 13 kB, 4.1 MB, 102 Bytes, etc).

#### Parameters

* `binary` - Per default decimal prefixes are used (Mega, Giga, etc.), if the parameter is set to true the binary prefixes are used (Mebi, Gibi).

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.filesizeformat).

### `number|round` {#filter-round}

Round the number to a given precision.

#### Parameters

* `precision` - Specifies the precision (default is 0).
* `method` - Specifies the method (default is common):
	* 'common' - rounds either up or down;
	* 'floor' - always rounds down;
	* 'ceil' - always rounds up.

#### Examples

```
{{ 42.55|round }}
-> 43.0
{{ 42.55|round(1, 'floor') }}
-> 42.5
```

Note that even if rounded to 0 precision, a float is returned. If you need a real integer, pipe it through int:

```
{{ 42.55|round|int }}
-> 43
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.round).
