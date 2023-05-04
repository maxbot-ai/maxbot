# Jinja Loader

Jinja loader extension allows you to include jinja template files into your response. You can enable this extension in `bot.yaml`:

```
extensions:
  jinja_loader: {}
```

The extension does not have any additional configuration.

## Usage examples

Jinja provides provides a couple of tags to compose templates:

- [include](https://jinja.palletsprojects.com/en/3.1.x/templates/#include),
- [import](https://jinja.palletsprojects.com/en/3.1.x/templates/#import).

In the both cases, the designer puts a piece of template in the file and then reuses it in the responses or other template files.

### Include

The `{% include ... %}` tag renders template from a file and outputs the result into the current template. This allows you to reuse a common template across multiple responses. For example, you might want to respond in the same way to user greetings  from two dialog branches. First, you should create template file with your response, call it `hello.yaml`:

```yaml
<text>
    Hello! <br />
    I am  MaxBot!
</text>
```

Then you can include this template file in your responses:

```django
dialog:
- condition: intents.hello
  response: |
    {% include 'hello.yaml' %}
```

### Import

Use the `{% import ... %}` tag if you want to use macros defined in a template file. Macros support parameter passing, so they allow you to reuse templates in a more flexible way then just including files.

Let's reuse the same hello response, but now using macro. You can now specify a bot name when calling a macro.

```django
{% macro hello(name) %}
<text>
    Hello! <br />
    I am  {{ name }}!
</text>
{% endmacro %}
```

Then you can import macro from template file `hello.yaml` and use it.

```django
dialog:
- condition: intents.hello
  response: |
    {% from 'hello.yaml' import hello %}
    {{ hello('MaxBot') }}
```

## Template directory

You can specify template files in `{% include ... %}` and `{% import ... %}` tags using absolute paths or paths that is relative to the bot resource base directory. Typically the base directory is the directory where your `bot.yaml` file is located, more specifically

* if the bot resources are loaded from a file (e.g. by calling `BotBuilder.use_file_resources`), then the base directory is the directory of that file;
* if the bot resources are loaded from a directory (e.g. by calling `BotBuilder.use_directory_resources`), then that directory becomes the base directory;
* if the bot resources are loaded from a package (e.g. by calling `BotBuilder.use_package_resources`), then the package directory becomes the base directory.

## Reloading templates on changes

You can change template files while the bot is running. Jinja template engine tracks the changes and reloads templates on the fly. So you will see all the changes immediately in the bot responses.
