from dataclasses import dataclass

from aiohttp import WSMessage
from aiohttp.web import Request


class Message:

    NOTIFICATION = 0
    CLIENT = 1

    @dataclass
    class Notification:
        payload: str
        topic: str = ""

        def to_multipart(self):
            return [
                self.topic.encode(),
                bytes([Message.NOTIFICATION]),
                self.payload.encode(),
            ]

        @classmethod
        def from_multipart(cls, xs):
            topic, t, payload = xs
            if int.from_bytes(t, byteorder="big") != Message.NOTIFICATION:
                raise Exception("multipart message is not of type NOTIFICATION")
            return cls(topic=topic.decode(), payload=payload.decode())

        def copy(self, topic=None, payload=None):
            return self.__class__(
                topic=topic or self.topic, payload=payload or self.payload
            )

    @dataclass
    class Client:
        name: str
        payload: str

        def to_multipart(self):
            return [
                self.name.encode(),
                bytes([Message.CLIENT]),
                self.payload.encode(),
            ]

        @classmethod
        def from_multipart(cls, xs):
            name, t, payload = xs
            if int.from_bytes(t, byteorder="big") != Message.CLIENT:
                raise Exception("multipart message is not of type CLIENT")
            return cls(name=name.decode(), payload=payload.decode())

        def copy(self, name=None, payload=None):
            return self.__class__(
                name=name or self.name, payload=payload or self.payload
            )

    @dataclass
    class Websocket:
        connection_id: int
        request: Request
        message: WSMessage

        def copy(self, connection_id=None, request=None, message=None):
            return self.__class__(
                connection_id=connection_id or self.connection_id,
                request=request or self.request,
                message=message or self.message,
            )
