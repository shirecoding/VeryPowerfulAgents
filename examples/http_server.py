import time

from agents import VeryPowerfulAgent
from aiohttp import web

class HTTPServer(VeryPowerfulAgent):

    def setup(self, host, port):
        self.start_http_server(host, port, [
            ('GET', '/time', self.time)
        ])

    async def time(self, request):
        return web.json_response(time.time())

if __name__ == '__main__':
    HTTPServer('127.0.0.1', 8080)
    