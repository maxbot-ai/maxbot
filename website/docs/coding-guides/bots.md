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

More details can be found in [maxml](/design-guides/maxml.md).

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
