---
sidebar_label: Maxml
---
# Maxml (Markup Language)

The bot's reaction to an incoming message is a set of commands to be sent.
These commands must be described in a special format: headless XML.
Headless XML document implies a string that is the mixed content of some root element that is not explicitly described in this document.
Headless XML document must be obtained as a result of [templating](/design-guides/templates.md) the string that is specified as a response in the [dialog tree](/design-guides/dialog-tree.md).
This technology stack is called `maxml`.

Mixed content means that both explicit commands using XML syntax and raw text are allowed in the string obtained after [templating](/design-guides/templates.md).
That is, we can say hello to the user using simple text:
```yaml
dialog:
  - condition: true
    response: |
      Hello, world!
```

Or we can explicitly use the `text` command:
```yaml
dialog:
  - condition: true
    response: |
      <text>Hello, world!</text>
```

Both options will generate an identical `text` command:
```
🧑 test
🤖 Hello, world!
```

Raw text between explicit commands is packaged into individual text commands.
For example the following response:
```yaml
dialog:
  - condition: true
    response: |
      Hello<image url="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg" />world
```

Will be deserialized into three separate commands: `text`, `image` and `text` again:
```
🧑 test
🤖 <text>Hello</text>
   <image url="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg" />
   <text>world</text>
```

## Markup

The contents of the text fields of the command can be described as a [regular string](/design-reference/strings.md),
then when describing the command, you can use `maxbot.maxml.fields.Str`.
But it is possible to define a text field as markup (`maxbot.maxml.markup.Field`).
How it is done for the built-in `text` command.

This means that Maxbot will apply special logic to the content.
It is acceptable to use nested tags (for example: `<br />`), and a renderer will be used to get the text sent to the user.
The default renderer (`maxbot.maxml.markup.PlainTextRenderer`) replaces the opening of the `br` tag with a newline and
normalizes all whitespace characters (including newline) to a single space.
Other closing and opening tags are ignored.
For example response:
```yaml
response: |
    <text>
        Hello,
        world! <br /> How are
        you?
    </text>
```

Will be rendered to text consisting of two lines: `Hello, world!` and `How are you?`.

More datails can be found in [Markup and Jinja](/coding-guides/maxml#normalization)

## Image

To send images to a user, one can use the builtin command [image](/design-reference/protocol.md#imagemessage).
The command must be represented as an XML element, for example:
```xml
<image url="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg" />
```

If it’s necessary to add a description to a picture, then the examples given above will look like this:
```xml
<image url="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg">
    <caption>Hello, world!</caption>
</image>
```

The content of `caption` child element is treated as [Markup](#markup).

## Advanced use of Maxml

Advanced use of Maxml is described in [Maxml (Advanced)](/coding-guides/maxml.md).
