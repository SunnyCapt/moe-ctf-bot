import sqlite3
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
                try:
                    key, value = line.rstrip("\n").rstrip("\r").split(" ")
                    self._users.update({key, value})
                except Exception as exc:
                    logger.error(f"Wrong token-user_name value in {self._file_path}: {line} [{exc}]")
        logger.info("Updated tokens")

    def get_user_name(self, token):
        user_name = self._users.get(token)
        if user_name is not None:
            return user_name
        self.update()
        user_name = self._users.get(token)
        return user_name


class DB:
    SELECT_TABLES_SQL = "select * from sqlite_master where type = 'table'"
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if PATH_TO_BOT_DB not in cls._instances:
            cls._instances.update({PATH_TO_BOT_DB: super(DB, cls).__new__(cls, *args, **kwargs)})
        return cls._instances.get(PATH_TO_BOT_DB)

    def __init__(self, db_path=PATH_TO_BOT_DB):
        self._conn = sqlite3.connect(db_path)
        self._cursor = self._conn.cursor()

    def execute(self, *args, **kwargs):
        return self._cursor.execute(*args, **kwargs)

    def commit(self):
        self._conn.commit()


def save_to_db(func, db):
    @wraps(func)
    def inner(*args, **kwargs):
        db.execute(f"")
        db.commit()
    return inner

