import logging

import aiohttp
import pytest
from aiohttp.web import Response

from agents import Agent
from agents.modules.webserver import WebServerModule

log = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def start_agents():
    class WebsocketTestAgent(Agent):
        def setup(self):
            self.register_module(
                WebServerModule(agent=self, routes=[("GET", "/hello", self.get_hello)])
            )

        async def get_hello(self, request):
            return Response(text="world")

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

        async with session.get("http://127.0.0.1:8080/hello") as resp, session2.get(
            "http://127.0.0.1:8080/hello"
        ) as resp2:
            assert await resp.text() == await resp2.text() == "world"
