import asyncio
import threading

from aiohttp import web

from .powerful_agent import PowerfulAgent


class VeryPowerfulAgent(PowerfulAgent):
    def _shutdown(self, signum, frame):
        if hasattr(self, "http_loop"):
            self.http_loop.call_soon_threadsafe(self.http_loop.stop)
        super()._shutdown(signum, frame)

    ##########################################################################################
    ## http server
    ##########################################################################################

    def start_http_server(self, host, port, routes=[]):
        def start():
            async def task():
                app = web.Application()

                # add routes
                for action, route, handler in routes:
                    self.log.info(f"adding http route {action} {route} ...")
                    app.router.add_route(action, route, handler)

                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, host, port)
                await site.start()

            self.http_loop = asyncio.new_event_loop()
            try:
                self.log.info(f"starting http server on {host}:{port} ...")
                self.http_loop.create_task(task())
                self.http_loop.run_forever()
            finally:
                self.log.info(f"closing http server ...")
                self.http_loop.close()

        t = threading.Thread(target=start)
        self.threads.append(t)
        t.start()
