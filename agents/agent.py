import zmq
import threading
import time
import uuid
from signal import signal
from signal import SIGINT
from signal import SIGTERM
import logging
from .utils import Logger, stdout_logger

log = stdout_logger(__name__, level=logging.DEBUG)

class Agent():
    
    def __init__(self, name=uuid.uuid4().hex):

        self.log = Logger(log, {'agent': name})
        self.name = name
        self.initialized_event = threading.Event()
        self.exit_event = threading.Event()
        
        # signals for graceful shutdown
        signal(SIGTERM, self._shutdown)
        signal(SIGINT, self._shutdown)

        # boot in thread
        threading.Thread(target=self.boot).start()
        self.initialized_event.wait()

    def boot(self):
        start = time.time()
        self.log.info(self.name)
        self.log.info('booting up ...')
        self.context = zmq.Context()

        # user setup
        self.log.info('running user setup ...')
        self.setup()

        self.initialized_event.set()
        self.log.info(f'booted in {time.time() - start} seconds ...')

    def _shutdown(self, signum, frame):
        self.log.info('set exit event ...')
        self.exit_event.set()

        self.log.info('wait for initialization before cleaning up ...')
        self.initialized_event.wait()

        self.log.info('running user shutdown ...')
        self.shutdown()
    
    ########################################################################################
    ## helpers
    ########################################################################################


    ########################################################################################
    ## override
    ########################################################################################
    def setup(self):
        pass

    def shutdown(self):
        pass
        