__all__ = ["AgentModule"]

from typing import Optional

from agents import Agent
from agents.utils import Logger, random_uuid


class AgentModule:
    def __init__(self, agent: Optional[Agent] = None, uid: Optional[str] = None):
        if not isinstance(agent, Agent):
            raise TypeError("agent must be of type Agent")
        self.agent = agent
        self.uid = uid or random_uuid()
        self.log = Logger(agent.log, {"module": self.uid})

    def setup(self):
        raise NotImplementedError("AgentModule/setup")

    def shutdown(self):
        raise NotImplementedError("AgentModule/shutdown")
