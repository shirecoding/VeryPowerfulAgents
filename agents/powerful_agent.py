import zmq
from .agent import Agent

class PowerfulAgent(Agent):

    def create_notification_broker(self, pub_address, sub_address, options={}):
        """ Starts a pub-sub notifications broker

        Args:
            pub_address (str): agents publish to this address to notify other agents
            sub_address (str): agents listen on this address for notifications

        Returns:
            connections (pub, sub)
        """
        xpub = self.bind_socket(zmq.XPUB, options, sub_address)
        xsub = self.bind_socket(zmq.XSUB, options, pub_address)
        xsub.observable.subscribe(lambda x: xpub.send(x))
        xpub.observable.subscribe(lambda x: xsub.send(x))
        return xsub, xpub

    def create_notification_client(self, pub_address, sub_address, options={}, topics=''):
        """ Creates 2 connections (pub, sub) to a notifications broker

        Args:
            pub_address (str): publish to this address to notify other agents
            sub_address (str): listen on this address for notifications

        Returns:
            connections (pub, sub)
        """
        pub = self.connect_socket(zmq.PUB, options, pub_address)
        sub = self.connect_socket(zmq.SUB, options, sub_address)
        sub.socket.subscribe(topics)
        return pub, sub