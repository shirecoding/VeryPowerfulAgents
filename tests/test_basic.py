from agents import Agent


class SimpleAgent(Agent):
    def setup(self):
        pass

    def shutdown(self):
        pass


def test_basic():

    # test unique name
    simple_agent_one = SimpleAgent()
    simple_agent_two = SimpleAgent()
    assert simple_agent_one.name != simple_agent_two.name
