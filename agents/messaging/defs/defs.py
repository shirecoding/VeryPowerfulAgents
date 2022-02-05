__all__ = ["BaseMessage", "BaseConnection"]

import logging
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

Deserialized_T = TypeVar("Deserialized_T")


@dataclass
class BaseMessage(Generic[Deserialized_T]):

    data: Deserialized_T

    @abstractmethod
    def serialize(self) -> str:
        raise NotImplementedError("BaseMessage/serialize")

    @classmethod
    @abstractmethod
    def deserialize(cls, serialized: str) -> Deserialized_T:
        raise NotImplementedError("BaseMessage/deserialize")

    @classmethod
    def from_serialized(cls, serialized: str, **kwargs: Any) -> "BaseMessage":
        return cls(data=cls.deserialize(serialized), **kwargs)


@dataclass
class BaseConnection:

    uid: str
    serializer: BaseMessage

    def __str__(self) -> str:
        return str(self.uid)

    def __repr__(self) -> str:
        return str(self.uid)

    @abstractmethod
    def send(self, serialized: str) -> None:
        """Implementation of how a serilized message is sent to the client in this connection

        Args:
            serialized: Output of BaseMessage.serialize
        Returns:
            None
        """
        raise NotImplementedError("BaseConnection/send")

    @abstractmethod
    async def send_async(self, serialized: str) -> None:
        raise NotImplementedError("BaseConnection/send_async")

    @abstractmethod
    def receive(self) -> Optional[str]:
        """Polling method to receive data on the connection

        Returns:
            Optional[str]: Serialized data
        """
        raise NotImplementedError("BaseConnection/receive")

    @abstractmethod
    async def receive_async(self) -> Optional[str]:
        raise NotImplementedError("BaseConnection/receive_async")

    @abstractmethod
    def close(self, *args: Any, **kwargs: Any) -> None:
        """Close the connection"""
        raise NotImplementedError("BaseConnection/close")

    @abstractmethod
    def close_async(self, *args: Any, **kwargs: Any) -> None:
        """Close the connection (async implementation)"""
        raise NotImplementedError("BaseConnection/close_async")

    def receive_message(
        self, deserialize: bool = False
    ) -> Union[BaseMessage, Deserialized_T]:
        if deserialize:
            return self.serializer.deserialize(self.receive())
        else:
            return self.serializer.from_serialized(self.receive())

    async def receive_message_async(
        self, deserialize: bool = False
    ) -> Union[BaseMessage, Deserialized_T]:
        if deserialize:
            return self.serializer.deserialize(await self.receive_async())
        else:
            return self.serializer.from_serialized(await self.receive_async())

    def send_message(self, message: Union[BaseMessage, Deserialized_T]) -> None:
        """Sends a message to the client in this connection

        Args:
            message: Union[BaseMessage, Deserialized_T]
        Returns:
            None
        """
        if isinstance(message, BaseMessage):
            self.send(message.serialize())
        else:
            self.send(self.serializer(data=message).serialize())

    async def send_message_async(
        self, message: Union[BaseMessage, Deserialized_T]
    ) -> None:
        """Sends a message to the client in this connection (self.send is async)

        Args:
            message: Union[BaseMessage, Deserialized_T]
        Returns:
            None
        """
        if isinstance(message, BaseMessage):
            await self.send_async(message.serialize())
        else:
            await self.send_async(self.serializer(data=message).serialize())
