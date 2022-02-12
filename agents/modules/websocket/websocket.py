__all__ = ["WebSocketModule"]

from typing import Optional

from aiohttp import web

from agents.messaging.connections import WebsocketConnection
from agents.messaging.defs import BaseMessage
from agents.messaging.messages import JSONMessage
from agents.messaging.pools import AsyncConnectionPool
from agents.modules.webserver import WebServerModule


class WebSocketModule(WebServerModule):
    """Websocket Agent Module"""

    def __init__(
        self,
        serializer: Optional[BaseMessage] = None,
        websocket_route: str = "/ws",
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.pool = AsyncConnectionPool(agent=self.agent, event_loop=self.event_loop)
        self.serializer = serializer or JSONMessage
        self.websocket_route = websocket_route

        # register websocket_route
        self.app.add_routes([web.get(self.websocket_route, self.websocket_handler)])

        # register cleanup
        self.app.on_shutdown.append(self.on_app_shutdown)

    async def websocket_handler(self, request):

        # create connection & add to pool
        socket = web.WebSocketResponse()
        await socket.prepare(request)
        connection = WebsocketConnection(
            socket=socket, serializer=self.serializer, uid=id(socket), timeout=0.005
        )
        self.pool.add(connection)

        # response
        return connection.socket

    def shutdown(self):  # on agent shutdown
        self.pool.shutdown()

    async def on_app_shutdown(self, *args, **kwargs):  # on app shutdown
        self.shutdown()
