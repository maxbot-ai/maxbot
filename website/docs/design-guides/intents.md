# Intents

Intents are purposes or goals that are expressed in a user input, such as answering a question or making a reservation.

MaxBot detects intents in user input using an NLU model trained on your examples. You access recognized intents using `intents` variable in conditions and responses.

## Define Intents

Create an intent by providing a short name and examples of utterances that user typically use to indicate their goal.

```yaml
- name: reservation
  examples:
    - i'd like to make a reservation
    - I want to reserve a table for dinner
    - do you have openings for next Wednesday at 7?
    - Is there availability for 4 on Tuesday night?
    - i'd like to come in for brunch tomorrow
- name: about_restaurant
  examples:
    - Tell me about the restaurant
    - i want to know about you
    - What's your story?
    - Where do you source your produce from?
```

The examples are used by the NLU model to recognize the same and similar types of utterances and map them to the appropriate intent. Start with a few examples and add them as needed.

## Access Intents

### Checking for Recognized Intent

Use expressions like `intents.reservation` in the dialog tree conditions to chose the correct dialog node for respond to the user.

```yaml
- condition: intents.reservation
  response: |
    Let's book a table for you...
- condition: intents.about_restaurant
  response: |
    Food Lovers is an unique restaurant...
```

If, for example, the user input is asking to make a reservation, then the `intents.reservation` condition evaluates to true and the node with this condition is processed.

### Intents Ranking

The `intents.ranking` list contains intents that were recognized in the user input, sorted in descending order of confidence.

Each intent has two attributes: name and confidence. The confidence property is a decimal percentage that represents the NLU models's confidence in the recognized intent.

While testing your dialog, you can see details of the intents that are recognized in user input by specifying this expression in a dialog node response:

```
{% debug intents.ranking %}
```

You will get the output like this.

```
(
    RecognizedIntent(name='reservation', confidence=0.61),
    RecognizedIntent(name='about_restaurant', confidence=0.33)
)
```

### Top Intent

Typically, the dialog logic address the single intent. The `intents.top` expression gives you access to information about the recognized intent with highest confidence score above a certain threshold defined by the NLU model.

If the user input is asking to make a reservation, then the `intents.top` will contain information about the reservation intent.

```
{% debug intents.top %}
-> RecognizedIntent(name='reservation', confidence=0.6)
```

You can use expressions like `intents.top == 'reservation'` to check if the user input is asking to make a reservation. But there is a more convenient equivalent expression `intents.reservation`. If the reservation intent is a top intent, this expression will return intent information and evaluate to true.

```
{% debug intents.reservation %}
-> RecognizedIntent(name='reservation', confidence=0.6)
```

Otherwise the `intents.reservation` expression will evaluate to false.

You can find any recognized intents with intent names that start with 'ask_', using a syntax like this.

```yaml
- condition: intents.top and intents.top.name.startswith('ask_')
  response: |
    {# ... #}
```

First, we check that `intents.top` is defined because it is only present when some intent is recognized from user input.

### Checking for Irrelevant Input

The `intents.irrelevant` condition will evaluate to true if the user sends a text message and MaxBot could not recognize any intent in that message. You can use it as an "anything else" condition at the end of the node list.
