import re
import sys
from logging import getLogger

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.parsemode import ParseMode

from config.settings import *
from utils import save_and_log, permission, role,  bot_db, Service, MoeAPI, AuthException, BadResponse

logger = getLogger("general")


@save_and_log
def start(update, context):
    update.message.reply_text("You are gay.")
    if bot_db.execute("SELECT 1 FROM user WHERE tg_id=?", update.message.chat.id).fetchall():
        return

    bot_db.execute(
        "INSERT INTO user (tg_user_name, tg_id, role) "
        "VALUES (?, ?, (SELECT name FROM role WHERE privilege=0));",
        update.message.chat.username,
        update.message.chat.id,
        need_commit=True
    )


@save_and_log
@permission(role.unauthorized_user)
def auth(update, context):
    if re.match("^/auth +[^ ]* +[^ ]*$", update.message.text) is None:
        update.message.reply_text("Сorrect format: /auth <username> <password>")
        return None

    _, username, password = list(filter(lambda param: param, update.message.text.split(" ")))
    auth_cookies = MoeAPI.get_auth_cookies(username, password)

    if auth_cookies is None:
        update.message.reply_text("Wrong username/password")
        return None

    bot_db.execute(
        "UPDATE user SET user_name=?, role=?, cookies=? WHERE tg_id=?",
        username,
        role.authorized_user,
        str(auth_cookies),
        update.message.chat.id,
        need_commit=True
    )

    update.message.reply_text("Succed")


@save_and_log
@permission(role.authorized_user)
def get_tasks(update, context):
    tasks = None

    try:
        auth_cookie = Service.get_auth_cookie(update.message.chat.id)
        tasks = MoeAPI.get_tasks(auth_cookie)
    except AuthException as e:
        # TODO: delete expired cookies
        logger.exception(f"Get tasks auth exception: {e}")
        update.message.reply_text("You should login again")
        return
    except BadResponse as e:
        logger.exception(f"Get tasks bad response exception: {e}")
        update.message.reply_text("Something broke")
        return
    result = Service.render_tasks(tasks)
    update.message.reply_text(result, parse_mode=ParseMode.HTML)


@save_and_log
@permission(role.authorized_user)
def get_stats(update, context):
    username = bot_db.execute("SELECT user_name FROM main.user WHERE tg_id=?", update.message.chat.id).fetchone()
    if not (username and username[0]):
        # TODO: delete cookies and username
        update.message.reply_text("You should login")
        return

    username = username[0]
    user = None

    try:
        auth_cookie = Service.get_auth_cookie(update.message.chat.id)
        user = MoeAPI.get_moe_user(username, auth_cookie)
    except AuthException as e:
        # TODO: delete expired cookies
        logger.exception(f"Get stats auth exception: {e}")
        update.message.reply_text("You should login again")
        return
    except BadResponse as e:
        logger.exception(f"Get stats bad response exception: {e}")
        update.message.reply_text("Something broke")
        return

    result = Service.render_stats(user)
    update.message.reply_text(result, parse_mode=ParseMode.HTML)


@permission(role.authorized_user)
def get_hint(update, context):
    task_id = int(update.message.text.split("_")[-1])
    task = None

    try:
        auth_cookie = Service.get_auth_cookie(update.message.chat.id)
        task = MoeAPI.get_tasks(auth_cookie, task_id)
    except AuthException as e:
        # TODO: delete expired cookies
        logger.exception(f"Get hint auth exception: {e}")
        update.message.reply_text("You should login again")
        return
    except BadResponse as e:
        logger.exception(f"Get hint bad response exception: {e}")
        update.message.reply_text("Something broke")
        return

    result = Service.render_hint(task)
    update.message.reply_text(result, parse_mode=ParseMode.HTML)


@permission(role.authorized_user)
def buy_hint(update, context):
    hint_id = int(update.message.text.split("_")[-1])
    hint = None

    try:
        auth_cookie = Service.get_auth_cookie(update.message.chat.id)
        hint = MoeAPI.get_hints(auth_cookie, hint_id)
    except AuthException as e:
        # TODO: delete expired cookies
        logger.exception(f"Get hint auth exception: {e}")
        update.message.reply_text("You should login again")
        return
    except BadResponse as e:
        logger.exception(f"Get hint bad response exception: {e}")
        update.message.reply_text("Something broke")
        return

    result = Service.render_hint_content(hint)
    update.message.reply_text(result, parse_mode=ParseMode.HTML)


@save_and_log
def command(update, context):
    if re.match("^/get_hint_[1-9]+[0-9]* *$", update.message.text) is not None:
        get_hint(update, context)
        return None
    if re.match("^/buy_hint_[1-9]+[0-9]* *$", update.message.text) is not None:
        buy_hint(update, context)
        return None
    update.message.reply_text(f"{update.message.text} command not found")


def error(update, context):
    """Log Errors caused by Updates."""
    logger.error(context.error)


try:
    BOT_TOKEN = BOT_TOKEN or sys.argv[1]
    assert BOT_TOKEN is not None
except:
    logger.error(f"Wrong token config")
    exit(-1)


def run_bot():
    logger.info("Start polling bot")
    updater = Updater(BOT_TOKEN, use_context=True, **({"request_kwargs": REQUEST_KWARGS} if REQUEST_KWARGS is not None else {}))
    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("auth", auth))
    updater.dispatcher.add_handler(CommandHandler("get_tasks", get_tasks))
    updater.dispatcher.add_handler(CommandHandler("get_stats", get_stats))
    updater.dispatcher.add_handler(MessageHandler(Filters.command, command))
    updater.dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    run_bot()
