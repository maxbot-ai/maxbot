# Using stories

You can use the stories mechanism to test the bot.
This is a mechanism that verifies that the bot will react in the expected way to events known in advance from the user.
Stories are written in a YAML file, the full format of which can be found in [Design Reference](/design-reference/stories.md).

## Example of using the stories

Let's take the example of a simple echo bot that sends back the contents of his own messages to the user.
The whole `bot.yaml` of such a bot looks like this:

```yaml
dialog:
  - condition: message.text
    response: |
      {{ message.text }}
```

To test the bot, next to the `bot.yaml` file, let's create the `stories.yaml` file.
In `stories.yaml` we will describe one story (named `echo`) that sends a bot a text message
and expects to receive it back:

```yaml
- name: echo
  turns:
    - message: hello
      response: hello
    - message: how are you?
      response: how are you?
    - message: lorem ipsum
      response: lorem ipsum
```

Now we can start the stories engine with the `stories` command of the `maxbot` utility.
We can only specify the path to `bot.yaml` in the `-B` argument (like the `run` command):

```bash
$ maxbot stories -B examples/echo/bot.yaml
echo OK
```

`OK` after the name of the story (`echo`) indicates that all the steps in the story were completed in accordance with the expected behavior of the bot.

The stories file can be located anywhere in the file system hierarchy.
To run an arbitrary stories file for execution, you need to specify the path to it in the `-S` argument:

```bash
$ maxbot stories -B examples/echo/bot.yaml -S examples/echo/stories.yaml
echo OK
```

### Error detection

Modify the bot code so that it returns only the first 6 characters of the user's message:

```yaml
dialog:
  - condition: message.text
    response: |
      {{ message.text[:6] }}
```

Let's change the content of `stories.yaml` too,
splitting the story with three steps into three separate stories:

```yaml
- name: hello
  turns:
    - message: hello
      response: hello
- name: how are you?
  turns:
    - message: how are you?
      response: how are you?
- name: lorem ipsum
  turns:
    - message: lorem ipsum
      response: lorem ipsum
```

And run the `maxbot` utility again with the `stories` command:
```bash
$ maxbot stories -B examples/echo/bot.yaml
hello OK
how are you? FAILED at step [0]
Expected:
  <text>how are you?</text>
Actual:
  <text>how ar</text>
Aborted!
```

In the console output of the utility we see:
In the steps of the `hello` story all bot responses are as expected.
In the steps of the `how are you?` story at first step (steps are numbered from 0) bot response is not as expected.
We expect a text message from the bot with the content "how are you?", but received a "how ar" message.

If we don't want stories to fail, we can mark the problematic story with the `xfail` field:
```yaml
- name: hello
  turns:
    - message: hello
      response: hello
- name: how are you?
  xfail: true
  turns:
    - message: how are you?
      response: how are you?
- name: lorem ipsum
  turns:
    - message: lorem ipsum
      response: lorem ipsum
```

And run the `maxbot` utility again with the `stories` command:
```bash
$ maxbot stories -B examples/echo/bot.yaml
how are you? XFAIL at step [0]
Expected:
  <text>how are you?</text>
Actual:
  <text>how ar</text>
lorem ipsum FAILED at step [0]
Expected:
  <text>lorem ipsum</text>
Actual:
  <text>lorem</text>
Aborted!
```

We see that the result of the "how are you?" story has changed from `FAILED` to `XFAIL`.
And now the next story "lorem ipsum" has started after it.

If running the `stories` command results in "FAILED", the return code of the `maxbot` utility will be different from 0.
Otherwise the `maxbot` utility will return 0.
