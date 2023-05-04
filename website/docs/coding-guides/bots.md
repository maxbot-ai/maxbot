# Bots

The bot consists of several different components. The bot builder allows you to customize these components before loading resources.

```
from maxbot import MaxBot

builder = MaxBot.builder()
#
# here you can customize your bot by changing builder properties
#
builder.use_file_resources('bot.yaml')
bot = builder.build()
```

Below are examples of customizing the bot.

## SQL Engine for State Tracker

MaxBot uses the `state_store` component to persist the state of the conversation. The default implementation is based on the [sqlalchemy](https://www.sqlalchemy.org) library with the in-memory sqlite engine preconfigured. You can set your own sqlalchemy [engine](https://docs.sqlalchemy.org/en/14/core/engines.html) by accessing the `engine` property.

```
from maxbot import MaxBot

builder = MaxBot.builder()
builder.state_store.engine = sqlalchemy.create_engine(...)
bot = builder.build()
```

Note that all tables needed to persist the state will be created immediately after you set the `engine` property.

## Jinja Filters, Tests and Globals

MaxBot actively uses the [Jinja](https://jinja.palletsprojects.com) template engine in its conversation scenarios. Jinja itself is highly customizable, so you can configure it directly through the `jinja_env` property of the `builder`.

```
builder.jinja_env.add_extension(...)
```

The `builder` also provides convenience methods and decorators for adding filters, test and globals to the jinja environment.

Here is an example of adding and using a simple filter. The filter will reverse the incoming string.

```
from maxbot import MaxBot

builder = MaxBot.builder()

@builder.template_filter()
def reverse(s):
	return s[::-1]

builder.use_inline_resources("""
    dialog:
      - condition: message.text
        response: |
            {{ message.text|reverse }}
""")
bot = builder.build()

message = {"text": "abcdef"}
print(bot.process_message(message))
# [{'text': 'fedcba'}]
```

Alternative ways to add such filter.

```
def reverse(s):
	return s[::-1]

# add a filter using a method
builder.add_template_filter(reverse, 'reverse')

# add a filter via direct access to jinja environment
builder.jinja_env.filters['reverse'] = reverse
```

There are similar methods to add globals and tests to the jinja environment.

## Receiving Custom Messages

Messages are what your bot receives from users. MaxBot supports most common message types by default, such as `text` or `image`. You can add any custom message type depending on your needs.

Each message type has a name and structure that are validated by marshmallow schema. To add a custom message, you need to declare its schema class and register its name and schema using the decorator `builder.message` or method `builder.add_message`. After that you are allowed to pass the message of specified structure to the `process_message` mehtod of the bot. You can access the message fields in your conversational scenarios via the `message` template variable.

See an example of creating `contact` message that allows user to pass some basic contact information to the bot, including their name and phone number.

```
from marshmallow import fields, Schema
from maxbot import MaxBot

builder = MaxBot.builder()

@builder.message("contact")
class ContactMessage(Schema):
	phone = fields.String(required=True)
	name = fields.String()

builder.use_inline_resources("""
    dialog:
      - condition: message.contact
        response: |
            Received {{ message.contact.phone }}
""")
bot = builder.build()

message = {"contact": {"phone": "1-541-754-3010"}}
print(bot.process_message(message))
# [{'text': 'Received 1-541-754-3010'}]
```

## Sending Custom Commands

Commands are what your bot sends to users. As for messages, MaxBot supports most common command types by default and you can add any custom command type.

Each command type has a name and structure that are validated by marshmallow schema. To add a custom command, you need to declare its schema class and register its name and schema using the decorator `builder.command` or method `builder.add_command`. After that you are allowed to use the command of specified structure in conversational scenarios and this command will be returned in the result of the `process_message` method of the bot.

The commands in the response of the bot must be written as XML elements. All the fields with simple types of data (`String`, `Number`, `Boolean`, `DateTime`, `TimeDelta` and their derivatives) must be described in the form of an XML element attribute by default. Nested schemas (`Nested`) must be described as nested XML elements.

Below is an example of adding the `location` command, which allows you to send an arbitrary point on the map to the user.

```
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
print(bot.process_message(message, dialog))
# [{'location': {'longitude': -73.9855, 'latitude': 40.758}}]
```

If we want to represent fields with simple data types in the form of nested XML elements, we need to specify it in the metadata explicitly:
the key `maxml` must contain the value `element`.

We will rewrite the example above so that the fields `longitude` and `latitude` had to be specified as nested XML elements:

```
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
print(bot.process_message(message))
# [{'location': {'longitude': -73.9855, 'latitude': 40.758}}]
```

An important difference between setting a field value via an attribute and via a nested XML element is that the content of the nested XML element is normalized:
all whitespaces (including a newline) are normalized to a single space.

To specify a line feed in the value of a nested XML element, one has to use the nested element `<br />` .
For example, the command `image` is implemented like this:

```
from marshmallow import fields, Schema
from maxbot import MaxBot

builder = MaxBot.builder()


@builder.command("image")
class ImageCommand(Schema):
    url = fields.Url(required=True)
    caption = fields.String(metadata={"maxml": "element"})


builder.use_inline_resources("""
    dialog:
      - condition: message.text == "Show a picture"
        response: |
          <image url="http://127.0.0.1/image1.jpeg">
            <caption>
              This
                is
              picture. <br /> Like it?
            </caption>
          </image>
""")
bot = builder.build()

dialog = {"channel_name": "cli", "user_id": "1"}
message = {"text": "Show a picture"}
print(bot.process_message(message, dialog))
# [{'image': {'caption': 'This is picture.\nLike it?', 'url': 'http://127.0.0.1/image1.jpeg'}}]
```

A command can contain a list. In order to organize a list of simple types, one can use the type `fields.List`.
For example, a simple version of the command `quick_reply` can be described like this:

```
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
print(bot.process_message(message, dialog))
# [{'quick_reply': {'button': ['Pizza', 'Desserts']}}]
```

For more complex versions when the lists of nested objects are used, one needs to use `Nested` with the argument `manu=True`.
For example, like this:

```
from marshmallow import fields, Schema
from maxbot import MaxBot

builder = MaxBot.builder()

class CarouselItem(Schema):
    title = fields.String(metadata={"maxml": "element"}, required=True)
    image = fields.Url(required=True)


@builder.command("carousel")
class CarouselCommand(Schema):
    item = fields.Nested(CarouselItem, many=True)


lder.use_inline_resources("""
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
print(bot.process_message(message, dialog))
# [{'carousel': {'item': [{'title': 'Pizza', 'image': 'http://127.0.0.1/Pizza.jpeg'}, {'title': 'Desserts', 'image': 'http://127.0.0.1/Desserts.jpeg'}]}}]
```

## Extending scenario context

Scenario context contains the data needed to control the conversation logic. MaxBot provides a lot of data for the context, such as `message` received from user, `intents`, `entities` and more.

The following example shows how to extend the scenario context with a user profile taken from an external source.

```
from maxbot import MaxBot

builder = MaxBot.builder()

# this is a stub, actually you can load user
# profile from database or external api
def _load_profile(user_id):
    return {
        "username": "Yours Truly"
    }

@builder.before_turn
def provide_profile(ctx):
    ctx.scenario.profile = _load_profile(ctx.dialog.user_id)

builder.use_inline_resources("""
    dialog:
      - condition: profile.username
        response: |
            Hello, {{ profile.username }}!
""")
bot = builder.build()

message = {"text": "hello"}
print(bot.process_message(message))
#[{'text': 'Hello, Yours Truly!'}]
```

In the above example, we do the following.

* We register the `before_turn` hook. This hook is called at the beginning of processing each message received from the user.
* We get the `ctx` object as the first argument to the hook. This object is an instance of the `TurnContext` class wich represents all information about the current turn of the  conversation.
* We access `ctx.dialog.user_id` attribute of the context to get the user identifier. We then load the user profile from an external source using it.
* We extend the `ctx.scenario` object with the loaded user profile by setting the `profile` attribute.
* Finally, we successfully use the `profile` template variable to get the `username` in our simple conversation scenario.


## Conversation audit

The result of processing the received message is the list of commands that need to be send to the user. During the processing commands are written to the `ctx.commands` attribute of the `TurnContext`.  You can access to these commands before sending using the `after_turn` hook.

In the example we show how to use `after_turn` hook to perform conversation audit. Using the `TurnContext` we access all the information about the current conversation turn. We simply print this information to stdout.

```
from maxbot import MaxBot

builder = MaxBot.builder()

@builder.after_turn
def journal_conversation(ctx, listening):
    print ((
        f"Got {ctx.message}\n"
        f"from {ctx.dialog}\n"
        f"with response {ctx.commands}."
    ))

builder.use_inline_resources("""
    dialog:
      - condition: message.text == 'hello'
        response: |
            Good day to you!
""")
bot = builder.build()

message = {"text": "hello"}
bot.process_message(message)
# Got {'text': 'hello'}
# from {'channel_name': 'cli', 'user_id': '1'}
# with response [{'text': 'Good day to you!'}].
```
