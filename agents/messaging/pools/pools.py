__all__ = ["ConnectionPool", "SyncConnectionPool", "AsyncConnectionPool"]

import asyncio
from asyncio import AbstractEventLoop
from typing import Optional, Union

from agents import Agent
from agents.messaging.defs import BaseConnection, BaseMessage
from agents.utils import Logger, RxTxSubject, random_uuid

ConnectionOrUid = Union[BaseConnection, str]
MessageOrSerialized = Union[BaseMessage, str]


class ConnectionPool:
    def __init__(self, agent: Optional[Agent] = None, uid: Optional[str] = None):
        if not isinstance(agent, Agent):
            raise TypeError("agent must be of type Agent")
        self.agent = agent
        self.rtx = RxTxSubject()
        self.uid = uid or random_uuid()
        self.log = Logger(agent.log, {"pool": self.uid})
        self.connections: dict[str, BaseConnection] = {}

    def get_connection(self, con: ConnectionOrUid) -> Optional[BaseConnection]:
        if isinstance(con, BaseConnection):
            return self.connections.get(con.uid)
        elif isinstance(con, str):
            return self.connections.get(con)
        return None

    def add(self, con: BaseConnection) -> None:
        self.connections[con.uid] = con
        self.log.debug(f"Added {con} to pool")

    def shutdown(self) -> None:
        self.rtx.dispose()


class SyncConnectionPool(ConnectionPool):
    def __init__(self, *args, **kwargs):
        from agents.messaging.pools import SyncPoller

        super().__init__(*args, **kwargs)
        self.poller = SyncPoller(pool=self.pool, rtx=self.rtx)

        # start polling loop
        self.agent.run_process_in_thread(self.poller.start)

    def remove(self, con: ConnectionOrUid) -> None:
        _con = self.get_connection(con)
        if _con is not None:
            self.log.debug(f"Closing {_con}")
            _con.close()
            del self.connections[_con.uid]
            self.log.debug(f"Removed {_con} from pool")

    def send_message(self, con: ConnectionOrUid, message: MessageOrSerialized):
        _con = self.get_connection(con)
        if _con is not None:
            _con.send_message(message)

    def shutdown(self) -> None:
        self.poller.shutdown()
        for uid in self.connections:
            self.remove(uid)
        super().shutdown()


class AsyncConnectionPool(ConnectionPool):
    def __init__(self, *args, event_loop: Optional[AbstractEventLoop] = None, **kwargs):
        from agents.messaging.pools import AsyncPoller

        super().__init__(*args, **kwargs)
        self.event_loop = event_loop or asyncio.new_event_loop()
        self.poller = AsyncPoller(pool=self, rtx=self.rtx)

        # start polling loop
        if event_loop:
            self.log.debug(f"Using existing event loop ...")
            self.event_loop.create_task(self.poller.start_async(self.agent.exit_event))
        else:
            self.log.debug(f"Creating event loop ...")
            try:
                self.event_loop.run_until_complete(
                    self.poller.start_async(self.agent.exit_event)
                )
            finally:
                self.event_loop.close()

    async def remove_async(self, con: ConnectionOrUid) -> None:
        _con = self.get_connection(con)
        if _con is not None:
            self.log.debug(f"Closing {_con}")
            await _con.close_async()
            del self.connections[_con.uid]
            self.log.debug(f"Removed {_con} from pool")

    async def send_message_async(
        self, con: ConnectionOrUid, message: MessageOrSerialized
    ):
        _con = self.get_connection(con)
        if _con is not None:
            await _con.send_message_async(message)

    def shutdown(self) -> None:
        self.poller.shutdown()

        async def _close_connections():
            self.log.debug("Closing connections ...")
            for uid in self.connections:
                await self.remove_async(uid)

        self.event_loop.create_task(_close_connections())
        super().shutdown()
