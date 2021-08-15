import asyncio
import traceback
from contextlib import suppress

from aiohttp import WSCloseCode, WSMsgType, web
from rx import operators as ops
from rxpipes import observable_to_async_queue

from agents.message import Message
from agents.utils import RxTxSubject


class WebserverMixin:
    def create_webserver(self, host, port):
        self.web_application = web.Application()
        self.web_application["host"] = host
        self.web_application["port"] = port
        self.web_application["websockets"] = set()
        self.web_application.on_shutdown.append(self.webserver_shutdown)
        return self.web_application

    async def webserver_shutdown(self, *args, **kwargs):
        self.log.debug("closing remaining websockets ...")
        for ws in self.web_application["websockets"]:
            await ws.close(code=WSCloseCode.GOING_AWAY, message="Server shutdown")
        self.shutdown()

    def create_route(self, method, route, handler):

        if not self.web_application:
            raise Exception("Requires web_application, run create_webserver first")

        self.web_application.add_routes([getattr(web, method.lower())(route, handler)])

    def create_websocket(self, route):

        if not self.web_application:
            raise Exception("Requires web_application, run create_webserver first")

        rtx = RxTxSubject()
        connections = {}

        async def websocket_handler(request):

            # create connection
            ws = web.WebSocketResponse()
            connection_id = id(ws)
            await ws.prepare(request)
            self.web_application["websockets"].add(ws)
            self.log.debug(f"Creating websocket connection {connection_id} ...")
            connections[connection_id] = ws

            # clean up connections
            for x in [_id for _id, _ws in connections.items() if _ws.closed]:
                self.log.debug(f"Removing closed websocket {x} ...")
                del connections[x]

            async def rtx_loop():

                tx_queue, tx_disposable = observable_to_async_queue(
                    rtx._tx.pipe(
                        ops.filter(lambda msg: msg.connection_id == connection_id)
                    ),
                    self.web_application["loop"],
                )

                while not self.exit_event.is_set():

                    # ws -> rx
                    with suppress(asyncio.exceptions.TimeoutError):
                        message = await ws.receive(timeout=0.005)

                        if message.type == WSMsgType.CLOSE:
                            self.log.debug(
                                f"Client {connection_id} closed websocket connection"
                            )
                            break  # exit loop
                        elif message.type == WSMsgType.ERROR:
                            self.log.debug(
                                f"Websocket connection {connection_id} closed with exception {ws.exception()}"
                            )
                            break  # exit loop
                        else:
                            rtx._rx.on_next(
                                Message.Websocket(
                                    request=request,
                                    connection_id=connection_id,
                                    message=message,
                                )
                            )

                    # tx -> ws
                    try:

                        with suppress(asyncio.queues.QueueEmpty):
                            await asyncio.sleep(0.005)
                            msg = tx_queue.get_nowait()
                            tx_queue.task_done()

                            if msg.message.type == WSMsgType.BINARY:
                                await asyncio.wait_for(
                                    ws.send_bytes(msg.message.data), timeout=1
                                )

                            elif msg.message.type == WSMsgType.TEXT:
                                await asyncio.wait_for(
                                    ws.send_str(msg.message.data), timeout=1
                                )

                            else:
                                self.log.warning(f"Unsupported datatype: {msg}")

                    except Exception as e:
                        self.log.error(f"{str(e)}\n\n{traceback.format_exc()}")
                        break  # exit loop

            # process
            await rtx_loop()

            # cleanup
            self.web_application["websockets"].discard(ws)
            del connections[connection_id]
            self.log.debug(f"Websocket connection {id(ws)} closed")

            return ws

        # register websocket route
        self.web_application.add_routes([web.get(route, websocket_handler)])

        return rtx, connections
