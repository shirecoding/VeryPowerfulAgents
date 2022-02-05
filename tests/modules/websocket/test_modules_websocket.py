import logging

import aiohttp
import pytest
from aiohttp.web import Response

from agents import Agent
from agents.messaging import ConnectionPool, JSONMessage
from agents.modules.websocket import WebSocketModule
from agents.utils import RxTxSubject

log = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def start_agents():
    class WebsocketTestAgent(Agent):
        def setup(self):
            self.connection_pool = ConnectionPool()
            self.rtx = RxTxSubject()
            self.register_module(
                WebSocketModule(
                    agent=self,
                    pool=self.connection_pool,
                    rtx=self.rtx,
                    routes=[("GET", "/hello", self.get_hello)],
                )
            )
            self.rtx.subscribe(self.echo)  # rx

        async def get_hello(self, request):
            return Response(text="world")

        def echo(self, packet):
            _, data = packet
            for uid in self.connection_pool.connections:
                self.rtx.on_next((uid, data))  # tx

    ws_agent = WebsocketTestAgent()
    yield ws_agent
    ws_agent.shutdown()


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

    ws_agent = start_agents

    async with aiohttp.ClientSession() as session, aiohttp.ClientSession() as session2:

        # connect ws client
        ws1 = await session.ws_connect("http://127.0.0.1:8080/ws")
        assert len(ws_agent.connection_pool.connections) == 1
        ws2 = await session2.ws_connect("http://127.0.0.1:8080/ws")
        assert len(ws_agent.connection_pool.connections) == 2

        d = {"hello": "world", "nest": {"nest": "nest"}}
        await ws1.send_str(JSONMessage(data=d).serialize())

        r = await ws1.receive()
        assert JSONMessage.deserialize(r.data) == d
        r = await ws2.receive()
        assert JSONMessage.deserialize(r.data) == d

        # test webserver
        async with session.get("http://127.0.0.1:8080/hello") as resp, session2.get(
            "http://127.0.0.1:8080/hello"
        ) as resp2:
            assert await resp.text() == await resp2.text() == "world"
