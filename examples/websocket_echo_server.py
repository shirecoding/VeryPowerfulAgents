from aiohttp import WSCloseCode, WSMsgType, web
from rxpipes import Pipeline

from agents import Agent


class WebServer(Agent):

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

    def setup(self, host, port, route):

        self.host = host
        self.port = port
        self.route = route
        self.create_webserver(host, port)
        self.create_route("GET", "/", self.echo)
        self.rx, self.tx = self.create_websocket(route)
        self.disposables.append(
            self.rx.subscribe(lambda xs: self.tx.on_next(xs[1].data))
        )

    async def echo(self, request):
        return web.Response(
            text=self.html.format(self.host, self.port, self.route),
            content_type="text/html",
        )


if __name__ == "__main__":
    webserver = WebServer("127.0.0.1", 8080, "/ws")
