import asyncio
import threading

from .powerful_agent import PowerfulAgent
from aiohttp import web

class VeryPowerfulAgent(PowerfulAgent):
    
    def __init__(self, *args, **kwargs):
        self.web = None
        super().__init__(*args, **kwargs)

    def _shutdown(self, signum, frame):
        if self.web:
            self.log.info("stopping aiohttp webserver ...")
            self.web.stop()
        super()._shutdown(signum, frame)

    ##########################################################################################
    ## http server
    ##########################################################################################

    def start_http_server(self, host, port):

        def start():
            async def task():
                app = web.Application()
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, host, port)
                await site.start()

                # sleep forever
                while not self.exit_event.is_set():
                    await asyncio.sleep(3600)  
            
            loop = asyncio.new_event_loop()
            try:
                self.log.info(f"starting http server on {host}:{port} ...")
                loop.run_until_complete(task())
            finally:
                self.log.info(f"closing http server ...")
                loop.close()

        t = threading.Thread(target=start)
        self.threads.append(t)
        t.start()