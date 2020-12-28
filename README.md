# VeryPowerfulAgents

Agents are lightweight microservices with built-in interprocess communications infrastructure using ZeroMQ.

## Features

#### Agents

- Graceful boot & shutdown with resource cleanup done correctly
- User setup/shutdown override methods for graceful boot & shutdown
- ZeroMQ communications is done in a thread safe manner using queues (ZeroMQ is not threadsafe)
- Socket data is received through Observables using RxPy
- Nicely formatted logs using self.log

#### Powerful Agents

- Pub/sub notification facilities
- Router/client facilities
- Simple Messaging protocol for standard facilities (notifications, client, etc ..)
- End-to-end encryption support using ECC, RSA, AES (TODO)
- Production ready communication architectures, lazy pirate, etc... (TODO)
- Mesh networks (TODO)
- ... (TODO)

#### Very Powerful Agents

- REST server routes (TODO)
- RPC endpoints (TODO)
- File sharing (TODO)
- ... (TODO)

```bash
# install from git
git clone https://github.com/shirecoding/VeryPowerfulAgents.git
cd VeryPowerfulAgents
pip3 install ./

# install from pypi
pip install powerful-agents
```

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

## Pub/sub notifications

```python
import zmq
import time
import threading
from agents import PowerfulAgent, Message

class NotificationBroker(PowerfulAgent):

    def setup(self, name=None, pub_address=None, sub_address=None):
        self.create_notification_broker(pub_address, sub_address)

class Sender(PowerfulAgent):
    
    def setup(self, name=None, pub_address=None, sub_address=None):
        self.counter = 0
        self.pub, self.sub = self.create_notification_client(pub_address, sub_address)

        # begin sending forever, add to managed threads for graceful cleanup
        t = threading.Thread(target=self.send_forever)
        self.threads.append(t)
        t.start()

    def send_forever(self):
        # use exit event to gracefully exit loop and graceful cleanup
        while not self.exit_event.is_set(): 
            time.sleep(1)
            self.counter += 1
            self.log.info(f"publishing: {self.counter}")
            self.pub.send(Message.notification(payload=self.counter))

class Listener(PowerfulAgent):
    
    def setup(self, name=None, pub_address=None, sub_address=None):
        self.pub, self.sub = self.create_notification_client(pub_address, sub_address)
        self.sub.observable.subscribe(lambda x: self.log.info(f"received: { Message.decode(x) }"))

if __name__ == '__main__':
    broker = NotificationBroker(name='broker', pub_address='tcp://0.0.0.0:5000', sub_address='tcp://0.0.0.0:5001')
    sender = Sender(name='sender', pub_address='tcp://0.0.0.0:5000', sub_address='tcp://0.0.0.0:5001')
    listener = Listener(name='listener', pub_address='tcp://0.0.0.0:5000', sub_address='tcp://0.0.0.0:5001')
```

```bash
INFO     [agent=broker] booting up ...
INFO     [agent=broker] running user setup ...
INFO     [agent=broker] binding 9 socket on tcp://0.0.0.0:5001 ...
INFO     [agent=broker] binding 10 socket on tcp://0.0.0.0:5000 ...
INFO     [agent=broker] booted in 0.0032880306243896484 seconds ...
INFO     [agent=broker] start processing sockets ...
INFO     [agent=sender] booting up ...
INFO     [agent=sender] running user setup ...
INFO     [agent=sender] connecting 1 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=sender] connecting 2 socket to tcp://0.0.0.0:5001 ...
INFO     [agent=sender] booted in 0.0016701221466064453 seconds ...
INFO     [agent=sender] start processing sockets ...
INFO     [agent=listener] booting up ...
INFO     [agent=listener] running user setup ...
INFO     [agent=listener] connecting 1 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=listener] connecting 2 socket to tcp://0.0.0.0:5001 ...
INFO     [agent=listener] booted in 0.0013346672058105469 seconds ...
INFO     [agent=listener] start processing sockets ...
INFO     [agent=sender] publishing: 1
INFO     [agent=listener] received: 1
INFO     [agent=sender] publishing: 2
INFO     [agent=listener] received: 2
INFO     [agent=sender] publishing: 3
INFO     [agent=listener] received: 3
INFO     [agent=sender] publishing: 4
INFO     [agent=listener] received: 4
INFO     [agent=sender] publishing: 5
INFO     [agent=listener] received: 5
```

## Router Client

```python
import zmq
import time
import threading
from agents import PowerfulAgent

class Router(PowerfulAgent):

    def setup(self, name=None, address=None):
        self.create_router(address)

class Client1(PowerfulAgent):
    
    def setup(self, name=None, address=None):
        self.counter = 0
        self.client = self.create_client(address)

        # begin sending forever, add to managed threads for graceful cleanup
        t = threading.Thread(target=self.send_forever)
        self.threads.append(t)
        t.start()

    def send_forever(self):
        # use exit event to gracefully exit loop and graceful cleanup
        while not self.exit_event.is_set(): 
            time.sleep(1)
            self.counter += 1
            target = 'client2'.encode('utf-8')
            multipart_message = [ target, str(self.counter).encode() ]
            self.log.info(f"send to {target}: {multipart_message}")
            self.client.send(multipart_message)

class Client2(PowerfulAgent):
    
    def setup(self, name=None, address=None):
        self.client = self.create_client(address)
        self.client.observable.subscribe(lambda x: self.log.info(f"received: {x}"))

if __name__ == '__main__':
    router = Router(name='router', address='tcp://0.0.0.0:5000')
    client1 = Client1(name='client1', address='tcp://0.0.0.0:5000')
    client2 = Client2(name='client2', address='tcp://0.0.0.0:5000')
```

```bash
INFO     [agent=router] booting up ...
INFO     [agent=router] running user setup ...
INFO     [agent=router] binding 6 socket on tcp://0.0.0.0:5000 ...
INFO     [agent=router] booted in 0.0016148090362548828 seconds ...
INFO     [agent=router] start processing sockets ...
INFO     [agent=client1] booting up ...
INFO     [agent=client1] running user setup ...
INFO     [agent=client1] connecting 5 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=client1] booted in 0.0007421970367431641 seconds ...
INFO     [agent=client1] start processing sockets ...
INFO     [agent=client2] booting up ...
INFO     [agent=client2] running user setup ...
INFO     [agent=client2] connecting 5 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=client2] booted in 0.0007507801055908203 seconds ...
INFO     [agent=client2] start processing sockets ...
INFO     [agent=client1] send to b'client2': [b'client2', b'1']
INFO     [agent=client2] received: [b'client1', b'1']
INFO     [agent=client1] send to b'client2': [b'client2', b'2']
INFO     [agent=client2] received: [b'client1', b'2']
INFO     [agent=client1] send to b'client2': [b'client2', b'3']
INFO     [agent=client2] received: [b'client1', b'3']
INFO     [agent=client1] send to b'client2': [b'client2', b'4']
INFO     [agent=client2] received: [b'client1', b'4']
INFO     [agent=client1] send to b'client2': [b'client2', b'5']
INFO     [agent=client2] received: [b'client1', b'5']
```