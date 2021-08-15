import zmq
from rx import operators as ops

from agents.message import Message


class NotificationsMixin:
    def create_notification_broker(self, pub_address, sub_address, options=None):
        """Starts a pub-sub notifications broker

        Args:
            pub_address (str): agents publish to this address to notify other agents
            sub_address (str): agents listen on this address for notifications

        Returns:
            connections (pub, sub)
        """
        if options is None:
            options = {}
        xpub = self.bind_socket(zmq.XPUB, options, sub_address)
        xsub = self.bind_socket(zmq.XSUB, options, pub_address)
        self.disposables.append(xsub.observable.subscribe(lambda x: xpub.send(x)))
        self.disposables.append(xpub.observable.subscribe(lambda x: xsub.send(x)))
        return xsub, xpub

    def create_notification_client(
        self, pub_address, sub_address, options=None, topics=""
    ):
        """Creates 2 connections (pub, sub) to a notifications broker

        Args:
            pub_address (str): publish to this address to notify other agents
            sub_address (str): listen on this address for notifications

        Returns:
            connections (pub, sub)
        """
        if options is None:
            options = {}
        pub = self.connect_socket(zmq.PUB, options, pub_address)
        sub = self.connect_socket(zmq.SUB, options, sub_address)
        sub.socket.subscribe(topics)
        return pub, sub.update(
            {
                "observable": sub.observable.pipe(
                    ops.map(Message.Notification.from_multipart)
                )
            }
        )
