# VeryPowerfulAgents

Agents are lightweight microservices with built-in interprocess communications infrastructure using ZeroMQ.

## Features

- Graceful boot & shutdown with resource cleanup done correctly
- User setup/shutdown override methods for graceful boot & shutdown
- ZeroMQ communications is done in a thread safe manner using queues (ZeroMQ is not threadsafe)
- Socket data is received through Observables using RxPy

# Examples

## Simple Echo Server & Client
```python
import zmq
import time
import threading
from agents import Agent

class EchoServer(Agent):

    def setup(self, name=None, address=None):
        self.connection = self.bind_socket(zmq.REP, {}, address)
        self.connection.observable.subscribe(self.echo)

    def echo(self, xs):
        self.connection.send(xs)

class Client(Agent):
    
    def setup(self, name=None, address=None):
        self.counter = 0

        # receive
        self.connection = self.connect_socket(zmq.REQ, {}, address)
        self.connection.observable.subscribe(lambda x: self.log.info(f"received: {x}"))

        # begin sending forever, add to managed threads for graceful cleanup
        t = threading.Thread(target=self.send_forever)
        self.threads.append(t)
        t.start()

    def send_forever(self):
        # use exit event to gracefully exit loop and graceful cleanup
        while not self.exit_event.is_set(): 
            time.sleep(1)
            self.counter += 1
            multipart_message = [str(self.counter).encode()]
            self.log.info(f"sending: {multipart_message}")
            self.connection.send(multipart_message)

if __name__ == '__main__':
    echo_server = EchoServer(name='server', address='tcp://0.0.0.0:5000')
    client = Client(name='client', address='tcp://0.0.0.0:5000')
```

```bash
INFO     [agent=server] booting up ...
INFO     [agent=server] running user setup ...
INFO     [agent=server] binding 4 socket on tcp://0.0.0.0:5000 ...
INFO     [agent=server] booted in 0.00168609619140625 seconds ...
INFO     [agent=server] start processing sockets ...
INFO     [agent=client] booting up ...
INFO     [agent=client] running user setup ...
INFO     [agent=client] connecting 3 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=client] booted in 0.0009851455688476562 seconds ...
INFO     [agent=client] start processing sockets ...
INFO     [agent=client] sending: [b'1']
INFO     [agent=client] received: [b'1']
INFO     [agent=client] sending: [b'2']
INFO     [agent=client] received: [b'2']
INFO     [agent=client] sending: [b'3']
INFO     [agent=client] received: [b'3']
INFO     [agent=client] sending: [b'4']
INFO     [agent=client] received: [b'4']
INFO     [agent=client] sending: [b'5']
INFO     [agent=client] received: [b'5']
```