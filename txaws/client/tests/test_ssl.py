import os
import tempfile

from OpenSSL.crypto import dump_certificate, load_certificate, FILETYPE_PEM
from OpenSSL.SSL import Error as SSLError
from OpenSSL.version import __version__ as pyopenssl_version

from twisted.internet import reactor
from twisted.internet.ssl import DefaultOpenSSLContextFactory
from twisted.protocols.policies import WrappingFactory
from twisted.python import log
from twisted.python.filepath import FilePath
from twisted.test.test_sslverify import makeCertificate
from twisted.web import server, static

try:
    from twisted.web.client import ResponseFailed
except ImportError:
    from twisted.web._newclient import ResponseFailed

from txaws import exception
from txaws.client import ssl
from txaws.client.base import BaseQuery
from txaws.service import AWSServiceEndpoint
from txaws.testing.base import TXAWSTestCase


def sibpath(path):
    return FilePath(__file__).sibling(path).path


PRIVKEY = sibpath("private.ssl")
PUBKEY = sibpath("public.ssl")
BADPRIVKEY = sibpath("badprivate.ssl")
BADPUBKEY = sibpath("badpublic.ssl")
PRIVSANKEY = sibpath("private_san.ssl")
PUBSANKEY = sibpath("public_san.ssl")


class WebDefaultOpenSSLContextFactory(DefaultOpenSSLContextFactory):
    def getContext(self, hostname=None, port=None):
        return DefaultOpenSSLContextFactory.getContext(self)


class BaseQuerySSLTestCase(TXAWSTestCase):

    def setUp(self):
        self.cleanupServerConnections = 0
        name = self.mktemp()
        os.mkdir(name)
        FilePath(name).child("file").setContent("0123456789")
        r = static.File(name)
        self.site = server.Site(r, timeout=None)
        self.wrapper = WrappingFactory(self.site)
        pub_key = file(PUBKEY)
        pub_key_data = pub_key.read()
        pub_key.close()
        pub_key_san = file(PUBSANKEY)
        pub_key_san_data = pub_key_san.read()
        pub_key_san.close()
        ssl._ca_certs = [load_certificate(FILETYPE_PEM, pub_key_data),
                         load_certificate(FILETYPE_PEM, pub_key_san_data)]

    def tearDown(self):
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
        context_factory = WebDefaultOpenSSLContextFactory(PRIVKEY, PUBKEY)
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
        context_factory = WebDefaultOpenSSLContextFactory(BADPRIVKEY, BADPUBKEY)
        self.port = reactor.listenSSL(
            0, self.site, context_factory, interface="127.0.0.1")
        self.portno = self.port.getHost().port

        endpoint = AWSServiceEndpoint(ssl_hostname_verification=True)
        query = BaseQuery("an action", "creds", endpoint)
        d = query.get_page(self._get_url("file"))
        def fail(ignore):
            self.fail('Expected SSLError')
        def check_exception(why):
            # XXX kind of a mess here ... need to unwrap the
            # exception and check
            root_exc = why.value[0][0].value
            self.assert_(isinstance(root_exc, SSLError))
        return d.addCallbacks(fail, check_exception)

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
        context_factory = WebDefaultOpenSSLContextFactory(PRIVSANKEY, PUBSANKEY)
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


class CertsFilesTestCase(TXAWSTestCase):

    def setUp(self):
        super(CertsFilesTestCase, self).setUp()
        # set up temp dir with no certs
        self.no_certs_dir = tempfile.mkdtemp()
        # create certs
        cert1 = makeCertificate(O="Server Certificate 1", CN="cn1")
        cert2 = makeCertificate(O="Server Certificate 2", CN="cn2")
        cert3 = makeCertificate(O="Server Certificate 3", CN="cn3")
        # set up temp dir with one cert
        self.one_cert_dir = tempfile.mkdtemp()
        self.cert1 = self._write_pem(cert1, self.one_cert_dir, "cert1.pem")
        # set up temp dir with two certs
        self.two_certs_dir = tempfile.mkdtemp()
        self.cert2 = self._write_pem(cert2, self.two_certs_dir, "cert2.pem")
        self.cert3 = self._write_pem(cert3, self.two_certs_dir, "cert3.pem")

    def tearDown(self):
        super(CertsFilesTestCase, self).tearDown()
        os.unlink(self.cert1)
        os.unlink(self.cert2)
        os.unlink(self.cert3)
        os.removedirs(self.no_certs_dir)
        os.removedirs(self.one_cert_dir)
        os.removedirs(self.two_certs_dir)

    def _write_pem(self, cert, dir, filename):
        data = dump_certificate(FILETYPE_PEM, cert[1])
        full_path = os.path.join(dir, filename)
        fh = open(full_path, "w")
        fh.write(data)
        fh.close()
        return full_path

    def test_get_ca_certs_no_certs(self):
        os.environ["TXAWS_CERTS_PATH"] = self.no_certs_dir
        self.patch(ssl, "DEFAULT_CERTS_PATH", self.no_certs_dir)
        self.assertRaises(exception.CertsNotFoundError, ssl.get_ca_certs)

    def test_get_ca_certs_with_default_path(self):
        self.patch(ssl, "DEFAULT_CERTS_PATH", self.two_certs_dir)
        certs = ssl.get_ca_certs()
        self.assertEqual(len(certs), 2)

    def test_get_ca_certs_with_env_path(self):
        os.environ["TXAWS_CERTS_PATH"] = self.one_cert_dir
        certs = ssl.get_ca_certs()
        self.assertEqual(len(certs), 1)

    def test_get_ca_certs_multiple_paths(self):
        os.environ["TXAWS_CERTS_PATH"] = "%s:%s" % (
            self.one_cert_dir, self.two_certs_dir)
        certs = ssl.get_ca_certs()
        self.assertEqual(len(certs), 3)

    def test_get_ca_certs_one_empty_path(self):
        os.environ["TXAWS_CERTS_PATH"] = "%s:%s" % (
            self.no_certs_dir, self.one_cert_dir)
        certs = ssl.get_ca_certs()
        self.assertEqual(len(certs), 1)

    def test_get_ca_certs_no_current_dir(self):
        """
        Do not include the current directory if the TXAWS_CERTS_PATH
        environment variable ends with a ":".
        """
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.one_cert_dir)
        os.environ["TXAWS_CERTS_PATH"] = "%s:" % self.no_certs_dir
        self.assertRaises(exception.CertsNotFoundError, ssl.get_ca_certs)
