import asyncio
import threading

from fastapi import FastAPI

from .powerful_agent import PowerfulAgent


class VeryPowerfulAgent(PowerfulAgent):

    app = FastAPI()

    def shutdown(self):
        # set uvicorn exit flag
        if getattr(self, "rest"):
            self.rest.should_exit = True

        super().shutdown()

    ##########################################################################################
    ## REST api
    ##########################################################################################

    def start_rest_api(self, host, port, reload=True, debug=True, workers=3):
        import uvicorn

        config = uvicorn.Config(
            "agents:VeryPowerfulAgent.app",
            host=host,
            port=port,
            reload=reload,
            debug=debug,
            workers=workers,
        )
        self.rest = uvicorn.Server(config=config)
        t = threading.Thread(target=self.rest.run)
        self.threads.append(t)
        t.start()
