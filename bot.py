import re
from logging import getLogger

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from config.settings import *
from utils import User, DB, save_and_log

logger = getLogger("general")
users = User()
db = DB()


@save_and_log(db, logger)
def start(update: Update, context):
    update.message.reply_text("You are gay.")


@save_and_log(db, logger)
def echo(update, context):
    update.message.reply_text(update.message.text)


@save_and_log(db, logger)
def auth(update, context):
    message = None
    if re.match("^/auth +.* *$", update.message.text) is None:
        message = "Сorrect format: /auth <token>"
    else:
        token = update.message.text.split(" ")[1].strip()
        user_name = users.get_user_name(token)
        if user_name is None:
            message = "Token not found"
        else:
            data_set = list(db.execute(f"select * from user where user_name='{user_name}'"))
            if not data_set:
                db.execute(
                    f"INSERT INTO user (user_name, tg_user_name, tg_id) "
                    f"VALUES ("
                        f"'{user_name}',"
                        f"'{update.message.chat.username}', "
                        f"{update.message.chat.id}"
                    f");",
                    need_commit=True
                )
            elif data_set[1] != update.message.chat.id:
                    message = "You can only use one telegram account"
        message = "Succed" if message is None else message
    update.message.reply_text(message)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.error(f"Message: {context.error}. Update: {update}")


try:
    assert BOT_TOKEN, "Not found bot token"
    assert PATH_TO_FILE_WITH_TOKENS, "Not found path to file with user's tokens"
except AssertionError as e:
    logger.error(f"Wrong config: {e}")


def run_bot():
    logger.info("Start polling bot")
    updater = Updater(BOT_TOKEN, use_context=True, **({"request_kwargs": REQUEST_KWARGS} if REQUEST_KWARGS is not None else {}))
    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("auth", auth))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, echo))
    updater.dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    run_bot()
