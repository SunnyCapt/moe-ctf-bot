from logging import getLogger

from telegram.ext import Updater, CommandHandler
from telegram.ext.dispatcher import run_async

from config.settings import *
from utils import User, DB

logger = getLogger("general")
users = User()
db = DB()


@run_async
def start(bot, update):
    logger.info(f"New request. Command start, source: {update.message.message}")
    bot.sendMessage(
        chat_id=update.message.chat_id,
        text="You are gay.",
        parse_mode="MARKDOWN"
    )


@run_async
def auth(bot, update):
    pass


try:
    assert BOT_TOKEN, "Not found bot token"
    assert PATH_TO_FILE_WITH_TOKENS, "Not found path to file with user's tokens"
except AssertionError as e:
    logger.error(f"Wrong config: {e}")


def run_bot():
    global updater
    logger.info("Start polling bot")
    updater = Updater(BOT_TOKEN, **({"request_kwargs": REQUEST_KWARGS} if REQUEST_KWARGS is not None else {}))
    start_handler = CommandHandler("start", start)
    updater.dispatcher.add_handler(start_handler)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    run_bot()
