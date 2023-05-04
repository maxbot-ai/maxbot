import logging
import sys

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

try:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, MessageHandler, filters
except ImportError:
    print(
        "Extra dependencies are required to run this example. Try `pip install -U maxbot[telegram]`."
    )
    sys.exit(1)

from maxbot import MaxBot

if len(sys.argv) < 2:
    print("Please, provide definitions file")
    print(f"{sys.argv[0]} <filename>")
    sys.exit(1)

bot = MaxBot.from_file(sys.argv[1])


async def callback(update, context):
    await bot.telegram.simple_adapter(update)


app = ApplicationBuilder().token(bot.telegram.config["api_token"]).build()
app.add_handler(MessageHandler(filters.ALL, callback))
app.run_polling()
