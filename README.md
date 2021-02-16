[![Documentation Status](https://readthedocs.org/projects/verypowerfulagents/badge/?version=latest)](https://verypowerfulagents.readthedocs.io/en/latest/?badge=latest)

# VeryPowerfulAgents

Agents are lightweight microservices with built-in interprocess communications infrastructure using ZeroMQ

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
- Elliptical curve encryption and authentication
- Production ready communication architectures
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
        self.sub.observable.subscribe(lambda x: self.log.info(f"received: { x['payload'] }"))

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
from agents import PowerfulAgent, Message

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
            target = 'client2'
            self.log.info(f"send to {target}: {self.counter}")
            self.client.send(Message.client(name=target, payload=self.counter))

class Client2(PowerfulAgent):
    
    def setup(self, name=None, address=None):
        self.client = self.create_client(address)
        self.client.observable.subscribe(lambda x: self.log.info(f"received: {x['payload']}"))

if __name__ == '__main__':
    router = Router(name='router', address='tcp://0.0.0.0:5000')
    client1 = Client1(name='client1', address='tcp://0.0.0.0:5000')
    client2 = Client2(name='client2', address='tcp://0.0.0.0:5000')
```

```bash
INFO     [agent=router] booting up ...
INFO     [agent=router] running user setup ...
INFO     [agent=router] binding 6 socket on tcp://0.0.0.0:5000 ...
INFO     [agent=router] booted in 0.0019252300262451172 seconds ...
INFO     [agent=router] start processing sockets ...
INFO     [agent=client1] booting up ...
INFO     [agent=client1] running user setup ...
INFO     [agent=client1] connecting 5 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=client1] booted in 0.0019159317016601562 seconds ...
INFO     [agent=client1] start processing sockets ...
INFO     [agent=client2] booting up ...
INFO     [agent=client2] running user setup ...
INFO     [agent=client2] connecting 5 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=client2] booted in 0.0008869171142578125 seconds ...
INFO     [agent=client2] start processing sockets ...
INFO     [agent=client1] send to client2: 1
INFO     [agent=client2] received: 1
INFO     [agent=client1] send to client2: 2
INFO     [agent=client2] received: 2
INFO     [agent=client1] send to client2: 3
INFO     [agent=client2] received: 3
INFO     [agent=client1] send to client2: 4
INFO     [agent=client2] received: 4
INFO     [agent=client1] send to client2: 5
INFO     [agent=client2] received: 5
```

## Elliptical Curve Encryption

This example allows any client with the server's public key to connect and communicate over a secure channel

```python
import zmq
import time
import threading
from agents import Agent, PowerfulAgent, Message

# generate public and private keys for server and client
server_public_key, server_private_key = Agent.curve_keypair()
wrong_server_public_key, wrong_server_private_key = Agent.curve_keypair()
client_public_key, client_private_key = Agent.curve_keypair()
client2_public_key, client2_private_key = Agent.curve_keypair()

class NotificationBroker(PowerfulAgent):

    def setup(self, name=None, pub_address=None, sub_address=None):
        self.create_notification_broker(pub_address, sub_address, options=self.curve_server_config(server_private_key))

class Sender(PowerfulAgent):
    
    def setup(self, name=None, pub_address=None, sub_address=None):
        self.counter = 0
        self.pub, self.sub = self.create_notification_client(
            pub_address,
            sub_address,
            options=self.curve_client_config(server_public_key, client_public_key, client_private_key)
        )

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
        self.pub, self.sub = self.create_notification_client(
            pub_address,
            sub_address,
            options=self.curve_client_config(server_public_key, client_public_key, client_private_key)
        )
        self.sub.observable.subscribe(lambda x: self.log.info(f"received: { x['payload'] }"))

class ListenerInvalid(PowerfulAgent):
    
    def setup(self, name=None, pub_address=None, sub_address=None):
        self.pub, self.sub = self.create_notification_client(
            pub_address,
            sub_address,
            options=self.curve_client_config(wrong_server_public_key, client2_public_key, client2_private_key)
        )
        self.sub.observable.subscribe(lambda x: self.log.info(f"received: { x['payload'] }"))

if __name__ == '__main__':
    broker = NotificationBroker(name='broker', pub_address='tcp://0.0.0.0:5000', sub_address='tcp://0.0.0.0:5001')
    sender = Sender(name='sender', pub_address='tcp://0.0.0.0:5000', sub_address='tcp://0.0.0.0:5001')
    listener = Listener(name='listener', pub_address='tcp://0.0.0.0:5000', sub_address='tcp://0.0.0.0:5001')
    listener_invalid = ListenerInvalid(name='listener_invalid', pub_address='tcp://0.0.0.0:5000', sub_address='tcp://0.0.0.0:5001')

