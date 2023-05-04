# Lists

A **list** is a positionally ordered collection of items. And you can refer to any item in the list by using its index number e.g., `list[0]` and `list[1]`.

Lists are useful for storing sequential data to be iterated over. Lists might contain items of different types, but usually the items all have the same type.

## Literals

### `[x, y, z]` {#new-list}

A new `list` can be written as a list of comma-separated values (items) between square brackets.

```
{% set toppings_array = ["onion", "olives", "ham"] %}
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#literals).

### `(x, y, z)` {#new-tuple}

Tuples are like lists that cannot be modified ("immutable"). If a tuple only has one item, it must be followed by a comma (`(x,)`).

```
{% set toppings_array = ("onion", "olives", "ham") %}
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#literals).

## Constructors

### `iterable|list` {#filter-list}

Convert an iterable value into a list.

It's good practice to always use `iterable|list` at the end of the filter chain if you plan on getting or displaying a list as a result.

```
{% set numbers = [0, 1, 2, 3, 2, 1] %}

# bad, no actual calculations
{{ numbers|select|unique }}
-> <generator object do_unique at 0x120ec1eb0>

# good, the result is calculated
{{ numbers|select|unique|list }}
-> [1, 2, 3]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.list), [Sequences and Iterables](#sequences-and-iterables).

### `range`

Return a list containing an arithmetic progression of integers.

#### Parameters

* `start` - First element of a list (default: 0).
* `stop*` - Last element of a list (exclusive).
* `step` - An increment (decrement) for progression.

#### Examples

`range(i, j)` returns `[i, i+1, i+2, ..., j-1]`; start (!) defaults to 0.

`range(4)` and `range(0, 4, 1)` return `[0, 1, 2, 3]`. The end point is omitted! These are exactly the valid indices for a list of 4 elements.

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-globals.range).

## Operators

### `x in list` {#operator-in}

Return true if the left value is contained in the right list.

```
{% set toppings_array = ["onion", "olives", "ham"] %}

{{ "ham" in toppings_array }}
-> true # because the array contains the element "ham"
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#other-operators).

### `list[i]` {#operator-get}

Return the list item by its index. The list index starts at 0, not 1.

```
{% set mylist = [ "one", "two" ] %}

The first item in the array is {{ mylist[0] }}.
-> "The first item in the array is one."
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#other-operators).

### `list1 + list2` {#operator-add}

Concatenate lists.

```
{% set list1 = [ "one", "two" ] %}
{% set list2 = [ "three", "four" ] %}

{{ list1 + list2 }}
-> [ "one", "two", "three", "four" ]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#math).

## Tests

### `x is in list` {#test-in}

Check if `x` is in `list`. Typicallty you need to use operator [`x in list`](#operator-in) instead of a test. Use a test when you need filter one list based on values in another list.

```
{% set desired = ["onion", "olives", "ham"] %}
{% set forbidden = ["mushroom", "onion"] %}

{{ desired|reject("in", forbidden)|list }}
-> ["olives", "ham"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.in), [`list|select`](#filter-select), [`list|selectattr`](#filter-selectattr), [`list|reject`](#filter-reject), [`list|rejectattr`](#filter-rejectattr).

### `x is sequence` {#test-sequence}

Return true if the variable is a [sequence](#sequences-and-iterables).

Let's say we got `x` from an external source and don't know what it is.

```
{% if x is sequence %}
	X has a length: {{ x|length }}
{% endif %}
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.sequence).

### `x is iterable` {#test-iterable}

Check if it’s possible to [iterate](#sequences-and-iterables) over an object.

Let's say we got `x` from an external source and don't know what it is.

```
{% if x is iterable %}
	X can be reversed {{ x|reverse|list }}
{% endif %}
```
**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.iterable).

## Filters: Transform {#filters-transform}

### `list|batch` {#filter-batch}

