import os

from twisted.internet import reactor
from twisted.internet.error import ConnectionRefusedError
from twisted.protocols.policies import WrappingFactory
from twisted.python import log
from twisted.python.filepath import FilePath
from twisted.python.failure import Failure
from twisted.web import server, static
from twisted.web.client import HTTPClientFactory
from twisted.web.error import Error as TwistedWebError

from txaws.client.base import BaseClient, BaseQuery, error_wrapper
from txaws.testing.base import TXAWSTestCase


class ErrorWrapperTestCase(TXAWSTestCase):

    def test_204_no_content(self):
        failure = Failure(TwistedWebError(204, "No content"))
        wrapped = error_wrapper(failure, None)
        self.assertEquals(wrapped, "204 No content")

    def test_302_found(self):
        # XXX I'm not sure we want to raise for 300s...
        failure = Failure(TwistedWebError(302, "found"))
        error = self.assertRaises(
            Exception, error_wrapper, failure, None)
        self.assertEquals(failure.type, type(error))
        self.assertTrue(isinstance(error, TwistedWebError))
        self.assertEquals(str(error), "302 found")

    def test_500(self):
        failure = Failure(TwistedWebError(500, "internal error"))
        error = self.assertRaises(
            Exception, error_wrapper, failure, None)
        self.assertTrue(isinstance(error, TwistedWebError))
        self.assertEquals(str(error), "500 internal error")

    def test_timeout_error(self):
        failure = Failure(Exception("timeout"))
        error = self.assertRaises(Exception, error_wrapper, failure, None)
        self.assertTrue(isinstance(error, Exception))
        self.assertEquals(str(error), "timeout")

    def test_connection_error(self):
        failure = Failure(ConnectionRefusedError("timeout"))
        error = self.assertRaises(
            Exception, error_wrapper, failure, ConnectionRefusedError)
        self.assertTrue(isinstance(error, ConnectionRefusedError))


class BaseClientTestCase(TXAWSTestCase):

    def test_creation(self):
        client = BaseClient("creds", "endpoint", "query factory", "parser")
        self.assertEquals(client.creds, "creds")
        self.assertEquals(client.endpoint, "endpoint")
        self.assertEquals(client.query_factory, "query factory")
        self.assertEquals(client.parser, "parser")


class BaseQueryTestCase(TXAWSTestCase):

    def setUp(self):
        self.cleanupServerConnections = 0
        name = self.mktemp()
        os.mkdir(name)
        FilePath(name).child("file").setContent("0123456789")
        r = static.File(name)
        self.site = server.Site(r, timeout=None)
        self.wrapper = WrappingFactory(self.site)
        self.port = self._listen(self.wrapper)
        self.portno = self.port.getHost().port

    def tearDown(self):
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

    def _listen(self, site):
        return reactor.listenTCP(0, site, interface="127.0.0.1")

    def _get_url(self, path):
        return "http://127.0.0.1:%d/%s" % (self.portno, path)

    def test_creation(self):
        query = BaseQuery("an action", "creds", "http://endpoint")
        self.assertEquals(query.factory, HTTPClientFactory)
        self.assertEquals(query.action, "an action")
        self.assertEquals(query.creds, "creds")
        self.assertEquals(query.endpoint, "http://endpoint")

    def test_init_requires_action(self):
        self.assertRaises(TypeError, BaseQuery)

    def test_init_requires_creds(self):
        self.assertRaises(TypeError, BaseQuery, None)

    def test_get_page(self):
        query = BaseQuery("an action", "creds", "http://endpoint")
        d = query.get_page(self._get_url("file"))
        d.addCallback(self.assertEquals, "0123456789")
        return d

    def test_get_request_headers_no_client(self):

        query = BaseQuery("an action", "creds", "http://endpoint")
        results = query.get_request_headers()
        self.assertEquals(results, None)

    def test_get_request_headers_with_client(self):

        def check_results(results):
            self.assertEquals(results.keys(), [])
            self.assertEquals(results.values(), [])

        query = BaseQuery("an action", "creds", "http://endpoint")
        d = query.get_page(self._get_url("file"))
        d.addCallback(query.get_request_headers)
        return d.addCallback(check_results)

    def test_get_response_headers_no_client(self):

        query = BaseQuery("an action", "creds", "http://endpoint")
        results = query.get_response_headers()
        self.assertEquals(results, None)

    def test_get_response_headers_with_client(self):

        def check_results(results):
            self.assertEquals(sorted(results.keys()), [
                "accept-ranges", "content-length", "content-type", "date",
                "last-modified", "server"])
            self.assertEquals(len(results.values()), 6)

        query = BaseQuery("an action", "creds", "http://endpoint")
        d = query.get_page(self._get_url("file"))
        d.addCallback(query.get_response_headers)
        return d.addCallback(check_results)
