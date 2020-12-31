# import asyncio

# from .powerful_agent import PowerfulAgent
# from aiohttp import web

# class VeryPowerfulAgent(PowerfulAgent):
    
#     def setup(self, *args, **kwargs):
#         super().setup(*args, **kwargs)
#         self.web = None


#     def start_http_server(self, *args, **kwargs):
#         self.web = web.Application(*args, **kwargs)

#     def add_http_route(self, route, handle):
#         app.add_routes([web.get('/', handle),
#                 web.get('/{name}', handle)])
        