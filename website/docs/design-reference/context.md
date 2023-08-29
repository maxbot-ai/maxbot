# Context {#context-reference}

Describes the variable types provided by the bot that you use in expressions and templates.

## `Context`

Attributes of this class are context and special variables.

| Name         | Type                              | Description |
| -----------  | ----------- 	                     | ----------- |
| `intents`    | [IntentsResult](#intentsresult)   | One or more intents that were recognized in user input. |
| `entities`   | [EntitiesResult](#entitiesresult) | One or more entities that were recognized in user input. |
| `user`       | [Dictionary](/design-reference/dictionaries.md) | User state variables that live forever. |
| `slots`      | [Dictionary](/design-reference/dictionaries.md) | Slot state variables that live during discussing a topic. |
| `message`    | [MessageSchema](/design-reference/protocol.md#messageschema) | A message processed by the bot. |
| `dialog`     | [DialogSchema](/design-reference/protocol.md#dialogschema)  | General information that does not change or rarely changes during a conversation. |
| `rpc`        | [RpcContext](#rpccontext) | The context of the RPC request processed by the bot. |
| `utc_time`   | [datetime](https://docs.python.org/3/library/datetime.html#datetime-objects) | Current UTC date and time. |

Special variables related to the [digression](/design-guides/digressions.md) flow.

| Name         | Type                                    | Description |
| -----------  | ----------- 	                           | ----------- |
| `digressing` | [Boolean](/design-reference/booleans.md) | The variable is set to true during the digression. You can check it to [prevent digressions](/design-guides/digressions.md#check-digressing) into a particular root node or execute some commands. |
| `returning`  | [Boolean](/design-reference/booleans.md) | The variable is set to true when returning after digression. Use it to add [custom return message](/design-guides/digressions.md#custom-return-message) to node response. |

The following special variables can help you check and set values in slots.

| Name             | Type        | Description |
| -----------      | ----------- | ----------- |
| `current_value`  | JSON Type   | Current value of the context variable for this slot. |
| `previous_value` | JSON Type   | Previous value of the context variable for this slot. |
| `slot_in_focus`  | [Boolean](/design-reference/booleans.md) | Forces the slot `check_for` expression to be applied to the currently prompted slot only. |

FIXME: The `slot_in_focus` property always evaluates to a boolean (true or false) value. Only include it in a condition for which you want a boolean result. Do not use it in slot conditions that check for an entity type and then save the entity value, for example.

## Intents

### `RecognizedIntent`

An intent recognized from the user utterance.

Examples:

```yaml
condition: intents.top.name.startswith("buy_")
# ...
```

```yaml
condition: intents.my_intent and intents.my_intent.confidence > 0.7
# ...
```

| Name         | Type                                  | Description |
| -----------  | ----------- 	                         | ----------- |
| `name`       | [String](/design-reference/strings.md) | The name of the intent. |
| `confidence` | [Float](/design-reference/numbers.md)  | A rating provided by NLU model that shows how confident it is that an intent is the correct intent. Should be in the range 0.0 < confidence <= 1.0. |


### `IntentsResult`

The result of intent recognition in the user utterance.

#### Attributes

| Name         | Type                                  | Description |
| -----------  | ----------- 	                         | ----------- |
| `top `       | [RecognizedIntent](#recognizedintent) | A recognized intent with the highest confidence score above a certain threshold defined by the NLU model. |
| `ranking`    | [Tuple](/design-reference/lists.md)[[RecognizedIntent](#recognizedintent)] | All recognized intents are sorted in descending order of confidence score. |
| `__getattr__` | [RecognizedIntent](#recognizedintent) | A convenient way to get intent (see example above). |
| `irrelevant` | [Boolean](/design-reference/booleans.md) | The condition will evaluate to true if the user sends a text message and the bot could not recognize any intent in that message. |

#### Examples

* You can use expressions like `intents.top.name == 'reservation'` to check if the user input is asking to make a reservation. But there is a more convenient equivalent expression `intents.reservation`. If the reservation intent is a top intent, this expression will return intent information and evaluate to true. Otherwise the `intents.reservation` expression will evaluate to false.

	```yaml
	condition: intents.reservation
	# ...
	```

* You can find any recognized intents with intent names that start with 'ask_', using a syntax like this.

	```yaml
	- condition: intents.top and intents.top.name.startswith('ask_')
	  response: |
        ...
	```
    First, we check that `intents.top` is defined because it is only present when some intent is recognized from user input.

* You can check if intent disambiguation is required as follows.

	```yaml
	condition: intents.ranking|selectattr("confidence", ">", 0.3)|list|length > 1
	# ...
	```

* You can use `intents.irrelevant` condition as an anything else condition at the end of the node list.

## Entities

### `RecognizedEntity`

An entity recognized from the user utterance.

| Name         | Type                                  | Description |
| -----------  | ----------- 	                         | ----------- |
| `name`       | [String](/design-reference/strings.md) | The name of the entity. |
| `value`      | Union[[String](/design-reference/strings.md), [Number](/design-reference/numbers.md)] | The value of the entity. |
| `literal`    | [String](/design-reference/strings.md) | How exactly the entity was present in the utterance. |
| `start_char` | [Integer](/design-reference/numbers.md) | An index of the first char of the literal value in the utterance. |
| `end_char ` | [Integer](/design-reference/numbers.md) | An index of the last char of the literal value in the utterance. |

### `EntitiesProxy`

All entities with the same name recognized from the user utterance.

| Name          | Type                                  | Description |
| -----------   | ----------- 	                         | ----------- |
| `all_objects` | [Tuple](/design-reference/lists.md)[[RecognizedEntity](#recognizedentity)] | A list of all entities with the same name. |
| `all_values ` | Union[[Tuple](/design-reference/lists.md)[[String](/design-reference/strings.md)], [Tuple](/design-reference/lists.md)[[Number](/design-reference/numbers.md)]] | The values of all entities. |
| `__getattr__` | Any | Access the proxied entities in a convenient way. See <ul><li>[Access the first entity](#access-the-first-entity)</li><li>[Checking a value presence](#checking-a-value-presence)</li></ul> |

### `EntitiesResult`

The result of entity recognition in the user utterance.

#### Attributes

| Name          | Type                                  | Description |
| -----------   | ----------- 	                         | ----------- |
| `proxies`     | [Dictionary](/design-reference/dictionaries.md)[[String](/design-reference/strings.md), [EntitiesProxy](#entitiesproxy)] | Maps entity names to proxies with corresponding entities. |
| `all_objects` | [Tuple](/design-reference/lists.md)[[RecognizedEntity](#recognizedentity)] | A tuple of all recognized entities in the order they are appear in the utterance. See [Access to Multiple Entities](#access-to-multiple-entities). |
| `__getattr__` | [EntitiesProxy](#entitiesproxy) | Convenient access to entity proxy with the entities that matched the name (see examples below). |

#### Examples

Simply use `entities.menu` instead of `entities.proxies['menu']`

```yaml
check_for: entities.menu
# ...
```

### Capturing entities

#### Capturing an entity mention

To store the value of an entity in a context variable, use this syntax

```
{% set slots.place = entities.place.value %}
```

For example, the user input is, "I want to go to Paris". If your `entities.place` recognizes "Paris", then the bot saves "Paris" in the `slots.place` variable.

#### Capturing literal representation

Frequently you need to obtain more information than just whether the regular expression matched or not. You can capture the exact span of text from the user input that matches the regular expression.

For example, the user input is "I want to cancel my order AB12345". Your regexp entity `entities.order_number` recognizes the '[A-Z]{2}\d{5}' order number format. By configuring the slot variable to store `entities.order_number.literal`, you indicate that you want to store the part of the input that matched the pattern.

```yaml
- condition: intents.cancel_order and entities.order_number
  response: |
    OK. The order {{ entities.order_number.literal }} is canceled.
```

The node response includes a literal representation of the order number provided by the user.

```
🧑 I want to cancel my order AB12345.
🤖 OK. The order AB12345 is canceled.
```

If you omit the `.literal` property from the value expression, then the entity value name that you specified for the regexp is returned instead of the segment of user input that matched the pattern.

#### Capturing regex groups

Any part of a regular expression inside a pair of normal parentheses will be captured as a group.

TODO: waiting for implementation, usage example, named groups

See [Python Regex Gouping](https://docs.python.org/3/howto/regex.html#grouping) to get more grouping theory and examples.

### Multiple entity values

Multiple values can be recognized in the user input for the same entity.
When you refer an entity by name, e.g. `entities.menu`, you actually get a proxy object that contains a list of recognized entities with the same name and supports default access to the 1st element.

#### Access to multiple entities

You can access the mentioned list using the `entities.menu.all_objects` expression.

For example, a user submits

```
🧑 Are there any specials today for vegan or maybe some bakery offerings?
```

The "vegetarian" and "cake" values are detected and are represented in the list that is returned as follows:

* `entities.menu.all_objects[0].value == "vegetarian"`
* `entities.menu.all_objects[1].value == "cake"`

The order of entities in the list that is returned matches the order in which they are mentioned in the user input.

Jinja Expressions contains a powerful [libray of filters](https://jinja.palletsprojects.com/en/3.1.x/templates/#list-of-builtin-filters) to work with lists. For example, to capture the literal values for multiple entity mentions, use the [map](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.map) filter:

```
entities.menu.all_objects|map(attribute='literal')|list
-> ["vegan", "bakery offerings"]
```

Entities proxy provides shorthand syntax fo the most widely used cases.

#### Access the first entity

The `entities.menu` proxy provide convenient access to the properties of the 1st recognized entity. For example,

* `entities.menu.value` is a shorthand syntax for the `entities.menu.all_objects[0].value`,
* `entities.menu.literal` is a shorthand syntax for the `entities.menu.all_objects[0].literal`.

#### Access all values

To get a list of values of an entity in the user input, use expression `entities.menu.all_values`. Refer to the list in a dialog response:

```
You asked about these menus: {{ entities.menu.all_values|join(", ") }}.
```

It is displayed like this:

```
🧑 Are there any specials today for vegan or maybe some bakery offerings?
🤖 You asked about these menus: vegetarian, cake.
```

#### Checking a value presence

Use `entities.menu.cake` if you want the condition to return true any time the term is mentioned in the user input, regardless of the order in which the entities are mentioned. This expression is a shorthand syntax for `"cake" in entities.menu.all_values`.


### Builtin entities

Entities that are based on a prebuilt rules. They cover commonly used categories, such as numbers or dates. You can just use rule based entities without defining them in bot resources.

#### `entities.number`

The `entities.number` detects mentions of numbers in user input. The number can be written with either numerals or words. In either case, a number is returned.

Recognized formats: "21", "twenty one", "3.14" or "1,234.56".

The `entities.number.value` returns canonical numeric value as a integer or a [Decimal](https://docs.python.org/3/library/decimal.html). If the input is "twenty", returns "20" . If the input is "1,234.56", returns "1234.56".

You can use the value in any [math expressions](https://jinja.palletsprojects.com/en/3.1.x/templates/#math). For example, `{{ entities.number.value + 1 }}` which outputs "2".

The `entities.number.literal` is the exact phrase in user input that is interpreted to be the number. If the input is "twenty", returns "twenty". If the input is "1,234.56" returns "1,234.56".

#### `entities.date`

The `entities.date` detects mentions of dates in user input.

Recognized formats: "Friday", "today", "May 8".

The `entities.date.value` is stored as a string in the format "yyyy-MM-dd". For example, the mention "May 8" is stored as "2022-05-08". The system augments missing elements of a date (such as the year for "May 8") with the current date values.

The `entities.date.literal` is the exact phrase in input that is interpreted to be the date. If the input is, "I plan to leave on Saturday.", then "on Saturday" is returned.

#### `entities.time`

The `entities.time` detects mentions of times in user input.

Recognized formats: "at 2pm", "15:30".

The `entities.time.value` returns the time that is specified in user input in the format "HH:mm:ss". For example, "13:00:00" for "at 1pm".

Use `entities.time.literal` to get the exact phrase in input that is interpreted to be the time. If the input is, "The store closes at 8PM.", then "at 8PM" is returned.


#### `entities.email`

The `entities.email` detects phrases in user input that look like email addresses. The recognized phrase is returned by the `entities.email.value` expression. If the input is, `"Email me at smith@example.com"`, then `"smith@example.com"` is returned.

#### `entities.url`

The `entities.url` detects phrases in user input that look like URL. The recognized phrase is returned by the `entities.url.value` expression. If the input is, `"Welcome to http://example.com"`, then `"http://example.com"` is returned.

## RPC

### `RpcRequest`

RPC request.

| Name          | Type                                    | Description |
| -----------   | ----------- 	                         | ----------- |
| `method`      | [String](/design-reference/strings.md)   | Requested method. |
| `params`      | [Dictionary](/design-reference/dictionaries.md)[[String](/design-reference/strings.md), Any]    | Actual parameters. |

### `RpcContext`

The context of the RPC request being processed.

**Example.** There is a convenient way to check the called rpc request in scenarios. Instead of

```yaml
condition: rpc.request.method == 'my_method'
# ...
```

you can just write

```yaml
condition: rp.my_method
# ...
```

| Name          | Type                                    | Description |
| -----------   | ----------- 	                         | ----------- |
| `request`     | [RpcRequest](#rpcrequest)               | RPC request. |
| `method`      | [String](/design-reference/strings.md)   | Return RPC method if request is present otherwise return `none`. |
| `params`      | [Dictionary](/design-reference/dictionaries.md)[[String](/design-reference/strings.md), Any]    | Return RPC params if request is present otherwise return `none`. |
| `__getattr__ ` | [RpcRequest](#rpcrequest)               | Return rpc request if its called. |
