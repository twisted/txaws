
"""
txaws/client/tests/test_ssl.py:9: 'ConnectionRefusedError' imported but unused
txaws/client/tests/test_ssl.py:13: 'Failure' imported but unused
txaws/client/tests/test_ssl.py:15: 'HTTPClientFactory' imported but unused
txaws/client/tests/test_ssl.py:16: 'TwistedWebError' imported but unused
txaws/client/tests/test_ssl.py:18: 'error_wrapper' imported but unused
txaws/client/tests/test_ssl.py:18: 'BaseClient' imported but unused
txaws/client/tests/test_ssl.py:19: 'VerifyingContextFactory' imported but
unused
"""

import os

from OpenSSL.crypto import load_certificate, FILETYPE_PEM
from OpenSSL.SSL import Error as SSLError
from OpenSSL.version import __version__ as pyopenssl_version

from twisted.internet import reactor
from twisted.internet.ssl import DefaultOpenSSLContextFactory
from twisted.protocols.policies import WrappingFactory
from twisted.python import log
from twisted.python.filepath import FilePath
from twisted.web import server, static

from txaws.client.base import BaseQuery
from txaws.service import AWSServiceEndpoint
from txaws.testing.base import TXAWSTestCase


def sibpath(path):
    return os.path.join(os.path.dirname(__file__), path)


PRIVKEY = sibpath("private.ssl")
PUBKEY = sibpath("public.ssl")
BADPRIVKEY = sibpath("badprivate.ssl")
BADPUBKEY = sibpath("badpublic.ssl")
PRIVSANKEY = sibpath("private_san.ssl")
PUBSANKEY = sibpath("public_san.ssl")


class BaseQuerySSLTestCase(TXAWSTestCase):

    def setUp(self):
        self.cleanupServerConnections = 0
        name = self.mktemp()
        os.mkdir(name)
        FilePath(name).child("file").setContent("0123456789")
        r = static.File(name)
        self.site = server.Site(r, timeout=None)
        self.wrapper = WrappingFactory(self.site)
        from txaws.client import ssl
        pub_key = file(PUBKEY)
        pub_key_data = pub_key.read()
        pub_key.close()
        pub_key_san = file(PUBSANKEY)
        pub_key_san_data = pub_key_san.read()
        pub_key_san.close()
        ssl._ca_certs = [load_certificate(FILETYPE_PEM, pub_key_data),
                         load_certificate(FILETYPE_PEM, pub_key_san_data)]

    def tearDown(self):
        from txaws.client import ssl
        ssl._ca_certs = None
        # If the test indicated it might leave some server-side connections
        # around, clean them up.
        connections = self.wrapper.protocols.keys()
        # If there are fewer server-side connections than requested,
        # that's okay.  Some might have noticed that the client closed
        # the connection and cleaned up after themselves.
        for n in range(min(len(connections), self.cleanupServerConnections)):
            proto = connections.pop()
            log.msg("Closing %r" % (proto,))
            proto.transport.loseConnection()
        if connections:
            log.msg("Some left-over connections; this test is probably buggy.")
        return self.port.stopListening()

    def _get_url(self, path):
        return "https://localhost:%d/%s" % (self.portno, path)

    def test_ssl_verification_positive(self):
        """
        The L{VerifyingContextFactory} properly allows to connect to the
        endpoint if the certificates match.
        """
        context_factory = DefaultOpenSSLContextFactory(PRIVKEY, PUBKEY)
        self.port = reactor.listenSSL(
            0, self.site, context_factory, interface="127.0.0.1")
        self.portno = self.port.getHost().port

        endpoint = AWSServiceEndpoint(ssl_hostname_verification=True)
        query = BaseQuery("an action", "creds", endpoint)
        d = query.get_page(self._get_url("file"))
        return d.addCallback(self.assertEquals, "0123456789")

    def test_ssl_verification_negative(self):
        """
        The L{VerifyingContextFactory} fails with a SSL error the certificates
        can't be checked.
        """
        context_factory = DefaultOpenSSLContextFactory(BADPRIVKEY, BADPUBKEY)
        self.port = reactor.listenSSL(
            0, self.site, context_factory, interface="127.0.0.1")
        self.portno = self.port.getHost().port

        endpoint = AWSServiceEndpoint(ssl_hostname_verification=True)
        query = BaseQuery("an action", "creds", endpoint)
        d = query.get_page(self._get_url("file"))
        return self.assertFailure(d, SSLError)

    def test_ssl_verification_bypassed(self):
        """
        L{BaseQuery} doesn't use L{VerifyingContextFactory}
        if C{ssl_hostname_verification} is C{False}, thus allowing to connect
        to non-secure endpoints.
        """
        context_factory = DefaultOpenSSLContextFactory(BADPRIVKEY, BADPUBKEY)
        self.port = reactor.listenSSL(
            0, self.site, context_factory, interface="127.0.0.1")
        self.portno = self.port.getHost().port

        endpoint = AWSServiceEndpoint(ssl_hostname_verification=False)
        query = BaseQuery("an action", "creds", endpoint)
        d = query.get_page(self._get_url("file"))
        return d.addCallback(self.assertEquals, "0123456789")

    def test_ssl_subject_alt_name(self):
        """
        L{VerifyingContextFactory} supports checking C{subjectAltName} in the
        certificate if it's available.
        """
        context_factory = DefaultOpenSSLContextFactory(PRIVSANKEY, PUBSANKEY)
        self.port = reactor.listenSSL(
            0, self.site, context_factory, interface="127.0.0.1")
        self.portno = self.port.getHost().port

        endpoint = AWSServiceEndpoint(ssl_hostname_verification=True)
        query = BaseQuery("an action", "creds", endpoint)
        d = query.get_page("https://127.0.0.1:%d/file" % (self.portno,))
        return d.addCallback(self.assertEquals, "0123456789")

    if pyopenssl_version < "0.12":
        test_ssl_subject_alt_name.skip = (
            "subjectAltName not supported by older PyOpenSSL")
