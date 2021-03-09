import logging
import os
import queue
import sys
import threading
import time
import traceback
import uuid
from signal import SIGINT, SIGTERM, signal

import zmq
from pyrsistent import pmap
from rx.subject import Subject
from zmq import auth

from .utils import Logger, stdout_logger

log = stdout_logger(__name__, level=logging.DEBUG)


class Agent:
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

    def boot(self, *args, **kwargs):
        try:
            start = time.time()
            self.log.info("booting up ...")
            self.zmq_context = zmq.Context()

            # user setup
            self.log.info("running user setup ...")
            self.setup(*args, **kwargs)

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
        self.log.info("set exit event ...")
        self.exit_event.set()

        self.log.info("wait for initialization before cleaning up ...")
        self.initialized_event.wait()

        # join threads
        self.log.info("joining threads ...")
        for t in self.threads:
            self.log.info(f"joining {t}")
            t.join()

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

    ####################################################################################################
    ## authentication
    ####################################################################################################

    def curve_server_config(self, server_private_key):
        return {zmq.CURVE_SERVER: 1, zmq.CURVE_SECRETKEY: server_private_key}

    def curve_client_config(
        self, server_public_key, client_public_key, client_private_key
    ):
        return {
            zmq.CURVE_SERVERKEY: server_public_key,
            zmq.CURVE_PUBLICKEY: client_public_key,
            zmq.CURVE_SECRETKEY: client_private_key,
        }

    @classmethod
    def curve_keypair(cls):
        return zmq.curve_keypair()

    @classmethod
    def create_curve_certificates(cls, path, name, metadata=None):
        return auth.create_certificates(path, name, metadata=metadata)

    @classmethod
    def load_curve_certificate(cls, path):
        return auth.load_certificate(path)

    @classmethod
    def load_curve_certificates(cls, path):
        return auth.load_certificates(path)

    ########################################################################################
    ## override
    ########################################################################################

    def setup(self):
        pass

    def initialized(self):
        pass
