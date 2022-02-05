__all__ = ["InternalConnection"]

from collections import defaultdict
from queue import Queue
from typing import Optional

from agents.messaging.defs import BaseConnection

_pidgeon_holes = defaultdict(Queue)


class InternalConnection(BaseConnection):
    def send(self, serialized: str) -> None:
        _pidgeon_holes[self.uid].put(serialized, block=False)

    def receive(self) -> Optional[str]:
        return (
            None
            if _pidgeon_holes[self.uid].empty()
            else _pidgeon_holes[self.uid].get(block=False)
        )

    def close(self) -> None:
        del _pidgeon_holes[self.uid]
