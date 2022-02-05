__all__ = [
    "RxTxSubject",
    "delete_directory",
    "random_uuid",
    "stdout_logger",
    "Logger",
    "Singleton",
]

import logging
import os
import shutil
import sys
import uuid
from itertools import cycle

from rx.subject import Subject

##############################################################################
## Rx
##############################################################################


class RxTxSubject(Subject):
    def __init__(self):
        super().__init__()
        self._tx = Subject()
        self._rx = Subject()

    def on_next(self, value):
        return self._tx.on_next(value)

    def subscribe(self, *args, **kwargs):
        return self._rx.subscribe(*args, **kwargs)

    def dispose(self):
        self._tx.dispose()
        self._rx.dispose()
        super().dispose()


##############################################################################
## Files and Folders
##############################################################################


def delete_directory(directory):
    if os.path.isdir(directory):
        shutil.rmtree(directory)


_uuid_cycle = cycle(map(lambda x: str(x), range(100)))


def random_uuid():
    """Generate a unique string

    Usage:

        ```python
        some_book = s['books'][s.random_uuid()]
        ```

    Returns:
        randomly generated string
    """
    return uuid.uuid4().hex + next(_uuid_cycle)


##############################################################################
## Logging
##############################################################################


def stdout_logger(name, level=logging.DEBUG):
    log = logging.getLogger(name)
    log.propagate = False
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(levelname)-8s %(message)s")
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    log.handlers = [stream_handler]
    log.setLevel(level)
    return log


class Logger(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return (
            "[{}] {}".format(
                " ".join(
                    ["{}={}".format(k, v) for k, v in {**kwargs, **self.extra}.items()]
                ),
                msg,
            ),
            kwargs,
        )


####################################################################################
## Meta Programming
####################################################################################


class _Singleton(type):
    """A metaclass that creates a Singleton base class when called."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Singleton(_Singleton("SingletonMeta", (object,), {})):
    pass
