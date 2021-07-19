import threading
import time

from fastapi import FastAPI

from agents import Agent


class Webchat(Agent):

    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"Hello": "World"}

    def shutdown(self):
        # set uvicorn exit flag
        if getattr(self, "rest"):
            self.rest.should_exit = True
        super().shutdown()

    def start_rest_api(self, host, port, reload=True, debug=True, workers=3):
        import uvicorn

        config = uvicorn.Config(
            "webchat:Webchat.app",
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


if __name__ == "__main__":
    agent = Webchat()
    agent.start_rest_api("127.0.0.1", 8080)

    while not agent.exit_event.is_set():
        time.sleep(1)
