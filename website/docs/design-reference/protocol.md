# Protocol

All communication with the users takes place under a single platform-independent protocol.

## Envelopes

### `DialogSchema`

General information about the current conversation. Includes information that does not change or rarely changes during a conversation.

| Name           | Type                                   | Description |
| -----------    | ----------- 	                          | ----------- |
| `channel_name` | [String](/design-reference/strings.md) | The name of the channel in which the conversation is taking place. |
| `user_id`      | [String](/design-reference/strings.md) | The ID of the user with whom the conversation is taking place. This ID is unique within the channel. So all users will have unique identifiers within any channel, such as Telegram, Facebook, Instagram or any other. It is the responsibility of the channel to ensure that users are uniquely identified. |

### `MessageSchema`

Message received by the user.

This schema is implemented as an envelope for a different message types. The schema field represents a message of particular type. The field name is the name of the message type. The field type is the payload for the message of that type. Typically, only one field is populated for the message.

The schema supports most widely used message types in a platform-independent way. You can customize the schema by adding new types and overriding existing types.

#### Attributes

| Name           | Type                                   | Description |
| -----------    | ----------- 	                          | ----------- |
| `text`         | [String](/design-reference/strings.md) | Text message. |
| `image`        | [ImageMessage](#imagemessage)          | Image message. |

#### Examples

* Check for text message in dialog tree.

	```yaml
	condition: message.text == "Hello world!"
	# ...
	```

* Check whether you receive an image message using `message.image` expression.

	```yaml
	condition: message.image
	# ...
	```

* You can capture the exact text uttered by the user using the `message.text` expression. For example, the node checks for a text message in its condition, stores the text in the state variable for the future use and repeats the text that the user specified back in the response.

	```yaml
	# ...
	response: |
      You can leave a comment to the order.
	followup:
	  - condition: message.text
	    response: |
	        {% set slots.order_comment = message.text %}
	        Got it! Your comment: {{ message.text }}.
	```

	The dialog could be like this.

	```
	...
	🤖 You can leave a comment to the order.
	🧑 Please add extra cheese.
	🤖 Got it! Your comment: Please add extra cheese.
	```

* To store the value of a string that you extract from the user's input, you can include a Jinja expression that uses the extract filter to apply a regular expression to the user input. The following expression extracts a number from the user input, and saves it to the `slots.number` variable.

	TODO: implement this

	```
	{% set slots.number = message.text|extract("\d+", 0) %}
	```

	TODO: Using regexp `message.text|match(...)`


### `CommandSchema`

Command to send to user.

This schema is implemented as an envelope for a different command types. The schema field represents a command of particular type. The field name is the name of the command type. The field type is the payload for the command of that type. Typically, only one field is populated for the command and commands are loaded in whole lists.

The schema supports most widely used command types in a platform-independent way. You can customize the schema by adding new types and overriding existing types.

#### Attributes

| Name           | Type                                        | Description |
| -----------    | ----------- 	                               | ----------- |
| `text`         | [Markup](/design-guides/maxml.md#markup) | Text command. |
| `image`        | [ImageCommand](#imagecommand)               | Image command. |

#### Examples

* Mixed text and image commands.

	```yaml
	response: |
	  <text>Hello world!</text>
	  <image url="http://example.com/hello.png" />
	```

* Send text command.

	```yaml
	response: |
	  <text>Hello world!</text>
	```

* Use short syntax single text command instead of command list.

	```yaml
	response: |
        Hello world!
	```


## Messages

### `ImageMessage`

An image message payload.

#### Attributes

| Name          | Type                                    | Description |
| -----------   | ----------- 	                          | ----------- |
| `url`\*       | [String](/design-reference/strings.md)  | Image URL. Use this URL to download the image file. Download it ASAP because many messaging platforms do not guarantee the lifetime of the URL. |
| `size`        | [Integer](/design-reference/numbers.md) | Image size in bytes. |
| `caption`     | [String](/design-reference/strings.md)  | Caption as defined by the user. |

#### Examples

The following node checks for an image message in its condition and responds with the image URL and caption.

```yaml
- condition: message.image
  response: |
    Received image {{ message.image.url }}
    with a caption {{ message.image.caption }}.
```

The MaxBot CLI application outputs the dialog turn like the following.

```yaml
🧑 image:
     caption: hello image
     url: https://api.telegram.org/file/bot123:XXXX/photos/file_10.jpg
🤖 Received image https://api.telegram.org/file/bot123:XXXX/photos/file_13.jpg with a caption hello.
```

## Commands

### ```ImageCommand```

An image command payload.

#### Attributes

| Name          | Type                                     | [Maxml metadata](/design-guides/maxml.md#metadata) | Description |
| -----------   | ----------- 	                           | ---------                                          | ----------- |
| `url`\*       | [String](/design-reference/strings.md)   | attribute                                          | HTTP URL to get a file from the Internet. |
| `caption`     | [Markup](/design-guides/maxml.md#markup) | element                                            | Caption of the image to be sent. |


#### Examples

```yaml
response: |
    <image url="http://example.com/hello.png">
        <caption>Hello world!</caption>
    </image>
```
