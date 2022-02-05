import logging

import pytest

from agents.messaging import JSONMessage

log = logging.getLogger(__name__)


@pytest.mark.report(
    specification="""
    """,
    procedure="""
    """,
    expected="""
    """,
)
def test_json_messaging():

    d = {"hello": "world", "nest": {"nest": "nest"}}
    m = JSONMessage(data=d)
    s = m.serialize()

    # test de/serialization
    assert JSONMessage.deserialize(s) == d

    # test from_serialized
    assert JSONMessage.from_serialized(s) == m
