import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Digressions


A digression occurs when the user is in the middle of a topic discussion abruptly switches to a different topic. The bot has always supported the user's ability to change topics. They can change topics, follow the new unrelated topic to its end, and then return to where they were before.

For example, the user might be ordering a new phone, but switches topics to ask about tablets. The bot can answer the question about tablets, and then bring the user back to where they left off in the process of ordering a phone.

The result is a dialog flow that more closely simulates a human-to-human conversation.

## Overview

To discuss a topic, the bot uses a **dialog branch** one of the types:

* [followup nodes](dialog-tree.md#followup-nodes) of a parent node;
* [slot filling](slot-filling.md) of a node;
* sibling nodes of a node we [jumped to and wait for user input](dialog-tree.md#jump-to-listen).

Digression between topics in terms of dialog nodes and branches looks as follows.

* If none of the nodes or slots in the dialog branch that is being processed match the user input, the bot goes back out to the root nodes to check for an appropriate match, thus *a digression occurs*.
* If the bot finds the matching root node, then *digression succeeds*. The bot starts processing this new node.
    * After new node and its branches are completed, the bot will return to the branch that was interrupted.
* If the bot does not find a matching root node, then *user input is not understood* at all. The bot immediately returns to the original branch, to let it process the misunderstanding.

You do not define the start and end of a digression. The user is entirely in control of the digression flow at run time. You only specify how each node should or should not participate in a user-led digression. You can tailor the digression behavior using digression settings, control commands and special variables.

Digressions can only target the root nodes of the dialog tree. Followup nodes cannot be the target of a digression. The details of the digression behavior depend on the *type of dialog branch* from which the digression occurs.

### Followup Nodes

Digression occurs when the parent node's response is displayed and none of the followup nodes match the user input. When returning after digression, the bot displays the parent node's response again.

For example, the restaurant bot talks about two topics: opening hours and vacancies.

```yaml
- condition: intents.restaurant_opening_hours
  response: |
    The restaurant is open from 8am to 8pm.
- condition: intents.job_opportunities
  label: job_opportunities
  response: |
    What kind of work are you interested in?
  followup:
    - condition: entities.job_role.wait_staff
      response: |
        We do need wait staff. Please send a resume...
    - condition: entities.job_role.greeter
      response: |
        Yes, we have openings! Please come to...
    - condition: entities.job_role.chef
      response: |
        Sorry, there are no vacancies yet.
```

During the discussion of vacancies, the bot displays the response of the parent node, "What kind of work are you interested in?". Then it waits for the user to provide the name of one of the vacancies. However, the user can write anything, for example, ask "When does the restaurant open?". Upon receiving this unexpected input, the bot digresses into the root node about opening hours. After giving the answer, it returns to the parent node and repeats its question about vacancies.

```
🧑 Are you hiring?
🤖 What kind of work are you interested in?
🧑 When does the restaurant open?
🤖 The restaurant is open from 8am to 8pm.
🤖 What kind of work are you interested in?
🧑 waiter
🤖 We do need wait staff. Please send a resume...
```

### Slot Filling

During the slot filling, digression occurs when user input is provided and  all of the following a true:

* none of the slots in the node are filled successfully;
* no slot handlers are understood.

When returning after digression to the slot filling the bot do the following.

* If the user input was not understood and the *last prompted slot* has a `not_found` response, the bot displays it to resolve the misunderstanding.
* Otherwise, the bot displays `prompt` response for the *first unfilled slot*, to encourage the user to continue providing information.

See [Slot Filling Flow](slot-filling.md#flow) for more details.

Let's look at digressions away from slot filling using the restaurant reservation example.

```yaml
- condition: intents.restaurant_opening_hours
  response: |
    The restaurant is open from 8am to 8pm.
- condition: intents.book_restaurant
  label: book_restaurant
  slot_filling:
    - name: date
      check_for: entities.date
      prompt: |
        When do you want to go?
    - name: time
      check_for: entities.time
      prompt: |
        What time do you want to go?
    - name: guests
      check_for: entities.number
      prompt: |
        How many people will be dining?
  response: |
    OK. I am making you a reservation.
```

Been prompted for the booking time, the user changes the topic and asks about opening hours. This user input does not fills any slot and slot handlers are missing. Thus the bot digresses into the root node, which answers the question about opening hours. After giving the answer, the bot returns to the slot filling and repeats its prompt for the booking time.

```
🧑 Book me a restaurant
🤖 When do you want to go?
🧑 Tomorrow
🤖 What time do you want to go?
🧑 What time do you close?
🤖 The restaurant is open from 8am to 8pm.
🤖 What time do you want to go?
🧑 ...
```

### Jump to a node

After receiving the `jump_to: {transition: listen, ...}` command, the bot waits for new input from the user, and then begins to process it from the node that you jump to. As stated above, digression occurs when neither the node you jumped to nor its subsequent sibling nodes match the user input.

* If the destination node of jump_to is *a root node*, the digression *doesn't occur*.

* If the destination node of jump_to is *not a root node*, the digression *occur*.

The bot never returns after such digressions, so use `jump_to` command with `transition: listen` to only address possible questions from the user that can safely be ignored.

### Digression chains

If a user digresses away from the current node to another node, the user could potentially digress away from that other node, and repeat this pattern one or more times again. If all subsequent nodes will return after the digression then the user will eventually be brought back to the current dialog node. The [return chain can be broken](#end-command) by the `end` control command. Test scenarios that digress multiple times to determine whether individual nodes function as expected.

## Digression Control

### Custom return message {#custom-return-message}

For the parent node, consider adding wording that lets users know they are returning to where they left off in a previous topic. Use a special variable `returning` that lets you add two versions of the response. Let's change the previous example a little.

```yaml
#...
- condition: intents.job_opportunities
  label: job_opportunities
  response: |
      {% if returning %}
        Now let's get back to where we left off. <br />
        What kind of work are you interested in?
      {% else %}
        What kind of work are you interested in?
      {% endif %}
  followup:
      #...
```

The dialog will change as follows

```
🧑 Are you hiring?
🤖 What kind of work are you interested in?
🧑 When does the restaurant open?
🤖 The restaurant is open from 8am to 8pm.
🤖 Now let's get back to where we left off.
   What kind of work are you interested in?
🧑 ...
```

### Dealing with misunderstanding
TODO: Currently we have no way to know if the digression was successful or user input was not understood at all. Do we have real use cases?


### Never return to the node

You can choose whether you want the conversation to come back to the parent node after a digression. Change the `after_digression_followup` setting of the parent node to one of the values:

* `allow_return` (default) - allows return from digression and continue to process followup nodes;
* `never_return` - prevent the dialog from returning to the parent node.

You might not want the dialog to return to where it left off, especially, if the followup nodes only address possible questions from the user that can safely be ignored. For example, the bot talks about cupcakes and ready to tell more if the user asks.

<Tabs
    defaultValue="snippet"
    values={[
        {label: 'Snippet', value: 'snippet'},
        {label: 'Full', value: 'full'},
    ]}>
<TabItem value="snippet">

  ```yaml
  - condition: intents.restaurant_opening_hours
    response: |
      The restaurant is open from 8am to 8pm.
  - condition: intents.about_cupcakes
    label: about_cupcakes
    settings:
        after_digression_followup: never_return
    response: |
      We offer cupcakes in a variety of flavors and sizes.
    followup:
      - condition: intents.about_flavors
        response: |
          We offer vanilla, banana...
      - condition: intents.about_sizes
        response: |
          There are mini, standard and jumbo cupcakes...
  ```

</TabItem>
<TabItem value="full">

  ```yaml
  channels:
    telegram:
      api_token: !ENV ${TELEGRAM_API_KEY}
  intents:
    - name: restaurant_opening_hours
      examples:
        - When does the restaurant close?
        - When is the restaurant open?
        - What are the restaurant opening hours
        - Restaurant openin hours
        - What time do you close?
        - When do you close?
        - When do you open?
        - At what time do you open?
    - name: about_cupcakes
      examples:
        - Do you have cupcakes?
        - Do you serve cupcakes?
        - Can I order cupcakes from you?
        - Are there cupcakes on the menu?
    - name: about_flavors
      examples:
        - What flavors do you have?
        - How many flavours of cakes?
    - name: about_sizes
      examples:
        - What size are cakes?
  dialog:
    - condition: intents.restaurant_opening_hours
      response: |
        The restaurant is open from 8am to 8pm.
    - condition: intents.about_cupcakes
      label: about_cupcakes
      settings:
          after_digression_followup: never_return
      response: |
        We offer cupcakes in a variety of flavors and sizes.
      followup:
        - condition: intents.about_flavors
          response: |
            We offer vanilla, banana...
        - condition: intents.about_sizes
          response: |
            There are mini, standard and jumbo cupcakes...
  ```

</TabItem>
</Tabs>

But the user is not interested in the details about the cupcakes and changes the topic. So the bot does not return to the cupcakes.

```
🧑 Do you have cupcakes?
🤖 We offer cupcakes in a variety of flavors and sizes.
🧑 When does the restaurant open?
🤖 The restaurant is open from 8am to 8pm.
```

Compare this sample conversation with the previous ones.

### Skip digression into the node {#check-digressing}

You might find that some root node is triggered too often, or at unexpected times. You can prevent users from being able to digress into it by checking the special condition `digressing` which evaluates to true only during the digression.

For example, this node will never be triggered during digressions.

```yaml
- condition: intents.some_intent and not digressing
  response: |
    {# ... #}
```
Also, the `digressing` condition can be checked in response. Next example shows how to prevent from jumping to a specific node in digression:

```yaml
- condition: intents.some_intent
  response: |
    ...
    {% if not digressing %}
      <jump_to node="some_node" transition="response" />
    {% endif %}
```

### Break digression chain {#end-command}

In some cases, you might want to prevent a return to the interrupted branch	. You can use control command `end` to prevent a return from a specific node.

For example, you can add the root node with intent condition that address cancellation request as a way to prevent users from getting stuck in your dialog branches. The `end` control command prevents the digression return from happening from this node.

```yaml
- condition: intents.cancel
  response: |
    OK. We're canceling for now. Have a nice day!
    <end />
```

When receiving user input "cancel this", the bot digress away to the cancellation root node. Then the proper response is displayed, and the reservation branch that was interrupted is not resumed.

```
🧑 Book me a restaurant
🤖 When do you want to go?
🧑 cancel this
🤖 OK. We're canceling for now. Have a nice day!
```

If there is a digression chain, the `end` control command not only prevents returning to the interrupted branch, but also breaks the whole chain of returns.

## Design Considerations

### Remember that branches get priority over root nodes

Root nodes are only considered as digression targets if the current branch  cannot address the user input. It is even more important in a node with slots. Any slot can be filled during the slot filling process. So, a slot might capture user input unexpectedly.

Back to the booking example. In the conversation below, the bot captures the booking time when the user just asks for the opening time.

```
🧑 Can I reserve a table for 2 of us tomorrow?
🤖 What time do you want to go?
🧑 Are you open after 6pm?
🤖 OK. I am making you a reservation.
```

If you define a clear confirmation statement, such as, "Ok, setting the reservation time to 6pm", the user is more likely to realize there was a miscommunication and correct it.

### Avoid "anything else" conditions in branches {#avoid-anything-else}

The bot might not digress away parent node as you expect if any of its followup nodes contain `true` or some other anything else condition. The digression away from slot filling is also made impossible when you use "anything else" condition in [slot handlers](slot-filling.md#slot-handlers).

In the example, `message.text` "anything else" condition is used to return a generic message and prompt again if the user input does not match any anticipated vacancy.

```yaml
- condition: intents.restaurant_opening_hours
  response: |
    The restaurant is open from 8am to 8pm.
- condition: intents.job_opportunities
  label: job_opportunities
  response: |
    What kind of work are you interested in?
  followup:
    - condition: entities.job_role.wait_staff
      response: |
        We do need wait staff. Please send a resume...
    - condition: entities.job_role.greeter
      response: |
        Yes, we have openings! Please come to...
    - condition: entities.job_role.chef
      response: |
        Sorry, there are no vacancies yet.
    - condition: message.text
      response: |
        Can't find a suitable job. You can try rephrasing.
        <jump_to node="job_opportunities" transition="response" />
```

This way, the bot returns generic response even if the user input matches against different root node.

```
🧑 Are you hiring?
🤖 What kind of work are you interested in?
🧑 When does the restaurant open?
🤖 Can't find a suitable job. You can try rephrasing.
🤖 What kind of work are you interested in?
```

Rather than responding with a generic message, you can effectively put all of the root nodes to work to try to address the user input. Just move the "anything else" node from the branch to the **root level**.

```yaml
- condition: intents.restaurant_opening_hours
  response: |
    The restaurant is open from 8am to 8pm.
- condition: intents.job_opportunities
  label: job_opportunities
  response: |
    What kind of work are you interested in?
  followup:
    - condition: entities.job_role.wait_staff
      response: |
        We do need wait staff. Please send a resume...
    - condition: entities.job_role.greeter
      response: |
        Yes, we have openings! Please come to...
    - condition: entities.job_role.chef
      response: |
        Sorry, there are no vacancies yet.
- condition: message.text
  response: |
    I didn't understand. You can try rephrasing.
```

Now the bot can address any root node at any time.

```
🧑 Are you hiring?
🤖 What kind of work are you interested in?
🧑 When does the restaurant open?
🤖 The restaurant is open from 8am to 8pm.
🤖 What kind of work are you interested in?
```

And the root-level "anything else" node can always respond to input that none of the other root nodes can address.

```
🧑 Are you hiring?
🤖 What kind of work are you interested in?
🧑 I can do everything
🤖 I didn't understand. You can try rephrasing.
🤖 What kind of work are you interested in?
```

### Reconsider jumps to a closing node

Many dialogs are designed to ask a standard closing question, such as, "Did I answer your question today?" This prevents digressions from returning as expected.

TODO: We also use this to display main menu. Need to rethink and implement our solution.
