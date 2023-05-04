# Packaging Guide

When you create a conversational app with **maxbot** it's a good choice to create your own Python package. That's what allows you to distribute your app, e.g. deploy and run it on a remote server.

Nowadays, there are several ways and tools to create Python packages (what you install with `pip install something`). You might even have your favorite already.

Here's a guide, showing one of the alternative ways of creating a Python package with a **maxbot** conversational app, from scratch.


## Prerequisites

For this tutorial we'll use [Poetry](https://python-poetry.org).

Poetry's docs are great, so go ahead, check them and install it.

## Create a Project

Let's say we want to create a **maxbot** application called `hello-world`.`

Create a project with Poetry:

```
$ poetry new hello-world
Created package hello_world in hello-world
```

Enter the new project directory:

```
$ cd hello-world/
```

You can see that you have a generated project structure that looks like:

```
$ tree
.
├── README.md
├── hello_world
│   └── __init__.py
├── poetry.lock
├── pyproject.toml
└── tests
    └── __init__.py
```

## Dependencies and Environment

Add `maxbot[all]` to your dependencies. This command also creates a virtual environment for your project:

```
$ poetry add maxbot[all]
Creating virtualenv hello-world-g89_GtdQ-py3.9 in /Users/user_name/Library/Caches/pypoetry/virtualenvs
Using version ^0.1.0.dev20220922191958 for maxbot

Updating dependencies
Resolving dependencies... (6.9s)

Writing lock file

Package operations: 47 installs, 1 update, 0 removals

  ...omit lots of dependencies...
  • Installing maxbot (0.1.0.dev20220922191958)
```

Activate that new virtual environment.

```
$ poetry shell
Spawning shell within /Users/user_name/Library/Caches/pypoetry/virtualenvs/hello-world-g89_GtdQ-py3.9
```

## Create Your Bot

Now let's create an extremely simple bot.

Add the following code into the `hello_world/__init__.py`:

```python
from maxbot import MaxBot

builder = MaxBot.builder()
#
# here you can customize your bot by changing builder properties
#
builder.use_package_resources(__name__)
bot = builder.build()
```

The bot uses `builder.use_package_resources` to load resources. `__name__` is the name of the current Python package `hello_world`. The bot needs to know where it’s located to load resources, and `__name__` is a convenient way to tell it that.

## Add Resources

All resources are located in the package directory `hello_world`.

In our project let's create a single file `hello_world/bot.yaml` with the contents from [Quick Start Guide](/getting-started/quick-start.md):

```yaml
channels:
    telegram:
        api_token: YOUR_TELEGRAM_API_TOKEN
intents:
  - name: greetings
    examples: [Good morning, Hello, Hi]
  - name: ending
    examples: [Goodbye, Bye, See you]
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

Of course, if you have a lot of resources, you can split them into multiple files and subdirectories in the package directory.

## Keep Your Secrets

The `telegram` channel settings in the `bot.yaml` contains `api_token` which is the secret token used to authenticate your bot. It's good practice to store such secrets in environment variables rather than in code.

So write the reference to the environment variable `TELEGRAM_API_KEY` instead of actual value `YOUR_TELEGRAM_API_TOKEN`.

```
channels:
    telegram:
        api_token: !ENV ${TELEGRAM_API_KEY}
```

Perhaps you don't want to reveal your secret to anyone, not even your team. Then a good place to put your secret environment variables is the virtualenv’s activate script. This script is located outside the project directory and will not be accessible to anyone but you.

You can get the path to your virtualenv with the `poetry env info -p` command. So put the following contents to the end of the script `$(poetry env info -p)/bin/activate`:

```
export TELEGRAM_API_KEY="YOUR_TELEGRAM_API_TOKEN"
```

Activating the virtualenv will set the variables.

## Install your package

You can now install your package:

```
$ poetry install
Installing dependencies from lock file

No dependencies to install or update

Installing the current project: hello-world (0.1.0)
```

Your package is installed in [editable mode](https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs) in the environment created by Poetry. Editable (or development) mode means that as you make changes to your local code, you’ll only need to re-install if you change the metadata about the project, such as its dependencies.

## Run The Bot

Now you can run your bot using the `maxbot run` command.

The `maxbot` command is installed by **maxbot** package, not your application. It must be told where to find your bot in order to use it. The `--bot` option is used to specify how to load the bot.

Your bot is in the `hello_world` package in the variable called `bot`. So type the following

```
$ maxbot run --bot hello_world:bot
```

You’ll see output similar to this:

```
TODO: just ptb logs for now
```

Open your telegram bot in the Telegram app, type "hello" and see the answer. Congratulations, you’re now running your **maxbot** conversational application!

## Test your code

TODO:

* just plain python tests using pytest
* need a bit advanced codebase to test it

## Write some stories

TODO:

* move stories from "quick start" tutorial
* need pytest plugin to run the stories
* need click environments and dotenv to not to repeat --bot option

## Create a wheel package

Python packages have a standard format called a "wheel". It's a file that ends in .whl.

You can create a wheel with Poetry:

```
$ poetry build
Building hello-world (0.1.0)
  - Building sdist
  - Built hello-world-0.1.0.tar.gz
  - Building wheel
  - Built hello_world-0.1.0-py3-none-any.whl
```

After that, if you check in your project directory, you should now have a couple of extra files at `dist/`:

```
$ tree dist/
dist/
├── hello-world-0.1.0.tar.gz
└── hello_world-0.1.0-py3-none-any.whl
```

The .whl is the wheel file. You can send that wheel file to anyone and they can use it to install your program.

The wheel file only includes source code and resources contained in the `hello_world/` directory (your Python package).

## Deploy your package

Let's say you have a server that you want to deploy your bot to. If you don't have a server you can open another terminal and set up a new virtual environment on your development computer to try out the instructions below.

You need to copy the wheel file to your server then install it with pip.

```
$ pip install hello_world-0.1.0-py3-none-any.whl
```

This will install your package along with its dependencies, i.e. the **maxbot** package.

The next step is to configure your application by setting the required environment variables on your server. The way you set variables depends on your server setup. We just export the variables before running the application.

Now you have your conversatinoal app installed and configured on yor server. And you can use it freely:

```
$ export TELEGRAM_API_KEY="YOUR_TELEGRAM_API_TOKEN"
$ maxbot run --bot hello_world:bot
```

## What's next

* Use [Git](https://git-scm.com), the version control system, to save your code.
* Integrate a CI tool to run your tests and deploy your package automatically.
