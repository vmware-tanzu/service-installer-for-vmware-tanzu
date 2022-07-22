#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import logging
import os

levels = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

logging.basicConfig(
    level=levels[os.environ.get("LOG_LEVEL", "DEBUG").lower()],
    format="%(asctime)s [%(module)s:%(funcName)s:%(lineno)-3s] [%(levelname)-5.5s]  %(message)s",
    datefmt="%Y-%m-%d %I:%M:%S %p",
)
logger = logging.getLogger(__name__)
fh = logging.FileHandler(os.environ.get("LOG_PATH", "tkg.log"))
logger.addHandler(fh)
logger.setLevel(levels[os.environ.get("LOG_LEVEL", "DEBUG").lower()])

NO_COLOR = "\33[m"
RED, GREEN, ORANGE, BLUE, PURPLE, LBLUE, GREY = map("\33[%dm".__mod__, range(31, 38))


def log(msg=None):
    def decorator(func):
        def inner(*args, **kwargs):
            if msg:
                logger.info(msg)
            result = func(*args, **kwargs)
            if result:
                logger.debug("Result : %s", result)
            logger.debug("=" * 80)
            return result

        return inner

    return decorator

def log_debug(func):
    def inner(*args, **kwargs):
        logger.debug(f"__init__ func: {func.__name__}")
        result = func(*args, **kwargs)
        if result:
            logger.debug(f"__return__ func: {func.__name__} - response: {result}")
        return result

    return inner


def add_color(logger_method, color):
    def wrapper(message, *args, **kwargs):
        return logger_method(
            # the coloring is applied here.
            color + message + NO_COLOR,
            *args,
            **kwargs
        )

    return wrapper


for level, color in zip(("info", "warn", "error", "debug"), (GREEN, ORANGE, RED, LBLUE)):
    setattr(logger, level, add_color(getattr(logger, level), color))

class LoggerHelper:
    @staticmethod
    def get_logger(
        name, colored_logger=False, loglevel=levels[os.environ.get("LOG_LEVEL", "DEBUG").lower()], output_shell=False
    ):
        log_formatter = logging.Formatter(
            "%(asctime)s [%(module)s:%(funcName)s:%(lineno)-3s] [%(levelname)-5.5s]  %(message)s")
        logger = logging.getLogger(name)
        logger.setLevel(loglevel)

        # Adding file handler for logger. To append logs to file
        fh = logging.FileHandler(os.environ.get("LOG_PATH", "tkg.log"))
        fh.setFormatter(log_formatter)
        logger.addHandler(fh)

        # Add shell logger
        if output_shell:
            ch = logging.StreamHandler()
            ch.setFormatter(log_formatter)
            logger.addHandler(ch)

        # coloured logs
        if colored_logger:
            for level, color in zip(("info", "warn", "error", "debug"), (GREEN, ORANGE, RED, LBLUE)):
                setattr(logger, level, add_color(getattr(logger, level), color))
        return logger
