import os

from jinja2 import Environment, PackageLoader, select_autoescape
from utils import template

from agents import Agent, Message

env = Environment(
    loader=PackageLoader("chatserver"),
    autoescape=select_autoescape(),
    enable_async=True,
)


class ChatServer(Agent):
    def setup(self, host, port, ws_route):

        self.host = host
        self.port = port
        self.ws_route = ws_route
        self.create_webserver(host, port)
        self.create_route("GET", "/", self.home)

        # get websocket and connection pool
        self.rtx, self.websocket_connections = self.create_websocket(ws_route)
        self.disposables.append(self.rtx.subscribe(self.handle_websocket_message))

    def handle_websocket_message(self, msg):
        parsed = json.loads(msg.message.data)
        message_out = Message.Websocket(
            connection_id=self.user_to_connection[user_uid],
            message=message.as_websocket(),
            request=None,
        )
        self.log.debug(message_out)
        self.rtx.on_next(message_out)

    @template(env, "index.html")
    def home(self, request):
        return {"host": self.host, "port": self.port, "ws_route": self.ws_route}


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8080))
    ws_route = os.getenv("WS_ROUTE", "/ws")

    webserver = ChatServer(host, port, ws_route)
