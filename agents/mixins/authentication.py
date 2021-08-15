import zmq
from zmq import auth
from zmq.auth import CURVE_ALLOW_ANY
from zmq.auth.thread import ThreadAuthenticator


class AuthenticationMixin:
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
