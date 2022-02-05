import logging

import pytest

from agents.messaging.connections import InternalConnection
from agents.messaging.messages import JSONMessage
from agents.messaging.pool import ConnectionPool

log = logging.getLogger(__name__)


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_pool():

    pool = ConnectionPool()

    ic1 = InternalConnection(uid="ic1", serializer=JSONMessage)
    ic2 = InternalConnection(uid="ic2", serializer=JSONMessage)

    pool.add(ic1)
    pool.add(ic2)

    assert set(pool.connections.keys()) == {"ic1", "ic2"}

    pool.remove(ic1)
    pool.remove(ic2)

    assert set(pool.connections.keys()) == set()

    pool.add(ic1)
    pool.add(ic2)

    pool.remove_by_uid("ic1")

    assert set(pool.connections.keys()) == {"ic2"}

    assert pool.get_by_uid("ic2") == ic2


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_pool_messaging():

    pool = ConnectionPool()

    d = {"hello": "world", "nest": {"nest": "nest"}}

    ic1 = InternalConnection(uid="ic1", serializer=JSONMessage)
    ic2 = InternalConnection(uid="ic2", serializer=JSONMessage)

    pool.add(ic1)
    pool.add(ic2)

    pool.send_message(ic1, d)

    assert ic1.receive_message(deserialize=True) == d
