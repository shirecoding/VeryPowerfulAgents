import logging

import aiohttp
import pytest
from aiohttp.web import Response

from agents import Agent
from agents.modules.websocket import WebSocketModule

log = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def start_agents():
    class WebsocketTestAgent(Agent):
        def setup(self):

            # register websocket module
            self.ws = WebSocketModule(
                agent=self,
                routes=[("GET", "/hello", self.get_hello)],
            )
            self.register_module(self.ws)

            # get connections and rtx
            self.connections = self.ws.pool.connections
            self.rtx = self.ws.pool.rtx

            # subscribe to echo handler
            self.rtx.subscribe(self.handle_message)  # rx

        async def get_hello(self, request):
            return Response(text="world")

        def handle_message(self, packet):
            _, data = packet
            for uid in self.connections:
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

        # # connect ws client
        # ws1 = await session.ws_connect("http://127.0.0.1:8080/ws")
        # assert len(ws_agent.connection_pool.connections) == 1
        # ws2 = await session2.ws_connect("http://127.0.0.1:8080/ws")
        # assert len(ws_agent.connection_pool.connections) == 2

        # d = {"hello": "world", "nest": {"nest": "nest"}}
        # await ws1.send_str(JSONMessage(data=d).serialize())

        # r = await ws1.receive()
        # assert JSONMessage.deserialize(r.data) == d
        # r = await ws2.receive()
        # assert JSONMessage.deserialize(r.data) == d

        # test webserver
        async with session.get("http://127.0.0.1:8080/hello") as resp, session2.get(
            "http://127.0.0.1:8080/hello"
        ) as resp2:
            assert await resp.text() == await resp2.text() == "world"
