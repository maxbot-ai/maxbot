# Channels

## Overview

Channels are an abstractions for messaging platforms which connect your bot to the intended user. There are a lot of such platforms: Telegram, Facebook Messenger and more.

Another purpose of channels is to provide implementations for conversational applications. (TODO: link to applications)

**maxbot** provides pre-built channels for the many famous platforms. (TODO: link to the list)

## Using Channels

For each platform, there is a channel class that derives from the abstract `Channel`. A bot can use one or more channels to interact with the user. The channel class instance is implicitly created when a channel configuration is added to bot resources.

## Receivers and Senders

The `Channel.call_receivers` and `Channel.call_senders` methods internally use hooks called senders and receivers. These hooks are used to receive messages and send commands of different types. A channel class discover its hooks among its members using a naming convention: the `receive_` or `send_` prefix followed by the message or command type.

## Mixins

It's easy to create new and extend existing channels thanks to the mixins technique based on Python's multiple inheritance.

The particular channel class is created at run time and does not contain any methods itself. It inherits the abstract `Channel` class and multiple mixin classes. Mixins implement all the necessary methods. They can be added using the `BotBuilder.add_channel_mixin` method or the `BotBuilder.channel_mixin` decorator. A channel method can be implemented in more than one mixin. The actual implementation is chosen based on the [multiple inheritance](https://docs.python.org/3/tutorial/classes.html#multiple-inheritance) rules.

Mixins are added to the list of base classes from right to left. The abstract class `Channel` is rightmost. For example, let's create a channel using a couple of mixins.

```python
builder.add_channel_mixin(MyChannel1, 'my_channel')
builder.add_channel_mixin(MyChannel2, 'my_channel')
```

The generated class will look like this.

```python
class GeneratedChannel_MyChannel(MyChannel2, MyChannel1, Channel):
	pass
```

Thus, any channel method is searched for in `MyChannel2`, then in `MyChannel1`, and then in `Channel`.

## Adding Channels

To create a channel, you need to create a mixin that implements at least all the abstract methods of the `Channel` class and register it using the `BotBuilder.channel_mixin` with the desired name.

In the example we will create a simple "repl" channel that will allow us to communicate with the bot through an interactive shell.

```python
import asyncio
from marshmallow import fields, Schema
from maxbot import MaxBot, Channel

builder = MaxBot.builder()

@builder.channel_mixin("repl")
class ReplChannel(Channel):
    class ConfigSchema(Schema):
        user_prompt = fields.String(load_default='User')
        bot_prompt = fields.String(load_default=' Bot')

    async def create_dialog(self, data):
        return {'channel_name': 'cli', 'user_id': 'John'}

    async def receive_text(self, data):
        return {'text': data}

    async def send_text(self, command, dialog):
        print(self.config["bot_prompt"] + ":", command["text"])


builder.use_inline_resources("""
    channels:
        repl:
            user_prompt: 🧑
            bot_prompt: 🤖
    dialog:
      - condition: message.text in ['hello', 'hi']
        response: |
            Good day to you!
      - condition: message.text in ['good bye', 'bye']
        response: |
            OK. See you later.
      - condition: true
        response: |
            Sorry I don"t understand.
""")
bot = builder.build()
channel = bot.channels.repl

def main():
    while True:
        # Getting channel-specific channel arguments
        text = input(channel.config["user_prompt"] + ": ")

        message = await channel.call_receivers(text)
        dialog = await channel.create_dialog(text)
        commands = await bot.dialog_manager.process_message(message, dialog)
        for command in commands:
            await channel.call_senders(command, dialog)

asyncio.run(main())
```

In the example above we have implemented:

* configuration schema for prompt strings for the bot and users;
* three abstract methods of the `Channel` class: `create_dialog` and a minimal set of mandatory hooks `receive_text` and `send_text`;
* the `main` function which runs the channel-specific conversational application as a [read–eval–print](https://en.wikipedia.org/wiki/Read–eval–print_loop) loop.

## Extending channels

To extend a channel you need to create an additional mixin with the methods you wish to add or overwrite and register it with the channel name.

### Custom Receivers

When you add a custom message to your bot you also need to add a message receiver for each of channels used in your application. In this example we'll add the custom message that represents a phone contact and message receiver for the pre-built Telegram channel.

```
from marshmallow import fields, Schema
from maxbot import MaxBot
from telegram import Update, Bot

builder = MaxBot.builder()

@builder.message("contact")
class ContactMessage(Schema):
	phone_number = fields.String(required=True)
	name = fields.String()

@builder.channel_mixin("telegram")
class TelegramContact:

    async def receive_contact(self, update: Update, bot: Bot):
        """
            @see https://core.telegram.org/bots/api#contact
        """
        if update.message.contact:
            contact = update.message.contact
            return {'contact': {
                'phone_number': contact.phone_number,
                'name': contact.first_name
            }}

builder.use_inline_resources("""
    channels:
        telegram:
            api_token: !ENV ${TELEGRAM_API_KEY}
    dialog:
      - condition: message.contact
        response: |
            Received {{ message.contact.phone_number }}
""")
bot = builder.build()
```

### Custom senders

When you add a custom command to your bot you also need to add a command sender for each of channels used in your application. In this example we'll add the custom command that represents a location on the map and command sender for the pre-built Telegram channel.

```
from marshmallow import fields, Schema
from maxbot import MaxBot
from telegram import Bot

builder = MaxBot.builder()

@builder.command("location")
class LocationCommand(Schema):
    longitude = fields.Float(required=True)
    latitude = fields.Float(required=True)

@builder.channel_mixin("telegram")
class TelegramLocation:
    async def send_location(self, command, channel, bot: Bot):
        """
            @see https://core.telegram.org/bots/api#sendlocation
        """
        location = command["location"]
        await bot.send_location(
            channel['user_id'],
            latitude=location["latitude"],
            longitude=location["longitude"],
        )

builder.use_inline_resources("""
    channels:
        telegram:
            api_token: !ENV ${TELEGRAM_API_KEY}
    dialog:
      - condition: message.text == "Where are you?"
        response: |
          I am here!
          <location latitude="40.7580" longitude="-73.9855" />
""")
bot = builder.build()
```

## Webhooks

Channels can receive data in two modes: webhook and polling. Polling means that the bot polls the server at some intervals to see if there are any changes. Please note: only the built-in `telegram` channel can run in polling mode. Webhook mode means that the bot has an external web address that will be called when there is new data from the messenger.

The processing time of an incoming webhook request is limited. We recommend completing the handling within 5 seconds. Keep in mind that if you take too long to process a message from a user, the messenger may resend the same message. In order not to process the same message again, it will be necessary to check the identifiers of the processed messages. This code can be represented as `middleware` and, for example, use a database as storage.
