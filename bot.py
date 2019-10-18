from logging import getLogger

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from config.settings import *
from utils import User, DB

logger = getLogger("general")
users = User()
db = DB()


def start(update: Update, context):
    logger.info(f"New request. Command start, source: {update.message.text}")
    update.message.reply_text("You are gay.")


def echo(update, context):
    update.message.reply_text(update.message.text)


def auth(update, context):
    pass


def error(update, context):
    """Log Errors caused by Updates."""
    logger.error('Update "%s" caused error "%s"', update, context.error)


try:
    assert BOT_TOKEN, "Not found bot token"
    assert PATH_TO_FILE_WITH_TOKENS, "Not found path to file with user's tokens"
except AssertionError as e:
    logger.error(f"Wrong config: {e}")


def run_bot():
    logger.info("Start polling bot")
    updater = Updater(BOT_TOKEN, use_context=True, request_kwargs={'proxy_url': "socks5://127.0.0.1:9050"})  # **({"request_kwargs": REQUEST_KWARGS} if REQUEST_KWARGS is not None else {}))
    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, echo))
    updater.dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    run_bot()
