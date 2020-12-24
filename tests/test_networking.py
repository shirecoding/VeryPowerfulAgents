import zmq
from agents import Agent

class SimpleAgent(Agent):
    
    def setup(self):
        pass

    def shutdown(self):
        pass

def test_basic():

    # test connect/bind
    simple_agent_one = SimpleAgent()
    simple_agent_two = SimpleAgent()

    simple_agent_one.bind_socket(zmq.PUB, {}, "tcp://0.0.0.0:5000")
    simple_agent_one.connect_socket(zmq.SUB, {}, "tcp://0.0.0.0:5000")
