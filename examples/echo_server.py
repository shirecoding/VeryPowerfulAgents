import zmq
import time
import threading
from agents import Agent

class EchoServer(Agent):
    
    def setup(self):
        self.reply_socket = self.bind_socket(zmq.REP, {}, "tcp://0.0.0.0:5000")
        self.reply_socket['observable'].subscribe(self.echo)

    def echo(self, xs):
        self.reply_socket['socket'].send_multipart(xs)

class Client(Agent):
    
    def setup(self):
        self.request_socket = self.connect_socket(zmq.REQ, {}, "tcp://0.0.0.0:5000")
        self.counter = 0

        # receive
        self.request_socket['observable'].subscribe(lambda x: self.log.info(f"received: {x}"))

        # start sending
        threading.Thread(target=self.send).start()

    def send(self):
        while not self.exit_event.is_set():
            time.sleep(1)
            self.counter += 1
            multipart_message = [str(self.counter).encode()]
            self.log.info(f"sending: {multipart_message}")
            self.request_socket['socket'].send_multipart(multipart_message)


if __name__ == '__main__':
    echo_server = EchoServer(name='server')
    client = Client(name='client')
