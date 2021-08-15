import zmq
from rx import operators as ops

from agents.message import Message


class RouterClientMixin:
    def create_router(self, address, options=None):
        if options is None:
            options = {}
        router = self.bind_socket(zmq.ROUTER, options, address)

        def route(x):
            source, dest = x[0:2]
            router.send([dest, source] + x[2:])

        self.disposables.append(router.observable.subscribe(route))
        return router

    def create_client(self, address, options=None):
        if options is None:
            options = {}
        if zmq.IDENTITY not in options:
            options[zmq.IDENTITY] = self.name.encode("utf-8")
        dealer = self.connect_socket(zmq.DEALER, options, address)
        return dealer.update(
            {
                "observable": dealer.observable.pipe(
                    ops.map(Message.Client.from_multipart)
                )
            }
        )
