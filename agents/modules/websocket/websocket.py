__all__ = ["WebSocketModule"]

import asyncio
from contextlib import suppress
from typing import Optional

from aiohttp import web
from rx import operators as ops
from rxpipes import observable_to_async_queue

from agents.messaging import BaseMessage, JSONMessage, WebsocketConnection
from agents.messaging.pool import ConnectionPool
from agents.modules.webserver import WebServerModule
from agents.utils import RxTxSubject


class WebSocketModule(WebServerModule):
    """Websocket Agent Module
    Args:
        rtx: RxTxSubject used to send and receive messages. Use (connection_uid, message) for sending and receiving
        pool: ConnectionPool
    """

    def __init__(
        self,
        pool: Optional[ConnectionPool] = None,
        rtx: Optional[RxTxSubject] = None,
        serializer: Optional[BaseMessage] = None,
        websocket_route: str = "/ws",
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.pool = pool or ConnectionPool()
        self.rtx = rtx or RxTxSubject()
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

        # get tx async queue from rtx for this connection
        tx_queue, tx_disposable = observable_to_async_queue(
            self.rtx._tx.pipe(ops.filter(lambda xs: xs[0] == connection.uid)),
            self.event_loop,
        )

        # poll socket
        while not self.agent.exit_event.is_set():

            try:

                # ws -> rx
                with suppress(asyncio.exceptions.TimeoutError):
                    self.rtx._rx.on_next(
                        (
                            connection.uid,
                            await connection.receive_message_async(deserialize=True),
                        )
                    )

                # tx -> ws
                with suppress(asyncio.queues.QueueEmpty):
                    await asyncio.sleep(0.005)
                    _, message = tx_queue.get_nowait()
                    await connection.send_message_async(message)
                    tx_queue.task_done()

            # exit loop on exception
            except Exception as e:
                self.log.exception(e)
                break

        # cleanup
        tx_disposable.dispose()
        await connection.close_async()
        self.pool.remove(connection)

        # response
        return connection.socket

    def shutdown(self):  # on agent shutdown
        self.rtx.dispose()

    async def on_app_shutdown(self, *args, **kwargs):  # on app shutdown
        self.log.debug("Closing remaining websockets ...")
        for c in self.pool.connections.values():
            await c.close_async()