A filter that batches items. It works pretty much like [`list|slice`](#filter-slice) just the other way round. It returns a list of lists with the given number of items. This filter is a [generator](/design-guides/templates.md#generators).

#### Parameters

* `linecount*` - A number of items in the inner list.
* `fill_with` - A value to fill up missing items.

#### Examples

This example renders the `flags` list as a table with 3 columns.

```
{% set flags = [ "🇺🇸", "🇬🇧", "🇪🇸", "🇲🇽", "🇵🇹", "🇧🇷"] %}

{% for row in flags|batch(3) %}
  {{ row|join(" ") }}
{% endfor %}
```

The number of **columns** (3) is fixed, the number of rows will increase as the list of `flags` expands.

```
🇺🇸 🇬🇧 🇪🇸
🇲🇽 🇵🇹 🇧🇷
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.batch), [`list|slice`](#filter-slice).

### `list|slice` {#filter-slice}

Slice a list and return a list of lists containing those items.  This filter is a [generator](/design-guides/templates.md#generators).

#### Parameters

* `slices*` - A number of slices.
* `fill_with` - A value to fill missing items on the last iteration.

#### Examples

This example renders the `flags` list as a table with 3 rows.

```
{% set flags = [ "🇺🇸", "🇬🇧", "🇪🇸", "🇲🇽", "🇵🇹", "🇧🇷"] %}

{% for row in flags|slice(3) %}
  {{ row|join(" ") }}
{% endfor %}
```

The number of **rows** (3) is fixed, the number of columns will increase as the list of `flags` expands.

```
🇺🇸 🇬🇧
🇪🇸 🇲🇽
🇵🇹 🇧🇷
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.slice), [`list|batch`](#filter-batch), [`list|join`](#filter-join).

### `list|groupby` {#filter-groupby}

Group a sequence of objects by an attribute. The values are sorted first so only one group is returned for each unique value. This filter is a [generator](/design-guides/templates.md#generators).

#### Parameters

* `attribute*` - An object attribute to group by. The attribute can use dot notation for nested access, like "address.city".
* `default` - A value to use if an object in the list does not have the given attribute.
* `case_sensitive` - Treat upper and lower case separately, when sorting and grouping strings (default: false).

#### Examples

For example, a list of User objects with a city attribute can be rendered in groups.

```
{% set users = [
	{"name": "John", "city": "CA"},
	{"name": "Bob", "city": "CA"},
	{"name": "Steve", "city": "NY"}
] %}

{% for city, items in users|groupby("city") %}
    {{ city }}: {{ items|join(", ", attribute="name") }}.
{% endfor %}
```

The following string will be rendered:

```
CA: John, Bob.
NY: Steve.
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.groupby), [`list|join`](#filter-join).

### `list|map` {#filter-map}

Applies a filter on a sequence of objects or looks up an attribute. This is useful when dealing with lists of objects but you are really only interested in a certain value of it. This filter is a [generator](/design-guides/templates.md#generators).

#### Parameters

* `filter` - A filter to apply.
* `attribute` - Appy filter to a cetain object attribute.
* `default` - A value to use if an object in the list does not have the given attribute.

#### Examples

The basic usage is mapping on an attribute. Imagine you have a list of users but you are only interested in a list of their name:

```
{% set users = [{"name": "John"}, {"name": "Bob"}, {"name": "Steve"}] %}

{{ users|map(attribute="name")|list }}
-> ["John", "Bob", "Steve"]
```

You can specify a default value to use if an object in the list does not have the given attribute.

```
{% set users = [{"name": "John"}, {"name": "Bob"}, {}] %}

{{ users|map(attribute="name", default="Anonymous")|list }}
-> ["John", "Bob", "Anonymous"]
```

Alternatively you can let it invoke a filter by passing the name of the filter and the arguments afterwards. A good example would be applying a text conversion filter on a list:

```
{% set usernames = ["John", "Bob", "Steve"] %}

{{ usernames|map("lower")|list }}
-> ["john", "bob", "steve"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.map), [`iterable|list`](#filter-list).

### `list|reverse` {#filter-reverse}

Iterates over list the other way round.

```
{% set toppings_array = ["onion", "olives", "ham"] %}

{{ toppings_array|reverse|list }}.
-> ["ham", "olives", "onion"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.reverse), [`list|sort`](#filter-sort).

### `list|sort` {#filter-sort}

Sort a list.  This filter is a [generator](/design-guides/templates.md#generators).

#### Parameters

* `reverse` - Sort descending instead of ascending.
* `case_sensitive` - When sorting strings, sort upper and lower case separately.
* `attribute` - When sorting objects or dicts, an attribute or key to sort by. Can use dot notation like "address.city". Can be a list of attributes like "age,name".

#### Examples

```
{% set cities = ["Tokyo", "Rome", "Beijing", "Paris"] %}

{{ cities|sort|list }}
-> ["Beijing", "Paris", "Rome", "Tokyo"]
```

The sort is stable, it does not change the relative order of elements that compare equal. This makes it is possible to chain sorts on different attributes and ordering.

```
{% set users = [
	{"name": "Pit", "age": 24},
	{"name": "John", "age": 49},
	{"name": "Bob", "age": 24}
] %}

{{ users|sort(attribute="name")|sort(reverse=true, attribute="age")|list }}
-> [
    {"name": "John", "age": 49},
    {"name": "Bob", "age": 24},
    {"name": "Pit", "age": 24}
]
```

As a shortcut to chaining when the direction is the same for all attributes, pass a comma separate list of attributes.

```
{{ users|sort(attribute="name,age")|list }}
-> [
    {"name": "Bob", "age": 24},
    {"name": "John", "age": 49},
    {"name": "Pit", "age": 24}
]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.sort), [`list|reverse`](#filter-reverse), [`iterable|list`](#filter-list).

### `list|unique` {#filter-unique}

Returns a list of unique items from the given iterable. The unique items are yielded in the same order as their first occurrence in the list passed to the filter. This filter is a [generator](/design-guides/templates.md#generators).

#### Parameters

* `case_sensitive` – Treat upper and lower case strings as distinct.
* `attribute` – Filter objects with unique values for this attribute.

#### Examples

```
{% set cities = ["Tokyo", "Beijing", "Paris", "beijing"] %}

{{ cities|unique|list }}
-> ["Tokyo", "Beijing", "Paris"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.unique), [`iterable|list`](#filter-list).

## Filters: Reduce {#filters-reduce}

### `list|first` {#filter-first}

Return the first item of a sequence.

#### Examples

```
{% set toppings_array = ["onion", "olives", "ham"] %}

The first topping is {{ toppings_array|first }}.
-> The first topping is onion.
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.first), [`list|last`](#filter-last).


### `list|last` {#filter-last}

Return the last item of a sequence.

```
{% set toppings_array = ["onion", "olives", "ham"] %}

The last topping is {{ toppings_array|last }}.
-> The last topping is ham.
```

**Note: Does not work with [generators](/design-guides/templates.md#generators).** You may want to explicitly convert it to a list:

```
{% set numbers = [0, 3, 2, 1, 0] %}

{{ numbers|select|list|last }}
-> 1
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.last), [`list|first`](#filter-first), [`iterable|list`](#filter-list), [Generators and Lazy Iterables](/design-guides/templates.md#generators).

### `list|join` {#filter-join}

Return a string which is the concatenation of the strings in the list.

#### Parameters

* `d` - A separator between elements. Default: empty string.
* `attribute` - Join object attributes.

#### Examples

```
{% set toppings_array = ["onion", "olives", "ham"] %}

So, you'd like {{ toppings_array|join(", ") }}.
-> So, you'd like onion, olives, ham.
```

It is also possible to join certain attributes of an objects:

```
{% set users = [{"name": "John"}, {"name": "Bob"}, {"name": "Steve"}] %}

Our users: {{ users|join(', ', attribute='name') }}.
-> Our users: John, Bob, Steve.
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.join).


### `list|length` {#filter-length}

Return the number of items in a sequence. **Alias:** `count`.

```
{% set toppings_array = ["onion", "olives", "ham"] %}

The number of toppings is {{ toppings_array|length }}.
-> The number of toppings is 3.
```

**Note: Does not work with [generators](/design-guides/templates.md#generators).** You may want to explicitly convert it to a list:

```
{% set numbers = [0, 3, 2, 1, 0] %}

{{ numbers|select|list|length }}
-> 3
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.length), [`iterable|list`](#filter-list), [Sequences and Iterables](#sequences-and-iterables).

### `list|max` {#filter-max}

Return the largest item from the lists.

#### Parameters

* `case_sensitive` – Treat upper and lower case strings as distinct.
* `attribute` – Get the object with the max value of this attribute.

#### Examples

```
{{ [1, 2, 3]|max }}
-> 3
```

```
{% set cities = [
   {"name": "Tokyo", "population": 9273000},
   {"name": "Rome", "population": 2868104},
   {"name": "Beijing", "population": 20693000},
   {"name": "Paris", "population": 2241346}
] %}

{{ cities|max(attribute="population") }}
-> {"name": "Beijing", "population": 20693000}
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.max), [`list|min`](#filter-min), [`list|sort`](#filter-sort).

### `list|min` {#filter-min}

Return the smallest item from the lists.

#### Parameters

* `case_sensitive` – Treat upper and lower case strings as distinct.
* `attribute` – Get the object with the min value of this attribute.

#### Examples

```
{{ [1, 2, 3]|min }}
-> 1
```

```
{% set cities = [
   {"name": "Tokyo", "population": 9273000},
   {"name": "Rome", "population": 2868104},
   {"name": "Beijing", "population": 20693000},
   {"name": "Paris", "population": 2241346}
] %}

{{ cities|min(attribute="population") }}
-> {"name": "Paris", "population": 2241346}
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.min), [`list|max`](#filter-max), [`list|sort`](#filter-sort).

### `list|random` {#filter-random}

Return a random item from the list.

Examples:

```
{% set toppings_array = ["onion", "olives", "ham"] %}

{{ toppings_array|random }} is a great choice!
-> "ham is a great choice!"
-> or "onion is a great choice!"
-> or "olives is a great choice!"
```

See also: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.random).

### `list|sum` {#filter-sum}

Returns the sum of a list of numbers plus the value of parameter `start` (which defaults to 0). When the list is empty it returns start.

#### Parameters

* `start` - A number to add to the returned sum.
* `attribute` - Sum up only certain attribute.

#### Examples

```
{% set items = [
	{"name": "Anti-Gravity Boots", "price": 9},
	{"name": "Fountain of Youth", "price": 89},
	{"name": "Inflatable Flower Bed", "price": 24},
] %}

Total: ${{ items|sum(attribute="price") }}
-> Total: $122
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.sum).

## Filters: Select {#filters-select}

### `list|reject` {#filter-reject}

Filters a list of objects by applying a test to each item, and rejecting the item with the test succeeding. If no test is specified, each item will be evaluated as a boolean. This filter is a [generator](/design-guides/templates.md#generators).

#### Parameters

* `test` – A test to apply to each element of the list.
* `value` – A value to compare with each element of the list.

#### Examples

```
{% set numbers = [0, 1, 2, 3, 4, 5] %}

{{ numbers|reject|list }}
-> [0]

{{ numbers|reject("odd")|list }}
-> [0, 2, 4]

{{ numbers|reject("lessthan", 2)|list }}
-> [2, 3, 4, 5]
```

```
{% set strings = ["", "one", "two", "three"] %}

{{ strings|reject|list }}
-> [""] # empty string evaluated as false

{{ strings|reject("in", ["two", "four"])|list }}
-> ["", "one", "three"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.reject), [`list|select`](#filter-select), [`list|selectattr`](#filter-selectattr), [`list|rejectattr`](#filter-rejectattr), [`iterable|list`](#filter-list).

### `list|rejectattr` {#filter-rejectattr}

Filters a list of objects by applying a test to the specified attribute of each object, and rejecting the objects with the test succeeding. If no test is specified, the attribute’s value will be evaluated as a boolean. This filter is a [generator](/design-guides/templates.md#generators).

#### Parameters

* `attribute*` – Reject objects with a successful test of this attribute.
* `test` – A test to apply to each object attribute of the list.
* `value` – A value to compare with each object attribute of the list.

#### Examples

```
{% set cities = [
   {"name": "Tokyo", "population": 9273000},
   {"name": "Rome", "population": 2868104},
   {"name": "Beijing", "population": 20693000},
   {"name": "Paris", "population": 2241346}
] %}

{{ cities|rejectattr("population", ">", 5000000)|list }}
-> [
	{"name": "Rome", "population": 2868104},
	{"name": "Paris", "population": 2241346}
]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.rejectattr), [`list|select`](#filter-select), [`list|selectattr`](#filter-selectattr), [`list|reject`](#filter-reject), [`iterable|list`](#filter-list).


### `list|select` {#filter-select}

Filters a list of values by applying a [test](/design-reference/jinja.md#tests) to each value, and only selecting the values with the test succeeding. This filter is a [generator](/design-guides/templates.md#generators).

If no test is specified, each value will be evaluated as a boolean.

#### Parameters

* `test` – A test to apply to each element of the list.
* `value` – A value to compare with each element of the list.

#### Examples

```
{% set numbers = [0, 1, 2, 3, 4, 5] %}

{{ numbers|select|list }}
-> [1, 2, 3, 4, 5] # 0 number evaluated as false

{{ numbers|select("odd")|list }}
-> [1, 3, 5]

{{ numbers|select("lessthan", 3)|list }}
-> [0, 1, 2]
```

```
{% set strings = ["", "one", "two", "three"] %}

{{ strings|select|list }}
-> ["one", "two", "three"] # empty string evaluated as false

{{ strings|select("in", ["two", "four"])|list }}
-> ["two"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.select), [Jinja Tests](https://jinja.palletsprojects.com/en/3.1.x/templates/#list-of-builtin-tests), [`list|selectattr`](#filter-selectattr), [`list|reject`](#filter-reject), [`list|rejectattr`](#filter-rejectattr), [`iterable|list`](#filter-list).

### `list|selectattr` {#filter-selectattr}

Filters a list of objects by applying a test to the specified attribute of each object, and only selecting the objects with the test succeeding. If no test is specified, the attribute’s value will be evaluated as a boolean. This filter is a [generator](/design-guides/templates.md#generators).

#### Parameters

* `attribute*` – Select objects with a successful test of this attribute.
* `test` – A test to apply to each object attribute of the list.
* `value` – A value to compare with each object attribute of the list.

#### Examples

The following `cities` variable contains a list of objects. Each object contains a name and population property.

```
{% set cities = [
   {"name": "Tokyo", "population": 9273000},
   {"name": "Rome", "population": 2868104},
   {"name": "Beijing", "population": 20693000},
   {"name": "Paris", "population": 2241346}
] %}
```

The expression filters the `cities` list to include only cities with a population of over 5 million:

```
{{ cities|selectattr("population", ">", 5000000)|list }}
-> [
   {"name": "Tokyo", "population": 9273000},
   {"name": "Beijing", "population": 20693000},
]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.selectattr), [Jinja Tests](https://jinja.palletsprojects.com/en/3.1.x/templates/#list-of-builtin-tests), [`list|select`](#filter-select), [`list|reject`](#filter-reject), [`list|rejectattr`](#filter-rejectattr), [`iterable|list`](#filter-list).

## Methods

### `list.append(x)` {#method-append}

Append a new value to the list.

```
{% set toppings_array = ["onion", "olives"] %}

{% do toppings_array.append("ketchup") %}
```

The list is updated to include new value:

```
toppings_array == ["onion", "olives", "ketchup"]
```

### `list.extend(list)` {#method-extend}

Append one list to another.

```
{% set toppings_array = ["onion", "olives"] %}
{% set more_toppings = ["mushroom","pepperoni"] %}

{% do toppings_array.extend(more_toppings) %}
```

The first list is updated to include the values from the second list:

```
toppings_array == ["onion", "olives", "mushroom", "pepperoni"]
```

### `list.clear()` {#method-clear}

Clear all values from the list.

```
{% do toppings_array.clear() %}
```

If you subsequently reference the `toppings_array` variable, it returns `[]` only.

### `list.index(x)` {#method-index}

Return the index number of the element in the list that matches the value you specify as a parameter. The value must be an exact match and is case sensitive.

```
{% set numbers = [8, 9, 10] %}

{{ numbers.index(10) }}
-> 2

```

```
{% set strings = ["Mary", "Lamb", "School"] %}

{{ strings.index("Mary") }}
-> 0

```

### `list.pop([i])` {#method-pop}

Remove the item at the given position in the list, and return it. If no index is specified, `list.pop()` removes and returns the last item in the list.

```
{% set toppings_array = ["onion", "olives", "ham"] %}

{% do toppings_array.pop(0) %}
```

Result:

```
toppings_array == ["olives", "ham"]
```

### `list.remove(x)` {#method-remove}

Remove the first item from the list whose value is equal to x. It raises an error if there is no such item.

```
{% set toppings_array = ["onion", "olives", "ham"] %}

{% do toppings_array.remove("olives") %}
```

Result:

```
toppings_array == ["onion", "ham"]
```
