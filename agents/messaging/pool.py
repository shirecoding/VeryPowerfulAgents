__all__ = ["ConnectionPool"]

from typing import Optional, Union

from agents.messaging.defs import BaseConnection, BaseMessage
from agents.utils import stdout_logger

log = stdout_logger(__name__)


class ConnectionPool:

    connections: dict[str, BaseConnection] = {}

    def add(self, con: BaseConnection) -> None:
        self.connections[con.uid] = con
        log.debug(f"Added {con} to pool")

    def remove(self, con: BaseConnection) -> None:
        if con.uid in self.connections:
            del self.connections[con.uid]
            log.debug(f"Removed {con} from pool")

    def remove_by_uid(self, uid: str) -> None:
        if uid in self.connections:
            del self.connections[uid]
            log.debug(f"Removed {uid} from pool")

    def get_by_uid(self, uid: str) -> Optional[BaseConnection]:
        return self.connections.get(uid)

    def send_message(
        self, connection: Union[BaseConnection, str], message: Union[BaseMessage, str]
    ):
        c = (
            connection
            if isinstance(connection, BaseConnection)
            else self.connections[connection]
        )
        c.send_message(message)
