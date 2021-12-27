import logging
import math
import time
import uuid
from queue import Queue

import pytest

from agents import Agent

log = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def start_agents():
    class AgentWithDaemon(Agent):
        def setup(self):
            pass

    agent = AgentWithDaemon()
    yield agent
    agent.shutdown()


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_agent_with_daemon(start_agents):
    
    def handle_queue(numbers, operation="add"):
        if operation == "multiple":
            return math.prod(numbers)

        return sum(numbers)

    agent = start_agents

    queue = Queue()
    agent.create_daemon(queue, handle_queue)

    pidgeon_uid = uuid.uuid4().hex

    # passing args
    args = ([1, 2, 4],)
    kwargs = {"pidgeon_uid": pidgeon_uid}
    queue.put((args, kwargs))
    result = agent.get_pidgeon(pidgeon_uid)
    assert result == 7

    # passing args and kwargs
    args = ([1, 2, 4],)
    kwargs = {"pidgeon_uid": pidgeon_uid, "operation": "multiple"}
    queue.put((args, kwargs))
    result = agent.get_pidgeon(pidgeon_uid)
    assert result == 8

    # non-blocking
    args = ([1, 2, 4],)
    queue.put((args, {}))


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_agent_with_daemon_timeout(start_agents):
    def handle_queue(numbers, operation="add"):
        time.sleep(2)
        if operation == "multiple":
            return math.prod(numbers)

        return sum(numbers)

    agent = start_agents

    queue = Queue()
    agent.create_daemon(queue, handle_queue)

    pidgeon_uid = uuid.uuid4().hex

    args = ([1, 2, 4],)
    kwargs = {"pidgeon_uid": pidgeon_uid}
    queue.put((args, kwargs))

    result = agent.get_pidgeon(pidgeon_uid, timeout=1)
    assert result is None

    result = agent.get_pidgeon(pidgeon_uid, timeout=3)
    assert result == 7


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_agent_with_multiple_daemon(start_agents):
    def handle_add(numbers):
        return sum(numbers)

    def handle_multiple(numbers):
        return math.prod(numbers)

    agent = start_agents

    queue_add = Queue()
    queue_multiple = Queue()

    agent.create_daemon(queue_add, handle_add)
    agent.create_daemon(queue_multiple, handle_multiple)

    pidgeon_uid_add = uuid.uuid4().hex
    pidgeon_uid_multiple = uuid.uuid4().hex

    args = ([1, 2, 4],)

    queue_add.put((args, {"pidgeon_uid": pidgeon_uid_add}))
    queue_multiple.put((args, {"pidgeon_uid": pidgeon_uid_multiple}))

    assert agent.get_pidgeon(pidgeon_uid_add) == 7
    assert agent.get_pidgeon(pidgeon_uid_multiple) == 8


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_agent_with_daemon_error(start_agents):
    agent = start_agents

    with pytest.raises(TypeError) as execinfo:
        agent.create_daemon()

    assert (
        execinfo.value.args[0]
        == "create_daemon() missing 2 required positional arguments: 'queue' and 'func'"
    )
