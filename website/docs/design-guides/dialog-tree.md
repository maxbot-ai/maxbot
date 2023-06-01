import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Dialog Tree

## Overview

The dialog tree defines what your assistant says in response to customers. A tree is composed of multiple nodes. Each node contains, at a minimum, a condition and a response.

* *Condition* specifies the information that must be present in the user input for this node to be used in the conversation. The information is typically a specific intent. It might also be an entity or a state variable value and more.
* *Response* is the utterance that bot uses to respond to the user. More generally, the response is a makrdown document that can contain a set of bot commands in the XML elements form.

The dialog tree that you create is processed by your bot from the first node in the tree to the last. As it travels down the tree, if your bot finds a node with a condition that is met, it triggers node's response. You can think of the node as having an if/then construction: if this condition is true, then return this response.

Various tree traversal schemas implement various aspects of conversational logic, such as changing the topic of conversation, follow-up questions, etc.

## Root Nodes {#root-nodes}

While single node answers single user question, you should create multiple nodes to answer multiple questions. These nodes are processed by the bot sequentially from the first to the last. As soon as the  bot finds a condition that is met, it triggers response. This completes the processing.

```yaml
dialog:
  - condition: intents.greeting
    response: |
        Good day to you!
  - condition: intents.about_you
    response: |
        My name is MaxBot.
  - condition: intents.ending
    response: |
        OK. See you later.
```

Communication can be like this.

```
🧑 hello
🤖 Good day to you!
🧑 describe yourself
🤖 My name is MaxBot.
🧑 bye
🤖 OK. See you later.
```

If the bot could not find a suitable node, then it cannot answer the question, ignores user input and proceeds to wait for the next one.

```
🧑 hello
🤖 Good day to you!
🧑 how are you
🧑 what you can do?
🧑 bye
🤖 OK. See you later.
```

Typically, the last node in the list contains an "anything else" condition that is always met, such as `true`. This allows the bot to respond to absolutely all user input (for example, saying "didn't understand you"). Here is an example of such dialog.

```yaml
dialog:
  - condition: intents.greeting
    response: |
        Good day to you!
  - condition: intents.ending
    response: |
        OK. See you later.
  # using the condition that is always met
  - condition: true
    response: |
        Sorry I don't understand.
```

```
🧑 hello
🤖 Good day to you!
🧑 how are you
🤖 Sorry I don't understand.
🧑 what you can do?
🤖 Sorry I don't understand.
🧑 bye
🤖 OK. See you later.
```

It is important to order the nodes correctly, as they are bypassed in the exact order in which they appear in the tree. Even if the condition is met for several nodes, the response will only triggered for the first one. The following dialog contains two nodes that handle the same user intent.


```yaml
dialog:
  - condition: intents.greeting
    response: |
        Good day to you!
  # this node will never triggered
  - condition: intents.greeting
    response: |
        Glad to see you!
```

```
🧑 hello
🤖 Good day to you!
🧑 hello again
🤖 Good day to you!
```

The user will never see the response "Glad to see you!".

## Followup Nodes {#followup-nodes}

### Ask follow up questions

Suppose the user asked a question to the bot, and the bot determined that a certain node should answer. It often happens that the bot cannot immediately answer the question, as it needs additional information from the user. You need to add followup nodes to ask followup questions to the user.

```yaml
dialog:
  - condition: intents.menu
    label: menu
    response: |
      Which menu do you want to see?
      {# instructs bot to wait for user input #}
      <listen />
    followup:
      - condition: entities.menu.standard
        response: |
            To see our menu, go to the ...
      - condition: entities.menu.vegetarian
        response: |
            To see our vegetarian menu, go to the ...
      - condition: entities.menu.cake
        response: |
            To see our cake shop menu, go to the ...
```

You must give a unique label to the parent node so that the bot can persistently store the dialog state associated with that node.

The parent node's response ends with the `listen` control command. This command instructs the bot to wait for the user to provide new input that the response elicits. The dialog will not progress until the user provides more input. `listen` is the default command, so you don't have to specify it explicitly. We have done this for clarity.

The dialog may looks like

```
🧑 I want to see a menu
🤖 Which menu do you want to see?
🧑 Cake shop
🤖 To see our cake shop menu, go to the ...
```

