import logging

import pytest

from agents import Agent
from agents.defs import AgentModule

log = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def start_agents():
    class SimpleModule(AgentModule):
        def setup(self):
            self.log.debug(f"Starting up SimpleModule {self.uid}")

        def shutdown(self):
            self.log.debug(f"Shutting down SimpleModule {self.uid}")

    class SimpleAgent(Agent):
        def setup(self):
            self.register_module(SimpleModule(self, uid=f"simple1_{self.uid}"))

    agent_one = SimpleAgent(uid="agent1")
    agent_two = SimpleAgent()
    agent_three = SimpleAgent()

    yield (agent_one, agent_two, agent_three)

    agent_one.shutdown()
    agent_two.shutdown()
    agent_three.shutdown()


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_module(start_agents):

    (agent_one, agent_two, agent_three) = start_agents

    # test unique names
    assert len({agent_one.uid, agent_two.uid, agent_three.uid}) == 3
