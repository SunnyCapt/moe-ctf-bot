import re
from ast import literal_eval
from logging import getLogger

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.parsemode import ParseMode

from config.settings import *
from utils import User, save_and_log, permission, role, calculate_points, bot_db, ctf_db, Service, MoeAPI, \
    AuthException, BadResponse

logger = getLogger("general")
users = User()


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
    moe_user_id, auth_cookies = MoeAPI.get_auth_cookies(username, password)

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
    try:
        auth_cookie = Service.get_auth_cookie(update.message.chat.id)
        tasks = MoeAPI.get_tasks(auth_cookie)
    except AuthException:
        # TODO: delete expired cookies
        update.message.reply_text(f'You should login again')
        return
    result = Service.render_tasks(tasks)
    update.message.reply_text(result, parse_mode=ParseMode.HTML)

    # solved_task_ids = ctf_db.execute(
    #     "SELECT task_id FROM stask "
    #     "WHERE user_id=(SELECT user_id FROM user WHERE user_name=? limit 1)",
    #     user_name[0]
    # )
    # solved_task_ids = ",".join(str(row[0]) for row in solved_task_ids)
    # solved_task_ids = solved_task_ids if solved_task_ids else "-1"
    # processed_tasks = []
    #
    # solved_tasks = ctf_db.execute(
    #     "SELECT task_name, task_content, task_points "
    #     "FROM task WHERE task_id in (?)",
    #     solved_task_ids
    # )
    # unresolved_task = ctf_db.execute(
    #     "SELECT task_name, task_content, task_points, task_id "
    #     "FROM task WHERE task_id not in (?)",
    #     solved_task_ids
    # )
    #
    # total_user_point = 0
    #
    # processed_tasks.append("<strong>Your solved tasks</strong>:\n")
    # for task in solved_tasks:
    #     tmp = f"+ <i>{task[0]} - {task[2]}</i>\n" \
    #         f"\t\t\t\t\t<code>{task[1]}</code>\n"
    #     total_user_point += task[2]
    #     processed_tasks.append(tmp)
    # processed_tasks.append("<strong>Unresolved tasks</strong>:\n")
    # for task in unresolved_task:
    #     tmp = f"- <i>{task[0]}</i> - {task[2]}\n" \
    #         f"\t\t\t\t\t<code>{task[1]}</code>\n" \
    #         f"\t\t\t\t\t/get_hint_{task[3]}\n"
    #     processed_tasks.append(tmp)
    # processed_tasks.append(f"You have {calculate_points(user_name, total_user_point)} points")
    # update.message.reply_text("\n".join(processed_tasks), parse_mode=ParseMode.HTML)


@save_and_log
@permission(role.authorized_user)
def get_stats(update, context):
    username = bot_db.execute("SELECT user_name FROM main.user WHERE tg_id=?", update.message.chat.id).fetchone()
    if not (username and username[0]):
        # TODO: delete cookies and username
        update.message.reply_text(f'You should login')
        return

    username = username[0]
    user = None

    try:
        auth_cookie = Service.get_auth_cookie(update.message.chat.id)
        user = MoeAPI.get_moe_user(username, auth_cookie)
    except (AuthException, BadResponse) as e:
        # TODO: delete expired cookies
        logger.info(f"Get stats exception: {e}")
        update.message.reply_text(f'You should login again')
        return

    result = Service.render_stats(user)
    update.message.reply_text(result, parse_mode=ParseMode.HTML)


@permission(role.authorized_user)
def get_hint(update, context):
    # TODO: replay keyboard with info about hint and buttons yes/no
    pass
    # task_id = int(update.message.text.split('_')[-1])
    #
    # task = Service.get_tasks(task_id)
    # if not task:
    #     update.message.reply_text(f"We don't have task with id={task_id}")
    #     return None
    #
    # hints = Service.get_public_hints(task_id)
    # if not hints:
    #     update.message.reply_text("We don't have hint for this task :c")
    #     return None
    #
    # update.message.reply_text(
    #     f"<strong>Hint for {task[0].get('task_name', 'noname task')}</strong>:\n<code>{hint_text}</code>",
    #     parse_mode=ParseMode.HTML
    # )


@permission(role.authorized_user)
def pay_for_hint(update, context):
    pass


@save_and_log
def command(update, context):
    if re.match('^/get_hint_[1-9]+[0-9]* *$', update.message.text) is not None:
        get_hint(update, context)
        return None
    update.message.reply_text(f"{update.message.text} command not found")


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
    updater.dispatcher.add_handler(CommandHandler("get_stats", get_stats))
    updater.dispatcher.add_handler(MessageHandler(Filters.command, command))
    updater.dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    run_bot()
