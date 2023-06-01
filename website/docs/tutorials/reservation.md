---
toc_min_heading_level: 2
toc_max_heading_level: 2
---

# Making Reservation

In this tutorial, you will add slots to a dialog node to collect multiple pieces of information from a user within a single node. The node you create will collect the information that is needed to make a restaurant reservation.

By the time you finish the tutorial, you will understand how to:

* Add slots to a dialog node.
* Use rule-based entities that are needed by your dialog.
* Add slot response conditions that address common user interactions.
* Anticipate and address unrelated user input.
* Handle unexpected user responses.

The source code of the bot is available on github:

* [reservation-basic](https://github.com/maxbot-ai/maxbot/tree/main/examples/reservation-basic) - a simple node with slots that can capture the information necessary to make a reservation;
* [reservation](https://github.com/maxbot-ai/maxbot/tree/main/examples/reservation) - an advanced implementation, that improves the experience of users who interact with the node.

## Prerequisite

Before you begin, complete the [Quick Start](/getting-started/quick-start.md) tutorial.

Create a `bot.yaml` file that will contain the source code of the bot.

Add channel settings, for example, we use telegram channel:

```yaml
channels:
  telegram:
    api_token: 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
```

## Add a dialog node with slots

In this section you created a node with slots that can capture the information necessary to reserve a table at a restaurant.

### Add an intent

First of all, add an `intents.reservation` intent and examples that recognizes user input that indicates that the user wants to make a restaurant reservation.

```yaml
- name: reservation
  examples:
    - i'd like to make a reservation
    - I want to reserve a table for dinner
    - Can 3 of us get a table for lunch on May 29, 2022 at 5pm?
    - do you have openings for next Wednesday at 7?
    - Is there availability for 4 on Tuesday night?
    - i'd like to come in for brunch tomorrow
    - can i reserve a table?
```

### Add a dialog node

The node you add will contain slots to collect the information required to make a reservation at a restaurant.

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

Each record in the slot filling block contains following fields.

* `name`- The name of the slot variable to be filled in, e.g. `slots.date`, `slots.time`, `slots.guests`.
* `check_for` - An expression that checks if the user's input contains a piece of information of interest. If so, the value of the expression is stored in the slot variable.
* `prompt` - A response that is used to request the value of a slot, it can be a string, a list of commands or a template.

The node above uses rule-based entities to check the presence of the date `entities.date`, the time `entities.time` and the number of guests `entities.number`. The `check_for` expression evaluates to captured entity values. These values are stored in the corresponding slots `slots.date`, `slots.time`, `slots.guests`. When all slots are filled, their values are substituted in the node's response.

### Run and test

Now you can run the bot.

```bash
$ maxbot run --bot bot.yaml
✓ Started polling updater... Press 'Ctrl-C' to exit.
```

Open your messenger and try to make a reservation.

* Type `i want to make a reservation`. The bot recognizes the `intents.reservation` intent, and it responds with the prompt for the first slot, *"What day would you like to come in?"*

* Type `on Friday`. The bot recognizes the value, and uses it to fill the `slots.date` variable for the first slot. It then shows the prompt for the next slot, *"What time do you want the reservation to be made for?"*

* Type `at 5pm`. The bot recognizes the value, and uses it to fill the `slots.time` variable for the second slot. It then shows the prompt for the next slot, *"How many people will be dining?"*

* Type `6`. The bot recognizes the value, and uses it to fill the `slots.guests` variable for the third slot. Now that all of the slots are filled, it shows the node response, *"OK. I am making you a reservation for 6 on 2022-05-29 at 17:00:00."*


The beauty of slot filling is that the user is not required to provide all the information sequentially, as requested by the bot. For example, he can immediately provide all the information.

```
🧑 Can 6 of us get a table for lunch tomorrow at 5pm?
🤖 OK. I am making you a reservation for 6 on 2022-05-29 at 17:00:00.
```

In next sections we improve the experience of users who interact with the node.

## Improve the format of the responses

When the values of `entities.date` and `entities.time` are saved, they are converted into a standardized ISO format. This standardized format is useful for performing calculations on the values, but you might not want to expose this reformatting to users. In this step, you will reformat the date (`2023-01-27`) and time (`17:00:00`) values that are referenced by the dialog.

First of all, enable the [babel extension](/extensions/babel.md):

```yaml
extensions:
    babel: { locale: en }
```

This will allow you to use the following template filters for variables.

* `x|format_date("EEEE, MMMM d")` - It converts the `2023-01-27` value into a full day of the week, followed by the full month and day. The EEEE indicates that you want to spell out the day of the week. If you use 3 Es (EEE), the day of the week will be shortened to Fri instead of Friday, for example. The MMMM indicates that you want to spell out the month. Again, if you use only 3 Ms (MMM), the month is shortened to Dec instead of December.
* `x|format_time("h:mm a")` - It converts the `17:00:00` value into the hour, minutes and indicates AM or PM.

Edit the node's response as follows:

```django
# ...
response: |
    OK. I am making you a reservation for {{ slots.guests }} on
    {{ slots.date|format_date("EEEE, MMMM d") }} at
    {{ slots.time|format_time("h:mm a") }}.
```
:::tip
After adding or changing the extensions you should restart the bot.
:::

Test the node again.

```
🧑 Can 6 of us get a table for lunch tomorrow at 5pm?
🤖 OK. I am making you a reservation for 6 on Friday, January 27 at 5:00 PM.
```

You have successfully improved the format that the dialog uses when it references variable values in its responses. The dialog now uses `Friday, January 27` instead of the more technical, `2023-01-27`. And it uses `5:00 PM` instead of `17:00:00`.

## Validate user input

So far, we have assumed that the user will provide the appropriate value types for the slots. That is not always the case in reality. You can account for times when users might provide an invalid value by adding `found` responses to slots. In this section, you will use conditional slot responses to perform the following tasks.

* Validate the user's input.
* Confirm the user's input.
* Indicate that you are replacing one value with another.

### Enable datetime extension

You need to enable [datetime extension](/extensions/datetime.md) to validate dates.

```yaml
extensions:
  babel: { locale: en }
# highlight-next-line
  datetime: {}
```

This extension allows you to use the following template filters for variables.

* `x|date` - It converts value to the date object.
* `x|time` - It converts value to the time object.

The date and time objects can be compared using standard comparison operators `>`, `<` and so on.


### Ensure that the date is not in the past

Add the `found` response for the `slots.date` slot. Use the following if-condition to check whether the date that the user specifies falls before today.

```yaml
- name: date
  check_for: entities.date
  prompt: |
      What day would you like to come in?
# highlight-start
  found: |
      {% if slots.date|date < utc_time.astimezone(""|tz)|date %}
        You cannot make a reservation for a day in the past.
        <prompt_again />
      {% else %}
        {{ slots.date|format_date("EEEE, MMMM d") }} it is.
      {% endif %}
# highlight-end
```

The template global `utc_time` is used to determine the current date and time ([datetime](https://docs.python.org/3/library/datetime.html#datetime-objects)).
By calling `utc_time.astimezone(""|tz)`, we get the local date and time (for current machine).

If date is in the past, the bot uses `promt_again` command to clear the value of the slot and prompt it again. The else-clause is executed if the user provides a valid date. It displays a simple confirmation lets the user know that her response was understood.

### Check whether a time falls within the seating time window

Add the `found` response for the `slots.time` slot. Use the following if-conditions  to check whether the time that the user specifies falls within the allowed time window.

```yaml
- name: time
  check_for: entities.time
  prompt: |
      What time do you want the reservation to be made for?
# highlight-start
  found: |
      {% if slots.time|time > "21:00:00"|time %}
        Our last seating is at 9 PM.
        <prompt_again />
      {% elif slots.time|time < "09:00:00"|time %}
        Our first seating is at 9 AM.
        <prompt_again />
      {% else %}
        Ok, the reservation is for {{ slots.time|format_time("h:mm a") }}.
      {% endif %}
# highlight-end
```

If time is invalid, the bot uses `promt_again` command to clear the value of the  slot and prompt it again. The else-clause is executed if the user provides a valid time. It displays a simple confirmation lets the user know that her response was understood.

### Track the change in the number of guests

Edit the `slots.guests` slot to validate the value provided by the user in the following ways.

* Check that the number of guests specified is larger than zero.
* Anticipate and address the case when the user changes the number of guests.

If, at any point while the node with slots is being processed, the user changes a slot value, the corresponding slot variable value is updated. However, it can be useful to let the user know that the value is being replaced, both to give clear feedback to the user and to give the user a chance to rectify it if the change was not what she intended.

Track the change in the number of guests using the special variables available in the found response: `previous_value` and `current_value`. These variables contain the previous and current value of the slot being filled.

```yaml
- name: guests
  check_for: entities.number
  prompt: |
      How many people will be dining?
  found: |
      {% if slots.guests < 1 %}
          Please specify a number that is larger than 0.
          <prompt_again />
      {% elif previous_value and previous_value != current_value %}
          Ok, updating the number of guests from {{ previous_value }}
          to {{ current_value }}.
      {% else %}
          Ok. The reservation is for {{ slots.guests }} guests.
      {% endif %}
```

## Add a confirmation slot

You might want to design your dialog to call an external reservation system and actually book a reservation for the user in the system. Before your application takes this action, you probably want to confirm with the user that the dialog has understood the details of the reservation correctly. You can do so by adding a confirmation slot to the node.

### Add intents

The confirmation slot will expect a Yes or No answer from the user. You must teach the dialog to be able to recognize a Yes or No intent in the user input first.

```yaml
  - name: "yes"
    examples:
      - "Yes"
      - Sure
      - I'd like that
      - Please do.
      - Yes please.
      - Ok
      - That sounds good.
  - name: "no"
    examples:
      - "No"
      - No thanks.
      - Please don't.
      - Please do not!
      - That's not what I want at all
      - Absolutely not.
      - No way
```

### Add a slot

Add the following slot to the dialog node. This slot must be the last slot in the node's list of slots.

```yaml
- name: confirmation
  check_for: slot_in_focus and (intents.yes or intents.no)
  prompt: |
      I'm going to reserve you a table for {{ slots.guests }} on
      {{ slots.date|format_date("EEEE, MMMM d") }} at
      {{ slots.time|format_time("h:mm a") }}. Should I go ahead?
```

The `check_for` condition checks for either answer. You will specify what happens next depending on whether the user answer Yes or No by using if-condition in `found` response.

The `slot_in_focus` property forces the scope of this condition to apply to the current slot only. This setting prevents random statements that could match against `intents.yes` or `intents.no` that the user might make from triggering this slot.

For example, the user might be answering the number of guests slot, and say something like, *"Yes, there will be 5 of us"*. You do not want the *"Yes"* included in this response to accidentally fill the confirmation slot. By adding the `slot_in_focus` property to the condition, a yes or no indicated by the user is applied to this slot only when the user is answering the prompt for this slot specifically.

### Add `found` response

Add the found response with if-condition that checks for a No response (`intents.no`). In this case, start requesting slots again. Otherwise, you can assume the user confirmed the reservation details and proceed with making the reservation.

```yaml
# ...
found: |
    {% if intents.no %}
        Alright. Let's start over. I'll try to keep up this time.
        {% delete slots.date %}
        {% delete slots.time %}
        {% delete slots.guests %}
        {% delete slots.confirmation %}
    {% endif %}
```

In order for the bot to start requesting slots, you need to delete their current values. Do this by using `{% delete ... %}` tag.

### Add `not_found` response

In the `not_found` response, clarify that you are expecting the user to provide a Yes or No answer. Add a response with the following values.

```yaml
# ...
not_found: |
    Respond with Yes to indicate that you want the reservation to be made
    as-is, or No to indicate that you do not.
```

### Prevent repetitive responses

Now that you have confirmation responses for slot values, and you ask for everything at once, you might notice that the individual slot responses are displayed before the confirmation slot response is displayed, which can appear repetitive to users. For example,

```
🧑 Can 6 of us get a table for lunch on May 29, 2023 at 5pm?
🤖 Monday, May 29 it is.
🤖 Ok, the reservation is for 5:00 PM.
🤖 Ok. The reservation is for 6 guests.
🤖 I'm going to reserve you a table for 6 on Monday, May 29 at 5:00 PM. Should I go ahead?
```

Edit the slot found responses to prevent them from being displayed under certain conditions. Replace the else-clause that is specified in the `found` responses with the following ones:

```yaml
- name: date
  check_for: entities.date
  prompt: |
      What day would you like to come in?
  found: |
      {% if slots.date|date < now|date %}
        You cannot make a reservation for a day in the past.
        <prompt_again />
# highlight-next-line
      {% elif not entities.time and not entities.number %}
        {{ slots.date|format_date("EEEE, MMMM d") }} it is.
      {% endif %}
```

```yaml
- name: time
  check_for: entities.time
  prompt: |
      What time do you want the reservation to be made for?
  found: |
      {% if slots.time|time > "21:00:00"|time %}
        Our last seating is at 9 PM.
        <prompt_again />
      {% elif slots.time|time < "09:00:00"|time %}
        Our first seating is at 9 AM.
        <prompt_again />
# highlight-next-line
      {% elif not entities.date and not entities.number %}
        Ok, the reservation is for {{ slots.time|format_time("h:mm a") }}.
      {% endif %}
```

```yaml
- name: guests
  check_for: entities.number
  prompt: |
      How many people will be dining?
  found: |
      {% if slots.guests < 1 %}
          Please specify a number that is larger than 0.
          <prompt_again />
      {% elif previous_value and previous_value != current_value %}
          Ok, updating the number of guests from {{ previous_value }}
          to {{ current_value }}.
# highlight-next-line
      {% elif not entities.date and not entities.time %}
          Ok. The reservation is for {{ slots.guests }} guests.
      {% endif %}
```

This prevent repetitive responses:

```
🧑 Can 6 of us get a table for lunch on May 29, 2023 at 5pm?
🤖 I'm going to reserve you a table for 6 on Monday, May 29 at 5:00 PM. Should I go ahead?
```

If you add more slots later, you must edit these conditions to account for the associated context variables for the additional slots.

## Give a way to exit the process

Adding a node with slots is powerful because it keeps users on track with providing the information you need to give them a meaningful response or perform an action on their behalf. However, there might be times when a user is in the middle of providing reservation details, but decides to not go through with placing the reservation. You must give users a way to exit the process gracefully. You can do so by adding a slot handler that can detect a user's desire to exit the process, and exit the node without saving any values that were collected.

### Add intent

You must teach the dialog to be able to recognize an `intents.exit` intent in the user input first. Add the `intents.exit` intent with the following example utterances.

```yaml
  - name: exit
    examples:
      - I want to stop
      - Exit!
      - Cancel this process
      - I changed my mind. I don't want to make a reservation.
      - Stop the reservation
      - Wait, cancel this.
      - Nevermind.
```

### Add slot handler

Add the following slot handler to the node. The `response` command jumps directly to the node-level response without displaying the prompts associated with any of the remaining unfilled slots.

```yaml
- condition: intents.reservation
  label: reservation
  slot_filling:
      # ...
# highlight-start
  slot_handlers:
    - condition: intents.exit
      response: |
        Ok, we'll stop there. No reservation will be made.
        <response />
# highlight-end
  response: |
      OK. I am making you a reservation for {{ slots.guests }}
      on {{ slots.date }} at {{ slots.time }}.
```

### Modify node-level response

Now, you need to edit the node-level response to make it recognize when a user wants to exit the process rather than make a reservation. Add an if-condition for the response.

```yaml
- condition: intents.reservation
  label: reservation
  slot_filling:
      # ...
  slot_handlers:
    - condition: intents.exit
      response: |
        Ok, we'll stop there. No reservation will be made.
        <response />
# highlight-start
  response: |
      {% if slots.confirmation %}
        OK. I am making you a reservation for {{ slots.guests }} on
        {{ slots.date|format_date("EEEE, MMMM d") }} at
        {{ slots.time|format_time("h:mm a") }}.
      {% else %}
        I look forward to helping you with your next reservation.
        Have a good day.
      {% endif %}
# highlight-end
```

The `slots.confirmation` condition is set to true when the user has filled in all the slots and confirmed them. The `intents.exit` handler skips all remaining slots to go directly to the node response. So, when the `slots.confirmation` slot is not filled, you know the `intents.exit` intent was triggered, and the dialog can display an alternate response.

### Run and test

Test this change by using the following script.

```
🧑 i'd like to make a reservation.
🤖 What day would you like to come in?
🧑 Nevermind
🤖 Ok, we'll stop there. No reservation will be made.
🤖 I look forward to helping you with your next reservation. Have a good day.
```

## Limit failed attempts

In some cases, a user might not understand what you are asking for. They might respond again and again with the wrong types of values. To plan for this possibility, you can add a counter to the slot, and after 3 failed attempts by the user to provide a valid value, you can apply a value to the slot on the user's behalf and move on.

For the `slots.time` information, you will define a follow-up statement that is displayed when the user does not provide a valid time. You will need one more slot variable `slots.count` that can keep track of how many times the user provides a value that does not match the value type that the slot expects. You want the slot variable to be initialized and set to 0 the first time it is processed, so you will use it with the `x|default` filter.

Add the following `not_found` response to the `slots.time` slot.

```yaml
- name: time
  check_for: entities.time
  prompt: |
      What time do you want the reservation to be made for?
  found: |
      {% if slots.time|time > "21:00:00"|time %}
        Our last seating is at 9 PM.
        <prompt_again />
      {% elif slots.time|time < "09:00:00"|time %}
        Our first seating is at 9 AM.
        <prompt_again />
      {% elif not entities.date and not entities.number %}
        Ok, the reservation is for {{ slots.time|format_time("h:mm a") }}.
      {% endif %}
# highlight-start
  not_found: |
      {% if slots.counter|default(0) > 1 %}
          {% set slots.time = '20:00' %}
          You seem to be having trouble choosing a time.
          I will make the reservation at 8PM for you.
      {% else %}
          {% set slots.counter = slots.counter|default(0) + 1 %}
          Please specify the time that you want to eat.
          The restaurant seats people between 9AM and 9PM.
      {% endif %}
# highlight-end
```

Remember, the `not_found` response is only triggered when the user does not provide a valid `slots.time` value. An if-condition checks the number of attempts: 0, 1 and more. When it exceeds, the bot assigns the time value on the user's behalf to the popular dinner reservation time of 8 PM. Don't worry; the user will have a chance to change the time value when the confirmation slot is triggered. The counter value is incremented whenever the user enters an invalid `slots.time` value.

### Run and test

Test your changes by using the following script.

```
🧑 i'd like to make a reservation on May 29
🤖 2023-05-29 it is.
🤖 What time do you want the reservation to be made for?
🧑 orange
🤖 Please specify the time that you want to eat. The restaurant seats people between 9AM and 9PM.
🧑 pink
🤖 Please specify the time that you want to eat. The restaurant seats people between 9AM and 9PM.
🧑 purple
🤖 You seem to be having trouble choosing a time. I will make the reservation at 8PM for you.
🤖 How many people will be dining?
```

## Conclusion

In this tutorial you tested a node with slots and made changes that optimize how it interacts with real users. For more information about this subject, see [Slot Filling](/design-guides/slot-filling.md) guide.
