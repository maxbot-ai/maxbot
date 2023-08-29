# Using stories

You can use the stories mechanism to test the bot.
This is a mechanism that verifies that the bot will react in the expected way to events known in advance from the user.
Stories are written in a YAML file, the full format of which can be found in [Design Reference](/design-reference/stories.md).
Multiple stories files can be grouped in a directory.

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

You will need [pytest](https://pytest.org/) to run stories.
It's a great framework for testing.
MaxBot is registered in it as plugin `maxbot_stories` to run stories.
`pytest` is not installed as a dependency to `maxbot` by default.
`pytest` must be installed additionally:

```bash
$ pip install pytest
```

**Note:** if in process of running stories you get warning message:
```
PytestConfigWarning: Unknown config option: asyncio_mode
```
You can either ignore it or install the `pytest-asyncio` package to remove the warning:
```bash
$ pip install pytest-asyncio
```

Now we can start the stories engine.
If `--bot` option is specified when starting `pytest`,
then `pytest` will interpret the file passed to it as a YAML stories file.

```bash
$ pytest --bot bot.yaml stories.yaml
============================ test session starts ============================
platform openbsd7 -- Python 3.9.17, pytest-7.3.1, pluggy-1.0.0
plugins: anyio-3.7.0, asyncio-0.20.3, cov-4.1.0, respx-0.20.1, maxbot-0.2.0
collected 1 item

stories.yaml .                                                         [100%]

============================ 1 passed in 6.75s ==============================
```

`1 passed` indicates that one story was successfully completed.
If we need more runtime details we can add the `-v` option:
```bash
$ pytest --bot bot.yaml stories.yaml
============================ test session starts ============================
platform openbsd7 -- Python 3.9.17, pytest-7.3.1, pluggy-1.0.0
plugins: anyio-3.7.0, asyncio-0.20.3, cov-4.1.0, respx-0.20.1, maxbot-0.2.0
collected 1 item

stories.yaml::echo PASSED                                              [100%]

============================ 1 passed in 6.75s ==============================
```

The value of option `--bot` can be a path for bot file or directory or the Maxbot instance to load.
The instance can be in the form 'module:name'.
Module can be a dotted import.
Name is not required if it is 'bot'.
This value is the same as the value of option `-B` / `--bot` when starting [maxbot run](/design-reference/cli#run).

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

Let's run stories again, but
now specify `-x` option - terminate testing at first mismatch:
```bash
$ pytest -x --bot bot.yaml stories.yaml
============================ test session starts ============================
platform openbsd7 -- Python 3.9.17, pytest-7.3.1, pluggy-1.0.0
plugins: anyio-3.7.0, asyncio-0.20.3, cov-4.1.0, respx-0.20.1, maxbot-0.2.0
collected 3 items

stories.yaml .F

============================ FAILURES =======================================
____________________________ how are you? ___________________________________
Mismatch at step [0]
Expected:
  <text>how are you?</text>
Actual:
  <text>how ar</text>
============================ short test summary info ========================
FAILED stories.yaml::how are you?
!!!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!
=========================== 1 failed, 1 passed in 2.19s =====================

```

The result:
* 3 stories were collected for testing
* first story executed successfully
* second story executed with mismatch,
* testing being stopped (third story was not run)

In the console output of the utility we see:
In the steps of the `hello` story all bot responses are as expected.
In the steps of the `how are you?` story at first step (steps are numbered from 0) bot response is not as expected.
We expect a text message from the bot with the content "how are you?", but received a "how ar" message.

If we don't want stories to fail, we can mark the problematic story with the `xfail` mark:
```yaml
- name: hello
  turns:
    - message: hello
      response: hello
- name: how are you?
  markers: ["xfail"]
  turns:
    - message: how are you?
      response: how are you?
- name: lorem ipsum
  turns:
    - message: lorem ipsum
      response: lorem ipsum
```

And run stories again with the `stories` command with same command-line options:
```bash
$ pytest -x --bot bot.yaml stories.yaml
============================ test session starts ============================
platform openbsd7 -- Python 3.9.17, pytest-7.3.1, pluggy-1.0.0
plugins: anyio-3.7.0, asyncio-0.20.3, cov-4.1.0, respx-0.20.1, maxbot-0.2.0
collected 3 items

stories.yaml .xF

============================ FAILURES =======================================
____________________________ lorem ipsum ____________________________________
Mismatch at step [0]
Expected:
  <text>lorem ipsum</text>
Actual:
  <text>lorem</text>
============================ short test summary info ========================
FAILED stories.yaml::lorem ipsum
!!!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!
============================ 1 failed, 1 passed, 1 xfailed in 2.20s =========
```

We see that the result of the "how are you?" story has changed from `failed` to `xfailed`.
And now the next story "lorem ipsum" has started after it.


### Selective stories run

For example, we have such stories (`stories.yaml` file context):
```yaml
- name: branch_1_story_1
  turns:
  - message: test1
    response: test1
- name: branch_2_story_2
  turns:
  - message: test2
    response: test2
- name: branch_2_story_3
  turns:
  - message: test3
    response: test3
- name: branch_2_story_4
  turns:
  - message: test4
    response: test4
```

To run only history `branch_1_story_1` you can use the command line parameter `-k`
```bash
$ pytest --bot bot.yaml -k "branch_1_story_1" stories.yaml
============================ test session starts ============================
platform openbsd7 -- Python 3.9.17, pytest-7.3.1, pluggy-1.0.0
plugins: anyio-3.7.0, asyncio-0.20.3, cov-4.1.0, respx-0.20.1, maxbot-0.2.0
collected 4 items / 3 deselected / 1 selected

stories.yaml .                                                         [100%]

============================ 1 passed, 3 deselected in 7.07s ================
```

But you can also use more complex expressions.
For example:
you can run all stories with an `branch_2_` substring in the name, excluding `branch_2_story_3`.
```bash
$ pytest -v --bot bot.yaml -k "branch_2_ and not branch_2_story_3" stories.yaml

============================ test session starts ============================
platform openbsd7 -- Python 3.9.17, pytest-7.3.1, pluggy-1.0.0
plugins: anyio-3.7.0, asyncio-0.20.3, cov-4.1.0, respx-0.20.1, maxbot-0.2.0
collected 4 items / 2 deselected / 2 selected

stories.yaml::branch_2_story_2 PASSED                                  [ 50%]
stories.yaml::branch_2_story_4 PASSED                                  [100%]

============================ 2 passed, 2 deselected in 6.07s ================
```

### Directory usage

As the number of stories increases, storing them in a single file becomes inconvenient.
Therefore, you can create a separate directory in which to place YAML files with stories
Let's split our previous example into three files:
`stories/1.yaml`, `stories/2.yaml` and `stories/3.yaml`.
Now let's run `pytest` to execute all stories from `stories/` directory:
```bash
$ pytest -v --bot bot.yaml stories/
============================ test session starts ============================
platform openbsd7 -- Python 3.9.17, pytest-7.3.1, pluggy-1.0.0
cachedir: .pytest_cache
plugins: anyio-3.7.0, asyncio-0.20.3, cov-4.1.0, respx-0.20.1, maxbot-0.2.0
collected 3 items

stories/1.yaml::hello PASSED                                           [ 33%]
stories/2.yaml::how are you? PASSED                                    [ 66%]
stories/3.yaml::lorem ipsum PASSED                                     [100%]

============================ 3 passed in 3.34s ==============================

```
