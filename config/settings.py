from logging.config import dictConfig
from os import path

_bot_root = path.dirname(path.dirname(path.abspath(__file__)))

BOT_TOKEN: str = None
PATH_TO_FILE_WITH_TOKENS: str = None  # valid format: <token> <user_name>
PATH_TO_BOT_DB: str = path.join(_bot_root, path.join("data", "bot_database.db"))
PATH_TO_CTF_DB: str = None  # set abspath to sqlite database file
LOG_PATH = path.join(_bot_root, path.join("data", "bot.log"))
REQUEST_KWARGS = None
_REQUEST_KWARGS_EXAMPLE = {
    "proxy_url": "socks5 OR socks5h://URL_OF_THE_PROXY_SERVER:PROXY_PORT",
    # Optional, if you need authentication:
    "urllib3_proxy_kwargs": {
        "username": "PROXY_USER",
        "password": "PROXY_PASS",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "base": {
            "format": "%(asctime)s %(levelname)s | %(pathname)s:%(funcName)s:%(lineno)d | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "base"
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_PATH,
            "formatter": "base",
            "maxBytes": 1024 * 1024 * 100,
        },
    },
    "loggers": {
        "general": {
            "handlers": ["file", "console"],
            "level": "INFO",
        },
    }
}

try:
    from .local_settings import *
except ImportError:
    pass

dictConfig(LOGGING)
