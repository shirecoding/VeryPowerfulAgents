from aiohttp.web import Response

from agents import Agent
from agents.modules.websocket import WebSocketModule


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
        # register websocket module
        self.ws = WebSocketModule(agent=self, routes=[("GET", "/", self.get_root)])
        self.register_module(self.ws)

        # get connections and rtx
        self.connections = self.ws.pool.connections
        self.rtx = self.ws.pool.rtx

        # subscribe to echo handler
        self.rtx.subscribe(self.handle_message)

    async def get_root(self, request):
        return Response(text="greetings!")

    def handle_message(self, uid, msg):
        self.log.debug(f"{uid}: {msg}")
        for _uid in self.connections:
            self.rtx.on_next((_uid, msg))


if __name__ == "__main__":
    webserver = WebSocketServer()
