import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Slot Filling

Add slot filling to a dialog node to gather additional information from a user within that node. Slots allow information to be collected at the user's pace. When the node condition is met, details that a user provides immediately are saved in slots. The bot then asks for the missing details and stores them in the slots as well. The node response will be processed only when the bot fills all the required slots.

## Basic Usage

### Ask follow up questions

Use slots to get the information you need before you can respond accurately to the user. For example, if users ask about operating hours, but the hours differ by store location, you could ask a follow up question about which store location they plan to visit before you answer. You can then add response conditions that take the provided location information into account.

<Tabs
    defaultValue="snippet"
    values={[
        {label: 'Snippet', value: 'snippet'},
        {label: 'Full', value: 'full'},
    ]}>
<TabItem value="snippet">

```yaml
- condition: intents.operating_hours
  label: operating_hours
  slot_filling:
    - name: location
      check_for: entities.location
      prompt: |
          Are you visiting our store downtown or the one in the mall?
  response: |
      {% if slots.location == 'downtown' %}
        We are open from 8AM to 8PM seven days a week.
      {% else %}
        Our retail store in the mall follows the mall
        operating hours of 9AM to 9 PM.
      {% endif %}
```

</TabItem>
<TabItem value="full">

  ```yaml
  channels:
    telegram:
      api_token: !ENV ${TELEGRAM_API_KEY}
  intents:
    - name: operating_hours
      examples:
        - When does the shop close?
        - When is the store open?
        - What are the store opening hours
        - Shop openin hours
        - What time do you close?
        - When do you close?
        - When do you open?
        - At what time do you open?
  entities:
    - name: location
      values:
        - name: downtown
          phrases:
            - downtown
            - city center
            - middle of town
        - name: mall
          phrases:
            - mall
            - shopping area
  dialog:
    - condition: intents.operating_hours
      label: operating_hours
      slot_filling:
        - name: location
          check_for: entities.location
          prompt: |
              Are you visiting our store downtown or the one in the mall?
      response: |
          {% if slots.location == 'downtown' %}
            We are open from 8AM to 8PM seven days a week.
          {% else %}
            Our retail store in the mall follows the mall
            operating hours of 9AM to 9 PM.
          {% endif %}
  ```

</TabItem>
</Tabs>

For each slot we specify following fields.

* `name` - a name for the slot variable in which to store the value of interest from the user input, in the example the variable  is `slots.location`.
* `check_for` - an expression that checks if the user input contains the value of interest, if so, the value is stored in the variable.
* `prompt` - a response that asks a piece of the information you need from the user.

The conversation could go like this

```
🧑 When do you open?
🤖 Are you visiting our store downtown or the one in the mall?
🧑 I prefer downtown.
🤖 We are open from 8AM to 8PM seven days a week.
```

When the node condition is met and `slots.location` is empty, the bot asks a follow up question using the `prompt` response. After displaying this prompt the bot waits for the user to respond. The bot then captures the `entities.location` from the user input and stores the value in the `slots.location` variable.

The response template uses the value in the `slots.location` variable to chose the correct operating hours.

### Collect multiple pieces of information

Slots can help you to collect multiple pieces of information that you need to complete a complex task for a user, such as making a dinner reservation.

```yaml
- condition: intents.reservation
  label: reservation
  slot_filling:
    - name: date
      check_for: entities.date
      prompt: |
        What day would you like to come in?
    - name: time
      check_for: entities.time
      prompt: |
        What time do you want the reservation to be made for?
    - name: guests
      check_for: entities.number
      prompt: |
        How many people will be dining?
  response: |
      OK. I am making you a reservation for {{ slots.guests }}
      on {{ slots.date }} at {{ slots.time }}.

```

The user might provide values for multiple slots at once. For example, the input might include the information, "I'd like to make a reservation for 6 people at 5 pm". This one input contains two of the missing required values: the number of guests and time of the reservation. Your assistant recognizes and stores both of them, each one in its corresponding slot. It then displays the prompt that is associated with the next empty slot.

```
🧑 I'd like to make a reservation for 6 people at 5 pm
🤖 What day would you like to come in?
🧑 tomorrow
🤖 OK. I am making you a reservation for 6 on 2022-05-29 at 17:00:00.
```

