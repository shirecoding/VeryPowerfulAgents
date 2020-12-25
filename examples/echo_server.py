import zmq
import time
import threading
from agents import Agent

class EchoServer(Agent):

    def setup(self, name=None, address=None):
        self.reply_socket = self.bind_socket(zmq.REP, {}, address)
        self.reply_socket['observable'].subscribe(self.echo)

    def echo(self, xs):
        self.reply_socket['socket'].send_multipart(xs)

class Client(Agent):
    
    def setup(self, name=None, address=None):
        self.request_socket = self.connect_socket(zmq.REQ, {}, address)
        self.counter = 0

        # receive
        self.request_socket['observable'].subscribe(lambda x: self.log.info(f"received: {x}"))

        # start sending
        t = threading.Thread(target=self.send)
        self.threads.append(t) # add to managed threads for graceful cleanup
        t.start()

    def send(self):
        while not self.exit_event.is_set(): # use exit event to gracefully exit loop
            time.sleep(1)
            self.counter += 1
            multipart_message = [str(self.counter).encode()]
            self.log.info(f"sending: {multipart_message}")
            self.request_socket['socket'].send_multipart(multipart_message)


if __name__ == '__main__':
    echo_server = EchoServer(name='server', address='tcp://0.0.0.0:5000')
    client = Client(name='client', address='tcp://0.0.0.0:5000')
