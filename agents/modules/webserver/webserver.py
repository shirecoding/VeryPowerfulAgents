__all__ = ["WebServerModule"]


import asyncio
from asyncio import AbstractEventLoop
from typing import Callable, List, Optional, Tuple

from aiohttp import web
from aiohttp.web import Application, Request, Response

from agents.defs import AgentModule

Routes = List[Tuple[str, str, Callable[[Request], Response]]]


class WebServerModule(AgentModule):
    """AIOHTTP web server agent module

    Args:
        app: AIOHTTP web application. Creates new web application if None
        event_loop: asyncio event loop. Creates new loop if None
        routes: eg. [('GET', '/index.html', get_index), ...]
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        app: Optional[Application] = None,
        event_loop: Optional[AbstractEventLoop] = None,
        routes: Optional[Routes] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.app = app or web.Application()
        self.event_loop = event_loop or asyncio.new_event_loop()
        self.routes = routes or []

        # add routes
        self.app.add_routes([getattr(web, m.lower())(r, h) for m, r, h in self.routes])

    def setup(self):
        def _run(exit_event):

            self.log.info(f"Starting web server on {self.host}:{self.port} ...")

            # Set event_loop as a current event loop for this current thread
            asyncio.set_event_loop(self.event_loop)

            _runner = web.AppRunner(self.app)

            async def _until_exit(exit_event):
                while not exit_event.is_set():
                    await asyncio.sleep(1)
                await _runner.cleanup()

            try:
                self.event_loop.run_until_complete(_runner.setup())
                self.event_loop.run_until_complete(
                    web.TCPSite(_runner, self.host, self.port).start()
                )
                self.event_loop.run_until_complete(_until_exit(exit_event))
            finally:
                self.event_loop.close()

        # run socket server
        self.agent.run_process_in_thread(_run)

    def shutdown(self):
        pass
