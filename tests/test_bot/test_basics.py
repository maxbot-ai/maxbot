from maxbot.bot import MaxBot


def test_bot():
    bot = MaxBot()
    assert [] == bot.process_message("hey bot")


def test_builder():
    bot = MaxBot.builder().build()
    assert isinstance(bot, MaxBot)


def test_inline():
    bot = MaxBot.inline(
        """
        dialog:
          - condition: message.text == "hey bot"
            response: hello world
    """
    )
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "hello world"}]


def test_from_file(tmp_path):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(
        """
        dialog:
          - condition: message.text == "hey bot"
            response: hello world
    """
    )
    bot = MaxBot.from_file(botfile)
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "hello world"}]


def test_from_directory(tmp_path):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(
        """
        dialog:
          - condition: message.text == "hey bot"
            response: hello world
    """
    )
    bot = MaxBot.from_directory(botfile.parent)
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "hello world"}]


def test_process_rpc():
    bot = MaxBot.inline(
        """
        rpc:
          - method: say_hello
        dialog:
          - condition: rpc.say_hello
            response: hello world
    """
    )
    commands = bot.process_rpc({"method": "say_hello"})
    assert commands == [{"text": "hello world"}]
