import threading
import time
from signal import SIGINT, SIGTERM, signal

import zmq

from agents import Agent, Message


class Router(Agent):
    def setup(self, name=None, address=None):
        self.create_router(address)


class Client1(Agent):
    def setup(self, name=None, address=None):
        self.counter = 0
        self.client = self.create_client(address)

        # begin sending forever, add to managed threads for graceful cleanup
        t = threading.Thread(target=self.send_forever)
        self.threads.append(t)
        t.start()

    def send_forever(self):
        # use exit event to gracefully exit loop and graceful cleanup
        while not self.exit_event.is_set():
            time.sleep(1)
            self.counter += 1
            target = "client2"
            self.log.info(f"send to {target}: {self.counter}")
            self.client.send(Message.client(name=target, payload=self.counter))


class Client2(Agent):
    def setup(self, name=None, address=None):
        self.client = self.create_client(address)
        self.disposables.append(
            self.client.observable.subscribe(
                lambda x: self.log.info(f"received: {x['payload']}")
            )
        )


if __name__ == "__main__":
    router = Router(name="router", address="tcp://0.0.0.0:5000")
    client1 = Client1(name="client1", address="tcp://0.0.0.0:5000")
    client2 = Client2(name="client2", address="tcp://0.0.0.0:5000")

    # override shutdown signals
    def shutdown(signum, frame):
        client1.shutdown()
        client2.shutdown()
        router.shutdown()

    signal(SIGTERM, shutdown)
    signal(SIGINT, shutdown)
