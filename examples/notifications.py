import threading
import time
from signal import SIGINT, SIGTERM, signal

import zmq

from agents import Agent, Message


class NotificationBroker(Agent):
    def setup(self, name=None, pub_address=None, sub_address=None):
        self.create_notification_broker(pub_address, sub_address)


class Sender(Agent):
    def setup(self, name=None, pub_address=None, sub_address=None):
        self.counter = 0
        self.pub, self.sub = self.create_notification_client(pub_address, sub_address)

        # begin sending forever, add to managed threads for graceful cleanup
        t = threading.Thread(target=self.send_forever)
        self.threads.append(t)
        t.start()

    def send_forever(self):
        # use exit event to gracefully exit loop and graceful cleanup
        while not self.exit_event.is_set():
            time.sleep(1)
            self.counter += 1
            self.log.info(f"publishing: {self.counter}")
            self.pub.send(Message.notification(payload=self.counter))


class Listener(Agent):
    def setup(self, name=None, pub_address=None, sub_address=None):
        self.pub, self.sub = self.create_notification_client(pub_address, sub_address)

        self.disposables.append(
            self.sub.observable.subscribe(
                lambda x: self.log.info(f"received: { x['payload'] }")
            )
        )


if __name__ == "__main__":
    broker = NotificationBroker(
        name="broker",
        pub_address="tcp://0.0.0.0:5000",
        sub_address="tcp://0.0.0.0:5001",
    )
    sender = Sender(
        name="sender",
        pub_address="tcp://0.0.0.0:5000",
        sub_address="tcp://0.0.0.0:5001",
    )
    listener = Listener(
        name="listener",
        pub_address="tcp://0.0.0.0:5000",
        sub_address="tcp://0.0.0.0:5001",
    )

    # override shutdown signals
    def shutdown(signum, frame):
        sender.shutdown()
        listener.shutdown()
        broker.shutdown()

    signal(SIGTERM, shutdown)
    signal(SIGINT, shutdown)
