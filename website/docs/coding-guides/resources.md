# Resources

TODO:

* Variable substitution
* ...

## Loading Resources

### Inline Resources

In the simplest case you can create bot by providing a string with resources. This is typically useful for testing or playing with some bot features. Try the `use_inline_resources` method of the `builder`.

```
from maxbot import MaxBot

builder = MaxBot.builder()
#
# here you can customize your bot by changing builder properties
#
builder.use_inline_resources("""
    dialog:
      - condition: message.text
        response: |
            Hello world!
""")
bot = builder.build()
```

### File Resources

You can create a simple bot from a single file containing all the necessary resources. Try the `use_file_resources` method of the `builder`.

```
from maxbot import MaxBot

builder = MaxBot.builder()
#
# here you can customize your bot by changing builder properties
#
builder.use_file_resources('bot.yaml')
bot = builder.build()
```

### Directory Resources

As your bot grows, it gets more convenient to split a lot of resources, especially intents and entities, into several files and place them into directory of given structure.

```
mybot/
    intents/
        core-intents.yaml
        faq-intents.yaml
    entities/
        core-entities.yaml
        products-entities.yaml
    bot.yaml
    dialog.yaml
```

You can use the name of that directory to load all the resources in one line by using the `use_directory_resources` method of the `builder`.

```
from maxbot import MaxBot

builder = MaxBot.builder()
#
# here you can customize your bot by changing builder properties
#
builder.use_directory_resources('mybot/')
bot = builder.build()
```

### Package Resources

However, as a project gets bigger, it becomes overwhelming to keep all the code in one file. Python projects use packages to organize code into multiple modules that can be imported where needed, and we do this as well.

You can also put all the resources into a python package to make it easier to distribute your project.

See [Packaging Guide](packaging.md) for example of using package resources.
