from agents import Agent
import logging
import math
import time
import uuid
from queue import Queue

class DaemonAgent(Agent):

    def setup(self):
        self.queue = Queue()
        self.create_daemon(self.queue, self.handle_queue)

    def handle_queue(self, numbers, operation="add"):
        if operation == "multiple":
            return math.prod(numbers)
        return sum(numbers)


if __name__ == "__main__":
    agent = DaemonAgent()

    pidgeon_uid = uuid.uuid4().hex
    agent.queue.put((
        ([1, 2, 4],), {"pidgeon_uid": pidgeon_uid}
    ))
    result = agent.get_pidgeon(pidgeon_uid)

    print(f"result: {result}")