```

```bash
INFO     [agent=broker] booting up ...
INFO     [agent=broker] running user setup ...
INFO     [agent=broker] binding 9 socket on tcp://0.0.0.0:5001 ...
INFO     [agent=broker] binding 10 socket on tcp://0.0.0.0:5000 ...
INFO     [agent=broker] booted in 0.0027320384979248047 seconds ...
INFO     [agent=broker] start processing sockets ...
INFO     [agent=sender] booting up ...
INFO     [agent=sender] running user setup ...
INFO     [agent=sender] connecting 1 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=sender] connecting 2 socket to tcp://0.0.0.0:5001 ...
INFO     [agent=sender] booted in 0.0042607784271240234 seconds ...
INFO     [agent=sender] start processing sockets ...
INFO     [agent=listener] booting up ...
INFO     [agent=listener] running user setup ...
INFO     [agent=listener] connecting 1 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=listener] connecting 2 socket to tcp://0.0.0.0:5001 ...
INFO     [agent=listener] booted in 0.0016052722930908203 seconds ...
INFO     [agent=listener] start processing sockets ...
INFO     [agent=listener_invalid] booting up ...
INFO     [agent=listener_invalid] running user setup ...
INFO     [agent=listener_invalid] connecting 1 socket to tcp://0.0.0.0:5000 ...
INFO     [agent=listener_invalid] connecting 2 socket to tcp://0.0.0.0:5001 ...
INFO     [agent=listener_invalid] booted in 0.0014069080352783203 seconds ...
INFO     [agent=listener_invalid] start processing sockets ...
INFO     [agent=sender] publishing: 1
INFO     [agent=listener] received: 1
INFO     [agent=sender] publishing: 2
INFO     [agent=listener] received: 2
INFO     [agent=sender] publishing: 3
INFO     [agent=listener] received: 3
```

## Full Authentication

This example adds another layer of protection for the server by allowing only trusted clients to connect.

```python
import os
import zmq
import time
import threading
import tempfile
from agents import Agent, PowerfulAgent, Message

class NotificationBroker(PowerfulAgent):

    def setup(self, name=None, pub_address=None, sub_address=None, private_key=None, client_certificates_path=None):
        
        # configure public key auth/encryption if private_key is provided
        options = self.curve_server_config(private_key) if private_key else {}
        self.create_notification_broker(pub_address, sub_address, options=options)
        
        # start authenticator if client_certificates_path is provided
        if client_certificates_path:
            self.auth = self.start_authenticator(domain='*', certificates_path=client_certificates_path)
        
class Sender(PowerfulAgent):
    
    def setup(self, name=None, pub_address=None, sub_address=None, private_key=None, public_key=None, server_public_key=None):
        # configure public key auth/encryption if keys are provided
        if private_key and public_key and server_public_key:
            options = self.curve_client_config(server_public_key, public_key, private_key)
        else:
            options = {}
        self.counter = 0
        self.pub, self.sub = self.create_notification_client(pub_address, sub_address, options=options)

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
    
    def setup(self, name=None, pub_address=None, sub_address=None, private_key=None, public_key=None, server_public_key=None):
        # configure public key auth/encryption if keys are provided
        if private_key and public_key and server_public_key:
            options = self.curve_client_config(server_public_key, public_key, private_key)
        else:
            options = {}
        self.pub, self.sub = self.create_notification_client(pub_address, sub_address, options=options)
        self.sub.observable.subscribe(lambda x: self.log.info(f"received: { x['payload'] }"))


if __name__ == '__main__':

    with tempfile.TemporaryDirectory() as trusted_keys_path, \
    tempfile.TemporaryDirectory() as untrusted_keys_path:

        # create key pairs in corresponding directories
        Agent.create_curve_certificates(trusted_keys_path, 'server')
        Agent.create_curve_certificates(trusted_keys_path, 'listener')
        Agent.create_curve_certificates(untrusted_keys_path, 'listener2')

        # load key pairs
        server_public_key, server_private_key = Agent.load_curve_certificate(os.path.join(trusted_keys_path, "server.key_secret"))
        listener_public_key, listener_private_key = Agent.load_curve_certificate(os.path.join(trusted_keys_path, "listener.key_secret"))
        listener2_public_key, listener2_private_key = Agent.load_curve_certificate(os.path.join(untrusted_keys_path, "listener2.key_secret"))

        broker = NotificationBroker(
            name='broker',
            pub_address='tcp://127.0.0.1:5000',
            sub_address='tcp://127.0.0.1:5001',
            private_key=server_private_key,
            client_certificates_path=trusted_keys_path
        )
        sender = Sender(
            name='sender',
            pub_address='tcp://127.0.0.1:5000',
            sub_address='tcp://127.0.0.1:5001',
            private_key=server_private_key,
            public_key=server_public_key,
            server_public_key=server_public_key
        )
        listener = Listener(
            name='listener',
            pub_address='tcp://127.0.0.1:5000',
            sub_address='tcp://127.0.0.1:5001',
            private_key=listener_private_key,
            public_key=listener_public_key,
            server_public_key=server_public_key
        )
        listener2 = Listener(
            name='listener2',
            pub_address='tcp://127.0.0.1:5000',
            sub_address='tcp://127.0.0.1:5001',
            private_key=listener2_private_key,
            public_key=listener2_public_key,
            server_public_key=server_public_key
        )
