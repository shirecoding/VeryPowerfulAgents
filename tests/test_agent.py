import logging
import sys
import threading
import time

import pytest
import zmq

from agents import Agent

log = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def start_agents():
    class SimpleAgent(Agent):
        def setup(self):
            pass

        def shutdown(self):
            pass

    agent_one = SimpleAgent()
    agent_two = SimpleAgent()
    agent_three = SimpleAgent()

    yield (agent_one, agent_two, agent_three)

    agent_one.initialized_event.set()
    agent_one.exit_event.set()
    agent_two.initialized_event.set()
    agent_two.exit_event.set()
    agent_three.initialized_event.set()
    agent_three.exit_event.set()


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_basic(start_agents):

    (agent_one, agent_two, agent_three) = start_agents

    # test unique names
    assert len({agent_one.name, agent_two.name, agent_three.name}) == 3


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_socket(start_agents):

    (agent_one, agent_two, agent_three) = start_agents

    pub = agent_one.bind_socket(zmq.PUB, {}, "tcp://0.0.0.0:5000")
    sub = agent_two.connect_socket(zmq.SUB, {}, "tcp://0.0.0.0:5000")

    res = []
    sub.socket.subscribe("")
    sub.observable.subscribe(lambda x: res.append(x))
    time.sleep(0.2)
    pub.send([b"topic", b"message"])
    time.sleep(0.2)
    log.debug(res)
    assert res[0] == [b"topic", b"message"]

    rep = agent_one.bind_socket(zmq.REP, {}, "tcp://0.0.0.0:5001")
    req = agent_two.connect_socket(zmq.REQ, {}, "tcp://0.0.0.0:5001")

    res = []
    rep.observable.subscribe(lambda x: res.append(x))
    time.sleep(0.2)
    req.send([b"request"])
    time.sleep(0.2)
    log.debug(res)
    assert res[0] == [b"request"]

    router = agent_one.bind_socket(zmq.ROUTER, {}, "tcp://0.0.0.0:5002")
    dealer = agent_two.connect_socket(
        zmq.DEALER, {zmq.IDENTITY: b"dealer"}, "tcp://0.0.0.0:5002"
    )
    dealer2 = agent_three.connect_socket(
        zmq.DEALER, {zmq.IDENTITY: b"dealer2"}, "tcp://0.0.0.0:5002"
    )

    router.observable.subscribe(lambda x: router.send([x[1], x[2]]))
    res = []
    dealer2.observable.subscribe(lambda x: res.append(x))
    time.sleep(0.2)
    dealer.send([b"dealer2", b"message"])
    time.sleep(0.2)
    log.debug(res)
    assert res[0] == [b"message"]
