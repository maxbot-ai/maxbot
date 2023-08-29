# Quick Start

In this quick start tutorial, we help you use MaxBot to build your first conversation.

What does a bot look like? Take a look at a simple bot that only knows how to greet and say goodbye to the user via the [Telegram Messenger](https://core.telegram.org/bots).

```yaml
channels:
  telegram:
    api_token: 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
intents:
  - name: greetings
    examples:
      - Good morning
      - Hello
      - Hi
  - name: ending
    examples:
      - Goodbye
      - Bye
      - See you
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

Bot resources such as channels, intents and a dialog tree are defined using YAML. So what did that code do?

## Configure channels

First, we configure channels. Channels are a way to integrate your bot with various messaging platforms. You must configure at least one channel to create a bot. The telegram channel is configured by specifying secret `api_token` for the telegram bot.

```yaml
channels:
  telegram:
    api_token: 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
```

:::caution
The actual token here is for demonstration only and does not refer to any telegram bot. If you want to run this bot, you should go to [@BotFather](https://t.me/botfather), create your own bot, get its API token and specify it in the bot resources.
:::

:::info
Telegram channel is the best choice for a quick start because it's easy to run right on your laptop. Telegram Bot API allows you to receive incoming updates via long polling, so you **don't need** to have an external IP and set up webhooks.
:::

## Define intents

Next, we define intents that recognize user greetings and endings. Intents are purposes or goals that is expressed in user input. For each intent we provide examples of utterances that real users might enter to trigger this intent. The bot uses this examples to train machine learning  models to understand user questions.

```yaml
intents:
  - name: greetings
    examples:
      - Good morning
      - Hello
      - Hi
  - name: ending
    examples:
      - Goodbye
      - Bye
      - See you
```

:::info

By default MaxBot uses simple builtin model based on cosine similarity to recognized intents. Is is easy to integrate MaxBot with state of the art natural language processing and machine learning models for the best recognition quality.

:::

## Build a dialog

Finally, we build a dialog. A dialog defines the flow of your conversation in the form of a logic tree. It matches intents (what users say) to responses (what your bot says back). Each node of the tree has a condition that triggers it, based on user input.

We create a simple dialog that handles greeting and ending intents, each with a single node. It is also good practice to add a node to handle misunderstood user utterances.

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

## Run the bot

We got a simple bot that recognizes and responds to both greeting and ending inputs. Let's see how well it works.

:::note
Follow the [Installation](/getting-started/installation.md) instructions and install MaxBot first.
:::

The bot will be available through the [Telegram Messenger](https://core.telegram.org/bots).

:::note
To integrate with the messenger, contact [@BotFather](https://t.me/botfather) and ask it to create a bot for you and generate an API token. Then specify API token in the bot resources. Refer [official docs](https://core.telegram.org/bots#6-botfather) for more information about telegram bots.
:::

Save the bot resources as `bot.yaml` or something similar. Run the MaxBot Command Line Interface (CLI) app passing the path to the `bot.yaml` as a parameter.

```bash
$ maxbot run --bot bot.yaml
✓ Started polling updater... Press 'Ctrl-C' to exit.
```

Open your bot in telegram messenger and greet it.

* Type `Hello`. You will see the appropriate response: *"Good day to you."*
* Type `bye` and the bot will reply *"OK. See you later."*
* Enter a message unknown to the bot, `How are you?` Get a response: *"Sorry I don't understand."*

The output in your console will look like this

```
[01/27/23 23:06:44], telegram#123456789
🧑 Hello
🤖 Good day to you!

[01/27/23 23:06:48], telegram#123456789
🧑 bye
🤖 OK. See you later.

[01/27/23 23:07:03], telegram#123456789
🧑 How are you?
🤖 Sorry I don't understand.
```

Press `Ctrl-C` to exit MaxBot CLI app.

Congratulations! You have successfully created and launched a simple bot and chatted with it.


## Examples

You can find a lot of basic bot examples in this reference. If you want to get more complex ones, check out the list of examples below. They show the advanced features of Maxbot, such as custom messanger controls, integration with different REST services, databases and so on.

- [Bank Bot example](https://github.com/maxbot-ai/bank_bot).
- [Taxi Bot example](https://github.com/maxbot-ai/taxi_bot).
- [Transport Bot example](https://github.com/maxbot-ai/transport_bot).