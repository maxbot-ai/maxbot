# Maxml (Advanced)

This document explains the advanced use of Maxml (Markup Language).
General information can be found in [Maxml (Markup Language)](/design-guides/maxml.md).

## How to get plain text from `text` command?

Use the default renderer:

```python
from maxbot import MaxBot

builder = MaxBot.builder()
builder.use_inline_resources("""
dialog:
- condition: true
  response: |
    <text>
        Hello,
        world! <br /> How are
        you?
    </text>
""")
command, = builder.build().process_message(message={"text": "test"})
command['text'].render()
# 'Hello, world!\nHow are you?'
```

## Markup and Jinja {#normalization}

Whitespace normalization applied to computed Jinja expressions as well.

In the following example, a newline from the slot value will be normalized to a space:
```python
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
command, = bot.process_message(message, dialog)
command['text'].render()
# 'Hello! How are you?'
```

To leave a newline in the text sent to a user, it’s necessary to use the Jinja filter `nl2br`:
```python
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
command, = bot.process_message(message, dialog)
command['text'].render()
# 'Hello!\nHow are you?'
```

## Metadata

XML allows you to specify the content of values in different ways.
Below is an example of adding the `location` command, which allows you to send an arbitrary point on the map to the user.

```python
import json
from marshmallow import fields, Schema
from maxbot import MaxBot

builder = MaxBot.builder()

@builder.command("location")
class LocationCommand(Schema):
    longitude = fields.Float(required=True)
    latitude = fields.Float(required=True)

builder.use_inline_resources("""
    dialog:
      - condition: message.text == "Where are you?"
        response: |
          <location latitude="40.7580" longitude="-73.9855" />
""")
bot = builder.build()

dialog = {"channel_name": "cli", "user_id": "1"}
message = {"text": "Where are you?"}
print(json.dumps(bot.process_message(message, dialog), indent=2))
```
```json
[
  {
    "location": {
      "longitude": -73.9855,
      "latitude": 40.758
    }
  }
]
```

For example, if we want to represent fields with simple data types in the form of nested XML elements,
we need to specify it in the metadata explicitly: the key `maxml` must contain the value `element`.

We will rewrite the example above so that the fields longitude and latitude had to be specified as nested XML elements:
```python
import json
from marshmallow import fields, Schema
from maxbot import MaxBot

builder = MaxBot.builder()

@builder.command("location")
class LocationCommand(Schema):
    longitude = fields.Float(required=True, metadata={"maxml": "element"})
    latitude = fields.Float(required=True, metadata={"maxml": "element"})

builder.use_inline_resources("""
    dialog:
      - condition: message.text == "Where are you?"
        response: |
          <location>
            <latitude>40.7580</latitude>
            <longitude>-73.9855</longitude>
          </location>
""")
bot = builder.build()

message = {"text": "Where are you?"}
print(json.dumps(bot.process_message(message), indent=2))
```
```json
[
  {
    "location": {
      "longitude": -73.9855,
      "latitude": 40.758
    }
  }
]
```

## List

A command can contain a list. In order to organize a list of simple types, one can use the type `fields.List`.
For example, a simple version of the command `quick_reply` can be described like this:

```python
import json
from marshmallow import fields, Schema
from maxbot import MaxBot

builder = MaxBot.builder()

@builder.command("quick_reply")
class QuickReplyCommand(Schema):
    button = fields.List(fields.String)

builder.use_inline_resources("""
    dialog:
      - condition: message.text == "What is on the menu?"
        response: |
          <quick_reply>
            <button>Pizza</button>
            <button>Desserts</button>
          </quick_reply>
""")
bot = builder.build()

dialog = {"channel_name": "cli", "user_id": "1"}
message = {"text": "What is on the menu?"}
print(json.dumps(bot.process_message(message, dialog), indent=2))
```
```json
[
  {
    "quick_reply": {
      "button": [
        "Pizza",
        "Desserts"
      ]
    }
  }
]
```

For more complex versions when the lists of nested objects are used, one needs to use `Nested` with the argument `many=True`.
For example, like this:

```python
import json
from marshmallow import fields, Schema
from maxbot import MaxBot

builder = MaxBot.builder()

class CarouselItem(Schema):
    title = fields.String(metadata={"maxml": "element"}, required=True)
    image = fields.Url(required=True)


@builder.command("carousel")
class CarouselCommand(Schema):
    item = fields.Nested(CarouselItem, many=True)


builder.use_inline_resources("""
    dialog:
      - condition: message.text == "What is on the menu?"
        response: |
          <carousel>
            <item image="http://127.0.0.1/Pizza.jpeg">
              <title>Pizza</title>
            </item>
            <item image="http://127.0.0.1/Desserts.jpeg">
              <title>Desserts</title>
            </item>
          </carousel>
""")
bot = builder.build()

dialog = {"channel_name": "cli", "user_id": "1"}
message = {"text": "What is on the menu?"}
print(json.dumps(bot.process_message(message, dialog), indent=2))
```
```json
[
  {
    "carousel": {
      "item": [
        {
          "title": "Pizza",
          "image": "http://127.0.0.1/Pizza.jpeg"
        },
        {
          "title": "Desserts",
          "image": "http://127.0.0.1/Desserts.jpeg"
        }
      ]
    }
  }
]
```
