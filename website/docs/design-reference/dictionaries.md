# Dictionaries

A dictionary (**dict**) is a collection of `key: value` pairs. Keys must be unique and always have exactly one value. Dictionaries are unordered, use [`dict|dictsort`](#filter-dictsort) if you need an order.

It is convenient to use dictionaries in templates to implement simple business logic.

## Literals

### `{key: value}` {#new-dict}

A new dictionary can be written as a comma-separated list of `key: value` pairs within braces.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#literals).

## Constructors

### `dict`

An alternative way to create a dict.

```
{% set user = dict(first_name="John", last_name="Snow") %}

{{ user }}
-> {"first_name": "John", "last_name": "Snow"}
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-globals.dict).

## Operators

### `key in dict`

Return true if the *key* is contained in the *dict*.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ "first_name" in user }}
-> true
```

Returns true because the user object contains the property first_name.

### `key not in dict`

Return true if the *key* is **not** contained in the *dict*.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ "middle_name" not in user }}
-> true
```

### `dict[key]` {#operator-dict-access}

Return the item of *dict* with key *key*.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ user["first_name"] }}
-> John
```

### `dict.key` {#operator-attr-access}

A convenient alternative to [`dict[key]`](#operator-dict-access).

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ user.first_name }}
-> John
```

## Tests

### `x is mapping` {#test-mapping}

Return true if the *x* is a mapping (dict etc.).

```
{% if x is mapping %}
	X got values: {{ x.values()|list }}
{% endif %}
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-tests.mapping), [`dict.values()`](#method-values), [`iterable|list`](lists.md#filter-list).

## Filters

### `dict|dictsort` {#filter-dictsort}

Sort a dict and return an iterable of `(key, value)` pairs. Python dicts may not be in the order you want to display them in, so sort them first.  This filter is a [generator](lists.md#generators).

#### Parametes

* `case_sensitive` - When sorting strings, sort upper and lower case separately.
* `by` - Sort by *"key"* or *"value"* (default=*"key"*).
* `reverse` - Sort descending instead of ascending.

#### Examples

The following `city_population` variable contains a dictionary in which the key is the name of the city, and the value is its population.

```
{% set city_population = {
   "Tokyo": 9273000,
   "Rome": 2868104,
   "Beijing": 20693000,
   "Paris": 2241346
} %}
```

Sort by city name:

```
{% for city, population in city_population|dictsort %}
    {{ city }} has a population of {{ population }}.
{% endfor %}
->
Beijing has a population of 20693000.
Paris has a population of 2241346.
Rome has a population of 2868104.
Tokyo has a population of 9273000.
```

Sort by city population:

```
{% for city, population in city_population|dictsort(by="value") %}
    {{ city }} has a population of {{ population }}.
{% endfor %}
->
Paris has a population of 2241346.
Rome has a population of 2868104.
Tokyo has a population of 9273000.
Beijing has a population of 20693000.
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.dictsort), [`list|sort`](lists.md#filter-sort).

### `dict|items` {#filter-items}

Return an iterable over the `(key, value)` items of a dict. This filter is a [generator](lists.md#generators).

`dict|items` is the same as [`dict.items()`](#method-items), except if dict is `undefined` an empty iterator is returned.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ user|items|list }}
-> [("first_name", "John"), ("last_name", "Snow")]
```

It is possible to iterate over dictionary.

```
User Info:
{% for key, value in user|items %}
    {{ key }}: {{ value }}
{% endfor %}
->
User Info:
    first_name: John
    last_name: Snow
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.items), [Sequences and Iterables](lists.md#sequences-and-iterables), [`dict.items()`](#method-items), [`dict.values()`](#method-values), [`dict.keys()`](#method-keys), [`iterable|list`](lists.md#filter-list).

### `dict|length` {#filter-length}

Return the number of items in the dictionary.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ user|length }}
-> 2
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.length).

### `dict|list` {#filter-list}

Return a list of all the keys used in the dictionary.


```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ user|list }}
-> ["first_name", "last_name"]
```

**See also**: [Jinja Docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.list), [`dict.keys()`](#method-keys), [`dict.values()`](#method-values).

## Methods

### `dict.clear()` {#method-clear}

Remove all items from the dictionary.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{% do user.clear() %}
```

If you subsequently reference the `user` variable, it returns `{}` only.

```
{{ user }}
-> {}
```

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#dict.clear).

### `dict.items()` {#method-items}

Return an [iterable](lists.md#sequences-and-iterables) of the dictionary’s items (`(key, value)` pairs). You may want to explicitly convert it to a list.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ user.items()|list }}
-> [("first_name", "John"), ("last_name", "Snow")]
```

It is possible to iterate over dictionary.

```
User Info:
{% for key, value in user.items() %}
    {{ key }}: {{ value }}
{% endfor %}
->
User Info:
    first_name: John
    last_name: Snow
```

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#dict.items), [Sequences and Iterables](lists.md#sequences-and-iterables), [`dict.values()`](#method-values), [`dict.keys()`](#method-keys), [`dict|items`](#filter-items), [`iterable|list`](lists.md#filter-list).

### `dict.keys()` {#method-keys}

Return an [iterable](lists.md#sequences-and-iterables) of the dictionary’s keys. You may want to explicitly convert it to a list.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ user.keys()|list }}
-> ["first_name", "last_name"]
```

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#dict.keys), [Sequences and Iterables](lists.md#sequences-and-iterables), [`dict.values()`](#method-values), [`dict.items()`](#method-items), [`dict|list`](#filter-list), [`iterable|list`](lists.md#filter-list).

### `dict.pop(key, ...)` {#method-pop}

`dict.pop(key[, default])`

If *key* is in the dictionary, remove it and return its value, else return *default*. If *default* is not given and *key* is not in the dictionary, an error is raised.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{% do user.pop("last_name") %}
```

If you subsequently reference the `user` variable, it returns only

```
{{ user }}
-> {"first_name": "John"}
```

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#dict.pop).

### `dict.setdefault(key, ...)` {#method-setdefault}

`dict.setdefault(key[, default])`

If *key* is in the dictionary, return its value. If not, insert *key* with a value of *default* and return *default*. *default* defaults to `none`.

```
{% set pizza_order = {} %}

{% do pizza_order.setdefault('toppings', []).append("onion") %}
{{ pizza_order }}
-> {"toppings": ["onion"]}
```

todo: need more clear and useful example.

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#dict.setdefault).

### `dict.update(other)` {#method-update}

Update the dictionary with the key/value pairs from other, overwriting existing keys. Return `none`.

```
{% set car = {"brand": "Ford", "model": "Mustang"} %}
{% set color_info = {"color": "White"} %}

{% do car.update(color_info) %}
```

A convenient alternative is

```
{% do car.update(color="White") %}
```

The updated dict will look like

```
{{ car }}
-> {"brand": "Ford", "model": "Mustang", "color": "White"}
```

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#dict.update).

### `dict.values()` {#method-values}

Return an [iterable](lists.md#sequences-and-iterables) of the dictionary’s values. You may want to explicitly convert it to a list.

```
{% set user = {"first_name": "John", "last_name": "Snow"} %}

{{ user.values()|list }}
-> ["John", "Snow"]
```

**See also**: [Python Docs](https://docs.python.org/3/library/stdtypes.html#dict.keys), [Sequences and Iterables](lists.md#sequences-and-iterables), [`dict.keys()`](#method-keys), [`dict.items()`](#method-items), [`iterable|list`](lists.md#filter-list).
