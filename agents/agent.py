import os
import sys
import zmq
import threading
import traceback
import time
import asyncio
import uuid
from rx.subject import Subject
from signal import signal
from signal import SIGINT
from signal import SIGTERM
import logging
from .utils import Logger, stdout_logger

log = stdout_logger(__name__, level=logging.DEBUG)

class Agent():
    
    def __init__(self, *args, **kwargs):
        
        # extract special kwargs
        self.name = kwargs['name'] if 'name' in kwargs else uuid.uuid4().hex

        self.log = Logger(log, {'agent': self.name})
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

    def boot(self, *args, **kwargs):
        try:
            start = time.time()
            self.log.info('booting up ...')
            self.zmq_context = zmq.Context()

            # user setup
            self.log.info('running user setup ...')
            self.setup(*args, **kwargs)

            # process sockets
            t = threading.Thread(target=self.process_sockets)
            self.threads.append(t)
            t.start()

            self.initialized_event.set()
            self.log.info(f'booted in {time.time() - start} seconds ...')
        
        except Exception as e:
            self.log.error(f"failed to boot ...\n\n{traceback.format_exc()}")
            self.initialized_event.set()
            os.kill(os.getpid(), SIGINT)

    def _shutdown(self, signum, frame):
        self.log.info('set exit event ...')
        self.exit_event.set()

        self.log.info('wait for initialization before cleaning up ...')
        self.initialized_event.wait()

        self.log.info('running user shutdown ...')
        self.shutdown()

        # join threads
        self.log.info('joining threads ...')
        for t in self.threads:
            t.join()

        # destroy zmq sockets
        for k, v in self.zmq_sockets.items():
            self.log.info(f"closing socket {k} ...")
            v['socket'].close()
            v['observable'].dispose()
        self.zmq_context.term()

        sys.exit(0)
    
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
        self.zmq_sockets[socket_name] = {
            'socket': socket,
            'address': address,
            'type': socket_type,
            'options': options,
            'observable': observable
        }
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
        self.zmq_sockets[socket_name] = {
            'socket': socket,
            'address': address,
            'type': socket_type,
            'options': options,
            'observable': observable
        }
        self.zmq_poller.register(socket, zmq.POLLIN)
        return self.zmq_sockets[socket_name]

    def process_sockets(self):
        
        # wait for initialization
        self.initialized_event.wait()
        self.log.info("start processing sockets ...")

        while not self.exit_event.is_set():
            sockets = dict(self.zmq_poller.poll(50))
            for k, v in self.zmq_sockets.items():
                if v['socket'] in sockets and sockets[v['socket']] == zmq.POLLIN:
                    v['observable'].on_next(v['socket'].recv_multipart())

    ########################################################################################
    ## override
    ########################################################################################
    def setup(self):
        pass

    def shutdown(self):
        pass
        