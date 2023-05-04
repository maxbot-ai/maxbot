# Maxbot

**Maxbot** is an open source library and framework for creating conversational apps.

## Features (work in progress)
- Unified and extendable messaging over any platform.
- Integration with external libraries and NLU services. Support for active learning.
- DSL for declarative dialog description based on ready-made models of conversational logic.
- An engine for creating your own dialog models.
- NLG command language and templates.
- Implementing business logic in a general-purpose programming language.
- Tracking dialog. Sessions. Dialog state. Error handling and recovery.
- Complex bots with multiple skills. Interaction of skills.
- Developing, debugging, testing and logging tools.
- Deployment in any environment: stand-alone, cloud-enabled, hosted. Scaling.
- Integration with external data sources, services, information systems and support services.
- Business analytics. Insights.

**Maxbot** is the right balance of simplicity and flexibility based on time-tested solutions.

## Documentation

| Documentation                                                     |                                                        |
| ----------------------------------------------------------------- | ------------------------------------------------------ |
| **[Getting Started](https://maxbot.ai/category/getting-started)** | Here's everything you need to know!                    |
| **[Design Guides](https://maxbot.ai/category/design-guides)**     | An introduction to the basics of building dialogues.   |
| **[Tutorials](https://maxbot.ai/category/tutorials)**             | Using examples to understand how to work.              |
| **[Complex Samples](https://maxbot.ai)**                          | Advanced demonstration of the system's capabilities.   |
| **[Complete documentation](https://maxbot.ai)**                   | Complete product information. Design concepts and more.|


## Install Maxbot

For detailed installation instructions, see the
[documentation](https://maxbot.ai/getting-started/installation).

- **Operating system**: macOS / OS X · Linux
- **Python version**: Python 3.9 (only 64 bit)
- **Package managers**: [pip](https://pypi.org/project/maxbot/)

### Pip

Using pip, **Maxbot** releases are available as source packages and binary wheels.
Before you install **Maxbot** and its dependencies, make sure that
your `pip` and `wheel` are up to date.

When using pip it is generally recommended to install packages in a virtual
environment to avoid modifying system state:

```bash
python -m venv .env
source .env/bin/activate
pip install -U pip wheel
pip install maxbot
```

### Quick Start

For detailed installation instructions, see the
[documentation](https://maxbot.ai/getting-started/quick-start).

First, we configure channels. Channels are a way to integrate your bot with various messaging platforms.
You must configure at least one channel to create a bot. The telegram channel is configured by specifying secret `api_token` for the telegram bot.

> Telegram channel is the best choice for a quick start because it's easy to run right on your laptop.
> Telegram Bot API allows you to receive incoming updates via long polling, so you don't need to have an external IP and set up webhooks.

Save the bot scenario as `bot.yaml` or something similar.

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

Run the MaxBot CLI app passing the path to the bot.yaml as a parameter.

```bash
$ maxbot run --bot bot.yaml
✓ Started polling updater... Press 'Ctrl-C' to exit.
```

Open your bot in telegram messenger and greet it.

- Type `Hello`. You will see the appropriate response: *"Good day to you."*
- Type `bye` and the bot will reply *"OK. See you later."*
- Enter a message unknown to the bot, `How are you?` Get a response: *"Sorry I don't understand."*

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

## Where to ask questions

The **Maxbot** project is maintained by the [Maxbot team](https://maxbot.ai).

| Type                            | Platforms                               |
| ------------------------------- | --------------------------------------- |
| **Usage Questions**             | [GitHub Discussions] · [Stack Overflow] |
| **Bug Reports**                 | [GitHub Issue Tracker]                  |
| **Feature Requests**            | [GitHub Discussions]                    |

[github issue tracker]: https://github.com/maxbot-ai/maxbot/issues
[github discussions]: https://github.com/maxbot-ai/maxbot/discussions
[stack overflow]: https://stackoverflow.com/questions/tagged/maxbot


## The near future

- Integration of deterministic dialog models (Dialog Tree, Slot Filling) with large language models (LLM) such as ChatGPT, LLaMA, etc.
- Improved debugging and logging tools.
- Switch from Markdown to command language (XML-based) in bot response scripts.
- Improved built-in date and time extensions.
- Released new examples of using the library to create complex bots.
- Support for Python 3.10, 3.11.
