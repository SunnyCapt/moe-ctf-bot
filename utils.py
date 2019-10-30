import json
import sqlite3
from ast import literal_eval
from functools import wraps
from logging import getLogger
from typing import List, Dict
from urllib.parse import urljoin

import requests

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
            result = conn.cursor().execute(sql, args)
            if need_commit:
                conn.commit()
                return None
            return result


bot_db = DB(PATH_TO_BOT_DB)
ctf_db = DB(PATH_TO_CTF_DB)


def calculate_points(user_name, total_points):
    return total_points


def permission(allowed_role: str):
    def f_inner(func):
        @wraps(func)
        def s_inner(update, context):
            logger.info(f"Check permission of {update.message.chat.username}[{update.message.chat.id}]")
            is_allow = bot_db.execute(
                "select privilege < (select privilege from role where name=?)"
                "from role where name=(SELECT role FROM user WHERE tg_id=?)",
                allowed_role,
                update.message.chat.id
            ).fetchall()
            if is_allow and is_allow[0][0]:
                update.message.reply_text("Not enough permissions or you are not authorized (use /auth or /start)")
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
        logger.info(
            f"New {func.__name__} request from {update.message.chat.username}[{update.message.chat.id}]. Source: {update.message.text}")
        return func(update, context)

    return inner


class role:
    unauthorized_user = bot_db.execute("SELECT name FROM role WHERE privilege=0").fetchall()
    authorized_user = bot_db.execute("SELECT name FROM role WHERE privilege=1").fetchall()
    admin = bot_db.execute("SELECT name FROM role WHERE privilege=1488").fetchall()

    assert unauthorized_user and authorized_user and admin, "Wrong data in bot_db.role"

    unauthorized_user = unauthorized_user[0][0]
    authorized_user = authorized_user[0][0]
    admin = admin[0][0]


class AuthException(Exception):
    pass


class BadResponse(Exception):
    pass


class Service:
    # @classmethod
    # def get_tasks(cls, task_id=None) -> List[Dict] or None:
    #     url = urljoin(MOE_URL, f"api/tasks/{task_id if task_id is not None else ''}")
    #     return cls._get_data(url)
    #
    # @classmethod
    # def get_public_hints(cls, task_id=None):
    #     url = urljoin(MOE_URL, f"hint{'s' if task_id is None else ''}")
    #     kwargs = {'data': {'id': task_id}} if task_id is not None else {}
    #     return cls._get_data(url, **kwargs)
    #
    # @staticmethod
    # def login(username, password) -> str:
    #     sess = requests.session()
    #     sess.get(urljoin(MOE_URL, 'login'), data={'username': username, 'password': password})
    #     sess.cookies

    @classmethod
    def render_tasks(cls, tasks):
        assert 'tasks' is not None, AttributeError('parameter have not tasks field')

        solved_tasks = []
        unsolved_tasks = []

        for task in tasks:
            if task.get('solved'):
                solved_tasks.append(task)
            else:
                unsolved_tasks.append(tasks)

        message = []

        message.append("<strong>Your solved tasks</strong>:\n")
        for task in solved_tasks:
            tmp = f"+ <strong>{task.get('name')}</strong> [<i>{task.get('categoryName')}</i>]\n" \
                  f"\t\t\t\t\tPoints: {task.get('points')}\n" \
                  f"\t\t\t\t\t<code>{task.get('content')}</code>\n"
            message.append(tmp)

        message.append("<strong>Unsolved tasks</strong>:\n")
        for task in solved_tasks:
            tmp = f"- <strong>{task.get('name')}</strong> [<i>{task.get('categoryName')}</i>]\n" \
                f"\t\t\t\t\tPoints: {task.get('points')}\n" \
                f"\t\t\t\t\t<code>{task.get('content')}</code>\n" + \
                f"\t\t\t\t\t/get_hint_{task.get('hint')['id']} [{task.get('hint')['price']}]\n" if task.get('hint') is not None else ""
            message.append(tmp)
            message = '\n'.join(message)
        logger.info(f"Rendered task: {repr(message)}")
        return message

    @classmethod
    def get_auth_cookie(cls, tg_id):
        auth_cookie = bot_db.execute("SELECT cookies FROM user WHERE tg_id=?", tg_id).fetchone()
        assert auth_cookie and auth_cookie[0], AuthException()
        return literal_eval(auth_cookie[0])

    @classmethod
    def render_stats(cls, user):
        message = f"<strong>Name</strong>: {user.get('name')}\n" \
                  f"<strong>Points</strong>: {user.get('points')}\n" \
                  f"<strong>Wallet</strong>: {user.get('wallet')}\n"
        return message


class MoeAPI:
    @classmethod
    def _get_data(cls, url, **kwargs):
        response = requests.post(url, **kwargs)
        if not response.ok:
            raise BadResponse()
        if '/api/' in url and response.headers.get('Content-Type') != 'application/json; charset=utf-8':
            raise AuthException()
        return response.json()

    @classmethod
    def _check_auth(cls, cookies: Dict[str, str]):
        logger.info(f"Checking auth for cookies: {cookies}")
        url = urljoin(MOE_URL, 'api/tasks')
        try:
            cls._get_data(url, cookies=cookies)
        except AuthException:
            return False
        return True

    # @classmethod
    # def get_init_cookies(cls):
    #     logger.info(f"Getting connect.sid cookie")
    #     sess = requests.session()
    #     sess.get(MOE_URL)
    #     return str(sess.cookies.get_dict())

    @classmethod
    def get_auth_cookies(cls, username, password) -> (int, str):
        data = {
            "username": username,
            "password": password
        }
        url = urljoin(MOE_URL, 'login')
        response = requests.post(url, data=data)
        auth_cookies = response.cookies.get_dict()
        if cls._check_auth(auth_cookies) is None:
            return None, None
        moe_user_id = cls.get_moe_user_id(username, auth_cookies)
        return moe_user_id, auth_cookies

    @classmethod
    def get_moe_user(cls, username: str, cookies: Dict[str, str]) -> dict or None:
        """
        Getting user data by username
        :exception: AuthException if auth cookies is wrong
        """
        url = urljoin(MOE_URL, 'api/users')
        response = cls._get_data(url, cookies=cookies)
        user = list(filter(lambda u: u.get('name') == username, response['users']))
        if not user:
            raise BadResponse(f'User {username} not found')
        return user[0]

    @classmethod
    def get_tasks(cls, auth_cookie, task_id=None):
        """
        Getting tasks by user auth
        :exception: AuthException if auth cookies is exexpired
        :return:
        """
        url = urljoin(MOE_URL, f'api/tasks{("/" + str(task_id)) if task_id is not None else ""}')
        return cls._get_data(url, cookies=auth_cookie).get('tasks')


