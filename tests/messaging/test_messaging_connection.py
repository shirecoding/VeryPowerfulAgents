import logging

import pytest

from agents.messaging.connections import InternalConnection, WebsocketConnection
from agents.messaging.messages import JSONMessage

log = logging.getLogger(__name__)


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_internal_connection():

    d = {"hello": "world", "nest": {"nest": "nest"}}
    ic1 = InternalConnection(uid="ic1", serializer=JSONMessage)
    ic2 = InternalConnection(uid="ic2", serializer=JSONMessage)

    assert ic1.uid == "ic1"
    assert ic2.uid == "ic2"

    ic1.send_message(d)
    assert ic1.receive_message(deserialize=True) == d

    d2 = {"new": "world"}
    ic1.send_message(JSONMessage(data=d2))
    assert ic1.receive_message() == JSONMessage(data=d2)


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_websocket_connection():

    d = {"hello": "world", "nest": {"nest": "nest"}}
    ic1 = WebsocketConnection(
        uid="ic1", serializer=JSONMessage, timeout=0.005, socket=None
    )
    ic2 = WebsocketConnection(
        uid="ic2", serializer=JSONMessage, timeout=0.010, socket=None
    )

    assert ic1.uid == "ic1"
    assert ic1.timeout == 0.005

    assert ic2.uid == "ic2"
    assert ic2.timeout == 0.010
