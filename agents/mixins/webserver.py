import asyncio
import threading
import traceback
from contextlib import suppress

from aiohttp import WSCloseCode, WSMsgType, web
from rx import operators as ops
from rxpipes import observable_to_async_queue

from agents.message import Message
from agents.utils import RxTxSubject


class WebserverMixin:

    web_application = None

    def setup(self, *args, **kwargs):
        # start webserver
        if self.web_application:
            self.log.info("Starting webserver ...")

            async def _until_exit():
                while not self.exit_event.is_set():
                    await asyncio.sleep(1)

            def _run_server_thread():
                try:
                    loop = asyncio.new_event_loop()
                    runner = web.AppRunner(self.web_application)
                    asyncio.set_event_loop(loop)
                    self.web_application["loop"] = loop
                    loop.run_until_complete(runner.setup())
                    site = web.TCPSite(
                        runner,
                        self.web_application["host"],
                        self.web_application["port"],
                    )
                    loop.run_until_complete(site.start())
                    loop.run_until_complete(_until_exit())
                finally:
                    loop.close()

            t = threading.Thread(target=_run_server_thread)
            self.threads.append(t)
            t.start()

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

    def create_websocket(self, route, authenticate=None):

        if not self.web_application:
            raise Exception("Requires web_application, run create_webserver first")

        rtx = RxTxSubject()
        connections = {}

        async def websocket_handler(request):

            # authenticate
            if authenticate and not authenticate(request):
                raise web.HTTPUnauthorized()

            # create connection
            ws = web.WebSocketResponse()
            connection_id = id(ws)
            await ws.prepare(request)
            self.web_application["websockets"].add(ws)
            self.log.debug(f"Creating websocket connection {connection_id} ...")
            connections[connection_id] = ws
            close_reason = (WSCloseCode.OK, "Closed OK")

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
                            err = f"Websocket connection {connection_id} closed with exception {ws.exception()}"
                            self.log.debug(err)
                            close_reason = (WSCloseCode.PROTOCOL_ERROR, err)
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
                                await ws.send_bytes(msg.message.data)

                            elif msg.message.type == WSMsgType.TEXT:
                                await ws.send_str(msg.message.data)

                            else:
                                raise Exception(f"Unsupported datatype: {msg}")

                    except Exception as e:
                        err = f"{str(e)}\n\n{traceback.format_exc()}"
                        close_reason = (WSCloseCode.UNSUPPORTED_DATA, err)
                        self.log.error(err)
                        break  # exit loop

            # process
            await rtx_loop()

            # cleanup
            await ws.close(code=close_reason[0], message=close_reason[1])
            self.web_application["websockets"].discard(ws)
            del connections[connection_id]
            self.log.debug(f"Websocket connection {id(ws)} closed")

            # clean up connections
            for x in [_id for _id, _ws in connections.items() if _ws.closed]:
                self.log.debug(f"Removing closed websocket {x} ...")
                del connections[x]

            return ws

        # register websocket route
        self.web_application.add_routes([web.get(route, websocket_handler)])

        return rtx, connections
