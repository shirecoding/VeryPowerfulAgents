__all__ = ["JSONMessage"]

import json

from agents.defs import JSONObject
from agents.messaging.defs import BaseMessage


class JSONMessage(BaseMessage):
    def serialize(self) -> str:
        return json.dumps(self.data)

    @classmethod
    def deserialize(self, raw: str) -> JSONObject:
        return json.loads(raw)
