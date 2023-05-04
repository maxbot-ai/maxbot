# Markdown

As a bot's reply the line specified in the dialog tree is used. Firstly, [templating](templates.md) is applied to this line, which should result in a [Markdown document](https://daringfireball.net/projects/markdown/syntax). In this document there can be bot commands in XML-based markup: [MAXML](#maxml) besides raw text.

The entire Markdown document is divided into paragraphs. A paragraph is simply one or more consecutive lines of a text, separated by one or more blank lines.

## MAXML {#maxml}

For explicit assigning commands to a bot, they should be written as XML elements (MAXML: MAxbot Xml based Markup Language).
For example, to finish processing a message from a user, one can use the command `end` in a reply of digression that cancels the order:

```
Your order is canceled.
<end />
```

As it is seen from the example above, the MAXML parser can successfully extract a command that is in the same paragraph as plain text.
Therefore, for the compactness of the source code of your bot, we recommend _sticking_ the control command to a single paragraph of text.

### A built-in command `text`

To send a text reply to a user, it can be represented as a usual text paragraph in a Markdown document:
```
Hello, world!
```

Explicit usage of the command `text` will be a similar option:
```
<text>Hello, world!</text>
```

The third similar option is using an HTML tag `p`:
```
<p>Hello, world!</p>
```

### A built-in command `image`

To send images to a user, one can use the command [image](/design-reference/protocol.md#imagemessage) .
It can be set as a Markdown markup:

```
![](https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg)
```

Or using MAXML explicitly:
```
<image url="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg" />
```

The third similar option will be using an HTML tag `img`:
```
<img src="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg" />
```

If it’s necessary to add a description to a picture, then the examples given above will look like this:
* Markdown-markup:
```
![Hello, world!](https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg)
```
* MAXML:
```
<image url="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg">
    <caption>Hello, world!</caption>
</image>
```
* HTML tag:
```
<img src="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg" alt="Hello, world!" />
```

[The normalization of the text describing a picture](#normalization) happens **only** when using MAXML.

## Text normalization {#normalization}

MAXML (like a regular XML) allows to set text content in two ways: the value of attributes and the content of elements.
In the second case (when the content is set inside the element), the text normalization happens for whitespace characters.
All whitespace characters (including line feeds), which include multiple whitespace characters in a row, are replaced with a single space.
This normalization is also applied when using a plain text Markdown paragraph.
In order to include a newline in the resulting text, one needs to use the HTML tag `<br />`.
For instance:


```
from maxbot import MaxBot

builder = MaxBot.builder()
builder.use_inline_resources("""
dialog:
- condition: true
  response: |
    Hello!
    I    am     MaxBot!<br />How can I help you?
""")
bot = builder.build()
dialog = {"channel_name": "cli", "user_id": "1"}
message = {"text": "Hello!"}
print(bot.process_message(message, dialog))
# [{'text': 'Hello! I am MaxBot!\nHow can I help you?'}]
```

It is also true for computed Jinja expressions.
In the following example, a newline from the slot value will be normalized to a space:
```
from maxbot import MaxBot

builder = MaxBot.builder()
builder.use_inline_resources("""
dialog:
- condition: true
  response: |
    {% set slots.message = "Hello!\\nHow are you?" %}
    {{ slots.message }}
""")
bot = builder.build()
dialog = {"channel_name": "cli", "user_id": "1"}
message = {"text": "Hello!"}
print(bot.process_message(message, dialog))
# [{'text': 'Hello! How are you?'}]
```

To leave a newline in the text sent to a user, it’s necessary to use the Jinja filter `nl2br`:
```
from maxbot import MaxBot

builder = MaxBot.builder()
builder.use_inline_resources("""
dialog:
- condition: true
  response: |
    {% set slots.message = "Hello!\\nHow are you?" %}
    {{ slots.message|nl2br }}
""")
bot = builder.build()
dialog = {"channel_name": "cli", "user_id": "1"}
message = {"text": "Hello!"}
print(bot.process_message(message, dialog))
# [{'text': 'Hello!\nHow are you?'}]
```
