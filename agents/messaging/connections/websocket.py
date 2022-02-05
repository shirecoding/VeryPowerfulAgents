__all__ = ["WebsocketConnection"]

from dataclasses import dataclass
from typing import Optional

from aiohttp import WSCloseCode, WSMessage, WSMsgType
from aiohttp.web import WebSocketResponse

from agents.messaging import BaseConnection


@dataclass
class WebsocketConnection(BaseConnection):

    socket: WebSocketResponse
    timeout: float

    async def send_async(self, serialized: str) -> None:
        await self.socket.send_str(serialized)

    async def receive_async(self) -> Optional[str]:
        message: WSMessage = await self.socket.receive(timeout=self.timeout)
        if message.type == WSMsgType.TEXT:
            return message.data
        return None

    async def close_async(self, message="Host terminated connection") -> None:
        await self.socket.close(code=WSCloseCode.GOING_AWAY, message=message)