```

```bash
INFO     [agent=broker] booting up ...
INFO     [agent=broker] running user setup ...
INFO     [agent=broker] binding 9 socket on tcp://127.0.0.1:5001 ...
INFO     [agent=broker] binding 10 socket on tcp://127.0.0.1:5000 ...
INFO     [agent=broker] trusted clients: {b'LJl(is$S!/A[3uj]lx}GosmI^28J+3TrR#N5L*C3': True, b'xHVFw-cZptp-.U=rMK)OdTM*p5iwnxX.6HEZWt9v': True}
DEBUG    [agent=broker] Starting
INFO     [agent=broker] authenticator started ...
DEBUG    [agent=broker] auth received API command b'ALLOW'
DEBUG    [agent=broker] Allowing 
DEBUG    [agent=broker] auth received API command b'CURVE'
DEBUG    [agent=broker] Configure curve: *[/var/folders/v2/9dzql1f509n1rqnlgrxs9_180000gn/T/tmp6f67aogg]
INFO     [agent=broker] booted in 0.006651878356933594 seconds ...
INFO     [agent=broker] start processing sockets ...
INFO     [agent=sender] booting up ...
INFO     [agent=sender] running user setup ...
INFO     [agent=sender] connecting 1 socket to tcp://127.0.0.1:5000 ...
INFO     [agent=sender] connecting 2 socket to tcp://127.0.0.1:5001 ...
INFO     [agent=sender] booted in 0.003384113311767578 seconds ...
INFO     [agent=sender] start processing sockets ...
INFO     [agent=listener] booting up ...
INFO     [agent=listener] running user setup ...
INFO     [agent=listener] connecting 1 socket to tcp://127.0.0.1:5000 ...
INFO     [agent=listener] connecting 2 socket to tcp://127.0.0.1:5001 ...
INFO     [agent=listener] booted in 0.001445770263671875 seconds ...
INFO     [agent=listener] start processing sockets ...
INFO     [agent=listener2] booting up ...
INFO     [agent=listener2] running user setup ...
INFO     [agent=listener2] connecting 1 socket to tcp://127.0.0.1:5000 ...
INFO     [agent=listener2] connecting 2 socket to tcp://127.0.0.1:5001 ...
INFO     [agent=listener2] booted in 0.0016427040100097656 seconds ...
INFO     [agent=listener2] start processing sockets ...
DEBUG    [agent=broker] version: b'1.0', request_id: b'1', domain: '', address: '127.0.0.1', identity: b'', mechanism: b'CURVE'
DEBUG    [agent=broker] ALLOWED (CURVE) domain=* client_key=b'LJl(is$S!/A[3uj]lx}GosmI^28J+3TrR#N5L*C3'
DEBUG    [agent=broker] ZAP reply code=b'200' text=b'OK'
DEBUG    [agent=broker] version: b'1.0', request_id: b'1', domain: '', address: '127.0.0.1', identity: b'', mechanism: b'CURVE'
DEBUG    [agent=broker] ALLOWED (CURVE) domain=* client_key=b'LJl(is$S!/A[3uj]lx}GosmI^28J+3TrR#N5L*C3'
DEBUG    [agent=broker] ZAP reply code=b'200' text=b'OK'
DEBUG    [agent=broker] version: b'1.0', request_id: b'1', domain: '', address: '127.0.0.1', identity: b'', mechanism: b'CURVE'
DEBUG    [agent=broker] ALLOWED (CURVE) domain=* client_key=b'xHVFw-cZptp-.U=rMK)OdTM*p5iwnxX.6HEZWt9v'
DEBUG    [agent=broker] ZAP reply code=b'200' text=b'OK'
DEBUG    [agent=broker] version: b'1.0', request_id: b'1', domain: '', address: '127.0.0.1', identity: b'', mechanism: b'CURVE'
DEBUG    [agent=broker] DENIED (CURVE) domain=* client_key=b're69C5>LWfw%//*Qc^6Ei]>ntoYZCc6E]rZXA=F9'
DEBUG    [agent=broker] ZAP reply code=b'400' text=b'Unknown key'
DEBUG    [agent=broker] version: b'1.0', request_id: b'1', domain: '', address: '127.0.0.1', identity: b'', mechanism: b'CURVE'
DEBUG    [agent=broker] ALLOWED (CURVE) domain=* client_key=b'xHVFw-cZptp-.U=rMK)OdTM*p5iwnxX.6HEZWt9v'
DEBUG    [agent=broker] ZAP reply code=b'200' text=b'OK'
DEBUG    [agent=broker] version: b'1.0', request_id: b'1', domain: '', address: '127.0.0.1', identity: b'', mechanism: b'CURVE'
DEBUG    [agent=broker] DENIED (CURVE) domain=* client_key=b're69C5>LWfw%//*Qc^6Ei]>ntoYZCc6E]rZXA=F9'
DEBUG    [agent=broker] ZAP reply code=b'400' text=b'Unknown key'
INFO     [agent=sender] publishing: 1
INFO     [agent=listener] received: 1
INFO     [agent=sender] publishing: 2
INFO     [agent=listener] received: 2
```
