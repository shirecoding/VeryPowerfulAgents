import logging

import aiohttp
import pytest

from agents import Agent
from agents.messaging.pool import ConnectionPool
from agents.modules.websocket import WebSocketModule
from agents.utils import RxTxSubject

log = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def start_agents():
    class MyAgent(Agent):
        def setup(self):

            self.connection_pool = ConnectionPool()
            self.rtx = RxTxSubject()

            self.register_module(
                WebSocketModule(
                    agent=self,
                    pool=self.connection_pool,
                    rtx=self.rtx,
                )
            )

    my_agent = MyAgent()

    yield my_agent

    my_agent.shutdown()


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
@pytest.mark.asyncio
async def test_module_websocket(start_agents):

    my_agent = start_agents

    session = aiohttp.ClientSession()
    ws = await session.ws_connect("http://127.0.0.1:8080/ws")

    msg = await ws.receive()
    log.debug(f"                   {msg}")

    await ws.close()
