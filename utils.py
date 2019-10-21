import json
import sqlite3
from ast import literal_eval
from functools import wraps
from logging import getLogger

from config.settings import *

logger = getLogger("general")


class User:
    def __init__(self, file_path=PATH_TO_FILE_WITH_TOKENS):
        self._file_path = file_path
        self._users = {}

    def update(self):
        logger.info("Updating tokens")
        with open(self._file_path) as data:
            for line in data.readlines():
                line = line.strip("\n").strip("\r").strip()
                if not line:
                    continue
                try:
                    key, value = line.split(" ")
                    self._users.update({key: value})
                except Exception as exc:
                    logger.error(f"Wrong token-user_name value in {self._file_path}: {line} [{exc}]")
        logger.info("Updated tokens")

    def get_user_name(self, token) -> "user_name or None":
        user_name = self._users.get(token)
        if user_name is not None:
            return user_name
        self.update()
        user_name = self._users.get(token)
        return user_name


class DB:
    def __init__(self, db_path=PATH_TO_BOT_DB):
        self.db_path = db_path

    def execute(self, sql, *args, need_commit=False):
        logger.info(f"sql query[need_commit={need_commit}]: {sql} with args: {args}")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            result = cursor.execute(sql, args)
            if need_commit:
                conn.commit()
                return None
            return result


bot_db = DB(PATH_TO_BOT_DB)
ctf_db = DB(PATH_TO_CTF_DB)


def calculate_points(user_name, total_points):
    return total_points


def permission(*allowed_roles: ["role field"]):
    def f_inner(func):
        @wraps(func)
        def s_inner(update, context):
            logger.info(f"Check permission of {update.message.chat.username}[{update.message.chat.id}]")
            if not bot_db.execute(
                    "SELECT 1 FROM user WHERE tg_id=? and role in (?)",
                    update.message.chat.id, ",".join(v for v in allowed_roles)
            ).fetchall():
                update.message.reply_text("Not enough permissions or you are not authorized (use /auth)")
                return None
            return func(update, context)
        return s_inner
    return f_inner


def save_and_log(func):
    @wraps(func)
    def inner(update, context):
        bot_db.execute(
            "INSERT INTO messages (src, tg_user_name, tg_id, date, text) "
            "VALUES (?, ?, ?, ?, ?);",
            json.dumps(literal_eval(str(update.message))),
            update.message.chat.username,
            update.message.chat.id,
            update.message.date,
            update.message.text,
            need_commit=True
        )
        logger.info(f"New {func.__name__} request from {update.message.chat.username}[{update.message.chat.id}]. Source: {update.message.text}")
        return func(update, context)
    return inner


class role:
    admin = "admin"
    user = "user"
