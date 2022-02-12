__all__ = ["AsyncPoller", "SyncPoller"]

import asyncio
from contextlib import suppress
from typing import Optional

from rxpipes import observable_to_async_queue

from agents.messaging.pools import ConnectionPool
from agents.utils import Logger, RxTxSubject


class BasePoller:
    def __init__(
        self,
        pool: Optional[ConnectionPool] = None,
        rtx: Optional[RxTxSubject] = None,
    ) -> None:
        if not isinstance(pool, ConnectionPool):
            raise TypeError("pool must be of type ConnectionPool")
        if not isinstance(rtx, RxTxSubject):
            raise TypeError("rtx must be of type RxTxSubject")
        self.pool = pool
        self.rtx = rtx
        self.log = Logger(self.pool.log, {"poller": self.__class__.__name__})

    def shutdown(self) -> None:
        pass


class AsyncPoller(BasePoller):
    async def start_async(self, exit_event) -> None:
        # get tx async queue from rtx for this connection
        self.tx_queue, self.tx_disposable = observable_to_async_queue(
            self.rtx._tx, self.pool.event_loop
        )
        self.log.info("Start polling ...")
        while not exit_event.is_set():
            await asyncio.sleep(0.005)
            await self.poll_async()
        self.log.info("Shutdown polling ...")
        self.shutdown()

    async def poll_async(self) -> None:

        # receive all messages into rx
        for uid, con in self.pool.connections.items():
            try:
                with suppress(asyncio.exceptions.TimeoutError):
                    m = await con.receive_message_async(deserialize=True)
                    if m:
                        self.rtx._rx.on_next((uid, m))
            # close and remove connection on error
            except Exception:
                self.log.exception(
                    f"Error while receiving messaging on connection {uid}"
                )
                await self.pool.remove_async(con)

        # push out all messages from tx
        while not self.tx_queue.empty():
            uid, m = await tx_queue.get()
            await self.pool.send_message_async(uid, m)
            tx_queue.task_done()

    def shutdown(self) -> None:
        self.tx_disposable.dispose()


class SyncPoller(BasePoller):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # push out all messages from tx
        self.tx_disposable = self.rtx._tx.subscribe(
            lambda xs: self.pool.send_message(*xs)
        )

    def start(self, exit_event) -> None:
        self.log.info("Start polling ...")
        while not exit_event.is_set():
            self.poll()
        self.log.info("Shutdown polling ...")
        self.shutdown()

    def poll(self) -> None:

        # receive all messages into rx
        for uid, con in self.pool.connections.items():
            try:
                m = con.receive_message(deserialize=True)
                if m:
                    self.rtx._rx.on_next((uid, m))
            # close and remove connection on error
            except Exception:
                self.log.exception(
                    f"Error while receiving messaging on connection {uid}"
                )
                self.pool.remove(con)

    def shutdown(self) -> None:
        self.tx_disposable.dispose()
