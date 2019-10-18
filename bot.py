import re
from logging import getLogger

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from config.settings import *
from utils import User, DB, save_to_db

logger = getLogger("general")
users = User()
db = DB()


@save_to_db(db)
def start(update: Update, context):
    logger.info(f"New start request from {update.message.chat.username}[{update.message.chat.id}]. Source: {update.message.text}")
    update.message.reply_text("You are gay.")


def echo(update, context):
    logger.info(f"New echo request from {update.message.chat.username}[{update.message.chat.id}]. Source: {update.message.text}")
    update.message.reply_text(update.message.text)


def auth(update, context):
    logger.info(f"New auth request from {update.message.chat.username}[{update.message.chat.id}]. Source: {update.message.text}")
    if re.match("^/start +.* *$", update.message.text) is None:

        message = ""
    else:
        message = ""
    update.message.reply_text(message)


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
