import asyncio
import threading
import time
from signal import SIGINT, SIGTERM, signal

import rx
import zmq
from rxpipes import Pipeline, observable_to_async_iterable

from agents import Agent, Message


class Router(Agent):
    def setup(self, name=None, address=None):
        self.create_router(address)


class Client1(Agent):
    def setup(self, name=None, address=None):
        self.counter = 0
        self.client = self.create_client(address)

    def initialized(self):
        self.disposables.append(
            Pipeline.take(5)
            .to_observable(rx.interval(0.5))
            .subscribe(self.send_message)
        )

    def send_message(self, x):
        self.counter += 1
        target = "client2"
        self.log.info(f"send to {target}: {self.counter}")
        self.client.send(Message.client(name=target, payload=self.counter))


class Client2(Agent):
    def setup(self, loop, name=None, address=None):
        self.client = self.create_client(address)
        self.loop = loop

    async def task(self, loop):
        obs = Pipeline.take(5).to_observable(self.client.observable)
        async for x in observable_to_async_iterable(obs, loop):
            self.log.info(f"received: {x['payload']}")

        self.log.info("done ...")

    def initialized(self):
        self.loop.run_until_complete(self.task(self.loop))


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    router = Router(name="router", address="tcp://0.0.0.0:5000")
    client1 = Client1(name="client1", address="tcp://0.0.0.0:5000")
    client2 = Client2(loop, name="client2", address="tcp://0.0.0.0:5000")

    # override shutdown signals
    def shutdown(signum, frame):
        client1.shutdown()
        client2.shutdown()
        router.shutdown()

    signal(SIGTERM, shutdown)
    signal(SIGINT, shutdown)
