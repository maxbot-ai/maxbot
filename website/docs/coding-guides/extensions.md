# Extensions

Extensions are extra packages that add functionality to a **maxbot** application. For example, an extension might add support for new channel, custom state tracker or sending some special types of messages.

**maxbot** extensions are usually named "maxbot-foo". You can search PyPI for packages tagged with [Framework :: MaxBot](https://pypi.org/search/?c=Framework+%3A%3A+MaxBot).

## Using Extensions

Consult each extension’s documentation for installation, configuration, and usage instructions.

### Installing

First, you need to install the extension

```
$ pip install maxbot-foo
```

If you are developing the **maxbot** project you need to add the extension package as a project dependency.

Next, there are two ways to add the extension to your bot. You can simply declare the required extensions in `bot.yaml`. If you need more control you can apply extensions in the source code.

### Declaring in bot.yaml

An extension can be declared in the `extensions` section of your `bot.yaml`.

```
extensions:
    foo: {}
```

Where `foo` is the name of the extension and value `{}` is the extension configuration dictionary. In our case configuration is empty. Generally, each extension has it's own configuration schema described in the extension's documentation. For example, an extension that installs a custom sql state\_store for a bot could be configured as follows

```
extensinos:
    my-state-tracker:
        dsn: "mssql+pyodbc://user:password@DSNSTRING"
```

No programming skills are required to add extensions this way.

TODO: Need an example based on real life extension.

### Applying in source code

If you are programmatically customizing your bot with a builder pattern note that the extensions declared in `bot.yaml` are loaded when your call the `build` method after all the customizations have been done. To apply your customizations to a loaded extension you must first load the extension manually.

```
from maxbot_foo import foo_extension
from maxbot import MaxBot

builder = MaxBot.builder()

# manualy load an extension
foo_extension(builder, config={})

# here you can customize your bot

# provide a way to load resources
builder.use_file_resources('bot.yaml')

# actually loads extensinos declared in the bot.yaml
bot = builder.build()
```

You do not need to declare extension in `bot.yaml` if you are loading it manually.

TODO: Do we need to configure such extensions in bot.yaml?

## Developing Extensions

This section will show how to create **maxbot** extensions.

### Naming

We give extensions string names so they can be declared in `bot.yaml`. Most of declarations in `bot.yaml` must be valid Python identifiers. For consistency, extension names follow the same requirement.

Typically, the extension name is prefixed with `maxbot` to make it a unique Python package name. A general Python packaging recommendation is that the install name from the package index and the name used in `import` statement should be related.  The import name is lowercase, with words separated by underscores (\_). The install name is lower case case, with words separated by dashes (-).

For example, extension named `foo_bar` installed as `maxbot-foo-bar` and imported as `maxbot_foo_bar`.

### Customizing Bots

An extension is nothing more then a Python callable with two arguments: a bot builder and an optional configuration dictionary. Given these arguments an extension should customize a bot builder.

```
def foo_bar_extension(builder, config):
	builder.before_turn(...)
	...
```

There are many ways that an extension can customize the builder. Any methods that are available on a bot builder can be used during an extension’s call. See [Bots](/coding-guides/bots.md) guide to learn how to customize a bot.

It is important that the `builder` instance is not stored on the extension and the `builder` methods should not be called after the extension callable is complete.

### Configuring

TODO: Not implemented yet. Needs to be refactored in that way.

The second argument to the extension callable is an optional configuration dictionay. If you want to pass a non-empty configuration when declaring an extension in `bot.yaml`, you must specify a schema for that configuration. The configuration dictionary schema is specified using the `maxbot_extension` annotation.

```
from marshmallow import Schema, fields
from maxbot import maxbot_extension

class ForBarConfig(Schema):
	some_str = fields.String(required=True)
	some_number = fields.Integer()

@maxbot_extension(config_schema=ForBarConfig)
def foo_bar_extension(builder, config):
	builder.before_turn(...)
```

Then the extension can be configured in `bot.yaml` as follows

```
extensions:
    foo_bar:
        some_str: !ENV some value with ${SOME_VARIABLE}
        some_number: 123
```

You can also use variable substitution (TODO: link) to pass environment variables to the extension's configuration.

A schema specification is not required when you apply an extension in source code.

### Discovering

To be available for declaration in `bot.yaml`, an extension must be specified in the `maxbot_extensions` [entry point](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata). **maxbot** will automatically discover such extensions. Entry points are specified in setup.py

```
from setuptools import setup

setup(
    name='maxbot-foo-bar',
    ...,
    entry_points={
        'maxbot_extensions': [
            'foo_bar=maxbot_foo_bar:foo_bar_extension'
        ],
    },
)
```

or pyproject.toml if you are using for example the [poetry](https://python-poetry.org) tool.

```
[tool.poetry.plugins.maxbot_extensions]
foo_bar = "maxbot_foo_bar:foo_bar_extension"
```

For other packaging tools refer to their documentation for support of defining entry points.

### In-project Extensions

Let's say you have developed an in-project extension in your **maxbot** project and want to make it available for declaring in the `bot.yaml` file. To do this, pass the `available_extensions` argument to the `builder` factory as follows.

TODO: Why is it an argument and not a separate builder method.

```
from maxbot import MaxBot

from .bar import bar_extension

builder = MaxBot.builder(available_extensions={
	'bar': bar_extension
})
# ...
builder.use_file_resources('bot.yaml')
bot = builder.build()
```

Then the extension can be declared in the `bot.yaml` file as usual.

```
extensions:
    bar: {}
```

In this case it will be loaded when your call the `build` method.
