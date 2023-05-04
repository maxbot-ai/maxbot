import logging
import os
import sys

from sanic import Sanic
from sanic.response import empty

try:
    from telegram import Bot, Update
except ImportError:
    print(
        (
            "Extra dependencies are required to run this example. "
            "Try `pip install -U maxbot[telegram,flask]`."
        )
    )
    sys.exit(1)

from maxbot import MaxBot

if len(sys.argv) < 3:
    print("Please, provide definitions file and webhook url")
    print(f"{sys.argv[0]} <filename> <url>")
    sys.exit(1)


bot = MaxBot.from_file(sys.argv[1])

webhook_url = sys.argv[2]
# use secret to make sure that the request comes from telegram
webhook_path = "/telegram/%s" % os.urandom(16).hex()

app = Sanic(__name__)


@app.after_server_start
async def register_webhooks(app, loop):
    await bot.telegram.bot.setWebhook(webhook_url + webhook_path)


@app.post(webhook_path)
async def telegram_endpoint(request):
    update = Update.de_json(data=request.json, bot=bot.telegram.bot)
    await bot.telegram.simple_adapter(update)
    return empty()


if __name__ == "__main__":
    # our current state store does not survive app reloads
    print("Listening on localhost:8080")
    app.run(port=8080, debug=True, auto_reload=False, single_process=True, motd=False)
