import json
import os
import pickle
import threading
from collections import defaultdict
from collections.abc import MutableMapping
from pathlib import Path
from signal import SIGINT, SIGTERM, signal

import h5py

from .utils import delete_directory

##############################################################################
## PickleDictionary
##############################################################################


def _none():
    """allow defaultdict to be pickled"""
    return None


def _ddnone():
    """allow defaultdict to be pickled"""
    return defaultdict(_none)


class PickleDictionary(MutableMapping):
    def __init__(self, storage_path):
        self.lock = threading.Lock()
        self.storage_path = Path(storage_path)

        if self.storage_path.is_file():
            with open(self.storage_path, "rb") as f:
                self._d = pickle.load(f)

        else:
            self._d = defaultdict(_ddnone)
            self.storage_path.parent.mkdir(exist_ok=True, parents=True)
            self.flush()

    def flush(self):
        with self.lock:
            with open(self.storage_path, "wb") as f:
                pickle.dump(self._d, f)

    def _unwrap(self, x):
        if isinstance(x, MutableMapping):
            return {k: self._unwrap(v) for k, v in x.items()}
        else:
            return x

    def __len__(self):
        with self.lock:
            return len(self._d)

    def __repr__(self):
        with self.lock:
            return str(self._unwrap(self._d))

    def __iter__(self):
        with self.lock:
            return iter(self._d)

    def __setitem__(self, key, item):
        with self.lock:
            self._d[key] = item

    def __getitem__(self, key):
        with self.lock:
            return self._d[key]

    def __delitem__(self, key):
        with self.lock:
            del self._d[key]


##############################################################################
## FileStore
##############################################################################


class FileStore(MutableMapping):
    """File Store

    Provides a dictionary interface to store and retrieve files.

    Usage:

        ```python
        # create store
        s = FileStore("path/to/storage/folder")

        # obtaining folders
        history_books = s['books/history']
        science_fiction_books = s['books/fiction/science']

        # set folder expiration
        from datetime import datetime, timedelta
        s.expire('books/history', datetime.now() + timedelta(hours=2))
        s.expire('books/fiction', 'science'], datetime.now() + timedelta(hours=10))
        ```
    """

    def __init__(self, storage_path):

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True, parents=True)
        self.meta = PickleDictionary(self.storage_path.joinpath(".meta"))
        self.lock = threading.Lock()

        # load storage
        self.populate_meta(self.storage_path, self.meta)

    def populate_meta(self, storage_path, meta):
        with self.lock:
            for paths in [
                str(x.relative_to(storage_path)).split(os.sep)
                for x in storage_path.glob("**")
                if x != storage_path
            ]:
                meta["/".join(paths)]["path"] = storage_path.joinpath(*paths)
            meta.flush()

    def __len__(self):
        with self.lock:
            return len(self.meta)

    def __repr__(self):
        with self.lock:
            return str(self.meta)

    def __iter__(self):
        with self.lock:
            return iter(self.meta)

    def __setitem__(self, key, item):
        pass

    def __getitem__(self, key):
        with self.lock:
            path = self.storage_path.joinpath(key)
            path.mkdir(exist_ok=True, parents=True)
            keys = key.split("/")
            for i, _ in enumerate(keys):
                parent = "/".join(keys[: i + 1])
                self.meta[parent]["path"] = self.storage_path.joinpath(parent)
            self.meta.flush()
            return self.meta[key]

    def __delitem__(self, key):
        with self.lock:
            delete_directory(self.storage_path.joinpath(key))
            to_delete = [k for k in self.meta if k.find(key) == 0]
            for d in to_delete:
                del self.meta[d]
            self.meta.flush()


##############################################################################
## HDF5Store
##############################################################################


class HDF5Store(MutableMapping):
    """HDF5 Store

    Provides a dictionary interface to the HDF5 storage file.

    Features:

        - HDF5 storage format
        - dictionary interface
        - file recyling (TODO)
        - file expiration (TODO)

    Usage:

        ```python
        s = HDF5Store("path/to/file.h5")

        # write
        s['hello'] = 'world'
        s['data'] = np.arange(100)

        # read
        s['hello'][()]
        s['data'][()]
        ```

    Notes:

        - Only used by parent process as HDF5 file cannot be read by multiple readers
    """

    def __init__(self, storage_path):
        # create storage_path parent directory
        self.storage_path = storage_path
        Path(storage_path).parent.mkdir(exist_ok=True, parents=True)

        # create hdf5 file if not exist
        if not os.path.isfile(self.storage_path):
            with h5py.File(self.storage_path, "w") as f:
                pass
        # open hdf5 ledger
        self.ledger = h5py.File(self.storage_path, "r+")

        # signals for graceful shutdown
        signal(SIGTERM, self._shutdown)
        signal(SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
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
