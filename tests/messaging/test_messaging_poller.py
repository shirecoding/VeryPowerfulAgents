import logging

import pytest

from agents.messaging.connections import InternalConnection
from agents.messaging.messages import JSONMessage
from agents.messaging.pools import ConnectionPool

log = logging.getLogger(__name__)


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_poller():

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

    assert pool.connections.get("ic2") == ic2
