---
toc_min_heading_level: 2
toc_max_heading_level: 2
---

# Templates

This document describes the syntax and semantics of the Jinja template engine tailored for use in MaxBot.

## Synopsis

A template is simply a string that is interpreted by template engine. Special delimiters in the template allow you to write code using statements and expressions. When responding to a user, the template is passed user input and bot state to render the final response. You can use [context variables](/design-reference/context.md) to access all necessary information during template rendering.

The templating engine is overlaid on a markdown document that is expected to be a reply of the bot.

Templates themselves has a few kinds of delimiters.

* `{{ ... }}` - A print statement, that include [expression](#expressions), which get replaced with values when a template is rendered.
* `{% ... %}` - Template tags include statements that control template logic, evaluate expressions, assign variables and more.
* `{# ... #}` - Comments that are not included in the template output.

## Variable Substitution

Include any context variable value in your response using the `{{ ... }}` print-statement. If you now that the `user.name` variable is set to the name of the user, then you can refer to it in the text response.

```yaml
response: |
  Good day to you, {{ user.name }}!
```

The same way you can include variable into the [MAXML response](markdown.md#maxml).

```yaml
response: |
  <text>Good day to you, {{ user.name }}!</text>
```

If the user name is Norman, then in both cases the response that is displayed to user is

```
🤖 Good day to you, Norman!
```


### Escaping

TODO

## Expressions {#expressions}

You can use expressions everywhere in dialog tree conditions and templates. The simplest form of expressions are variables and literals. More complex expressions are built by combining expressions using operators. It is also possible to group expressions and control the order of operations using parentheses ().

### Variables

Template variables are used to store and refer to values during template rendering. The most important variables are context variables, of which state variables are a part. Templates also use global and local variables.

Context variables are a predefined set of variables passed for each template by the bot using Jinja context dictionary. Most context variables contain information about user input. You can just read those variables and you can't change them. The `slots` and `user` context variables allows you to retaining information across dialog turns. You can change their attributes which are called state variables.

Global variables are shared by the bot between all templates. Typically they are utility functions. Examples are [`namespace`](#namespace), [`dict`](/design-reference/dictionaries.md#dict), [`range`](/design-reference/lists.md#range.). Local variables help you to store intermediate values and refer them later during the template rendering. They are described in the [Local Variables](#local-variables) section of this guide.

### Data Types

Which literals and operators are available to build an expression depends on the data type. There are *basic data types* that you mostly use in expressions: [strings](/design-reference/strings.md), [numbers](/design-reference/numbers.md), [boolean](/design-reference/booleans.md), [lists](/design-reference/lists.md) and [dictionaries](/design-reference/dictionaries.md). The links above are references with the detailed information about these types. For the most context variables the bot uses its custom object types which a described in [Context](/design-reference/context.md)  reference.

When working with templates, you may come across None Type, which is used to define a so-called null variable or attribute. This is like JSON null. It has a single valid value given by a literal `none`, which is not the same as `0`, `false`, or an empty string. Be careful when using None Type, as almost all operations on it will fail. In most cases, maxbot avoids using this type and prefer [an undefined value](#undefined-value) which is more relaxed.

### Literals {#literals}

There are literals for different data types:

* [String Literals](/design-reference/strings.md#literals) - `"Hello World"`,
* [Boolean Literals](/design-reference/booleans.md#literals) - `true`, `false`,
* [List Literals](/design-reference/lists.md#literals) - `["onion", "olives", "ham"]`,
* [Dictionary Literals](/design-reference/dictionaries.md#literals) - `{"first_name": "John", "last_name": "Snow"}`,
* [Number Literals](/design-reference/numbers.md#literals) - `42`, `42.1e2`,
* None Type - `none`.

### Operators {#operators}

Jinja has operators to call *methods*, apply *filters*, perform *tests*. More type-specific operators are also availabe:

* [String-specific Operators](/design-reference/strings.md#operators) - `"yes" in message.text`,
* [Comparison Operators](/design-reference/booleans.md#comparisons) - `slots.count > 0`,
* [Logic Operators](/design-reference/booleans.md#logic) - `slot_in_focus and message.text`,
* [List-specific Operators](/design-reference/lists.md#operators) - `entities.menu.all_values[0]`,
* [Dictionary-specific Operators](/design-reference/dictionaries.md#operators) - `"description" in slots.product`,
* [Math Operators](/design-reference/numbers.md#operators) - `slots.count + 1`.

### Methods {#methods}

You can call any of the methods defined on a variable’s type. The value returned from the invocation is used as the value of the expression. You can output this value with a print-statement. For example call the [`str.capitalize()`](/design-reference/strings.md#method-capitalize) method defined on strings (where `entities.menu.value` is a string):

```
{{ entities.menu.value.capitalize() }}
```

The [expression-statement](/design-reference/jinja.md#expression-statement) is useful to call methods that modify lists or dictionaries. It simply evaluates the expression and does nothing else.  Examples:

```
{% do slots.toppings_array.append("ketchup") %}
{% do user.car.update(color="White") %}
```

Methods are available for the following basic types:

* [String Methods](/design-reference/strings.md#methods);
* [List Methods](/design-reference/lists.md#methods);
* [Dictionary Methods](/design-reference/dictionaries.md#methods).

### Filters {#filters}

Filters are a convenient way to change variables. Filters are separated from the variable by a pipe symbol `|`.

```
{{ x|upper }}
```

Filters may have optional arguments in parentheses.

```
{{ x|replace("Hello", "Goodbye") }}
{{ x|indent(width=8) }}
```

Filters are more convenient than methods because multiple filters can be easily chained. The output of one filter is applied to the next.

```
{{ x|select|first }}
```

Filters are available for the following basic types:

* [String Filters](/design-reference/strings.md#filters);
* [List Filters](/design-reference/lists.md#filters-transform);
* [Dictionary Filters](/design-reference/dictionaries.md#filters).

### Tests {#tests}

Tests can be used to test a variable against a common property. To test a variable or expression, you add `is` plus the name of the test after the variable.

Tests can be used along with [inline If-expression](/design-reference/jinja.md#conditional-expression). For example, to output the `user.name` variable depending on whether it is defined, you can do

```
Hello, {{ user.name if user.name is defined else "dear stranger" }}!
```

where `user.name` is a variable and `defined` is a test.

Tests can accept arguments: `slots.count is divisibleby 3`.

The power of tests is revealed when used with [list selection filters](/design-reference/lists.md#filters-select) to select or reject list items based on a property defined by the test. For example, the following expression finds and returns the first element of the `numbers` list that are divisible by 3:

```
{{ numbers|select("divisibleby", 3)|first }}
```

Tests are available for the following basic types:

* [String Tests](/design-reference/strings.md#tests);
* [Boolean Tests](/design-reference/booleans.md#tests);
* [List Tests](/design-reference/lists.md#tests);
* [Dictionary Tests](/design-reference/dictionaries.md#tests);
* [Number Tests](/design-reference/numbers.md#tests).

See also: [`x is divisibleby`](/design-reference/numbers.md#test-divisibleby), [`list|select`](/design-reference/lists.md#filter-select), [`list|first`](/design-reference/lists.md#filter-first).

### Undefined Value {#undefined-value}

If variable or its attribute does not exist, you will get back an undefined value. An undefined value will **fail for every operation**, except for those listed below.

* You can use undefined value with [boolean operators](/design-reference/booleans.md#logic) and conditions. In this case the undefined value will be considered false.
* You can get any attribute on undefined variable which will also result in a undefined value.
* You can iterate over undefined value, which will result in empty sequence.


```yaml
# Suppose variable temperatureC is not defined.
{{ temperatureC }} -> UndefinedError
{% if temperatureC %} -> false
{% set slots.current_temperature = temperatureC %} -> UndefinedError (SIC!)

# Suppose slot temperatureC is not defined.
{{ slots.temperatureC }} -> UndefinedError
{% if slots.temperatureC %} -> false

# Both entity temperatureC and it's literal are not defined
{{ entities.temperatureC.literal }} -> UndefinedError
{% if entities.temperatureC.literal %} -> UndefinedError
```

You can not use undifined value in [print statement](/design-reference/jinja.md#print-statement) and [state assignments](/design-reference/jinja.md#slot-assignment). Use [`x|default`](/design-reference/lists.md#filter-default) filter to prevent undefined values in expressions.

## If Conditions {#if-conditions}

Use if statement to change the response based on a specific conditions. In its simplest form, the if statement has a single if condition. It executes a block only if that condition is true.

```yaml
response: |
    The temperature outside is {{ slots.temperatureF }}°F.
    {% if slots.temperatureF <= 32 %}
    It's very cold. Consider wearing a scarf.
    {% endif %}
    Have a nice day!
```

The example above checks whether the temperature is less than or equal to 32 degrees Fahrenheit (the freezing point of water). If it is, a recommendation is printed.

```
🤖 The temperature outside is 30°F.
   It's very cold. Consider wearing a scarf.
   Have a nice day!
```

Otherwise, no recommendation is printed, and code execution continues after the if statement’s closing tag.

```
🤖 The temperature outside is 35°F.
   Have a nice day!
```

The if statement can provide an alternative set of statements, known as an else clause, for situations when the if condition is false. These statements are indicated by the else keyword. One of these two branches is always executed.

```
{% if slots.temperatureF <= 32 %}
It's very cold. Consider wearing a scarf.
{% else %}
It's not that cold. Wear a t-shirt.
{% endif %}
```

You can chain multiple if statements together to consider additional clauses.

```
{% if slots.temperatureF <= 32 %}
It's very cold. Consider wearing a scarf.
{% elif slots.temperatureF >= 86 %}
It's really warm. Don't forget to wear sunscreen.
{% else %}
It's not that cold. Wear a t-shirt.
{% endif %}
```

The final else clause is optional, however, and can be excluded if the set of conditions doesn’t need to be complete.

```
{% if slots.temperatureF <= 32 %}
It's very cold. Consider wearing a scarf.
{% elif slots.temperatureF >= 86 %}
It's really warm. Don't forget to wear sunscreen.
{% endif %}
```

*If* can also be used as an [inline expression](/design-reference/jinja.md#conditional-expression) and for [loop filtering](/design-reference/jinja.md#for-if).

### Indirect Boolean Conversion

The boolean operators `and`, `or`, `not` and statements like `{% if ... %}` handle not only boolean type (*true*, *false*) but also numbers, strings, lists, etc.

The following values are considered **false** in boolean operations:

* constants defined to be *false*: `none` and [`false`](/design-reference/booleans.md#false);
* zero of any numeric type: [`0`](/design-reference/numbers#new-int), [`0.0`](/design-reference/numbers#new-float);
* empty sequences and collections: [`""`](/design-reference/strings.md#new-string), [`()`](/design-reference/lists.md#new-tuple), [`[]`](/design-reference/lists.md#new-list), [`{}`](/design-reference/dictionaries.md#new-dict)
* [undefined value](#undefined-value).

Everything else is considered **true**. For example,

```
{% x = "hello world" %}
{% y = "" %}

{{ x if x else "nothing" }}
-> hello world

{{ y if y else "nothing" }}
-> nothing
```

**See also**: [Python Docs](https://docs.python.org/3/reference/expressions.html#boolean-operations).

## For-In Loops

For-in loop allows template blocks to be executed repeatedly. You use the loop to iterate over lists, dictionaries, strings, as long as any objects that conform to the [iterable](#sequences-and-iterables) protocol.

### Iterating over lists

Use for-in loop to build a response text based on dynamically collected data. For example, `slots.products` variable contains a list of products that the user wants to buy

```json
["Anti-Gravity Boots", "Fountain of Youth", "Inflatable Flower Bed"]
```

This example uses a for-in loop to iterate over the list of products in the user's bag.

```yaml
Items in your bag.
{% for product in slots.products %}
    {{ product }}
{% endfor %}
->
Items in your bag.
    Anti-Gravity Boots
    Fountain of Youth
    Inflatable Flower Bed
```

It is common to use [`list|sort`](/design-reference/lists.md#filter-sort), [`list|select`](/design-reference/lists.md#filter-select) and other [transformation](/design-reference/lists.md#filters-transform) and [selection](/design-reference/lists.md#filters-select) filters to prepare lists before output.

### Iterating over dictionaries

You can use [`dict|items`](/design-reference/dictionaries.md#filter-items) filter to iterate over a dictionary to access its key-value pairs. Each item in the dictionary is returned as a (key, value) pair and you use them within the body of the for-in loop as explicitly named variables. In the template example below, the dictionary’s keys are decomposed into a variable called `city`, and the dictionary’s values are decomposed into a variable called `population`.

Let's the `slots.city_population` variable contains a dictionary in which the key is the name of the city, and the value is its population.

```json
{"Tokyo": 9273000, "Rome": 2868104, "Beijing": 20693000}
```

The dictionary can be iterated in the following way.

```
{% for city, population in slots.city_population|items %}
    {{ city }} has a population of {{ population }}.
{% endfor %}
->
Tokyo has a population of 9273000.
Rome has a population of 2868104.
Beijing has a population of 20693000.
```

The contents of a dictionary are inherently unordered, and iterating over them doesn’t guarantee the order in which they will be retrieved. If order matters, use the [`dict|dictsort`](/design-reference/dictionaries.md#filter-dictsort) filter to iterate over dictionary. If you want to iterate over dictionary keys or values separately, it is convenient to use [`dict.keys()`](/design-reference/dictionaries.md#method-keys) and [`dict.values()`](/design-reference/dictionaries.md#method-values) methods for this purpose.

### Loop filtering and else-block

You can filter the sequence during iteration, which allows you to skip items. The following example skips all the products which are not in stock.

```
Product List
{% set products = [{"id":1,"title":"olive", "in_stock":true}, {"id":2,"title":"ham"}, {"id":3,"title":"cheese", "in_stock":true}] %}
{% for product in products if product.in_stock %}
    {{ product.title }} <br />
{% endfor %}
->
olive
cheese
```

Use [selection](/design-reference/lists.md#filters-select) filters if you need more sophisticated filtering.

If no iteration took place because the sequence was empty or the filtering removed all the items from the sequence, you can render a default block by using else:

```
Product List
{% for product in products %}
    {{ product.title }}
{% else %}
    no products found
{% endfor %}
```

### Break and continue statements in the loop

You can use break statement to break out of  the loop. In the following example, there is an exit from the loop when a certain product is found.

```
{% set products = ["Anti-Gravity Boots", "Fountain of Youth", "Inflatable Flower Bed"] %}
{% for product in products %}
    {{ product }} <br/>
    {% if product == "Fountain of Youth" %}
        --------------<br/>
        Stop cycle there.
        {% break %}
    {% endif %}
{% endfor %}
->
Anti-Gravity Boots
Fountain of Youth
--------------
Stop cycle there.
```
The continue statement continues with the next iteration of the loop:

```
{% set products = ["Anti-Gravity Boots", "Fountain of Youth", "Inflatable Flower Bed"] %}
{% for product in products %}
    {% if product == "Fountain of Youth" %}
        --------------<br/>
        {{ product }} is found.<br/>
        --------------<br/>
        {% continue %}
    {% endif %}
    {{ product }} <br/>
{% endfor %}
->
Anti-Gravity Boots
--------------
Fountain of Youth is found.
--------------
Inflatable Flower Bed
```

Also, inside of a for-in block, you can access special [loop variable](/design-reference/jinja.md#loop-variable) which has many useful features.

## Local Variables

Local variables are any variables, that you define in a template. Local variables are not stored anywhere and only live while the template is being rendered. You can use local variables to store intermediate values and refer them later during the template rendering. Set a value of a local variable using the [local-assignment](/design-reference/jinja.md#local-assignment) statement.

```
{% set greeting = "Hello" %}
```

Later in your template, you can get a value of a local variable simply by using its name `greeting`.

You can use local variables to avoid code duplication. If you need to use a complex expression multiple times, you can assign its value to a local variable and use that variable instead.

```yaml
response: |
    {% set rating = slots.total_points / slots.total_voters %}
    {% if rating > 4 %}
    Great stuff!
    {% elif rating > 3 %}
    A good thing.
    {% else %}
    Bad reviews...
    {% endif %}
```

If you try to use a variable that is not assigned a value in a template before, you will get an [undefined value](#undefined-value).

### Block assignment {#block-assignment}

Block assignments are used to capture the contents of a block into a [local variable](#local-variables). Instead of using an equals sign and a value, you just write the variable name and then everything until `{% endset %}` is captured.

```
{% set reply %}
You wrote: {{ message.text }}
{% endset %}
```

The block assignment supports [filters](#filters).

```
{% set reply | truncate %}
You wrote: {{ message.text }}
{% endset %}
```

### Scoping behavior {#scoping-behavior}

Keep in mind that it is **not possible** to set variables inside a block and have them show up outside of it. This also applies to [loops](#for-in-loops). The only exception to that rule are [if statement](#if-conditions) which do not introduce a scope.

As a result the following template is not going to do what you might expect:

```
{% set iterated = false %}
{% for item in seq %}
    {{ item }}
    {% set iterated = true %}
{% endfor %}
{% if not iterated %} did not iterate {% endif %}
```

It is not possible with Jinja syntax to do this. Instead use alternative constructs like the [loop-else](/design-reference/jinja.md#for-else) block or the special [`loop`](/design-reference/jinja.md#loop-variable) variable.

```
{% for item in seq %}
    {{ item }}
{% else %}
    did not iterate
{% endfor %}
```

More complex use cases can be handled using [`namespace()`](#using-namespaces) objects which allow propagating of changes across scopes.

### Namespace object {#using-namespaces}

Use `namespace()` global function to create a new container that allows attribute assignment using the set-tag:

```
{% set ns = namespace() %}
{% set ns.foo = "bar" %}
```

The main purpose of this is to allow carrying a value from within a loop body to an outer scope. Initial values can be provided as a dict, as keyword arguments, or both.

```
{% set products = [{"id":1,"title":"olive", "quantity":5}, {"id":2,"title":"ham", "quantity":3}, {"id":3,"title":"cheese", "quantity":4}] %}
{% set ns = namespace(found=false) %}
{% for product in products %}
    {% if product.quantity < 4 %}
        {% set ns.found = true %}
    {% endif %}
        * {{ product.title }}: {{ product.quantity}} <br/>
{% endfor %}
{% if ns.found %}
    Products with quantity less than four were found.
{% else %}
    Products with quantity less than four were not found.
{% endif %}
->
* olive: 5
* ham: 3
* cheese: 4
Products with quantity less than four were found.
```

Note that the `x.y` notation in the set tag is only allowed for namespace objects; attempting to assign an attribute on any other object will raise an exception.

## Whitespace Control

Template tags `{% ... %}` introduce extra spaces and newlines into the template. We configured the Jinja Engine to

* remove block lines `{% ... %}` when rendering templates,
* preserve other spaces.

For example, the template

```
Items in your bag.

{% for product in products %}
    {{ product }}
{% endfor %}
```

will render the text like this

```
Items in your bag.

    Anti-Gravity Boots
    Fountain of Youth
    Inflatable Flower Bed
```

As you may see,

* first line "Items in your bag." and the second empty line are kept as is,
* `{% for ... %}` block line is removed,
* the spaces at the beginning of each generated product line are preserved,
* `{% endfor %}` block line is removed.

### Remove spaces around blocks

There is a common situation when you use a bunch of template blocks to build just a single line of response text. You can break such blocks into multiple template lines and remove unnecessary spaces and newlines by hand.

If you add a minus sign to the start `{%-...%}` and/or end `{%...-%}` of a block, the spaces and newlines before or after that block will be removed.

For example, let's build an address line consisting of optional parts. We have to use a conditional block for each optional part.

```
{%- if address.building %}{{ address.building }} {% endif -%}
{{ address.street }}, {{ address.city }}
{%- if address.state %}, {{ address.state }}{% endif -%}
{%- if address.country %}, {{ address.country }}{% endif %}
```

If an address variable has the following value (country is missing):

```json
{
    "street": "Landing Lange",
    "building": 4455,
    "city": "Louisville",
    "state": "KY",
}
```

In the resulting string, all template lines will be joined into one.

```
4455 Landing Lange, Louisville, KY
```

## Iterating over {#sequences-and-iterables}

### Sequences {#sequences}

A **sequence** is a generalization of a list that can be immutable. Most common sequences are

* [list](/design-reference/lists.md) - a *mutable* sequence in which you can add and remove items;
* **tuple** - an *immutable* sequence in which you cannot add new or remove existing elements;
* [string](/design-reference/strings.md) - an immutable sequence of characters.

Most often you will work with lists. Strings are used in [their own way](/design-reference/strings.md). But keep in mind, that operators, tests and filters in this sections can filter any sequence. Methods are list-only.

**See also**: [Python Sequence Types](https://docs.python.org/3/library/stdtypes.html#sequence-types-list-tuple-range).

### Iterables {#iterables}

A generalization of a sequence is an **iterable**. An iterable is just a collection where you can get each item one by one. You can't refer items in random order. All sequences are iterables. Examples of iterables that not a sequences are:

* [dictionary](/design-reference/dictionaries.md), because it is unordered;
* the results of [dict.keys()](/design-reference/dictionaries.md#method-keys), [dict.values()](/design-reference/dictionaries.md#method-values), [dict.items()](/design-reference/dictionaries.md#method-items), because they are special iterable views.

Only some of the filters (see [generators](#generators) below) and tests in this section can be applied  directly to iterables. Operators and methods cannot. But you alwas can turn an iterable into a list using [`iterable|list`](/design-reference/lists.md#filter-list) filter.

**See also**: [Python Iterator Types](https://docs.python.org/3/library/stdtypes.html#iterator-types).

### Generators {#generators}

Since you can't refer items of iterable in random order, this allows to have *lazy iterables*.

Many filters in this section (called **generators**) return special kind of iterable which is lazy and postpones calculations until they are actually needed. These are all [selectors](/design-reference/lists.md#filters-select) and almost all [transformers](/design-reference/jinja.md#filters-transform).

Generators can be freely chained together, but in the end you have to explicitly calculate the result. It's good practice to **always use [`iterable|list`](/design-reference/lists.md#filter-list) at the end of the generators chain** if you plan on getting or displaying a list as a result.

```
{% set numbers = [0, 1, 2, 3, 2, 1] %}

# bad, no actual calculations
{{ numbers|select|unique }}
-> <generator object do_unique at 0x120ec1eb0>

# good, the result is calculated
{{ numbers|select|unique|list }}
-> [1, 2, 3]
```

There are also some filters such as [`list|last`](/design-reference/lists.md#filter-last) and [`list|length`](/design-reference/lists.md#filter-length) that does not work with generators. You may want to explicitly convert it to a list too:

```
{% set numbers = [0, 3, 2, 1, 0] %}

{{ numbers|select|list|last }}
-> 1

{{ numbers|select|list|length }}
-> 3
```

**See also**: [Python Generator Types](https://docs.python.org/3/library/stdtypes.html#generator-types).