The node-level response is not executed until after all of the required slots are filled. Typically, the response summarizes the information you collected.

### Optional Slots

Add a slot without a `prompt` to make a slot optional. The bot does not ask the user for the information, but it does look for the information in the user input, and saves the value if the user provides it.

For example, you might add a slot that captures dietary restriction informations in case the user specifies any. However, you don't want to ask all users for dietary information since it is irrelevant in most cases.

<Tabs
    defaultValue="snippet"
    values={[
        {label: 'Snippet', value: 'snippet'},
        {label: 'Full', value: 'full'},
    ]}>
<TabItem value="snippet">

  ```yaml
  - condition: intents.order_pizza
    label: order_pizza
    slot_filling:
      - name: size
        check_for: entities.size
        prompt: |
          What size pizza would you like?
      - name: time
        check_for: entities.time
        prompt: |
          When do you need the pizza by?
      - name: dietary
        check_for: entities.dietary
    response: |
      {% if slots.dietary %}
        I am ordering a {{ slots.size }} {{ slots.dietary }}
        pizza for delivery at {{ slots.time }}.
      {% else %}
        I am ordering a {{ slots.size }}
        pizza for delivery at {{ slots.time }}.
      {% endif %}
  ```

</TabItem>
<TabItem value="full">

  ```yaml
  extensions:
    format: { locale: en }
    datetime: {}
  channels:
    telegram:
      api_token: !ENV ${TELEGRAM_API_KEY}
  intents:
    - name: order_pizza
      examples:
        - I want to order pizza
        - I need a pizza
        - Pizza delivery
        - Can I order a pizza?
        - Can I get a pizza, please
  entities:
    - name: size
      values:
        - name: large
          phrases:
            - big
            - large
            - biggest
        - name: medium
          phrases:
            - midsize
            - medium
        - name: small
          phrases:
            - small
            - little
            - undersized
    - name: dietary
      values:
        - name: diet
          phrases:
            - dietary
            - diet
            - gluten-free
  dialog:
    - condition: intents.order_pizza
      label: order_pizza
      slot_filling:
        - name: size
          check_for: entities.size
          prompt: |
            What size pizza would you like?
        - name: time
          check_for: entities.time
          prompt: |
            When do you need the pizza by?
        - name: dietary
          check_for: entities.dietary
      response: |
        {% if slots.dietary %}
          I am ordering a {{ slots.size }} {{ slots.dietary }}
          pizza for delivery at {{ slots.time }}.
        {% else %}
          I am ordering a {{ slots.size }}
          pizza for delivery at {{ slots.time }}.
        {% endif %}
  ```

</TabItem>
</Tabs>

If you make a slot optional, only reference its slot variable in the node-level response text if you can word it such that it makes sense even if no value is provided for the slot. The resulting text makes sense whether the dietary restriction information, such as gluten-free or dairy-free, is provided

```
🧑 Can I get a small pizza, gluten-free please
🤖 When do you need the pizza by?
🧑 at 3:00PM
🤖 I am ordering a small gluten-free pizza for delivery at 15:00:00.
```

or not provided

```
🧑 I want to order a large pizza at 7pm
🤖 I am ordering a large pizza for delivery at 19:00:00.
```

## Capturing Slot Values

During the slot filling, when a user input is received, the `check_for` expressions are evaluated for all slots and captured values are saved in slot variables.

In most cases, you check for entity values as in the basic examples above. You can also check for a specific entity attribute, an intent or a message.

