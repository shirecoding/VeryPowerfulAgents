from agents import Agent
from agents.messaging.pool import ConnectionPool
from agents.modules.websocket import WebSocketModule
from agents.utils import RxTxSubject


class WebSocketServer(Agent):

    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>WebSocket Echo</title>
        </head>
        <body>
            <h1>WebSocket Echo</h1>
            <form action="" onsubmit="sendMessage(event)">
                <input type="text" id="messageText" autocomplete="off"/>
                <button>Send</button>
            </form>
            <ul id='messages'>
            </ul>
            <script>
                var ws = new WebSocket("ws://{}:{}{}");
                ws.onmessage = function(event) {{
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                }};
                function sendMessage(event) {{
                    var input = document.getElementById("messageText")
                    ws.send(input.value)
                    input.value = ''
                    event.preventDefault()
                }}
            </script>
        </body>
    </html>
    """

    def setup(self):
        self.connection_pool = ConnectionPool()
        self.rtx = RxTxSubject()
        self.register_module(
            WebSocketModule(
                agent=self,
                pool=self.connection_pool,
                rtx=self.rtx,
            )
        )
        self.rtx.subscribe(self.handle_message)

    def handle_message(self, msg):
        self.log.debug(msg)
        for uid in self.connection_pool.connections:
            self.rtx.on_next((uid, msg))


if __name__ == "__main__":
    webserver = WebSocketServer()
