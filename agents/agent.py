import asyncio
import logging
import os
import queue
import threading
import time
import traceback
import uuid
from signal import SIGINT, SIGTERM, signal

import zmq
from aiohttp import web
from pyrsistent import pmap
from rx.subject import Subject

from .message import Message
from .mixins import (
    AuthenticationMixin,
    NotificationsMixin,
    RouterClientMixin,
    WebserverMixin,
)
from .utils import Logger, stdout_logger

log = stdout_logger(__name__, level=logging.DEBUG)


class Agent(RouterClientMixin, NotificationsMixin, AuthenticationMixin, WebserverMixin):
    def __init__(self, *args, name=None, **kwargs):

        # extract special kwargs
        if name:
            self.name = name
        else:
            self.name = uuid.uuid4().hex

        self.log = Logger(log, {"agent": self.name})
        self.initialized_event = threading.Event()
        self.exit_event = threading.Event()
        self.zmq_sockets = {}
        self.zmq_poller = zmq.Poller()
        self.threads = []
        self.disposables = []
        self.zap = None
        self.web_application = None

        # signals for graceful shutdown
        signal(SIGTERM, self._shutdown)
        signal(SIGINT, self._shutdown)

        # boot in thread
        t = threading.Thread(target=self.boot, args=args, kwargs=kwargs)
        self.threads.append(t)
        t.start()
        self.initialized_event.wait()

        # call initialized hook
        self.initialized()

    def setup(self):
        """
        User override
        """

    def initialized(self):
        """
        User override
        """

    def boot(self, *args, **kwargs):
        try:
            start = time.time()
            self.log.info("booting up ...")
            self.zmq_context = zmq.Context()

            # user setup
            self.log.info("running user setup ...")
            self.setup(*args, **kwargs)

            # start webserver
            if self.web_application:
                self.log.info("starting webserver ...")

                async def _until_exit():
                    while not self.exit_event.is_set():
                        await asyncio.sleep(1)

                def _run_server_thread():
                    try:
                        loop = asyncio.new_event_loop()
                        runner = web.AppRunner(self.web_application)
                        asyncio.set_event_loop(loop)
                        self.web_application["loop"] = loop
                        loop.run_until_complete(runner.setup())
                        site = web.TCPSite(
                            runner,
                            self.web_application["host"],
                            self.web_application["port"],
                        )
                        loop.run_until_complete(site.start())
                        loop.run_until_complete(_until_exit())
                    finally:
                        loop.close()

                t = threading.Thread(target=_run_server_thread)
                self.threads.append(t)
                t.start()

            # process sockets
            t = threading.Thread(target=self.process_sockets)
            self.threads.append(t)
            t.start()

            self.initialized_event.set()
            self.log.info(f"booted in {time.time() - start} seconds ...")

        except Exception as e:
            self.log.error(f"failed to boot ...\n\n{traceback.format_exc()}")
            self.initialized_event.set()
            os.kill(os.getpid(), SIGINT)

    def shutdown(self):
        """
        Shutdown procedure, call super().shutdown() if overriding
        """

        # stop authenticator
        if self.zap:
            self.log.info("stopping ZMQ Authenticator ...")
            self.zap.stop()

        # dispose observables
        for d in self.disposables:
            self.log.info(f"disposing {d} ...")
            d.dispose()

        self.log.info("set exit event ...")
        self.exit_event.set()

        self.log.info("wait for initialization before cleaning up ...")
        self.initialized_event.wait()

        # join threads
        self.log.info("joining threads ...")
        for t in self.threads:
            self.log.info(f"joining {t}")
            t.join()
        self.log.info("joining threads complete ...")

        # destroy zmq sockets
        for k, v in self.zmq_sockets.items():
            self.log.info(f"closing socket {k} ...")
            v["socket"].close()
        self.zmq_context.term()

    def _shutdown(self, signum, frame):
        self.shutdown()

    ########################################################################################
    ## networking
    ########################################################################################

    def bind_socket(self, socket_type, options, address):
        self.log.info(f"binding {socket_type} socket on {address} ...")
        socket = self.zmq_context.socket(socket_type)
        for k, v in options.items():
            if type(v) == str:
                socket.setsockopt_string(k, v)
            else:
                socket.setsockopt(k, v)
        socket.bind(address)
        observable = Subject()
        socket_name = f"{socket_type}:{address}"
        send_queue = queue.Queue()
        self.zmq_sockets[socket_name] = pmap(
            {
                "socket": socket,
                "address": address,
                "type": socket_type,
                "options": options,
                "observable": observable,
                "send_queue": send_queue,
                "send": lambda x: send_queue.put(x),
            }
        )
        self.zmq_poller.register(socket, zmq.POLLIN)
        return self.zmq_sockets[socket_name]

    def connect_socket(self, socket_type, options, address):
        self.log.info(f"connecting {socket_type} socket to {address} ...")
        socket = self.zmq_context.socket(socket_type)
        for k, v in options.items():
            if type(v) == str:
                socket.setsockopt_string(k, v)
            else:
                socket.setsockopt(k, v)
        socket.connect(address)
        observable = Subject()
        socket_name = f"{socket_type}:{address}"
        send_queue = queue.Queue()
        self.zmq_sockets[socket_name] = pmap(
            {
                "socket": socket,
                "address": address,
                "type": socket_type,
                "options": options,
                "observable": observable,
                "send_queue": send_queue,
                "send": lambda x: send_queue.put(x),
            }
        )
        self.zmq_poller.register(socket, zmq.POLLIN)
        return self.zmq_sockets[socket_name]

    def process_sockets(self):

        # wait for initialization
        self.initialized_event.wait()
        self.log.info(
            f"start processing sockets in thread {threading.current_thread()} ..."
        )

        while not self.exit_event.is_set():
            if self.zmq_sockets:
                sockets = dict(self.zmq_poller.poll(50))
                for k, v in self.zmq_sockets.items():
                    # receive socket into observable
                    if v.socket in sockets and sockets[v.socket] == zmq.POLLIN:
                        v.observable.on_next(v.socket.recv_multipart())
                    # send queue to socket (zmq is not thread safe)
                    while not v.send_queue.empty() and not self.exit_event.is_set():
                        try:
                            v.socket.send_multipart(v.send_queue.get(block=False))
                        except queue.Empty:
                            pass
            else:
                time.sleep(1)
