import re
from logging import getLogger

from telegram import Update
from telegram.parsemode import ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from config.settings import *
from utils import User, save_and_log, permission, role, calculate_points, bot_db, ctf_db

logger = getLogger("general")
users = User()


@save_and_log
def start(update: Update, context):
    update.message.reply_text("You are gay.")


@save_and_log
@permission(role.user, role.admin)
def echo(update, context):
    update.message.reply_text(update.message.text)


@save_and_log
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
            data_set = list(bot_db.execute("select * from user where user_name=?", user_name))
            if not data_set:
                bot_db.execute(
                    "INSERT INTO user (user_name, tg_user_name, tg_id) "
                    "VALUES (?, ?, ?);",
                    user_name,
                    update.message.chat.username,
                    update.message.chat.id,
                    need_commit=True
                )
            elif data_set[1] != update.message.chat.id:
                message = "You can only use one telegram account"
        message = "Succed" if message is None else message
    update.message.reply_text(message)


@save_and_log
@permission(role.user, role.admin)
def get_tasks(update, context):
    user_name = bot_db.execute("SELECT user_name FROM user WHERE tg_id=?", update.message.chat.id).fetchone()
    solved_task_ids = ctf_db.execute(
        "SELECT task_id FROM stask "
        "WHERE user_id=(SELECT user_id FROM user WHERE user_name=? limit 1)",
        user_name[0]
    )
    solved_task_ids = ",".join(str(row[0]) for row in solved_task_ids)
    solved_task_ids = solved_task_ids if solved_task_ids else "-1"
    processed_tasks = []

    solved_tasks = ctf_db.execute(
        "SELECT task_name, task_content, task_points "
        "FROM task WHERE task_id in (?)",
        solved_task_ids
    )
    unresolved_task = ctf_db.execute(
        "SELECT task_name, task_content, task_points, task_id "
        "FROM task WHERE task_id not in (?)",
        solved_task_ids
    )

    total_user_point = 0

    processed_tasks.append("<strong>Your solved tasks</strong>:\n")
    for task in solved_tasks:
        tmp = f"+ <i>{task[0]}__ - {task[2]}</i>\n" \
              f"\t\t\t\t\t<code>{task[1]}</code>\n"
        total_user_point += task[2]
        processed_tasks.append(tmp)
    processed_tasks.append("<strong>Unresolved tasks</strong>:\n")
    for task in unresolved_task:
        tmp = f"- <i>{task[0]}</i> - {task[2]}\n" \
              f"\t\t\t\t\t<code>{task[1]}</code>\n" \
              f"\t\t\t\t\t/get_hint_{task[3]}\n"
        processed_tasks.append(tmp)
    processed_tasks.append(f"You have {calculate_points(user_name, total_user_point)} points")
    update.message.reply_text("\n".join(processed_tasks), parse_mode=ParseMode.HTML)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.error(context.error)


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
    updater.dispatcher.add_handler(CommandHandler("get_tasks", get_tasks))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, echo))
    updater.dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    run_bot()
