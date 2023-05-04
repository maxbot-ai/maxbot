# Jinja Syntax

## Delimiters

### `{{ ... }}` {#print-statement}

Print statements include expressions, which get replaced with values when a template is rendered. As a simple expression, you can use a variable `username` so that your response includes the name of the user:

```
Good day to you, {{ username }}!
```

If the user name is Norman, then the response that is displayed to user is

```
Good day to you, Norman!
```

See also: [Expressions](/design-guides/templates.md#expressions).

### `{% ... %}` {#tags}

Template tags include statements that control template logic, evaluate expressions, assign variables and more.

See also: [Statements](#statements).

### `{\# ... #}` {#comments}

Comments that are not included in the template output. This is useful to comment out parts of the template for debugging or to add information for other template designers or yourself:

```
{# note: commented-out template because we no longer use this
    {% for user in users %}
        ...
    {% endfor %}
#}
```

## Literals

This section contains only literal for None Type. There are also links to and examples of literals for basic data types:

* [String Literals](strings.md#literals) - `"Hello World"`,
* [Boolean Literals](booleans.md#literals) - `true`, `false`,
* [List Literals](lists.md#literals) - `["onion", "olives", "ham"]`,
* [Dictionary Literals](dictionaries.md#literals) - `{"first_name": "John", "last_name": "Snow"}`,
* [Number Literals](numbers.md#literals) - `42`, `42.1e2`.

### `none` {#literal-none}

The `none` literal is used to define a value of None Type.

See also: [Data types](/design-guides/templates.md#data-types).

## Operators

This section contains only general purpose opeators. More type-specific operators are also availabe:

* [String-specific Operators](strings.md#operators),
* [Comparison Operators](booleans.md#comparisons),
* [Logic Operators](booleans.md#logic),
* [List-specific Operators](lists.md#operators),
* [Dictionary-specific Operators](dictionaries.md#operators),
* [Math Operators](numbers.md#operators).

### `x.y` / `x[y]` {#attibutes}

Get an attribute of an object. You can use both a dot `x.y` and a "subscript" `x[y]` operators to access attributes of a variable. The following lines do the same thing:

```
{{ entities.menu }}
{{ entities["menu"] }}
```

### `x()` {#callabale}

Call a function or method.

```
{{ title.capitalize() }}
```

Inside of the parentheses you can use positional arguments and keyword arguments like in Python:

```
{% set ns = namespace(found=true) %}
```

Typically, functions are available as global variables.

Methods are available for the following basic types:

* [String Methods](strings.md#methods);
* [List Methods](lists.md#methods);
* [Dictionary Methods](dictionaries.md#methods).

### `x | y`

Filters are a convenient way to change variables. Filters are separated from the variable by a pipe symbol `x | y`.

```
{{ x|upper }}
```

Filters may have optional arguments in parentheses.

```
{{ x|replace("Hello", "Goodbye") }}
{{ x|indent(width=8) }}
```

Multiple filters can be chained. The output of one filter is applied to the next.

```
{{ x|select|first }}
```

Filters are available for the following basic types:

* [String Filters](strings.md#filters);
* [List Filters](lists.md#filters-transform);
* [Dictionary Filters](dictionaries.md#filters).

### `x if y else z` {#conditional-expression}

A conditional expression, yields the value of `x` if `y` if true, otherwise the value of `z` if returned.

```
{% set n = numbers|first if numbers|length > 0 else -1 %}
```

**See also**: [if-statement](#statement-if).

## Statements

### `{% delete ... %}` {#delete-state-variable}

Delete a state variable.

```
{% delete slots.counter %}
{% delete user.name %}
```

The variable is considered deleted and no longer uses the bot's memory. Trying to get the value of a variable will result in an error.

**See also**: [State Variables](/design-guides/state.md).


### `{% do ... %}` {#expression-statement}

The expression-statement simply evaluates the expression and does nothing else. It does not print or assign the result.

This can be used to modify lists or dicts:

```
{% do toppings_array.append("ketchup") %}
{% do car.update(color="White") %}
```

**See also**: [`list.append`](lists.md#method-append), [`dict.update`](dictionaries.md#method-update).

### `{% filter x %} ...` {#filter-block}

Filter block allows you to apply string filters on a block of template data. Just wrap the code in the special filter section:

```
{% filter upper %}
This text becomes uppercase
{% endfilter %}
```

Filters that accept arguments can be called like this:

```
{% filter indent(width=8) %}
Indent this
{% endfilter %}
```

**See also**: [`str|upper`](strings.md#filter-upper), [`str|indent`](strings.md#filter-indent).

### `{% for x in ... %}` {#for}

You use the for-in loop to iterate over lists, dictionaries, strings, and other sequences.

Use for-statement to build a response text based on dynamically collected data. For example, to display the contents of the shopping cart to the user:

```yaml
{% set products = [
    {"title": "Anti-Gravity Boots"},
    {"title": "Fountain of Youth"},
    {"title": "Inflatable Flower Bed"},
] %}

Items in your bag.
{% for product in products %}
    {{ product.title }}
{% endfor %}
->
Items in your bag.
    Anti-Gravity Boots
    Fountain of Youth
    Inflatable Flower Bed
```

It is possible to iterate over dictionaries using method [`dict.items()`](dictionaries.md#method-items). Dictionaries may not be in the order you want to display them in. If order matters, use the [`dict|dictsort`](dictionaries.md#filter-dictsort) filter.

Please note that assignments in loops will be cleared at the end of the iteration and cannot outlive the loop scope. See [Scoping Behavior](/design-guides/templates.md#scoping-behavior) for more information about how to deal with this.

**See also**: [Iterating over](lists.md#sequences-and-iterables), [`dict.items()`	](dictionaries.md#method-items), [`dict|dictsort`](dictionaries.md#filter-dictsort), [Scoping Behavior](/design-guides/templates.md#scoping-behavior).

#### `{% for ... if ... %}` {#for-if}

Filter the sequence during iteration, which allows you to skip items. The following example skips all the products which are not in stock.

```
Product List
{% set products = [{"id":1,"title":"olive", "in_stock":true}, {"id":2,"title":"ham"}, {"id":3,"title":"cheese", "in_stock":true}] %}
{% for product in products if product.in_stock %}
    {{ product.title }} <br/>
{% endfor %}
->
olive
cheese
```

See also: [If-expression: `x if y else z`](#conditional-expression), [`{% if ... %}`](#statement-if), [`{% for x in ... %}`](#for).

#### `{% for ... %}` - `{% else %}` {#for-else}

If no iteration took place because the sequence was empty or the filtering removed all the items from the sequence, you can render a default block by using else:

```
Product List
{% set products = [{"id":1,"title":"olive", "in_stock":true}, {"id":2,"title":"ham"}, {"id":3,"title":"cheese", "in_stock":true}] %}
{% for product in products %}
    {{ product.title }} <br/>
{% else %}
    no products found
{% endfor %}
->
olive
ham
cheese
```

See also: [`{% for x in ... %}`](#for), [Scoping Behavior](/design-guides/templates.md#scoping-behavior).

#### `{% for ... recursive %}` {#for-recursive}

It is possible to use loops recursively. This is useful if you are dealing with recursive data such as article references. To use loops recursively, you basically have to add the recursive modifier to the loop definition and call the `loop` variable with the new iterable where you want to recurse.

The following example shows article references with recursive loops:

```
{% set articles =[
    {
    "id": 1,
    "title": "Title 1",
    "references": [
          {
            "id": 5,
            "title": "Title 5",
            "references": [
            {
              "id": 6,
              "title": "Title 6",
              "references": []
            }]
          },
          {
            "id": 7,
            "title": "Title 7",
            "references": []
          }]
    },
    {
    "id": 2,
    "title": "Title 2",
    "references": []
    },
    {
    "id": 3,
    "title": "Title 3",
    "references": []
    }]
%}
{% for article in articles recursive %}
    {{ article.title }};
    {% if article.references %}
        {{ loop(article.references)|indent(width=8) }}
    {% endif %}
{% endfor %}
->
Title 1; Title 5; Title 6;
Title 7;
Title 2; Title 3;
```

See also: [`{% for x in ... %}`](#for), [`loop` variable](#loop-variable), [`str|indent`](strings.md#filter-indent).

### `{% if ... %}` {#statement-if}

Use if-statement to change the response based on a specific conditions. In the simplest form, you can use it to test if a variable is defined, not empty and not false.

If the product description is not defined or is an empty string, the description line should not be printed at all. Then the response may be the following.

```
Product Name: {{ slots.product.name }}.
{% if slots.product.description %}
Description: {{ slots.product.description }}
{% endif %}
```

Use elif- and else-statements for multiple branches. You can use more complex expressions there, too.

```
{%   if slots.total_points / slots.total_voters > 4 %}
Great stuff!
{% elif slots.total_points / slots.total_voters > 3 %}
A good thing.
{% else %}
Bad reviews...
{% endif %}
```

If can also be used as an inline [If-expression: `x if y else z`](#conditional-expression)  and for loop filtering [`{% for ... if ... %}`](#for-if).

### `{% set x = ... %}` {#local-assignment}

Assign value to a local variable.

```
{% set rating = slots.total_points / slots.total_voters %}
```

Assign value to [slot variable](/design-guides/state.md#slot-variables).

```
{% set slots.counter = 1 %}
```

Assign value to [user variable](/design-guides/state.md#user-variables).

```
{% set user.name = "Steve" %}
```

Assignments can have multiple targets separated by commas. In the example, variable `x` is set to `0` and variable `y` is set to `1`.

```
{% set x, y = 0, 1 %}
```

**See also**: [State Variables](/design-guides/state.md).


### `{% set x %} ...` {#block-assignment}

Block assignments are used to capture the contents of a block into a [local variable](#local-variables). Instead of using an equals sign and a value, you just write the variable name and then everything until `{% endset %}` is captured.

```
{% set reply %}
	You wrote:
	{{ message.text }}
{% endset %}
```

The block assignment supports [filters](#filters).

```
{% set reply | truncate %}
	You wrote:
	{{ message.text }}
{% endset %}
```

**See also**: [Filters](#filters), [`str|truncate`](strings.md#filter-truncate).

### `{% set slots.x = ... %}` {#slot-assignment}

Assign value to [slot variable](/design-guides/state.md#slot-variables).

```
{% set slots.counter = 1 %}
```

**See also**: [Slot Variables](/design-guides/state.md#slot-variables), [Working with State Variables](/design-guides/state.md#working-with-state-variables).

### `{% set user.x = ... %}` {#user-assignment}

Assign value to [user variable](/design-guides/state.md#user-variables).

```
{% set user.name = "Steve" %}
```

**See also**: [User Variables](/design-guides/state.md#user-variables), [Working with State Variables](/design-guides/state.md#working-with-state-variables).

## Globals

This section contains only general purpose filters. There also type-specific [`dict`](dictionaries.md#dict) and [`range`](lists.md#range.).

### `namespace()` {#namespace}

Creates a new container that allows attribute assignment using the `{% set x = ... %}` tag:

```
{% set ns = namespace() %}
{% set ns.foo = "bar" %}
```

**See also**: [Assignment](#local-assignment), [Scoping Behavior](/design-guides/templates.md#scoping-behavior)

## Filters

This section contains only general purpose filters. More type-specific filters are also availabe:

* [String Filters](strings.md#filters);
* [List Filters](lists.md#filters-transform);
* [Dictionary Filters](dictionaries.md#filters).

### `x|default` {#filter-default}

If the value is undefined it will return the passed default value, otherwise the value of the variable:

```
{{ entities.order_number.literal|default("unknown order number") }}
```

This will output the value of `entities.order_number.literal` if the variable was defined, otherwise `"unknown order number"`.

```
{% set slots.guests = entities.number.value|default(2) %}
```

If the `entities.number` is undefined, then the value of state variable `slots.guests` will be `2`.

If you want to use default with variables that evaluate to false you have to set the second parameter to true:

```
{{ ''|default('the string was empty', true) }}
```

**Aliases**: `x|d`.

**See also**: [Filters](/design-guides/templates.md#filters), [Undefined Value](/design-guides/templates.md#undefined-value).

## Tests

This section contains only general purpose tests. More type-specific tests are also availabe:

* [String Tests](strings.md#tests);
* [Boolean Tests](booleans.md#tests);
* [List Tests](lists.md#tests);
* [Dictionary Tests](dictionaries.md#tests);
* [Number Tests](numbers.md#tests).

### `x is defined`

Return true if the variable or its attribute is defined.

```
{% if variable is defined %}
    value of variable: {{ variable }}
{% else %}
    variable is not defined
{% endif %}
```

**See also**: [Tests](/design-guides/templates.md#tests), [Undefined Value](/design-guides/templates.md#undefined-value).

### `x is filter`

Check if a filter exists by name. Useful if a filter may be optionally available.

```
{% if "markdown" is filter %}
    {{ value | markdown }}
{% else %}
    {{ value }}
{% endif %}
```

See also: [Tests](#tests), [Filters](#filters).

### `x is none` {#test-none}

Return true if the variable is none.

**See also**: [Tests](/design-guides/templates.md#tests), [None Type](#literal-none).

### `x is test`

Check if a test exists by name. Useful if a test may be optionally available.

```
{% if "loud" is test %}
    {% if value is loud %}
        {{ value|upper }}
    {% else %}
        {{ value|lower }}
    {% endif %}
{% else %}
    {{ value }}
{% endif %}
```

See also: [Tests](#tests), [`str|upper`](strings.md#filter-upper), [`str|lower`](strings.md#filter-lower).

### `x is undefined`

Return true if the variable or its attribute is undefined.

**See also**: [Tests](/design-guides/templates.md#tests), [Undefined Value](/design-guides/templates.md#undefined-value).

## `loop` variable {#loop-variable}

Inside of a [for-statement](#for) block, you can access special `loop` variable.

The `loop` variable always refers to the closest (innermost) loop. If we have more than one level of loops, we can rebind the variable loop by writing  `{% set outer_loop = loop %}` after the loop that we want to use recursively. Then, we can call it using `outer_loop.index` and so on.

### `loop.index / index0` {#loop.index}

* `loop.index` - The current iteration of the loop. (1 indexed).
* `loop.index0` - The current iteration of the loop. (0 indexed).

### `loop.revindex / revindex0`

* `loop.revindex` - The number of iterations from the end of the loop (1 indexed).
* `loop.revindex0` - The number of iterations from the end of the loop (0 indexed).

### `loop.first / last`	{#loop.first-last}

* `loop.first` - True if first iteration.
* `loop.last` - True if last iteration.

### `loop.length` {#loop.length}

The number of items in the sequence.

### `loop.cycle` {#loop.cycle}

A helper function to cycle between a list of sequences.

Within a for-loop, it’s possible to cycle among a list of strings/variables each time through the loop by using the special `loop.cycle` helper:

```
{% for row in rows %}
    {{ loop.cycle('odd', 'even') }} {{ row }}
{% endfor %}
```

### `loop.depth / depth0` {#loop.depth}

* `loop.depth` - Indicates how deep in a recursive loop the rendering currently is. Starts at level 1.
* `loop.depth0` - Indicates how deep in a recursive loop the rendering currently is. Starts at level 0.

**See also**: [`{% for ... recursive %}`](#for-recursive).

### `loop.previtem / nextitem` {#loop.depth}

* `loop.previtem` - The item from the previous iteration of the loop. `undefined` during the first iteration.
* `loop.nextitem` - The item from the following iteration of the loop. `undefined` during the last iteration.

If all you want to do is check whether some value has changed since the last iteration or will change in the next iteration, you can use previtem and nextitem:

```
{% for value in values %}
    {% if loop.previtem is defined and value > loop.previtem %}
        The value just increased!
    {% endif %}
    {{ value }}
    {% if loop.nextitem is defined and loop.nextitem > value %}
        The value will increase even more!
    {% endif %}
{% endfor %}
```

### `loop.changed(*val)`

True if previously called with a different value (or not called at all).

If you only care whether the value changed at all, using changed is even easier:

```
{% for entry in entries %}
    {% if loop.changed(entry.category) %}
        {{ entry.category }}
    {% endif %}
    {{ entry.message }}
{% endfor %}
```

## JSON Compatibility


| JSON        | Jinja                           | Description |
| ----------- | -----------                     | ----------- |
| string      | [Strings](strings.md)           |             |
| number      | [Numbers](numbers.md)           |             |
| boolean     | [Booleans](booleans.md)         |             |
| array       | [Lists](lists.md)               |             |
| object      | [Dictionaries](dictionaries.md) |             |
| null        | [None Type](#none-type)         |             |
