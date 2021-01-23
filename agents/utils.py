import collections
import json
import logging
import sys


class Message:

    ##############################################################################
    ## message interface
    ##############################################################################

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

    ##############################################################################
    ## helper methods
    ##############################################################################

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


# logging
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
