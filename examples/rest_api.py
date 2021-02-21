import time

from agents import VeryPowerfulAgent


class RESTApi(VeryPowerfulAgent):
    def setup(self):

        app = VeryPowerfulAgent.app

        @app.get("/")
        def read_root():
            return {"Hello": "World"}


if __name__ == "__main__":
    agent = RESTApi()
    agent.start_rest_api("127.0.0.1", 8080)