If none of the followup nodes conditions are met, then the bot was unable to extract the additional information it needed from the user's input.
Perhaps the user wants to talk about something else. In this case, the further actions of the bot are determined by the [digression](digressions.md) mechanism.

### Chaining conditions

The parent node may determine that all the necessary information is already contained in the user input. In this case followup question is not required, and you should immediately chain the parent node's condition with the conditions of followup nodes.

```yaml
dialog:
  - condition: intents.menu and entities.menu
    label: menu
    response: |
      Always happy to meet your needs!
      {# process followup nodes without waiting for user input #}
      <followup />
    followup:
      - condition: entities.menu.standard
        response: |
            To see our menu, go to the ...
      - condition: entities.menu.vegetarian
        response: |
            To see our vegetarian menu, go to the ...
      - condition: entities.menu.cake
        response: |
            To see our cake shop menu, go to the ...
```

The `followup` command is not set by default, so you must specify it explicitly.

The `followup` control command instructs the bot to skip waiting for user input and go directly to the followup nodes instead. The bot processes followup nodes, selects a suitable one for which the condition is met and sends the final response to the user.

```
🧑 do you serve desserts?
🤖 Always happy to meet your needs!
🤖 To see our cake shop menu, go to the ...
```

You must ensure that one of the followup conditions is met in order to respond to the user. Otherwise, an error will occur, further processing of the nodes will be interrupted and the bot will return to its initial state.

In the example, no error will occur, since the parent condition checks `entities.menu`, which will necessarily take one of three values. An error is possible if a new value is added to the `entities.menu`, but a followup node is not added to process it.


## `jump_to` another Node {#jump_to}

The `jump_to` control command instructs the bot to jump from one node directly to another (target) node. This command takes two arguments:

* `node` - the unique label of the target node,
* `transition` - specifies how the target node is processed, the options are described below.

### Chaining responses

The bot does not evaluate the condition of the target node and immediately triggers response. Response targeting is useful for chaining responses of several nodes together. If the target node has another `jump_to` command, that command is run immediately, too.

Let's illustrate how the `jump_to` command with the `response` transition works with an order cancellation scenario.

```yaml
dialog:
  - condition: intents.cancel_order
    label: ask_order_number
    response: |
        What is the order number?
    followup:
      - condition: entities.order_number
        response: |
            OK. The order is canceled.
      - condition: true
        response: |
          I need the order number to cancel the order for you.
          <jump_to node="ask_order_number" transition="response" />
```

After a followup question from the bot, the user does not provide the order number. Then the bot jumps to the `ask_order_number` node and immediately triggers node's response, which causes the bot to ask the followup question again. The bot will keep asking for the order number until it receives it.

```
🧑 I want to cancel my order.
🤖 What is the order number?
🧑 I didn't remember
🤖 I need the order number to cancel the order for you.
🤖 What is the order number?
🧑 I don't know
🤖 I need the order number to cancel the order for you.
🤖 What is the order number?
🧑 AB12345
🤖 OK. The order is canceled.
```

In the example, the last node in the list contains a `true` condition. This ensures that one of the followup nodes triggers during processing. This is not always convenient, since the bot cannot digress and the user loses the opportunity to change the dialog topic. The [Digressions](digressions.md) section will show how to both be able to digress to change the topic and re-question the user when he gives inappropriate/irrelevant answers.

### Chaining conditions

The bot checks first whether the condition of the targeted node evaluates to true.

* If the condition evaluates to true, the bot processes the target node immediately.
* If the condition does not evaluate to true, the bot moves to the next sibling node of the target node to evaluate its condition, and repeats this process until it finds a node with a condition that evaluates to true.
* If the bot processes all the siblings and none of the conditions evaluate to true, the bot returns to its initial state.

Condition targeting is useful for chaining the conditions of several nodes. Chaining conditions helps to structure larger dialog trees. For example, let's combine two trees from the restaurant menu examples above into a bigger one.

```yaml
dialog:
  - condition: intents.menu and entities.menu
    response: |
      Always happy to meet your needs!
      <jump_to node="menu_start" transition="condition" />
  - condition: intents.menu
    label: menu
    response: |
        Which menu do you want to see?
    followup:
      - label: menu_start
        condition: entities.menu.standard
        response: |
            To see our menu, go to the ...
      - condition: entities.menu.vegetarian
        response: |
            To see our vegetarian menu, go to the ...
      - condition: entities.menu.cake
        response: |
            To see our cake shop menu, go to the ...
```

