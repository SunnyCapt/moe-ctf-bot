import json
import sqlite3
from functools import wraps
from logging import getLogger, Logger
from ast import literal_eval
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

    def execute(self, sql, need_commit=False):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            result = cursor.execute(sql)
            if need_commit:
                conn.commit()
                return None
            return result


def save_and_log(db: DB, logger: Logger):
    def f_inner(func):
        @wraps(func)
        def s_inner(update, context):
            db.execute(
                f"INSERT INTO messages (src, tg_user_name, tg_id, date, text) "
                f"VALUES ("
                    f"'{json.dumps(literal_eval(str(update.message)))}', "
                    f"'{update.message.chat.username}', "
                    f"{update.message.chat.id}, "
                    f"'{update.message.date}', "
                    f"'{update.message.text}'"
                f");",
                need_commit=True
            )
            logger.info(f"New {func.__name__} request from {update.message.chat.username}[{update.message.chat.id}]. Source: {update.message.text}")
            return func(update, context)
        return s_inner
    return f_inner


