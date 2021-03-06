import json
import sqlite3
from ast import literal_eval
from functools import wraps
from logging import getLogger
from typing import Dict
from urllib.parse import urljoin

import requests

from config.settings import *

logger = getLogger("general")


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
            ).fetchone()

            if allowed_role == role.unauthorized_user and is_allow is None:
                is_allow = (0,)

            if is_allow is None or is_allow and is_allow[0]:
                update.message.reply_text("Not enough permissions or you are not authorized (use /auth)")
                return None
            return func(update, context)

        return s_inner

    return f_inner


def log(func):
    @wraps(func)
    def inner(update, context):
        logger.info(
            f"New {func.__name__} request from "
            f"{update.message.chat.username if hasattr(update.message.chat, 'username') else ''}[{update.message.chat.id}]. "
            f"Source: {update.message.text}"
        )
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
    @classmethod
    def render_tasks(cls, tasks) -> list:
        assert "tasks" is not None, AttributeError("parameter have not tasks field")

        solved_tasks = []
        unsolved_tasks = []

        for task in tasks:
            if task.get("solved"):
                solved_tasks.append(task)
            else:
                unsolved_tasks.append(task)

        message = []

        message.append("<strong>Your solved tasks</strong>:\n")
        for task in solved_tasks:
            tmp = f"+ <strong>{task.get('name')}</strong> [<i>{task.get('categoryName')}</i>]\n" \
                f"\t\t\t\t\tPoints: {task.get('points')}\n" \
                f"\t\t\t\t\t<code>{task.get('content')}</code>\n"
            message.append(tmp)

        message.append("<strong>Unsolved tasks</strong>:\n")
        for task in unsolved_tasks:
            tmp = f"- <strong>{task.get('name')}</strong> [<i>{task.get('categoryName')}</i>]\n" \
                f"\t\t\t\t\tPoints: {task.get('points')}\n" \
                f"\t\t\t\t\t<code>{task.get('content')}</code>\n"
            tmp += f"\t\t\t\t\t/get_hint_{task.get('id')} [{task.get('hint')['price']} coins]\n" if task.get(
                "hint") is not None else ""
            message.append(tmp)
        # message = "\n".join(message)
        logger.info(f"Rendered task: {repr(message)}")
        return message

    @classmethod
    def get_auth_cookie(cls, tg_id):
        logger.info(f"Getting auth cookie of {tg_id} tg_user")
        auth_cookie = bot_db.execute("SELECT cookies FROM user WHERE tg_id=?", tg_id).fetchone()
        if not (auth_cookie and auth_cookie[0]):
            raise AuthException("Auth is not valid")
        return literal_eval(auth_cookie[0])

    @classmethod
    def render_stats(cls, user):
        if user is None:
            return "We dont have info about it"
        return f"<strong>Name</strong>: {user.get('name')}\n" \
            f"<strong>Points</strong>: {user.get('points')}\n" \
            f"<strong>Wallet</strong>: {user.get('wallet')}\n"

    @classmethod
    def render_hint(cls, task):
        hint = task.get("hint")
        if hint is None:
            return "We dont have info about it"
        return f"<strong>Hint for</strong>: {task.get('task_name', 'noname task')}\n" \
            f"<strong>Price is</strong>: {hint.get('price')} coins\n" \
            f"\nTo pay and get a hint, use the command:\n" \
            f"/buy_hint_{hint.get('id')}"

    @classmethod
    def render_hint_content(cls, hint):
        return f"<strong>Status</strong>: {hint.get('status')} coins\n" \
            f"<strong>Hint</strong>: <code>{hint.get('hint')}</code>\n" \
            f"\nFor check all your hints use command:\n/check_my_hints"

    @classmethod
    def render_users(cls, users):
        message = []
        for user in users:
            message.append(cls.render_stats(user))
        return "\n".join(message)

    @classmethod
    def render_hints_content(cls, hints):
        message = []
        for hint in hints:
            message.append(
                f"* <strong>{hint.get('taskName')}</strong> [<i>{hint.get('categoryName')}</i>]\n"
                f"\t\t\t\t\t<code>{hint.get('taskContent')}</code>\n"
                f"\t\t\t\t\tHint: <i>{hint.get('hint')}</i>"
            )
        return "".join(message) if message else "You have not hints"

    @classmethod
    def render_help(cls):
        return "\n/auth &lt;username&gt; &lt;password&gt; - <code>авторизация</code>\n" \
              "/get_stats - <code>информация о текущем юзере</code>\n" \
              "/get_teams - <code>информация о всех командах</code>\n" \
              "/get_tasks - <code>получение списка тасков</code>\n" \
              "/get_hint_&lt;id&gt; - <code>получение информации о подсказке с указанным id</code>\n" \
              "/get_hints - <code>получить все купленные подсказки</code>\n" \
              "/buy_hint_&lt;id&gt; - <code>покупка подсказки с указанным id</code>"


class MoeAPI:
    @classmethod
    def _get_data(cls, url, **kwargs):
        logger.info(f"Getting data. URL: {url}; kwargs: {kwargs}")
        response = requests.post(url, **kwargs)
        if not response.ok:
            raise BadResponse()
        if "/api/" in url and response.headers.get("Content-Type") != "application/json; charset=utf-8":
            raise AuthException("auth is not valid")
        return response.json()

    @classmethod
    def _is_valid_auth(cls, cookies: Dict[str, str]):
        logger.info(f"Checking auth for cookies: {cookies}")
        url = urljoin(MOE_URL, "api/tasks")
        try:
            cls._get_data(url, cookies=cookies)
        except AuthException:
            return False
        return True

    @classmethod
    def get_auth_cookies(cls, username, password) -> dict:
        logger.info(f"Getting[creating] auth cookies for {username} with hash(pass) {hash(password)}")
        data = {
            "username": username,
            "password": password
        }
        url = urljoin(MOE_URL, "login")
        response = requests.post(url, data=data)
        auth_cookies = response.cookies.get_dict()
        if not cls._is_valid_auth(auth_cookies):
            return None
        return auth_cookies

    @classmethod
    def get_moe_user(cls, cookies: Dict[str, str], username: str = None) -> dict:
        """
        Getting users
        :exception: AuthException if auth cookies is wrong
        """
        logger.info(f"Getting user(s); username={username}")
        url = urljoin(MOE_URL, "api/users")
        response = cls._get_data(url, cookies=cookies)

        if username is None:
            return response["users"]

        user = list(filter(lambda u: u.get("name") == username, response["users"]))
        if not user:
            raise BadResponse(f"User {username} not found")
        return user[0]

    @classmethod
    def get_tasks(cls, auth_cookie, task_id=None) -> list or dict:
        """
        Getting tasks by user auth
        :exception: AuthException if auth cookies is exexpired
        :return:
        """
        logger.info(f"Getting task(s); task_id={task_id}")
        url = urljoin(MOE_URL, f"api/tasks{('/' + str(task_id)) if task_id is not None else ''}")
        data = cls._get_data(url, cookies=auth_cookie)
        if "tasks" in data:
            return data.get("tasks")
        elif "task" in data:
            return data.get("task")
        raise BadResponse()

    @classmethod
    def get_hints(cls, auth_cookie, hint_id=None) -> list or dict:
        logger.info(f"Getting hint(s); hint_id={hint_id}")
        url = urljoin(MOE_URL, f"api/{'wallet' if hint_id is None else ('pay/' + str(hint_id))}")
        data = cls._get_data(url, cookies=auth_cookie)
        return data.get("hints", []) if hint_id is None else data
