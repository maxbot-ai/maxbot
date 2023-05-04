# Booleans

The **boolean type** is used to represent the truth value of an expression. For example, the expression `1 <= 2` is true , while the expression `0 == 1` is false. Expressions that evaluate to a boolean type are called **boolean expressions**.

## Literals

### `true`

`true` value is always true.

Another way you may come across is `True`. But you should use the lowercase version for consistency (all Jinja identifiers are lowercase).

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#literals).

### `false`

`false` value is always false.

Another way you may come across is `False`. But you should use the lowercase version for consistency (all Jinja identifiers are lowercase).

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#literals).

## Operators

### `==` `!=` `>` `>=` `<` `<=` {#comparisons}

Use this operators to build simple boolean expressions.

* `==` - Compares two objects for equality.
* `!=` - Compares two objects for inequality.
* `>` - *true* if the left hand side is greater than the right hand side.
* `>=` - *true* if the left hand side is greater or equal to the right hand side.
* `<` - *true* if the left hand side is lower than the right hand side.
* `<=` - *true* if the left hand side is lower or equal to the right hand side.

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#comparisons), [Python Docs](https://docs.python.org/3/reference/expressions.html#value-comparisons).

### `and` `or` `not` {#logic}

* The expression `x and y` yields false if *x* is false, otherwise **the value of y is returned**.
* The expression `x or y` yields true if *x* is true, otherwise **the value of y is returned**.
* The expression `not x` yields true if *x* is false, false otherwise.

Note that `and` `or` **does NOT always return bool type**, but rather return the last evaluated argument. For example,

```
{% set x = "hello world" %} {# true #}
{% set y = "" %}  {# false #}

"{{ x and y }}"
-> ""

{{ x or y }}
-> hello world

{{ not x }}
-> false
```

The same is true for other types such as numbers, lists, etc.

When using it as a conditional expression in an `{% if ... %}` statement, [the result is tested as a boolean value](/design-guides/templates.md#indirect-boolean-conversion), so there is no need to worry about it, but be careful when using the return value in subsequent operations.

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#logic), [Python Docs](https://docs.python.org/3/reference/expressions.html#boolean-operations).

## Tests

### `x is boolean` {#test-boolean}

Return true if the object is a boolean value.

```
{{ (0 == 1) is boolean }}
-> true
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.boolean).

### `x is true` {#test-true}

Return true if the object is *true*.

```
{{ (1 == 1) is true }}
-> true
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.true).

### `x is false` {#test-false}

Return true if the object is *false*.

```
{{ (0 == 1) is false }}
-> true
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.false).


## Tests: Comparisons

### `x is eq y` {#test-eq}

Same as `x == y`.

Aliases: `==`, `equalto`.

```
{{ [1, 2, 3, 2]|select('eq', 2)|list }}
-> [2, 2]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.eq), [`list|select`](lists.md#filter-select).

### `x is ge y` {#test-ge}

Same as `x >= y`.

Aliases: `>=`.

```
{{ [1, 2, 3, 2]|select('ge', 2)|list }}
-> [2, 3, 2]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.ge), [`list|select`](lists.md#filter-select).

### `x is gt y` {#test-gt}

Same as `x > y`.

Aliases: `>`, `greaterthan`.

```
{{ [1, 2, 3, 2]|select('gt', 2)|list }}
-> [3]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.gt), [`list|select`](lists.md#filter-select).

### `x is le y` {#test-le}

Same as `x <= y`.

Aliases: `<=`.

```
{{ [1, 2, 3, 2]|select('le', 2)|list }}
-> [1, 2, 2]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.le), [`list|select`](lists.md#filter-select).

### `x is lt y` {#test-lt}

Same as `x < y`.

Aliases: `<`, `lessthan`.

```
{{ [1, 2, 3, 2]|select('lt', 2)|list }}
-> [1]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.lt), [`list|select`](lists.md#filter-select).

### `x is ne y` {#test-ne}

Same as `x != y`.

Aliases: `!=`.

```
{{ [1, 2, 3, 2]|select('ne', 2)|list }}
-> [1, 3]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.ne), [`list|select`](lists.md#filter-select).
