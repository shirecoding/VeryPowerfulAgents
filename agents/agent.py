__all__ = ["Message", "Agent"]

import asyncio
import json
import logging
import os
import queue
import sys
import threading
import time
import traceback
import uuid
from signal import SIGINT, SIGTERM, signal

import zmq
from aiohttp import WSCloseCode, WSMsgType, web
from pyrsistent import pmap
from rx import operators as ops
from rx.subject import Subject
from rxpipes import observable_to_async_iterable
from zmq import auth
from zmq.auth import CURVE_ALLOW_ANY
from zmq.auth.thread import ThreadAuthenticator

from .utils import Logger, RxTxSubject, stdout_logger

log = stdout_logger(__name__, level=logging.DEBUG)


class Message:

    NOTIFICATION = 0
    CLIENT = 1

    @classmethod
    def notification(cls, topic="", payload=""):
        return [
            topic.encode(),
            bytes([cls.NOTIFICATION]),
            json.dumps({"topic": topic, "payload": payload}).encode(),
        ]

    @classmethod
    def client(cls, name="", payload=""):
        return [
            name.encode(),
            bytes([cls.CLIENT]),
            json.dumps({"payload": payload}).encode(),
        ]

    # Helper Methods

    @classmethod
    def decode(cls, multipart):
        """
        Parse zmq multipart buffer into message
        """

        v, t, payload = multipart
        t = int.from_bytes(t, byteorder="big")

        # notifications pattern
        if t == cls.NOTIFICATION:
            return json.loads(payload.decode())
        # router/client pattern
        if t == cls.CLIENT:
            return json.loads(payload.decode())
        else:
            return multipart


