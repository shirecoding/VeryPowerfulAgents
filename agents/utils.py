import json
import logging
import os
import shutil
import sys
import uuid
from itertools import cycle

##############################################################################
## Message
##############################################################################


class Message:

    # Message Interface

    NOTIFICATION = 0
    CLIENT = 1

    @classmethod
    def notification(cls, topic="", payload=""):
        return [
            topic.encode(),
            bytes([cls.NOTIFICATION]),
            json.dumps({"topic": topic, "payload": payload}).encode(),
        ]

    @classmethod
    def client(cls, name="", payload=""):
        return [
            name.encode(),
            bytes([cls.CLIENT]),
            json.dumps({"payload": payload}).encode(),
        ]

    # Helper Methods

    @classmethod
    def decode(cls, multipart):
        """
        Parse zmq multipart buffer into message
        """

        v, t, payload = multipart
        t = int.from_bytes(t, byteorder="big")

        # notifications pattern
        if t == cls.NOTIFICATION:
            return json.loads(payload.decode())
        # outer/client pattern
        if t == cls.CLIENT:
            return json.loads(payload.decode())
        else:
            return multipart


##############################################################################
## Files and Folders
##############################################################################


def delete_directory(directory):
    if os.path.isdir(directory):
        shutil.rmtree(directory)


_uuid_cycle = cycle(map(lambda x: str(x), range(100)))


def random_uuid(self):
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
    """ A metaclass that creates a Singleton base class when called. """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Singleton(_Singleton("SingletonMeta", (object,), {})):
    pass
