import json
import logging
import sys
import os
import shutil
import h5py
from signal import SIGINT, SIGTERM, signal
from collections import defaultdict
from collections.abc import MutableMapping

##############################################################################
## Message
##############################################################################


class Message:

    ##############################################################################
    ## message interface
    ##############################################################################

    NOTIFICATION = 0
    CLIENT = 1

    @classmethod
    def notification(cls, topic="", payload=""):
        return [
            topic.encode(),
            bytes([cls.NOTIFICATION]),
            json.dumps({"topic": topic, "payload": payload}).encode(),
        ]

    @classmethod
    def client(cls, name="", payload=""):
        return [
            name.encode(),
            bytes([cls.CLIENT]),
            json.dumps({"payload": payload}).encode(),
        ]

    ##############################################################################
    ## helper methods
    ##############################################################################

    @classmethod
    def decode(cls, multipart):
        """
        Parse zmq multipart buffer into message
        """

        v, t, payload = multipart
        t = int.from_bytes(t, byteorder="big")

        # notifications pattern
        if t == cls.NOTIFICATION:
            return json.loads(payload.decode())
        # outer/client pattern
        if t == cls.CLIENT:
            return json.loads(payload.decode())
        else:
            return multipart


##############################################################################
## Files and Folders
##############################################################################


def delete_directory(directory):
    if os.path.isdir(directory):
        shutil.rmtree(directory)


def make_directory(directory, delete=False, exist_ok=True):
    if delete:
        delete_directory(directory)
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=exist_ok)
    return os.path.abspath(directory)


##############################################################################
## Logging
##############################################################################


def stdout_logger(name, level=logging.DEBUG):
    log = logging.getLogger(name)
    log.propagate = False
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(levelname)-8s %(message)s")
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    log.handlers = [stream_handler]
    log.setLevel(level)
    return log


class Logger(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return (
            "[{}] {}".format(
                " ".join(
                    ["{}={}".format(k, v) for k, v in {**kwargs, **self.extra}.items()]
                ),
                msg,
            ),
            kwargs,
        )


##############################################################################
## HDF5Store
##############################################################################


class HDF5Store(MutableMapping):
    """HDF5 Store

    - hdf5 storage format
    - dictionary interface

    - handles storage/access methods and formats based on data type
    - partial access without loading the entire data
    - lru (least recently used) caching for large files
    - data expiration
    """

    def __init__(self, storage_path):
        # create storage_path parent directory
        self.storage_path = storage_path
        make_directory(os.path.dirname(self.storage_path))
        # create hdf5 file if not exist
        if not os.path.isfile(self.storage_path):
            with h5py.File(self.storage_path, "w") as f:
                pass
        # open hdf5 ledger
        self.ledger = h5py.File(self.storage_path, "r+")

        # signals for graceful shutdown
        signal(SIGTERM, self._shutdown)
        signal(SIGINT, self._shutdown)

    def _shutdown(self):
        self.ledger.close()

    def __len__(self):
        return len(self.ledger)

    def __repr__(self):
        return str({k: self.getr(k) for k, v in self.ledger.items()})

    def __iter__(self):
        return iter(self.ledger)

    def __setitem__(self, key, item):
        self.setr(str(key), item)

    def __getitem__(self, key):
        return self.getr(str(key))

    def __delitem__(self, key):
        del self.ledger[str(key)]

    def setr(self, k, v):
        if k in self.ledger:
            del self.ledger[k]
        if isinstance(v, dict):
            for _k, _v in v.items():
                self.setr(f"{k}/{_k}", _v)
        else:
            self.ledger[k] = v

    def getr(self, k):
        if isinstance(self.ledger[k], h5py.Dataset):
            return self.ledger[k]
        elif isinstance(self.ledger[k], h5py.Group):
            return {_k: self.getr(f"{k}/{_k}") for _k, _v in self.ledger[k].items()}
