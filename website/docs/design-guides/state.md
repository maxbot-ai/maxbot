import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Dialog State


State variables are used to retaining information across dialog turns. Use state variables to collect information from the user and then refer back to it later in the conversation.

There are two kinds of state variables.

* Slot variables are used by the bot as short-term memory to keep the conversation on the current topic only.
* User variables are long-term memory that is used to personalize the entire communication process.

## Slot Variables {#slot-variables}

Slot variables only retain information during current topic discussion. When current user goal is reached, then the collected information is no longer needed, so the bot "forgets" it, the slot values are cleared. This kind of forgetfulness simplifies conversation design. If you need to store information for a long time, consider using [User Variables](#user-variables).

### Passing state when moving across nodes

Use slot variables to pass state when you *move from parent node to followup nodes* or *jump from one node to another*. Set slot value in a node response using the block like `{% set slots.dessert = "cake" %}`. Get the value of a slot variable by using `slots` template variable: `slots.dessert`.

In the example, the bot performs an order cancellation. The parent node receives the order number, stores it in a slot, and asks for confirmation from the user that he wants to cancel an order. The child node receives confirmation, reads the order number from the slot, and uses it to cancel the order.

```yaml
- condition: intents.cancel_order and entities.order_number
  label: cancel_order
  response: |
      {% set slots.order_number = entities.order_number.literal %}
      Do you want to cancel order {{ slots.order_number }}?
  followup:
    - condition: intents.yes
      response: |
          The order {{ slots.order_number }} is canceled.
```

The slot variable value (`entities.order_number.literal`) is an expression that captures the number that the user specifies that matches the pattern defined by the `entities.order_number` regexp entity. It saves it to the `slots.order_number` variable. After canceling the order, `slots.order_number` variable is no longer needed and is cleared by the bot.

### Retaining state during slot filling

As the bot collects answers from the user per slot, they are saved in slot variables. You then use the slot variables in node-level response to address user goal. After the node-level response is completed and the user's goal has been reached, the slot values are cleared so that the node can start collecting information again. See [Slot Filling](slot-filling.md) for mode details and examples.

### Lifespan of slot variables {#slots-lifespan}

After the node response is completed, it depends on the bot's farther actions whether the user's current goal has been reached or whether discussion of the topic continues. The discussion continues and **slots are saved** when after executing the node response the bot needs to

* process followup nodes;
* jump to another node;
* return after digression to the node that was interrupted.

Otherwise, the goal is considered reached and the slots values are cleared.

## User Variables {#user-variables}

You can add user variables to retain information between different topic discussions. User variables store information for as long as necessary, unless you explicitly update or delete it.

User variables can pass information from one node to any other unrelated node. As the bot asks for and gets information from the user, it can keep track of the information and reference it later in the conversation. Set user variable value in a node response using the block like `{% set user.phone_number = "958-234-3456" %}`. Get the value of a user variable by using `user` template variable: `{{ user.phone_number }}`.

For example, in one node you might ask users for their name, and in a later node address them by name.

<Tabs
    defaultValue="snippet"
    values={[
        {label: 'Snippet', value: 'snippet'},
        {label: 'Full', value: 'full'},
    ]}>
<TabItem value="snippet">

  ```yaml
  - condition: intents.introductions
    label: introductions
    response: |
      My name is Max, the bot. What's yours?
    followup:
      - condition: message.text
        response: |
          {% set user.name = message.text %}
          It's lovely to meet you, {{ user.name }}!
          What can I do for you?
  - condition: intents.purchase
    response: |
      What would you like to buy, {{ user.name }}?
  ```

</TabItem>
<TabItem value="full">

  ```yaml
  channels:
    telegram:
      api_token: !ENV ${TELEGRAM_API_KEY}
  intents:
    - name: introductions
      examples:
        - What do they call you?
        - What's your name?
        - Who are you?
        - How can I call you?
        - Tell me your name
    - name: purchase
      examples:
        - I'd like to buy something.
        - I want to buy some stuff
        - Do you sell things?
        - Are you a salesman?
        - Can I buy something.
  dialog:
    - condition: intents.introductions
      label: introductions
      response: |
        My name is Max, the bot. What's yours?
      followup:
        - condition: message.text
          response: |
            {% set user.name = message.text %}
            It's lovely to meet you, {{ user.name }}!
            What can I do for you?
    - condition: intents.purchase
      response: |
        What would you like to buy, {{ user.name }}?
  ```

</TabItem>
</Tabs>

In this example, the raw user input `message.text` is interpreted as a username. The `user.name` variable is defined and set to the `message.text` value.

```
🧑 What do they call you?
🤖 My name is Max, the bot. What's yours?
🧑 Steve
🤖 It's lovely to meet you, Steve! What can I do for you?
```

In a subsequent node, the `user.name` variable is included in the response to address the user by name.

```
🧑 I'd like to buy something.
🤖 What would you like to buy, Steve?
```

## Working with State Variables

You define state variables in a node. Other nodes can subsequently set or change the value of the state variable. You can condition against state variable values by referencing a slot variable from a node condition to determine whether to execute a node. You can also reference a state variable from dialog node template conditions to show different responses depending on a value provided.

### Defining state variables

In most cases, you define the state variable as part of the node response by setting its value.

```yaml
{% set slots.counter = 0 %}
{% set user.name = "Steve" %}
```

State variable name can contain any upper- and lowercase alphabetic characters, numeric characters (0-9), and underscores. The value can be any JSON-serializable type, such as strings, numbers, lists, and dicts. See [Templates](/design-guides/templates.md#data-types) guide for more information about data types.

You can use any [Jinja Expressions](/design-guides/templates.md#expressions) when defining state variables but make sure the resulting value will be JSON-serializable type.

```
slot contains_yes = ("yes" in message.text)
```

### Default values

When you define variable in the node response, the state variable is created and given the specified value when the bot returns the node response. Make sure state variables are defined before usage, otherwise use them with the [default filter](/design-reference/jinja.md#filter-default):

```
slots.counter|default(0) > 1
```

or explicitly check that variable is defined:

```
{% if user.name %}
  What would you like to buy, {{ user.name }}?
{% else %}
  What would you like to buy?
{% endif %}
```

### Updating state variables

To update a state variable's value, use the same statements, but this time, specify a different value for it.

```
{% set slots.counter = slots.counter + 1 %}
{% set user.name = "Bob" %}
```

When more than one node sets the value of the same state variable, the value for the state variable can change over the course of a conversation with a user. Which value is applied at any given time depends on which node is being triggered by the user in the course of the conversation. The value specified for the state variable in the last node that is processed overwrites any values that were set for the variable by nodes that were processed previously.

TODO: example

### Deleting state variables

To delete a state variable use the {% delete ... %} tag.

```
{% delete slots.counter %}
{% delete user.name %}
```

The variable is considered deleted and no longer uses the bot's memory. Trying to get the value of a variable will result in an error.

Note that slot variables automatically deleted when they out of their [lifespan](#slots-lifespan).

## Capturing Values

The following is examples of using Jinja expressions to capture different parts of the user input. For more information about the methods available for you to use, see [Jinja Syntax](/design-reference/jinja.md) reference.

### Capturing user input

To store the entire string that was provided by the user as input, use `message.text` expression:

```
slot repeat = message.text
```

For example, the user input is, "I want to order a device". If the node response is

```
response: |
    "You said: {{ slots.repeat }}."
```

then the response would be displayed as, "You said: I want to order a device."


### Capturing an entity mention

To store the value of an entity in a context variable, use this syntax

```
slot place = entities.place.value
```

For example, the user input is, "I want to go to Paris". If your `entities.place` recognizes "Paris", then the bot saves "Paris" in the `slots.place` variable.

### Using a filter

To store the value of a string that you extract from the user's input, you can include a Jinja expression that uses the extract filter to apply a regular expression to the user input. The following expression extracts a number from the user input, and saves it to the `slots.number` variable.

TODO: implement this

```
slot number = message.text|extract("\d+", 0)
```

### Capturing a regexp entity literal value

To store the value of a regex entity, append `.literal` to the entity name. Using this syntax ensures that the exact span of text from user input that matched the specified regexp is stored in the variable.

```
slot order_number = entities.order_number.literal
```

For example, the user input is "Please, cancel the order AB12345". Your regexp entity `entities.order_number` recognizes the '[A-Z]{2}\d{5}' order number format. By configuring the slot variable to store `entities.order_number.literal`, you indicate that you want to store the part of the input that matched the pattern. If you omit the `.literal` property from the value expression, then the entity value name that you specified for the regexp is returned instead of the segment of user input that matched the pattern.
