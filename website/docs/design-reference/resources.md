# Resources

Bot resources are a collection of all the data and code necessary to build a particular bot. The bot development process is primarily the process of creating resources. Resources are described in YAML markup language according to a given schema and stored in files.

## `BotSchema`

Container for all bot resources.

| Name         | Type                                  | Description |
| -----------  | ----------- 	                         | ----------- |
| `extensions` | `ExtensionsSchema` 		               | Extensions used to customize a bot. |
| `channels`   | `ChannelsSchema` 		               | Channels used to communicate with the user. |
| `intents`    | [List](/design-reference/lists.md)[[IntentSchema](#intentschema)] | Intents used to recognize user goals based on user input. |
| `entities`   | [List](/design-reference/lists.md)[[EntitySchema](#entityschema)] | Entities used to extract pieces of information from user input. |
| `rpc`        | [List](/design-reference/lists.md)[[MethodSchema](#methodschema)] | RPC methods. |
| `dialog`\*   | [List](/design-reference/lists.md)[[DialogNodeSchema](#dialognodeschema)]     | Dialog tree containing conversational logic. |

## Intents

### `IntentSchema`

Schema for intent definition.

| Name         | Type                                  | Description |
| -----------  | ----------- 	                         | ----------- |
| `name`\*     | [String](/design-reference/strings.md) | Intent name. |
| `examples`   | [List](/design-reference/lists.md)[[String](/design-reference/strings.md)] | Intent examples. |

## Entities

### `EntitySchema`

Schema for entity definition.

#### Phrase entity

You define an entity (`entities.menu`), and then one or more values for that entity (`standard`, `vegetarian`, `cake`). For each value, you specify a bunch of phrases with which this value can be mentioned in the user input, e.g. "cake shop", "desserts" and "bakery offerings" for the `cake` value etc.

```yaml
- name: menu
  values:
    - name: standard
      phrases:
        - standard
        - carte du jour
        - cuisine
    - name: vegetarian
      phrases:
        - vegetarian
        - vegan
        - plants-only
    - name: cake
      phrases:
        - cake shop
        - dessert menu
        - bakery offerings
```

MaxBot recognizes pieces of information in the user input that closely match the phrases that you defined for the entity as mentions of that entity.

#### Regex entity

You define an entity (`entities.order_number`), and then one or more values for that entity (`short_syntax`, `full_syntax`). For each value, you specify a regular expression that defines the textual pattern of mentions of that value type.

```yaml
- name: order_number
  values:
    - name: short_syntax
      regexps:
        - '[A-Z]{2}\\d{5}'
    - name: full_syntax
      regexps:
        - '[DEF]\\-[A-Z]{2}\\d{5}'
```

MaxBot looks for patterns matching your regular expression in the user input, and identifies any matches as mentions of that entity.

#### Attributes

| Name         | Type                                  | Description |
| -----------  | ----------- 	                         | ----------- |
| `name`\*    | [String](/design-reference/strings.md) | Entity name. |
| `values`     | [List](/design-reference/lists.md)[[EntityValue](#entityvalue)] | Entity values. |

### `EntityValue`

Schema for entity value definition.

A value of phrase entity.

```yaml
- name: standard
  phrases:
    - standard
    - carte du jour
    - cuisine
```

A value of regex entity.

```yaml
- name: short_syntax
  regexps:
    - '[A-Z]{2}\\d{5}'
```

| Name         | Type                                  | Description |
| -----------  | ----------- 	                         | ----------- |
| `name`\*     | [String](/design-reference/strings.md) | A name used to identify the value. |
| `phrases`    | [List](/design-reference/lists.md)[[String](/design-reference/strings.md)] | A list of phrases with which the value can be mentioned in the user input. |
| `regexps`    | [List](/design-reference/lists.md)[[String](/design-reference/strings.md)] | A list of a regular expressions that defines the textual pattern of mentions of the value. |

## RPC

### `MethodSchema`

JSON-RPC method definition.

| Name         | Type                                  | Description |
| -----------  | ----------- 	                         | ----------- |
| `method`\*   | [String](/design-reference/strings.md) | Method name. |
| `params`     | [List](/design-reference/lists.md)[[ParamSchema](#paramschema)] | Formal parameters of the method. |

### `ParamSchema`

JSON-RPC formal parameter definition.

| Name         | Type                                  | Description |
| -----------  | ----------- 	                         | ----------- |
| `name`\*     | [String](/design-reference/strings.md)  | The name of the parameter. |
| `required`   | [Boolean](/design-reference/booleans.md) | Whether the parameter is required. |

## Dialog Tree

### `DialogNodeSchema`

An umbrella for all possible tree nodes. Essentially, it is one of the following schemes:

* [NodeSchema](#nodeschema)
* [SubtreeRefSchema](#subtreerefschema)


### `NodeSchema`

Definition of the dialog tree node.

| Name            | Type                                  | Description |
| -----------     | ----------- 	                         | ----------- |
| `label`         | [String](/design-reference/strings.md)  | Unique node label. The following nodes must have a label. <ul><li>Nodes that contains slot filling or followup nodes. This kind of nodes use labels internally to store their state.</li><li>Nodes that targeted by the `jump_to` command. Labels are used in the jump_to arguments.</li></ul> |
| `condition`\*    | [Expression](/design-guides/templates.md#expressions) | Determines whether that node is used in the conversation. |
| `slot_filling`  | [List](/design-reference/lists.md)[[SlotSchema](#slotschema)] | List of slots for the Slot Filling Flow. |
| `slot_handlers` | [List](/design-reference/lists.md)[[HandlerSchema](#handlerschema)] | List of slot handlers for the Slot Filling Flow. |
| `response`      | [Template](/design-reference/jinja.md)[[NodeCommands](#nodecommands)] | Defines how to reply to the user. |
| `followup`      | [List](/design-reference/lists.md)[[NodeSchema](#nodeschema)] | List of followup nodes. |
| `settings`      | [NodeSettings](#nodesettings) | Node settings. |


### `NodeCommands`

Control commands for node `response` scenarios.

| Name            | Type                                   | Description |
| -----------     | ----------- 	                          | ----------- |
| `end`           | [{}](/design-reference/dictionaries.md) | End the conversation and reset its state. |
| `listen`        | [{}](/design-reference/dictionaries.md) | Wait for the user to provide new input that the response elicits. |
| `followup`      | [{}](/design-reference/dictionaries.md) | Bypass waiting for user input and go directly to the first followup node of the current node instead.<br/><br/>Note: the current node must have at least one followup node for this option to be available. |
| `jump_to`       | [JumpTo](#jumpto)                      | Go directly to an entirely different dialog node. |

### `JumpTo`

Jump to a different node after response is processed.

Specify when the target node is processed by choosing one of the following options.

* `condition` - the bot checks first whether the condition of the targeted node evaluates to true.
	* If the condition evaluates to true, the system processes the target node immediately.
	* If the condition does not evaluate to true, the system moves to the next sibling node of the target node to evaluate its condition, and repeats this process until it finds a dialog node with a condition that evaluates to true.
	* If the system processes all the siblings and none of the conditions evaluate to true, the bot resets its current conversation state.
* `response` - the bot does not evaluate the condition of the targeted dialog node; it processes the response of the targeted dialog node immediately.
* `listen` - Waits for new input from the user, and then begins to process it from the node that you jump to.

| Name            | Type                                   | Description |
| -----------     | ----------- 	                          | ----------- |
| `node`\*        | [String](/design-reference/strings.md)  | A label of the node to jump to. |
| `transition`    | Enum[`condition`, `response`, `listen`]| Specifies when the target node is processed. |

### `NodeSettings`

Settings that change the behavior for an individual node.

| Name                        | Type                                  | Description |
| -----------                 | -----------                           | ----------- |
| `after_digression_followup` | Enum[`allow_return`, `never_return`]  | For nodes that have `followup` children, when digression triggered after the node's response.<ul><li>`allow_return` - allow return from digression and continue to process its followup nodes (default).</li><li>`never_return` - prevent the dialog from returning to the current node.</li></ul> |

## Subtrees

### `SubtreeRefSchema`

A reference to a subtree located in separate resource file.

| Name            | Type                                   | Description |
| -----------     | ----------- 	                       | ----------- |
| `subtree`\*     | [String](/design-reference/strings.md) | The name of the subtree to include. |

### `Subtree`

A group of nodes to include in the dialog tree.

| Name            | Type                                   | Description |
| -----------     | ----------- 	                          | ----------- |
| `name`\*        | [String](/design-reference/strings.md)  | Subtree name is used to refer to a subtree from the dialog tree. |
| `guard`         | [Expression](/design-guides/templates.md#expressions)  | A condition that determines whether the nodes in the subtree should be processed. |
| `nodes`\*       | [List](/design-reference/lists.md)[[DialogNodeSchema](#dialognodeschema)]     | A list of dialog nodes. |

## Slot Filling

### `SlotSchema`

Slot is used to gather a piece of information from the user input.

See [Slot Filling](/design-guides/slot-filling.md) for more information.

| Name            | Type                                   | Description |
| -----------     | ----------- 	                          | ----------- |
| `name`\*        | [String](/design-reference/strings.md)  | A name for the slot variable in which to store the value of interest from the user input.<br/><br/>Do not reuse a slot variable that is used elsewhere in the dialog. If the slot variable has a value already, then the slot's prompt is not displayed. It is only when the slot variable is null that the prompt for the slot is displayed. |
| `check_for`\*   | [Expression](/design-guides/templates.md#expressions) | Checks if the user input contains the value of interest. If so, the value is stored in the slot variable which you provided in the `name` field.<br/><br/>Avoid checking for any state variable values in the `check_for` field. Because the value you check for is also the value that is saved, using a state variable in the condition can lead to unexpected behavior. Instead, consider using a slot `condition`. |
| `value`         | [Expression](/design-guides/templates.md#expressions) | If provided, the result will be stored as a slot value instead of `check_for`.<br/><br/>In some cases, you might want to use the `check_for` expression to capture the value, but not apply the expression to what is saved. In such cases, you can use one expression in the `check_for` field to capture the value, and other expression in the `value` field to store something else. |
| `condition`     | [Expression](/design-guides/templates.md#expressions) | Makes the slot only be enabled under the specified condition. |
| `prompt`        | [Template](/design-reference/jinja.md)[[PromptCommands](#promptcommands)] | A response that asks a piece of the information you need from the user. After displaying this prompt the bot waits for the user to respond.<br/><br/>Add a slot without a prompt to make a slot optional. |
| `found`         | [Template](/design-reference/jinja.md)[[FoundCommands](#foundcommands)] | Displayed after the user provides the expected information. Useful to validate the information provided. |
| `not_found`     | [Template](/design-reference/jinja.md)[[NotFoundCommands](#notfoundcommands)] | Displayed only if the information provided by the user is not understood, which means all of the following are true:<ul><li>none of the active slots are filled successfully;</li><li>no slot handlers are understood;</li><li>nothing triggered as a digression from slot filling.</li></ul> |

### `HandlerSchema`

Provide responses to questions users might ask that are tangential to the purpose of the slot filling. After responding to the off-topic question, the prompt associated with the current empty slot is displayed.

See [Slot Filling](/design-guides/slot-filling.md#slot-handlers) for more information.

| Name            | Type                                           | Description |
| -----------     | ----------- 	                                  | ----------- |
| `condition`\*    | [Expression](/design-guides/templates.md#expressions)  | Triggers slot handler based on user input provided any time during the slot filling. |
| `response`      | [Template](/design-reference/jinja.md)[[HandlerCommands](#handlercommands)] | Responds to the user when the slot handler is triggered. |

### `FoundCommands`

Controls what happens after `found` response is sent.

See [Slot Filling](/design-guides/slot-filling.md#found) for more information.

| Name            | Type                                   | Description |
| -----------     | ----------- 	                          | ----------- |
| `move_on`       | [{}](/design-reference/dictionaries.md) | Move on to the next empty slot after displaying the response (default). |
| `prompt_again`  | [{}](/design-reference/dictionaries.md) | Clear the current slot value and prompt for the correct value. |
| `listen_again`  | [{}](/design-reference/dictionaries.md) | Do not prompt for the slot and just wait for the user to respond. |
| `response`      | [{}](/design-reference/dictionaries.md) | Skip the remaining slots and go directly to the node-level response. |

### `NotFoundCommands`

Controls what happens after `not_found` response is sent.

See [Slot Filling](/design-guides/slot-filling.md#not-found) for more information.

| Name            | Type                                   | Description |
| -----------     | ----------- 	                          | ----------- |
| `prompt_again`  | [{}](/design-reference/dictionaries.md) | Prompt for the correct slot value (default) |
| `listen_again`  | [{}](/design-reference/dictionaries.md) | Do not prompt for the slot and just wait for the user to respond. |
| `response`      | [{}](/design-reference/dictionaries.md) | Skip the remaining slots and go directly to the node-level response. |

### `PromptCommands`

Controls what happens after `prompt` response is sent.

See [Slot Filling](/design-guides/slot-filling.md) for more information.

| Name            | Type                                   | Description |
| -----------     | ----------- 	                          | ----------- |
| `listen_again`  | [{}](/design-reference/dictionaries.md) | Wait for the user to respond (default). |
| `response`      | [{}](/design-reference/dictionaries.md) | Skip the remaining slots and go directly to the node-level response. |

### `HandlerCommands`

Controls what happens after slot handler response is sent.

See [Slot Filling](/design-guides/slot-filling.md#slot-handlers) for more information.

| Name            | Type                                   | Description |
| -----------     | ----------- 	                          | ----------- |
| `move_on`       | [{}](/design-reference/dictionaries.md) | Move on to the next empty slot after displaying the response (default). |
| `response`      | [{}](/design-reference/dictionaries.md) | Skip the remaining slots and go directly to the node-level response. |