Avoid checking for any state variable values. Because the value you check for is also the value that is saved, using a state variable can lead to unexpected behavior. Instead, consider using [conditional slots](#conditional-slots).

### Capturing user input

Special variable `slot_in_focus` forces the `check_for` condition to be applied only when the current slot has just been prompted. The `slot_in_focus` variable always evaluates to a boolean (true or false) value.

You might want to prompt a user to supply free form text in a dialog node with slots that you can save and refer to later. Using `check_for: message.text` is useless because it causes the slot to fill up whenever the user types a text at other times during the dialog. Do it this way instead.

```yaml
- name: summary
  check_for: slot_in_focus and message.text
  prompt: |
    Can you summarize the problem?
```

Note that the boolean operators `and` and `or` can return not only boolean type, but right or left values.

In the example above, the `check_for` expression first evaluates `slot_in_focus`; if `slot_in_focus` is false, its value is returned; otherwise, the value of `message.text` is returned (which is not a boolean, but a string).

The order of operands is important. If you swap the operands in the example: `message.text and slot_in_focus`, you will never get `message.text` when it is not empty.

See [Python Boolean Operators](https://docs.python.org/3/reference/expressions.html#boolean-operations) for more information.

### Capturing multiple values

You can ask for a list of items and save them in one slot.

For example, you might want to ask users whether they want toppings on their pizza. To do so define an `entity.toppings`, and the accepted values for it (pepperoni, cheese, mushroom, and so on). Add a slot that asks the user about toppings. Use the `all_values` attribute of the entity to capture multiple values, if provided.

```yaml
- name: toppings
  check_for: entities.toppings.all_values
  prompt: |
    Any toppings on that?
```

Later, in the response, use [join](https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.join) filter to list each item in the toppings array and separate the values with a comma. For example,

```yaml
response: |
    I am ordering you a {{ slots.size }} pizza with
    {{ slots.toppings|join(',') }} for delivery by {{ slots.time }}.
```
### Capturing slot value

You can also adjust the value of the slot and make it different from `check_for` using the `value` field.

For example, if the user has entered several values suitable for filling the slot, you can select a specific one:

```yaml
- name: guests
  check_for: entities.number
  value: entities.number.all_values|max
  prompt: |
    How many people will be dining?
  found: |
    Ok. The reservation is for {{ slots.guests }} guests.
```
If the user enters several options for the number of guests the maximum of the entered ones will be selected.

```
🧑 I'd like to make a reservation
🤖 How many people will be dining?
🧑 2 or 3, I'm not sure
🤖 Ok. The reservation is for 3 guests.
```
## Processing Slots {#found}

Use the `found` response to acknowledge user input, add validation or other processing to filled slots. The `found` response is displayed after the user provides the expected information that matches the `check_for` field. In the `found` response, you can define further behavior of the bot using the following control commands.

* `move_on` (default) - move on to the next empty slot;
* `prompt_again` - repeat the slot prompt again and wait for the user to respond;
* `listen_again` - skip prompt for the slot and just wait for the user to respond;
* `response` - skip the remaining slots and go directly to the node-level response next.

### Acknowledge user input

It is good practice to send a response for each filled slot to assure the user that their input is understood. This example shows slots that helps users place a pizza order by collecting two pieces of information, the pizza size and delivery time.

```yaml
- name: size
  check_for: entities.size
  prompt: |
    What size pizza would you like?
  found: |
    {{ slots.size }} it is.
- name: time
  check_for: entities.time
  prompt: |
    When do you need the pizza by?
  found: |
    For delivery by {{ slots.time }}.
```

After displaying the `found` response, the bot moves on to the next empty slot. This is how the default `move_on` command works. We don't specify it explicitly. The dialog could go like this:

```
🤖 What size pizza would you like?
🧑 medium
🤖 medium it is.
🤖 When do you need the pizza by?
🧑 at 5 pm
🤖 For delivery by 17:00:00.
```

### Validate user input

If you are using an entity in the `check_for` field that could pick up the wrong value, add conditions that catch any likely misinterpretations, and use `prompt_again` command to clear the current slot value and prompt for the correct value.

For example, a slot is expecting the `entities.time` for a dinner reservation. To prevent an invalid time from being saved, you can add a conditional response that checks whether the time provided is before the restaurant's last seating time.

```yaml
- name: time
  check_for: entities.time
  prompt: |
    What time do you want the reservation to be made for?
  found: |
    {% if slots.time|time > '21:00:00'|time %}
      Our last seating is at 9PM.
      <prompt_again />
    {% endif %}
```

The corresponding dialog might be something like,

```
🤖 What time do you want the reservation to be made for?
🧑 10PM please
🤖 Our last seating is at 9PM.
🤖 What time do you want the reservation to be made for?
```

### Display error messages

You might word the `found` response such that it overlaps with the `prompt` response. Use the `listen_again` command to skip the prompt for the slot and simply wait for the user to respond. Perhaps, this modification of the dinner reservation example will look more natural, because the bot repeats the question to the user in a different wording.

```yaml
- name: time
  check_for: entities.time
  prompt: |
    What time do you want the reservation to be made for?
  found: |
    {% if slots.time|time > '21:00:00'|time %}
      The restaurant seats people between 9AM and 9PM. <br />
      Please specify the time that you want to eat.
      <listen_again />
    {% endif %}
```

Compare the following dialog with the previous one.

```
🤖 What time do you want the reservation to be made for?
🧑 10PM please
🤖 The restaurant seats people between 9AM and 9PM.
   Please specify the time that you want to eat.
```

### Skip to node-level response

If you no longer need to fill any of the remaining slots, use `response` command to skip the remaining slots and go directly to the node-level response next. For example, you could add a condition that checks whether the user's age is under 18. If so, you might skip the remaining slots which ask questions about the user's driving record.

```yaml
#...
slot_filling:
  - name: age
    check_for: entities.number
    prompt: |
      How old are you?
    found: |
      {% if slots.age < 18 %}
        Sorry we don't rent cars to teenagers.
        <response />
      {% endif %}
  - name: driving_record
    check_for: entities.driving_record
    prompt: |
      What is your driving record?
  #...
response: |
  {% if slots.age and slots.driving_record ... %}
      ...
  {% else %}
    Booking cancelled.
  {% endif %}
```

In the node-level response, the bot checks for all slot variables. If the all of them is filled, then it reports success. If not, it just shows a cancel message.

```
🤖 How old are you?
🧑 i am 16
🤖 Sorry we don't rent cars to teenagers.
🤖 Booking cancelled.
```

### Access the previous slot value

If, during the slot filling, the user provides a new value for a slot, then the new value is saved in the slot variable, replacing the previously-specified value. Your dialog can acknowledge explicitly that this replacement has occurred by using special properties that are defined for the `found` response:

* `previous_value` - previous value of this slot variable;
* `current_value` - current value of this slot variable.

`previous_value` is filled even if new value is the same as the previous one.

For example, your bot asks for a destination city for a flight reservation.

```yaml
- name: destination
  check_for: entities.city
  prompt: |
      Enter your destination city.
  found: |
      {% if previous_value and previous_value != current_value %}
        Ok, updating destination from {{ previous_value }}
        to {{ current_value }}.
      {% else %}
        Okay, flight to {{ slots.destination }}.
      {% endif %}
```

If you set up the `found` response as above, then your bot can handle this type of change gracefully.

```
🤖 Enter your destination city.
🧑 fly to Paris
🤖 Okay, flight to Paris.
...
🧑 Oh wait. I want to fly to Madrid instead
🤖 Ok, updating destination from Paris to Madrid.
```

### Getting confirmation {#getting-confirmation}

Add a slot after the others that asks the user to confirm that the information you have collected is accurate and complete. The slot can look for responses that match the `intents.yes` or `intents.no`.

```yaml
- name: confirmation
  check_for: slot_in_focus and (intents.yes or intents.no)
  prompt: |
      I'm going to order you a {{ slots.size }} pizza
      for delivery at {{ slots.time }}. <br />
      Should I go ahead?
```

Because users might include affirmative or negative statements at other times during the dialog ("Oh yes, we want the pizza delivered at 5pm") or ("no guests tonight, let's make it a small"), use the `slot_in_focus` property to make it clear in the slot condition that you are looking for a Yes or No response to the prompt for this slot only.

In the `found` response, add a condition that checks for `intents.no` response. When found, delete the slot variables that you saved earlier and ask for the information all over again.

```yaml
  found: |
      {% if intents.no %}
        {% delete slots.size %}
        {% delete slots.time %}
        {% delete slots.confirmation %}
        Let's try this again.
      {% endif %}
```

In the end you see the bot prompts slots again, because they have been were reset.

```
🤖 I'm going to order you a small pizza for delivery at 17:00:00.
   Should I go ahead?
🧑 No I changed my mind
🤖 Let's try this again.
🤖 What size pizza would you like?
```

## Handling Misunderstood {#not-found}

A `not_found` response is displayed only if the information provided by the user is not understood by the bot, which means all of the following are true:

* none of the slots in the node are filled successfully;
* no [slot handlers](#slot-handlers) are understood;
* no root nodes are triggered as a [digression](digressions.md) from slot filling.

See [Slot Filling Flow](#flow) for more details.

In the simplest case, the text you specify in `not_found` response can more explicitly state the type of information you need the user to provide. After displaying the text to the user, the further behavior of the bot can be defined using the following control commands:

* `prompt_again` - repeat the slot prompt again and wait for the user to respond;
* `listen_again` (default) - skip prompt for the slot and just wait for the user to respond;
* `response` - skip the remaining slots and go directly to the node-level response next.

If `not_found` response can be triggered but is not defined, bot executes `prompt_again` command.

### Clarify your expectations

Back to [Getting confirmation](#getting-confirmation) example. You can use `not_found` response to clarify that you are expecting the user to provide a Yes or No answer.

```yaml
  not_found: |
      Respond with Yes to indicate that you want the order to
      be placed as-is, or No to indicate that you do not.
```

The dialog will be like this

```
🤖 I'm going to order you a small pizza for delivery at 17:00:00.
   Should I go ahead?
🧑 What should I do?
🤖 Respond with Yes to indicate that you want the order to be placed as-is, or No to indicate that you do not.
🤖 I'm going to order you a small pizza for delivery at 17:00:00.
   Should I go ahead?
```

### Multiple failed attempts

You can provide users with a way to skip a slot if they cannot answer it correctly after several attempts by using `not_found` response.

In this example, the bot asks for the pizza size. It lets the user answer the question incorrectly 3 times before applying a size (medium) to the variable for the user.

```yaml
- name: size
  check_for: entities.size
  prompt: |
      What size did you want?
  not_found: |
      {% set counter = slots.counter|default(0) %}
      {% if counter > 1 %}
        {% set slots.size = "medium" %}
        We will bring you a medium size pizza.
      {% else %}
        {% set slots.counter = counter + 1 %}
        What size did you want?
        We have small, medium, and large.
        <listen_again />
      {% endif %}
```

Use a `slots.counter` variable to keep track of the number of times the `not_found` response is returned. The `default` filter sets the initial counter variable value to 0. Note that you have to manually set "medium" value for `slots.size` to prevent the bot from prompting for it.

Dialog could be like this.

```
🤖 What size did you want?
🧑 plus size
🤖 What size did you want? We have small, medium, and large.
🧑 then it's all the same to me
🤖 What size did you want? We have small, medium, and large.
🧑 choose yourself
🤖 We will bring you a medium size pizza.
...
```

## Keep Users on Track {#slot-handlers}

You can optionally define slot handlers that provide responses to questions users might ask during the interaction that are tangential to the purpose of the node. After answering the question, the further behavior of the bot can be defined using the following control commands:

* `move_on` (default) - move on and display prompt for the next empty slot;
* `response` -  skip the remaining slots and go directly to the node-level response next.x

### Answering off-topic questions

For example, the user might ask about the tomato sauce recipe or where you get your ingredients. To handle such off-topic questions, add a slot handler with a condition and response for each anticipated question.

```yaml
slot_filling:
  - name: size
    check_for: entities.size
    prompt: What size did you want?
  #...
slot_handlers:
  - condition: intents.sauce_recipe
    response: |
        It is a secret family recipe passed
        down from generation to generation.
        And I will take it to my grave.
```

This condition is triggered if the user provides input that matches the slot handler conditions at any time during the dialog node flow up until the node-level response is displayed.

After responding to the off-topic question, the prompt associated with the current empty slot is displayed.

```
🧑 I want to order pizza.
🤖 What size did you want?
🧑 What kind of sauce do you have there?
🤖 It is a secret family recipe passed down from generation to generation. And I will take it to my grave.
🤖 What size did you want?
```

Be careful about adding conditions that always evaluate to true (such as the special condition, `true`) as slot handlers. If the slot handler evaluates to true, then the `not_found` condition and [digression](digressions.md) are skipped entirely.

### Exit a process

Add at least one slot handler that can recognize it when a user wants to exit the node.

For example, in a node that collects information to schedule a pet grooming appointment, you can add a handler that conditions on the `intents.cancel`.

```yaml
slot_handlers:
  - condition: intents.cancel
    response: |
      Ok, we'll stop there. No appointment will be scheduled.
      <response />
response: |
    {% if slots.animal and slots.time and slots.date  %}
      I am making a grooming appointment for your
      {{ slots.animal }} at {{ slots.time }} on {{ slots.date }}.
    {% else %}
      If you decide to make an appointment later,
      I'm here to help.
    {% endif %}
```

In the handler's response, the bot acknowledges cancellation and uses `response` control command to skip the prompts for all remaining empty slots and go directly to the node-level response.

In the node-level response, the bot checks for all slot variables. If the all of them is filled, then it displays the standard summary message for the node. If not, it just shows a final message.

```
...
🧑 Forget it. I changed my mind.
🤖 Ok, we'll stop there. No appointment will be scheduled.
🤖 If you decide to make an appointment later, I'm here to help.
```

## Advanced Usage

### Conditional Slots {#conditional-slots}

If you want a slot to be enabled only under certain conditions, then you can add a `condition` field to it. This field is intended for checking slots, it is not recommended to use intents and entities in slot filling `condition`. It can lead to unexpected effects, such as sudden disabling of the slot.

For example, if slot 1 asks for a meeting start time, slot 2 captures the meeting duration, and slot 3 captures the end time, then you might want to enable slot 3 (and ask for the meeting end time) only if a value for slot 2 is not provided.

TODO: need full example

You can condition on the value of a slot variable from an earlier slot because the order in which the slots are listed is the order in which they are evaluated. However, only condition on a slot variable that you can be confident will contain a value when this slot is evaluated. The earlier slot must be a required slot, for example.

### Lifespan of slot variables

The bot stores collected information into slot variables. The information is then used in the node-level response to address user goal.

After the node-level response is completed, and the bot [does not take any further action](/design-guides/state.md#slots-lifespan), the slot values are cleared so that the node can start collecting information again. This is due to the fact that a node with slots only prompts users for information that it considers missing. *If a slot variable is filled with valid value, prompt is not displayed.*

Do not reuse a slot variable that is used elsewhere in the dialog. If the slot variable has a value already, then the slot's prompt is not displayed.

See [Dialog State](/design-guides/state.md) guide for more information.

### Avoiding slot filling confusion

When a user input is evaluated, the slot with the first slot `check_for` condition to match it is filled only. Test for the following possible causes of misinterpretation, and address them.

#### The same entity is used in more than one slot

For example, `entities.date` is used to capture the departure date in one slot and arrival date in another.

Use slot found conditions that get clarification from the user about which date you are saving in a slot before you save it.

#### A term fully or partially matches the entities in more than one slot

For example, if one slot captures a product ID (`entities.product_id`) with a syntax like "GR1234" and another slot captures a number (`entities.number`), such as 1234, then user input that contains an ID, such as BR3344 might get claimed by the `entities.number` slot as a number reference and fill the `slots.number` variable with 3344.

Place the slot with the entity condition that captures the longer pattern (`entities.id`) higher in the list of slots than the condition that captures the shorter pattern (`entities.number`).

#### A term is recognized as more than one builtin entity type

For example, if the user enters "May 2", then your bot recognizes both the `entities.date` (2022-05-02) and `entities.number` (2).

In logic that is unique to the slots feature, when two system entities are recognized in a single user input, the one with the larger span is used. Therefore, even though your bot recognizes both system entities in the text, only the system entity with the longer span (`entities.date` with 2017-05-02) is registered and applied to the slot.

Note, that the maxbot builtin nlu consider date reference to be an `entities.date` mention only, and is not also treated as an `entities.number` mention. For more details, see [Context](/design-reference/context.md) reference.

### Slot filling flow {#flow}

Let's take an overall look to the slot filling flow. When a user input is received, the conditions and responses are evaluated in the following order.

* `check_for` expressions are evaluated for all slots and slot variables are filled with the captured values.
* `found` responses are processed for each filled slot.
* If none of the slots are filled, the next one is processed sequentially until something succeeds.
	* `slot_handlers` in the order they are listed.
	* A [digression](digressions.md) into the root level dialog nodes.
	* `not_found` response of previously prompted slot.
* `prompt` response of the first empty slot is processed.