The bot processes the same followup nodes in two ways. In the first case, as the bot requires additional information it asks followup question and processes followup nodes after receiving an answer.

```
🧑 I want to see a menu
🤖 Which menu do you want to see?
🧑 Cake shop
🤖 To see our cake shop menu, go to the ...
```

In the second case all the necessary information is already contained in the user input, so the bot immediately chains conditions of the same followup nodes.

```
🧑 do you serve desserts?
🤖 Always happy to meet your needs!
🤖 To see our cake shop menu, go to the ...
```

Notice how irrelevant user input is processed differently by the same followup nodes in these two cases.

* It's okay when you're waiting for a answer and you get user input that can't be processed by followup nodes. Probably the user suddenly change the topic while answering to follow-up question and the bot uses digression to determine it.
* But when you immediately chain conditions the digression is pointless, since the current user input exactly sets the topic. So if none of the chained conditions address the user input, an error will occur, further processing will be interrupted and the bot will return to its initial state.

Avoid using `condition` when adding a `jump_to` command that goes to the node above the current node in the dialog tree. Such transitions can lead to infinite loops. In this case, processing will be interrupted and the bot will return to its initial state.

### Ask follow up questions {#jump-to-listen}

The bot waits for new input from the user, and then begins to process it from the node that you jump to. This option is useful if the source node asks a question, and you want to jump to a separate node to process the user's answer to the question.

In the example, the bot can recognize the user's phone number and place a request for a callback.

<Tabs
    defaultValue="snippet"
    values={[
        {label: 'Snippet', value: 'snippet'},
        {label: 'Full', value: 'full'},
    ]}>
<TabItem value="snippet">

  ```yaml
  dialog:
    - condition: intents.back_call
      label: back_call
      response: |
          Enter your phone number so we can call you back.
      followup:
        - label: back_call_start
          condition: entities.phone_number
          response: |
              We will call you back soon!
        - condition: true
          response: |
            Enter a phone number, for example 958-234-3456.
            <jump_to node="back_call_start" transition="listen" />
    - condition: intents.cancel_order
      response: |
        You can cancel your order by calling 888-123-4567. <br />
        Or leave your number and we will call you back.
        <jump_to node="back_call_start" transition="listen" />
  ```

</TabItem>
<TabItem value="full">

  ```yaml
  channels:
    telegram:
      api_token: !ENV ${TELEGRAM_API_KEY}
  intents:
    - name: cancel_order
      examples:
        - I want to cancel my cake order
        - I need to cancel an order I just placed
        - Can I cancel my cake order?
        - I'd like to cancel my order
        - There's been a change. I need to cancel my bakery order.
        - please cancel the birthday cake order I placed last week
        - The party theme changed; we don't need a cake anymore
        - that order i placed, i need to cancel it.
    - name: back_call
      examples:
        - Call me back, please
        - Could you call me
        - I want to get a call back
        - Can you call me
        - a callback please
        - Give me a call.
  entities:
    - name: phone_number
      values:
        - name: phone_number
          regexps:
            - '[0-9]{3}-[0-9]{3}-[0-9]{4}'
  dialog:
    - condition: intents.back_call
      label: back_call
      response: |
          Enter your phone number so we can call you back.
      followup:
        - label: back_call_start
          condition: entities.phone_number
          response: |
              We will call you back soon!
        - condition: true
          response: |
            Enter a phone number, for example 958-234-3456.
            <jump_to node="back_call_start" transition="listen" />
    - condition: intents.cancel_order
      response: |
        You can cancel your order by calling 888-123-4567. <br />
        Or leave your number and we will call you back.
        <jump_to node="back_call_start" transition="listen" />
  ```

</TabItem>
</Tabs>

The user can directly ask to call back

```
🧑 please, call me back
🤖 Enter your phone number so we can call you back.
🧑 958-543-8765
🤖 We will call you back soon!
```

or as one of the ways to cancel the order.

```
🧑 I want to cancel my order
🤖 You can cancel your order by calling 888-123-4567.
   Or leave your number and we will call you back.
🧑 958-543-8765
🤖 We will call you back soon!
```