class Agent:
    def __init__(self, *args, name=None, **kwargs):

        # extract special kwargs
        if name:
            self.name = name
        else:
            self.name = uuid.uuid4().hex

        self.log = Logger(log, {"agent": self.name})
        self.initialized_event = threading.Event()
        self.exit_event = threading.Event()
        self.zmq_sockets = {}
        self.zmq_poller = zmq.Poller()
        self.threads = []
        self.disposables = []
        self.zap = None
        self.web_application = None

        # signals for graceful shutdown
        signal(SIGTERM, self._shutdown)
        signal(SIGINT, self._shutdown)

        # boot in thread
        t = threading.Thread(target=self.boot, args=args, kwargs=kwargs)
        self.threads.append(t)
        t.start()
        self.initialized_event.wait()

        # call initialized hook
        self.initialized()

    def boot(self, *args, **kwargs):
        try:
            start = time.time()
            self.log.info("booting up ...")
            self.zmq_context = zmq.Context()

            # user setup
            self.log.info("running user setup ...")
            self.setup(*args, **kwargs)

            # start webserver
            if self.web_application:
                self.log.info("starting webserver ...")

                async def _until_exit():
                    while not self.exit_event.is_set():
                        await asyncio.sleep(1)

                def _run_server_thread():
                    try:
                        loop = asyncio.new_event_loop()
                        runner = web.AppRunner(self.web_application)
                        asyncio.set_event_loop(loop)
                        self.web_application["loop"] = loop
                        loop.run_until_complete(runner.setup())
                        site = web.TCPSite(
                            runner,
                            self.web_application["host"],
                            self.web_application["port"],
                        )
                        loop.run_until_complete(site.start())
                        loop.run_until_complete(_until_exit())
                    finally:
                        loop.close()

                t = threading.Thread(target=_run_server_thread)
                self.threads.append(t)
                t.start()

            # process sockets
            t = threading.Thread(target=self.process_sockets)
            self.threads.append(t)
            t.start()

            self.initialized_event.set()
            self.log.info(f"booted in {time.time() - start} seconds ...")

        except Exception as e:
            self.log.error(f"failed to boot ...\n\n{traceback.format_exc()}")
            self.initialized_event.set()
            os.kill(os.getpid(), SIGINT)

    def shutdown(self):
        """
        Shutdown procedure, call super().shutdown() if overriding
        """

        # stop authenticator
        if self.zap:
            self.log.info("stopping ZMQ Authenticator ...")
            self.zap.stop()

        # dispose observables
        for d in self.disposables:
            self.log.info(f"disposing {d} ...")
            d.dispose()

        self.log.info("set exit event ...")
        self.exit_event.set()

        self.log.info("wait for initialization before cleaning up ...")
        self.initialized_event.wait()

        # join threads
        self.log.info("joining threads ...")
        for t in self.threads:
            self.log.info(f"joining {t}")
            t.join()
        self.log.info("joining threads complete ...")

        # destroy zmq sockets
        for k, v in self.zmq_sockets.items():
            self.log.info(f"closing socket {k} ...")
            v["socket"].close()
        self.zmq_context.term()

    def _shutdown(self, signum, frame):
        self.shutdown()

    ########################################################################################
    ## networking
    ########################################################################################

    def bind_socket(self, socket_type, options, address):
        self.log.info(f"binding {socket_type} socket on {address} ...")
        socket = self.zmq_context.socket(socket_type)
        for k, v in options.items():
            if type(v) == str:
                socket.setsockopt_string(k, v)
            else:
                socket.setsockopt(k, v)
        socket.bind(address)
        observable = Subject()
        socket_name = f"{socket_type}:{address}"
        send_queue = queue.Queue()
        self.zmq_sockets[socket_name] = pmap(
            {
                "socket": socket,
                "address": address,
                "type": socket_type,
                "options": options,
                "observable": observable,
                "send_queue": send_queue,
                "send": lambda x: send_queue.put(x),
            }
        )
        self.zmq_poller.register(socket, zmq.POLLIN)
        return self.zmq_sockets[socket_name]

    def connect_socket(self, socket_type, options, address):
        self.log.info(f"connecting {socket_type} socket to {address} ...")
        socket = self.zmq_context.socket(socket_type)
        for k, v in options.items():
            if type(v) == str:
                socket.setsockopt_string(k, v)
            else:
                socket.setsockopt(k, v)
        socket.connect(address)
        observable = Subject()
        socket_name = f"{socket_type}:{address}"
        send_queue = queue.Queue()
        self.zmq_sockets[socket_name] = pmap(
            {
                "socket": socket,
                "address": address,
                "type": socket_type,
                "options": options,
                "observable": observable,
                "send_queue": send_queue,
                "send": lambda x: send_queue.put(x),
            }
        )
        self.zmq_poller.register(socket, zmq.POLLIN)
        return self.zmq_sockets[socket_name]

    def process_sockets(self):

        # wait for initialization
        self.initialized_event.wait()
        self.log.info(
            f"start processing sockets in thread {threading.current_thread()} ..."
        )

        while not self.exit_event.is_set():
            if self.zmq_sockets:
                sockets = dict(self.zmq_poller.poll(50))
                for k, v in self.zmq_sockets.items():
                    # receive socket into observable
                    if v.socket in sockets and sockets[v.socket] == zmq.POLLIN:
                        v.observable.on_next(v.socket.recv_multipart())
                    # send queue to socket (zmq is not thread safe)
                    while not v.send_queue.empty() and not self.exit_event.is_set():
                        try:
                            v.socket.send_multipart(v.send_queue.get(block=False))
                        except queue.Empty:
                            pass
            else:
                time.sleep(1)

    ########################################################################################
    ## router/client pattern
    ########################################################################################

    def create_router(self, address, options=None):
        if options is None:
            options = {}
        router = self.bind_socket(zmq.ROUTER, options, address)

        def route(x):
            source, dest = x[0:2]
            router.send([dest, source] + x[2:])

        self.disposables.append(router.observable.subscribe(route))
        return router

    def create_client(self, address, options=None):
        if options is None:
            options = {}
        if zmq.IDENTITY not in options:
            options[zmq.IDENTITY] = self.name.encode("utf-8")
        dealer = self.connect_socket(zmq.DEALER, options, address)
        return dealer.update(
            {"observable": dealer.observable.pipe(ops.map(Message.decode))}
        )

    ########################################################################################
    ## notifications pattern
    ########################################################################################

    def create_notification_broker(self, pub_address, sub_address, options=None):
        """Starts a pub-sub notifications broker

        Args:
            pub_address (str): agents publish to this address to notify other agents
            sub_address (str): agents listen on this address for notifications

        Returns:
            connections (pub, sub)
        """
        if options is None:
            options = {}
        xpub = self.bind_socket(zmq.XPUB, options, sub_address)
        xsub = self.bind_socket(zmq.XSUB, options, pub_address)
        self.disposables.append(xsub.observable.subscribe(lambda x: xpub.send(x)))
        self.disposables.append(xpub.observable.subscribe(lambda x: xsub.send(x)))
        return xsub, xpub

    def create_notification_client(
        self, pub_address, sub_address, options=None, topics=""
    ):
        """Creates 2 connections (pub, sub) to a notifications broker

        Args:
            pub_address (str): publish to this address to notify other agents
            sub_address (str): listen on this address for notifications

        Returns:
            connections (pub, sub)
        """
        if options is None:
            options = {}
        pub = self.connect_socket(zmq.PUB, options, pub_address)
        sub = self.connect_socket(zmq.SUB, options, sub_address)
        sub.socket.subscribe(topics)
        return pub, sub.update(
            {"observable": sub.observable.pipe(ops.map(Message.decode))}
        )

    ########################################################################################
    ## webserver
    ########################################################################################

    def create_webserver(self, host, port):
        self.web_application = web.Application()
        self.web_application["host"] = host
        self.web_application["port"] = port
        self.web_application["websockets"] = set()
        self.web_application.on_shutdown.append(self.webserver_shutdown)
        return self.web_application

    async def webserver_shutdown(self, *args, **kwargs):
        self.log.debug("closing websockets ...")
        for ws in self.web_application["websockets"]:
            await ws.close(code=WSCloseCode.GOING_AWAY, message="Server shutdown")
        self.shutdown()

    #
    # routes
    #

    def create_route(self, method, route, handler):

        if not self.web_application:
            raise Exception("Requires web_application, run create_webserver first")

        self.web_application.add_routes([getattr(web, method.lower())(route, handler)])

    #
    # websockets
    #

    def create_websocket(self, route):

        if not self.web_application:
            raise Exception("Requires web_application, run create_webserver first")

        rtx = RxTxSubject()

        async def websocket_handler(request):

            ws = web.WebSocketResponse()
            await ws.prepare(request)
            self.web_application["websockets"].add(ws)
            ws_exit_event = threading.Event()
            self.log.debug("creating websocket connection ...")

            # ws -> rx
            async def rx_loop():
                while not any([self.exit_event.is_set(), ws_exit_event.is_set()]):
                    msg = await ws.receive()
                    if msg.type == WSMsgType.ERROR:
                        self.log(
                            "ws connection closed with exception %s" % ws.exception()
                        )
                        ws_exit_event.set()
                        break
                    else:
                        rtx._rx.on_next((request, msg))

            # tx -> ws
            async def tx_loop():
                xs = observable_to_async_iterable(rtx._tx, self.web_application["loop"])
                while not any([self.exit_event.is_set(), ws_exit_event.is_set()]):
                    try:
                        await ws.send_str(await xs.__anext__())
                    except Exception as e:
                        self.log.error(e)
                        ws_exit_event.set()
                        break

            try:
                await asyncio.gather(rx_loop(), tx_loop())

            finally:
                self.web_application["websockets"].discard(ws)

            return ws

        # register websocket route
        self.web_application.add_routes([web.get(route, websocket_handler)])

        return rtx

    ########################################################################################
    ## authentication
    ########################################################################################

    def curve_server_config(self, server_private_key):
        return {zmq.CURVE_SERVER: 1, zmq.CURVE_SECRETKEY: server_private_key}

    def curve_client_config(
        self, server_public_key, client_public_key, client_private_key
    ):
        return {
            zmq.CURVE_SERVERKEY: server_public_key,
            zmq.CURVE_PUBLICKEY: client_public_key,
            zmq.CURVE_SECRETKEY: client_private_key,
        }

    @classmethod
    def curve_keypair(cls):
        return zmq.curve_keypair()

    @classmethod
    def create_curve_certificates(cls, path, name, metadata=None):
        return auth.create_certificates(path, name, metadata=metadata)

    @classmethod
    def load_curve_certificate(cls, path):
        return auth.load_certificate(path)

    @classmethod
    def load_curve_certificates(cls, path):
        return auth.load_certificates(path)

    def start_authenticator(
        self, domain="*", whitelist=None, blacklist=None, certificates_path=None
    ):
        """Starts ZAP Authenticator in thread

        configure_curve must be called every time certificates are added or removed, in order to update the Authenticator’s state

        Args:
            certificates_path (str): path to client public keys to allow
            whitelist (list[str]): ip addresses to whitelist
            domain: (str): domain to apply authentication
        """
        certificates_path = certificates_path if certificates_path else CURVE_ALLOW_ANY
        self.zap = ThreadAuthenticator(self.zmq_context, log=self.log)
        self.zap.start()
        if whitelist is not None:
            self.zap.allow(*whitelist)
        elif blacklist is not None:
            self.zap.deny(*blacklist)
        else:
            self.zap.allow()
        self.zap.configure_curve(domain=domain, location=certificates_path)
        return self.zap

    ########################################################################################
    ## override
    ########################################################################################

    def setup(self):
        pass

    def initialized(self):
        pass
