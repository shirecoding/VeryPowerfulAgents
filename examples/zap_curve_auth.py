import os
import tempfile
import threading
import time
from signal import SIGINT, SIGTERM, signal

from agents import Agent, Message


class NotificationBroker(Agent):
    def setup(
        self,
        name=None,
        pub_address=None,
        sub_address=None,
        private_key=None,
        client_certificates_path=None,
    ):

        # configure public key auth/encryption if private_key is provided
        options = self.curve_server_config(private_key) if private_key else {}
        self.create_notification_broker(pub_address, sub_address, options=options)

        # start authenticator if client_certificates_path is provided
        if client_certificates_path:
            self.auth = self.start_authenticator(
                domain="*", certificates_path=client_certificates_path
            )


class Sender(Agent):
    def setup(
        self,
        name=None,
        pub_address=None,
        sub_address=None,
        private_key=None,
        public_key=None,
        server_public_key=None,
    ):
        # configure public key auth/encryption if keys are provided
        if private_key and public_key and server_public_key:
            options = self.curve_client_config(
                server_public_key, public_key, private_key
            )
        else:
            options = {}
        self.counter = 0
        self.pub, self.sub = self.create_notification_client(
            pub_address, sub_address, options=options
        )

        # begin sending forever, add to managed threads for graceful cleanup
        t = threading.Thread(target=self.send_forever)
        self.threads.append(t)
        t.start()

    def send_forever(self):
        # use exit event to gracefully exit loop and graceful cleanup
        while not self.exit_event.is_set():
            time.sleep(1)
            self.counter += 1
            msg = Message.Notification(payload=str(self.counter))
            self.log.info(f"publishing: {msg}")
            self.pub.send(msg.to_multipart())


class Listener(Agent):
    def setup(
        self,
        name=None,
        pub_address=None,
        sub_address=None,
        private_key=None,
        public_key=None,
        server_public_key=None,
    ):
        # configure public key auth/encryption if keys are provided
        if private_key and public_key and server_public_key:
            options = self.curve_client_config(
                server_public_key, public_key, private_key
            )
        else:
            options = {}
        self.pub, self.sub = self.create_notification_client(
            pub_address, sub_address, options=options
        )
        self.sub.observable.subscribe(lambda x: self.log.info(f"received: {x}"))


if __name__ == "__main__":

    with tempfile.TemporaryDirectory() as trusted_keys_path, tempfile.TemporaryDirectory() as untrusted_keys_path:

        # create key pairs in corresponding directories
        Agent.create_curve_certificates(trusted_keys_path, "server")
        Agent.create_curve_certificates(trusted_keys_path, "listener")
        Agent.create_curve_certificates(untrusted_keys_path, "listener2")

        # load key pairs
        server_public_key, server_private_key = Agent.load_curve_certificate(
            os.path.join(trusted_keys_path, "server.key_secret")
        )
        listener_public_key, listener_private_key = Agent.load_curve_certificate(
            os.path.join(trusted_keys_path, "listener.key_secret")
        )
        listener2_public_key, listener2_private_key = Agent.load_curve_certificate(
            os.path.join(untrusted_keys_path, "listener2.key_secret")
        )

        broker = NotificationBroker(
            name="broker",
            pub_address="tcp://127.0.0.1:5000",
            sub_address="tcp://127.0.0.1:5001",
            private_key=server_private_key,
            client_certificates_path=trusted_keys_path,
        )
        sender = Sender(
            name="sender",
            pub_address="tcp://127.0.0.1:5000",
            sub_address="tcp://127.0.0.1:5001",
            private_key=server_private_key,
            public_key=server_public_key,
            server_public_key=server_public_key,
        )
        listener = Listener(
            name="listener",
            pub_address="tcp://127.0.0.1:5000",
            sub_address="tcp://127.0.0.1:5001",
            private_key=listener_private_key,
            public_key=listener_public_key,
            server_public_key=server_public_key,
        )
        listener2 = Listener(
            name="listener2",
            pub_address="tcp://127.0.0.1:5000",
            sub_address="tcp://127.0.0.1:5001",
            private_key=listener2_private_key,
            public_key=listener2_public_key,
            server_public_key=server_public_key,
        )

        # override shutdown signals
        def shutdown(signum, frame):
            listener.shutdown()
            listener2.shutdown()
            sender.shutdown()
            broker.shutdown()

        signal(SIGTERM, shutdown)
        signal(SIGINT, shutdown)
