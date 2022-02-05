import os
import queue
import threading
import time
import traceback
from signal import SIGINT, SIGTERM, signal
from typing import Optional

import zmq
from pyrsistent import pmap
from rx.subject import Subject

from agents.utils import Logger, random_uuid, stdout_logger

log = stdout_logger(__name__)


class Agent(
    # RouterClientMixin,
    # NotificationsMixin,
    # AuthenticationMixin,
    # WebserverMixin,
    # DaemonMixin,
):
    def __init__(self, uid: Optional[str] = None):

        self.uid = uid or random_uuid()
        self.log = Logger(log, {"agent": self.uid})
        self.initialized_event = threading.Event()
        self.exit_event = threading.Event()
        self.zmq_sockets = {}
        self.zmq_poller = zmq.Poller()
        self.threads = []
        self.disposables = []

        self._modules = {}

        # signals for graceful shutdown
        signal(SIGTERM, self._shutdown)
        signal(SIGINT, self._shutdown)

        # boot in thread
        self.run_process_in_thread(self.boot)
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

    def is_initialized(self):
        return self.initialized_event.is_set()

    def register_module(self, module):
        self.log.info(f"Registering module {module.uid} ...")
        self._modules[module.uid] = module
        module.setup()
        self.log.info(f"Module {module.uid} setup complete ...")

    def run_process_in_thread(self, f):
        t = threading.Thread(target=f, args=(self.exit_event,))
        self.threads.append(t)
        t.start()

    def boot(self, *args, **kwargs):
        try:
            start = time.time()
            # self.log.info("Booting up ...")
            # self.zmq_context = zmq.Context()

            # user setup
            self.log.info("Running user setup ...")
            self.setup()

            # # setup bases
            # for base in Agent.__bases__:
            #     if hasattr(base, "setup"):
            #         self.log.info(f"Initiating {base.__name__} setup procedure")
            #         base.setup(self, *args, **kwargs)

            # # process sockets
            # t = threading.Thread(target=self.process_sockets)
            # self.threads.append(t)
            # t.start()

            self.initialized_event.set()
            self.log.info(f"Booted in {time.time() - start} seconds ...")

        except Exception as e:
            self.log.error(f"Failed to boot ...\n\n{traceback.format_exc()}")
            self.initialized_event.set()
            os.kill(os.getpid(), SIGINT)

    def shutdown(self):
        """
        Shutdown procedure, call super().shutdown() if overriding
        """

        # shutdown modules
        for m in self._modules.values():
            self.log.info(f"Shutting down module {m.uid} ...")
            m.shutdown()
            self.log.info(f"Module {m.uid} shutdown complete ...")

        # # run shutdown procedures of all bases
        # for base in Agent.__bases__:
        #     if hasattr(base, "shutdown"):
        #         self.log.info(f"Initiating {base.__name__} shutdown procedure")
        #         base.shutdown(self)

        # dispose observables
        for d in self.disposables:
            self.log.info(f"disposing {d} ...")
            d.dispose()

        self.log.info("set exit event ...")
        self.exit_event.set()

        self.log.info("wait for initialization before cleaning up ...")
        self.initialized_event.wait()

        # join threads
        self.log.info(f"joining {len(self.threads)} threads ...")
        for t in self.threads:
            self.log.info(f"joining {t}")
            t.join()
        self.log.info("joining threads complete ...")

        # # destroy zmq sockets
        # for k, v in self.zmq_sockets.items():
        #     self.log.info(f"closing socket {k} ...")
        #     v["socket"].close()
        # self.zmq_context.term()

        self.log.info("shutdown complete ...")

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
