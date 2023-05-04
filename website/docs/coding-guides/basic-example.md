# Basic Example

A basic conversational application based on **maxbot** looks something like this:

```python
from maxbot import MaxBot

bot = MaxBot.inline("""
    dialog:
      - condition: message.text.lower() in ['hello', 'hi']
        response: Good day to you!
      - condition: message.text.lower() in ['good bye', 'bye']
        response: OK. See you later.
      - condition: true
        response: Sorry I don"t understand.
""")

while True:
    message = {"text": input("🧑: ")}
    commands = bot.process_message(message)
    for command in commands:
        print("🤖:", command["text"])
```

So what did that code do?

* First we imported the MaxBot class. An instance of this class will be our bot.
* Next we create an instance of this class using factory classmethod `MaxBot.inline`. This method allows us to define all the necessary resources, such as intents and dialog nodes, right in the code instead of external files.
* At each step of the conversation loop we receive a message from the user and process it with our bot.
* The method `bot.process_message` returns a list of commands. These commands are printed as a response to the user.

Save this code as `basic.py`. To run the application, use the `python basic.py` command. Type some messages and you get similar output:

```bash
$ python basic.py
🧑: Hello
🤖: Good day to you!
🧑: Good bye
🤖: OK. See you later.
🧑: |
```
