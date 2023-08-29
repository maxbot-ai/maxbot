---
toc_min_heading_level: 2
toc_max_heading_level: 2
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Creating Bots


This guide will walk you through the basics of creating bots. The typical bot creation workflow includes the following steps.

* Start by creating a YAML-file that will house the bot resources. Call it `bot.yaml` or whatever you want.
* Create intents that represent the user needs. For example, intents such as `intents.about_company` or `intents.place_order`.
* Define any entities that are needed to more clearly understand the user's meaning. For example, you might add an `entities.product` entity that you can use with the `intents.place_order` intent to understand what product the customer wants to buy.
* Build a dialog that detects the defined intents and addresses them, either with simple responses or with a dialog flow that collects more information first.
* Test each function that you add to the bot running the MaxBot CLI app, incrementally, as you go.
* As your bot grows, split resources into several files and place them into the MaxBot-specified directory structure.
* Add more features to your bot with extensions.

## YAML Basics

This section provides a briefly and opinionated overview of YAML syntax, which is how MaxBot resources are expressed. We use YAML because it is easier for humans to read and write than other common data formats like XML or JSON.

The YAML document consists of a nested collection of dictionaries, lists, and strings where indentation is used to indicate nesting.

:::info

MaxBot uses [marshmallow](https://marshmallow.readthedocs.io/) schemas to validate and convert YAML data into a specific types. For example, schemas can turn

* YAML dictionaries into objects with required and optional attributes;
* strings into more specific scalars such as numbers and booleans.

:::

### Strings

YAML strings are good to read, but they can be tricky to write instead.

Plain strings are unquoted and are the most readable.

```yaml
Good day to you!
```

While you can put just about anything into an unquoted string, there are some exceptions:

* `: #` - delimiters that better not to use at all,
* `' " [] {} > | * & ! % # `` @ ,` - special characters that better not to use in the begining of a string.

Use double-quoted strings to not care about special characters.

```yaml
response: "I should put a colon here: so I did"
```

Strings enclosed in double-quotes is only capable of expressing arbitrary unicode characters, by using c-style escape sequences starting with a backslash `\`.

```yaml
response: "a \t TAB and a \n NEWLINE"
```

Incorrect sequences will cause a syntax error. Escape backslash itself `\\` to avoid the problem.

```yaml
response: "c:\\windows"
```

The single-quoted style becomes useful to avoid escaping mess when your string contains a lot of backslashes.

```yaml
regexps:
  - '[DEF]\-[A-Z]{2}\d{5}'
```

Within single quotes the only supported escape sequence is a doubled single quote `''` denoting the single quote itself as in

```yaml
response: 'I won''t!'
```

There are also literal and folded block styles are the most readable way to create multi-line responses or those containing long lines. String blocks relies on outline indentation and resistant to delimiter collision. They are describe in the [Responses](#responses) section below.

### Lists and Dictionaries

All members of a list are lines beginning at the same indentation level starting with a "- " (a hyphen and a space):

```yaml
- Good morning
- How are you?
- Hello
- Hi
```

A dictionary is represented in a simple `key: value` form (the colon must be followed by a space):

```yaml
- condition: intents.greetings
  response: Good day to you!
```

More complicated data structures are possible with outline indentation. There may be lists of dictionaries, dictionaries whose values are lists or a mix of both:

```yaml
intents:
  - name: greetings
    examples:
      - Good morning
      - How are you?
      - Hello
      - Hi
dialog:
  - condition: intents.greetings
    response: Good day to you!
```

The specific number of spaces in the indentation is unimportant as long as parallel elements have the same left justification and the hierarchically nested elements are indented further.

There is more compact format for both lists

```yaml
["Good morning", "How are you?", "Hello", "Hi"]
```

and dictionaries

```yaml
{condition: intents.greetings, response: Good day to you!}
```
For example:
```yaml
channels:
  telegram:
    api_token: !ENV ${TELEGRAM_API_KEY}
intents:
  - name: greetings
    examples: ["Good morning", "How are you?", "Hello", "Hi"]
dialog:
  - {condition: intents.greetings, response: "Good day to you!"}
```

These are called "flow collections" and can sometimes be useful.

## Channels

Channels are a way to integrate your bot with various messaging platforms. You must configure at least one channel to create a bot. MaxBot provides pre-built channels for `Telegram`, `Viber Chatbots`, `VK` and there will be more soon.

Just add the channel configuration to the bot resources to integrate the bot with that channel. The process of integrating your bot with a specific messaging platform is covered in the schema description of the corresponding channel. For example, [TelegramSchema](/design-reference/resources.md#telegramschema) description says that you should go to [@BotFacther](https://t.me/botfather), get an API token and specify it in the bot resources.

```yaml
channels:
  telegram:
    api_token: 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
```
See [Channel settings](/design-guides/channel-setting) for information about other channels.
## Intents

Intents are purposes or goals that are expressed in a user input, such as answering a question or making a reservation. By recognizing the intent expressed in a user's input, the bot can choose the correct dialog flow for responding to it. For example, you might want to define `intents.buy_something` intent to recognize when the user wants to make a purchase.

Create an intent by providing a short name and examples of utterances that user typically use to indicate their goal.

```yaml
intents:
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

You access recognized intents using `intents` variable in conditions and responses. Use expressions like `intents.reservation` in the dialog tree conditions to chose the correct dialog node for respond to the user.

```yaml
- condition: intents.reservation
  response: |
    Let's book a table for you...
- condition: intents.about_restaurant
  response: |
    Food Lovers is an unique restaurant...
```

If, for example, the user input is asking to make a reservation, then the `intents.reservation` condition evaluates to true and the node with this condition is processed.

## Entities

Entities are structured pieces of information in the user input that is relevant to the user's purpose. By defining entities, you can help the bot identify references in the user input that are related to intents of interest. Given the `intents.buy_something` you may want to add `entities.product` to extract information about the product that the user is interested in. MaxBot detects entities in the user input by using phrases, regexps or prebuilt set of rules.

Rule-based entities cover commonly used categories, such as numbers or dates. You can just use rule based entities without defining them in bot resources. See [Context Variables](/design-reference/context#builtin-entities) guide for a list of rule-based entities.

Phrase and regex entities are defined in bot resources. An entity definition includes a set of entity values that represent vocabulary that is often used in the context of a given intent. For each value, you define a set of recognition rules, which can be either phrases or regular expressions.

You can also save entities values to variables. There are two kinds of state variables:

* Slot variables are used by the bot as short-term memory to keep the conversation on the current topic only.
* User variables are long-term memory that is used to personalize the entire communication process.

State variables are used to retaining information across dialog turns. Use state variables to collect information from the user and then refer back to it later in the conversation.

For more information about state variables, see [State Variables](/design-guides/state.md) guide.

### Phrase Entities {#phrase-entities}

You define an entity (`entities.menu`), and then one or more values for that entity (`standard`, `vegetarian`, `cake`). For each value, you specify a bunch of phrases with which this value can be mentioned in the user input, e.g. "cake shop", "desserts" and "bakery offerings" for the `cake` value etc.

```yaml
intents:
  ...
entities:
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
          - desserts
          - bakery offerings
dialog:
  ...
```

MaxBot recognizes pieces of information in the user input that closely match the phrases that you defined for the entity as mentions of that entity.
MaxBot performs a comparison of phrases on tokens, which are extracted on the basis of linguistic features of a particular language, [details](https://spacy.io/usage/linguistic-features#tokenization).

### Regex Entities {#regex-entities}

You define an entity (`entities.order_number`), and then one or more values for that entity (`short_syntax`, `full_syntax`). For each value, you specify a regular expression that defines the textual pattern of mentions of that value type.

```yaml
entities:
  - name: order_number
    values:
      - name: short_syntax
        regexps:
          - '[A-Z]{2}\d{5}'
      - name: full_syntax
        regexps:
          - '[DEF]\-[A-Z]{2}\d{5}'
```

Note, that we use single-quoted strings to specify regular expressions. This avoids escaping mess when your string contains a lot of backslashes.

MaxBot performs a character-by-character comparison with a template, and identifies any matches as mentions of that entity.

### Using entities

Use the syntax `entities.order_number` in node condition to trigger node when an entity is recognized in the user input. This expression checks whether any of the values that are defined for the "order_number" entity were detected in the user input. If so, the node or response is processed.

```yaml
- condition: entities.order_number
  response: ...
```

Use the syntax `entities.menu.vegetarian` to trigger node when *the entity value* is detected in the user input. This expression checks whether the vegetarian menu was detected in the user input.

```yaml
- condition: entities.menu.vegetarian
  response: ...
```

## Dialog Tree

The dialog tree defines what your assistant says in response to customers. A tree is composed of multiple nodes. Each node contains, at a minimum, a condition and a response.

### Root nodes

A root node represents the start of a topic of dialog between your bot and the user. In the simplest form, the user asks a question, the bot traverses the list of root nodes of the tree, finds a suitable one and gives the answer to the user.

```yaml
dialog:
  - condition: intents.greetings
    response: |
      Good day to you!
  - condition: intents.ending
    response: |
      OK. See you later.
  - condition: true
    response: |
      Sorry I don't understand.
```

The dialog may looks like

```
🧑 hello
🤖 Good day to you!
🧑 how are you?
🤖 Sorry I don't understand.
🧑 bye
🤖 OK. See you later.
```

### Followup nodes

You may want to ask the user for more input that is needed to respond correctly. You can ask for more details in a text response and create one or more followup nodes to process the new input.

```yaml
dialog:
  - condition: intents.menu
    label: menu
    response: |
      Which menu do you want to see?
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

The dialog may looks like

```
🧑 I want to see a menu
🤖 Which menu do you want to see?
🧑 Cake shop
🤖 To see our cake shop menu, go to the ...
```

## Conditions

Condition specifies the information that must be present in the user input for this node to be used in the conversation. The information is typically a specific intent. It might also be an entity or a state variable value and more.

### `intents`

The simplest condition is a single intent. The node is triggered if the MaxBot determines that the purpose of the user input maps to the pre-defined intent.

Let's say you define an intent called "weather". Put the `intents.weather` expression after the `condition` keyword to check if the user input is asking for a weather forecast. If so, the node with the `intents.weather` condition is processed.

```yaml
- condition: intents.weather
  response: ...
```

### `entities`

Use the syntax `entities.city` in node condition to trigger node when *any value for the entity* is recognized in the user input. This expression checks whether any of the city names that are defined for the "city" entity were detected in the user input. If so, the node or response is processed.

```yaml
- condition: entities.city
  response: ...
```

Use the syntax `entities.city.boston` to trigger node when *the entity value* is detected in the user input. Assuming you have defined the value `boston` for the entity, this expression checks whether the specific city name, Boston, was detected in the user input.

```yaml
- condition: entities.city.boston
  response: ...
```

### `user`, `slot`, `dialog`

The node is used if the state variable expression that you specify is true. Use the syntax with [comparison operators](/design-reference/booleans.md#comparisons) like, `dialog.channel_name == "telegram"` or `slots.guests > 5`.

Make sure state variables are initialized before usage (see [State Variables](/design-guides/state.md)), otherwise use them with the [default filter](/design-reference/jinja.md#filter-default): `slots.counter|default(0) > 1`.

For node conditions, state variables is typically used with an `and` operator and another condition value because something in the user input must trigger the node.

```yaml
- condition: intents.book_restaurant and user.city == "boston"
  response: ...
```

Use state variables alone in the template conditions which are used to change the response based on a specific state variable value.

For more information about state variables, see [State Variables](/design-guides/state.md) guide.

### `message`

Messages are what you receive from the user. Text messages and images supported for all channels out of the box.

Use the syntax like `message.text` or `message.image` in node condition to trigger node when the *message of particular type* is received from the user.

The `message.text` expression is typically used to capture the exact text uttered by the user.

```yaml
- condition: message.text
  response: |
    You said: {{ message.text }}
```

See [Protocol](/design-reference/protocol.md) reference to learn more about different types of messages.

### "Anything else" Conditions

"Anything else" conditions are what you use at the end of the node list, to be processed when the user input does not match any other nodes. Typically this last node returns a generic message. There are several types of "anything else" conditions that you can use depending on your needs.

The `true` condition is always evaluated to true. You can use it at the end of a list of nodes to catch any requests that did not match any of the previous conditions.

The `message` expression is used in to trigger node if the MaxBot receives the *any type of message* from the user, i.e. text message, image file, button click, etc. This is the opposite of [`RPC`](/design-guides/rpc) (remote procedure call) methods, which are called by integrations and not by users.

```yaml
- condition: message
  response: |
    I am triggered by the user!
- condition: rpc
  response: |
    Got an RPC call!
```

Use the `message.text` expression in the last node in the list to match user text messages that does not match any other dialog nodes. This is opposed to media files and other structured messages that may be sent by the user.

```yaml
- condition: intents.greetings
  response: |
    Good day to you!
- condition: intents.ending
  response: |
    OK. See you later.
- condition: message.text
  response: |
    Sorry I don't understand.
```

When the bot receives any text message that is not recognized as a hello or goodbye, it will respond "Sorry I don't understand."

The `intents.irrelevant` condition will evaluate to true if the user sends a text message and MaxBot could not recognize any intent in that message.

Be aware that using these conditions may have side effects. For example, they can make [digressions impossible](/design-guides/digressions.md#avoid-anything-else).

### Boolean Conditions

#### `true`

The condition is always evaluated to true. You can use it at the end of a list of nodes to catch any requests that did not match any of the previous conditions.

#### `false`

The condition is always evaluated to false. You might use this at the start of a branch that is under development, to prevent it from being used, or as the condition for a node that provides a common function and is used only as the target of a [`jump_to`](/getting-started/creating-bots/#jump-to-a-node) control command.

## Responses

Response is the utterance that bot uses to respond to the user. The response can also be a list of commands to show an image or clickable buttons.

### Text Responses

Simply put the text that you want to display to the user after the `response` keyword.

```yaml
response: Good day to you!
```

The string may contain delimiters and special characters (`:`, `#` and so on), in which case it must be enclosed in quotation marks.

```yaml
response: "We are the #1!"
```

### Long lines

You may want to display a long line to the user, but it's inconvenient to put such lines in a text editor.
By default, the text normalization happens for whitespace characters.
All whitespace characters (including line feeds), which include multiple whitespace characters in a row, are replaced with a single space.

Therefore, lines can be specified by breaking them into several lines using a literal style (`|`):

```yaml
response: |
	We have no brick and mortar stores.
	But, with an internet connections,
	you can shop as from anywhere!
```

The newlines will be replaced and the user will get a single line of text:

```
🤖 We have no brick and mortar stores. But, with an internet connections, you can shop as from anywhere!
```

### Multiline strings

A single text response can include multiple lines.
For explicit indication of the need for a newline in a text, one needs to use HTML tag `<br />`:

```yaml
response: |
    We offer different types of menus: <br />
    * standard, <br />
    * vegeterian, <br />
    * cake shop. <br />
```

The user gets the resulting string as is.

```
We offer different types of menus:
* standard,
* vegeterian,
* cake shop.
```

Literal strings can contain any character without quotes or escaping.

### Command `text`

The other way to send a text to the user is to use `text` command.
The content of the `text` XML element will be the user response string.

```yaml
response: |
  <text>Good day to you!</text>
```

The content of the XML element `text` is subjected to text normalization for whitespace (like raw lines).

### Command `image`

Include images in your response using an `image` command. Add the full URL to the hosted image file into the `url` attribute.

```yaml
response: |
    <image url="https://example.com/hello.png" />
```

If you want to display an image caption in the response, then add them in the `caption` child element.

```yaml
response: |
  <image url="https://example.com/hello.png">
    <caption>Hello, Image!</caption>
  </image>
```

The image file must be stored in a location that is publicly addressable by an URL. See your messaging platform's documentation for image format and size limits.

### Command `quick_reply`

Add `quick_reply` command when you want to give the user a set of options to choose from. For example, you can construct a response like this:


```yaml
response: |
  <quick_reply>
      <text>Which of these items do you want to insure</text>
      <button>Boat</button>
      <button>Car</button>
      <button>Home</button>
  </quick_reply>
```

When the button is clicked, its label will be passed to the bot as user input. You may use [phrase entities](#phrase-entities) to recognize this user input. Most channels allow a limited number of buttons to be displayed (for example, 10 or less) and limit the length of the button label.

A complete list of all reply commands and their arguments is contained in the [Protocol](/design-reference/protocol.md#commandschema) reference.

### Control Commands {#control-commands}

You can end the list of reply commands with a special *control command* that will determine the further course of the conversation flow. You can end the node response with one of the commands below.

Different kinds of dialog flows has their own sets of control commands which is described in the [Dialog Tree Guide](/design-guides/dialog-tree.md), [Slot Filling Guide](/design-guides/slot-filling.md) and [Digressions Guide](/design-guides/digressions.md).

## Templates

The template mechanism is applied to all the lines that are set as replies in a bot.
It means that any piece of a [XML document](/design-guides/maxml.md) can be generated dynamically based on the current data.

### Expressions

Include any context variable value in your response using the `{{ ... }}` print-statement. If you now that the `user.name` variable is set to the name of the user, then you can refer to it in the text template

```yaml
response: |
    Good day to you, {{ user.name }}!
```

If the user name is Norman, then the response that is displayed to user is

```
🤖 Good day to you, Norman!
```

The same rules about [delimiter collisions](#plain-style) also apply to template strings. For instance, plain YAML strings cannot start with `{` character. So you must quote the string that starts with variable substitution.

```yaml
response: "{{ user.name }}, right?"
```

Or you can use the literal style.

```yaml
response: |
    {{ user.name }}, right?
```

### Autoescaping

The substrings formed in this way are automatically escaped.

For example, let us have a command `foo` with an attribute `bar`, that has to be represented as an XML attribute.
If we generate an attribute `bar` using jinja-expressions, for example like this:

```
<foo bar="{{ user.var1 }}" />
```

Then we don't need to worry about the fact that the value `user.var1` can contain a character of line ending (quotes: `"`).
Automatic escaping will replace it with a safe counterpart HTML entity.
For example, if the value of `user.var1` consists of one quote character (`"`), then the following command will be generated:

```
<foo bar="&#34;" />
```

And while reading a resulting XML document, the parser will process the found HTML entity and write it with the next character of the value of the field `bar`.

### Statements

More complex templates are also possible. If you need to be able to populate the list of buttons with different values based on some other factors, you can design a dynamic `quick_reply` command using loop statement.

```yaml
response: |
    {% if slots.products %}
      <quick_reply>
        <text>Choose one of our products.</text>
        {% for product in slots.products %}
          <button>{{ product.name }}</button>
        {% endfor %}
      </quick_reply>
    {% else %}
      I can't find the products that match your request.
    {% endif %}
```

Given a list of products in `slots.products`

```json
[
    {"name": "Anti-Gravity Boots"},
    {"name": "Fountain of Youth"},
    {"name": "Inflatable Flower Bed"},
]
```

you will get the following output:

```yaml
<quick_reply>
  <text>Choose one of the products.</text>
  <button>Anti-Gravity Boots</button>
  <button>Fountain of Youth</button>
  <button>Inflatable Flower Bed</button>
</quick_reply>
```

See [Templates](/design-guides/templates) for more information about template engine.

## Jump to a node

You can configure a node jump directly to another node after it is processed. This allow the bot to change the topic by moving between adjacent branches of the tree. Jumps from child nodes to parent nodes implement recursive behavior within the same topic (branch).

<Tabs
    defaultValue="snippet"
    values={[
        {label: 'Snippet', value: 'snippet'},
        {label: 'Full', value: 'full'},
    ]}>
<TabItem value="snippet">

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
  entities:
    - name: order_number
      values:
        - name: order_syntax
          regexps:
            - '[A-Z]{2}\d{5}'
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

</TabItem>
</Tabs>


For the `jump_to` command, we used a more compact way of writing arguments called "flow collections".

The dialog may looks like

```
🧑 I want to cancel my order.
🤖 What is the order number?
🧑 I didn't remember
🤖 I need the order number to cancel the order for you.
🤖 What is the order number?
🧑 AB12345
🤖 OK. The order is canceled.
```

## Slot Filling

A tree node can contain a [slot filling](/design-guides/slot-filling.md) block. A slot is a piece of information used by the bot to answer the user's question. The bot asks questions to the user until it knows the values of all the required slots and answers the user's original question after that. The dialog built on slot filling allows the user to enter information in a random order without waiting for the bot to ask questions.

```yaml
dialog:
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
    	OK. I am making you a reservation for
    	{{ slots.guests }} on {{ slots.date }} at {{ slots.time }}.
```

The user can sequentially answer the questions.

```
🧑 i want to make a reservation
🤖 What day would you like to come in?
🧑 tomorrow
🤖 What time do you want the reservation to be made for?
🧑 at 5pm
🤖 How many people will be dining?
🧑 6
🤖 OK. I am making you a reservation for 6 on 2022-05-29 at 17:00:00.
```

Maybe not sequentially and several answers at the same time.

```
🧑 i want to make a reservation
🤖 What day would you like to come in?
🧑 there will be six of us
🤖 What day would you like to come in?
🧑 tomorrow at 5pm
🤖 OK. I am making you a reservation for 6 on 2022-05-29 at 17:00:00.
```

Or just provide all the information.

```
🧑 I'd like to make a reservation for 6 people tomorrow at 5 pm
🤖 OK. I am making you a reservation for 6 on 2022-05-29 at 17:00:00.
```

## Digressions

During the communication, the user may suddenly change the topic. The bot should keep the conversation going. So it must switch from one branch to another corresponding to the new topic. Moreover, after discussing a new topic, the bot can optionally switch back and prompt the user to complete the discussion of the old topic. The built-in mechanism for such switches is called [digressions](/design-guides/digressions.md).

<Tabs
    defaultValue="snippet"
    values={[
        {label: 'Snippet', value: 'snippet'},
        {label: 'Full', value: 'full'},
    ]}>
<TabItem value="snippet">

  ```yaml
  dialog:
    - condition: intents.restaurant_opening_hours
      response: |
        The restaurant is open from 8am to 8pm.
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
        OK. I am making you a reservation for
        {{ slots.guests }} on {{ slots.date }} at {{ slots.time }}.
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
    - name: reservation
      examples:
        - i'd like to make a reservation
        - I want to reserve a table for dinner
        - Can 3 of us get a table for lunch on May 29, 2022 at 5pm?
        - do you have openings for next Wednesday at 7?
        - Is there availability for 4 on Tuesday night?
        - i'd like to come in for brunch tomorrow
        - can i reserve a table?
  dialog:
    - condition: intents.restaurant_opening_hours
      response: The restaurant is open from 8am to 8pm.
    - condition: intents.reservation
      label: reservation
      slot_filling:
        - name: date
          check_for: entities.date
          prompt: What day would you like to come in?
        - name: time
          check_for: entities.time
          prompt: What time do you want the reservation to be made for?
        - name: guests
          check_for: entities.number
          prompt: How many people will be dining?
      response: |
          OK. I am making you a reservation for
          {{ slots.guests }} on {{ slots.date }} at {{ slots.time }}.
  ```

</TabItem>
</Tabs>

The dialog may looks like

```
🧑 I want to reserve a table for lunch for 6 people tomorrow
🤖 What time do you want the reservation to be made for?
🧑 What time do you close?
🤖 The restaurant is open from 8am to 8pm.
🤖 What time do you want the reservation to be made for?
🧑 at 5pm
🤖 OK. I am making you a reservation for 6 on 2022-05-29 at 17:00:00.
```

## Extensions

You can use extensions to add more features to your bot. Enable and configure extensions in bot resources.

For example, the datetime extension is enabled as follows

```yaml
extensions:
    datetime: {}
channels:
  ...
intents:
  ...
```

Where `datetime` is the name of the extension and value `{}` is the extension configuration dictionary. In our case configuration is empty. Generally, each extension has it's own configuration schema described in the extension's documentation. For example, an extension that provides filters to format numbers and dates could be configured as follows

```yaml
extensions:
    babel: { locale: en }
```

Refer to the extension's documentation for the specific features provided by this extension and its configuration.

Maxbot contains the following built-in extensions:
* [datetime](/extensions/datetime.md): provides template filters to convert input value to date/time.
* [babel](/extensions/babel.md): [Babel library](https://babel.pocoo.org/) frontend.
* [rasa](/extensions/rasa.md):  allows you to use an external Rasa Open Source Server as an NLU module for MaxBot.
* [jinja\_loader](/extensions/jinja_loader.md): allows you to include jinja template files into your response.

## Resources

### Resource Directory

In the simple case you create bot by putting all the resources into the single file usually called *bot.yaml*. As your bot grows, it gets more convenient to split resources, especially intents and entities, into several files and place them into the MaxBot-specified directory structure.

* Place intent definitions in `*.yaml` files in the `intents/` directory.
* Place entity definitions in `*.yaml` files in the `entities/` directory.
* Place [subtrees](/design-guides/subtrees.md) of a dialog tree in `*.yaml` files in the `dialog/` directory.
* Leave the rest of the definitions in `bot.yaml`.

Below are an example:

```
mybot/
    dialog/
        registered-users.yaml
        under-development.yaml
    entities/
        core-entities.yaml
        products-entities.yaml
    intents/
        core-intents.yaml
        faq-intents.yaml
    bot.yaml
```

Then you can pass the path to a directory as a parameter to CLI app:

```
$ maxbot run --bot mybot/
✓ Started polling updater... Press 'Ctrl-C' to exit.
```

### Using environment variables

If you want to publish you bot, you may notice that it contains some sensitive information such as authorization keys for channels. It's good practice to store such secrets in environment variables rather than in code.

For example, the telegram channel settings contains `api_token` which is the secret token used to authenticate your bot. So write the reference to the environment variable `TELEGRAM_API_KEY` instead of actual value. Use the `!ENV` tag to mark a string as containing an environment variable.

```yaml
channels:
    telegram:
        api_token: !ENV ${TELEGRAM_API_KEY}
```

After that, make the variable available to the CLI app using bash export, for example.

```bash
$ export TELEGRAM_API_KEY="110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
$ maxbot run --bot mybot/
✓ Started polling updater... Press 'Ctrl-C' to exit.
```

Another way is to create an `.env` file in your working directory and put a variable in that file.

```bash
$ echo 'TELEGRAM_API_KEY="110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"' >> .env
```

Keep `.env` file only on your laptop. Run CLI app from the same directory and it works.

```bash
$ maxbot run --bot mybot/
✓ Started polling updater... Press 'Ctrl-C' to exit.
```
