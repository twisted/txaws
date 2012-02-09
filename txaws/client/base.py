try:
    from xml.etree.ElementTree import ParseError
except ImportError:
    from xml.parsers.expat import ExpatError as ParseError

from StringIO import StringIO

from twisted.internet.ssl import ClientContextFactory
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred, succeed
from twisted.python import failure
from twisted.web import http
from twisted.web.iweb import UNKNOWN_LENGTH
from twisted.web.client import HTTPClientFactory
from twisted.web.client import Agent, FileBodyProducer
from twisted.web.client import ResponseDone
from twisted.web.http_headers import Headers
from twisted.web.error import Error as TwistedWebError

from txaws.util import parse
from txaws.credentials import AWSCredentials
from txaws.exception import AWSResponseParseError
from txaws.service import AWSServiceEndpoint
from txaws.client.ssl import VerifyingContextFactory


def error_wrapper(error, errorClass):
    """
    We want to see all error messages from cloud services. Amazon's EC2 says
    that their errors are accompanied either by a 400-series or 500-series HTTP
    response code. As such, the first thing we want to do is check to see if
    the error is in that range. If it is, we then need to see if the error
    message is an EC2 one.

    In the event that an error is not a Twisted web error nor an EC2 one, the
    original exception is raised.
    """
    http_status = 0
    if error.check(TwistedWebError):
        xml_payload = error.value.response
        if error.value.status:
            http_status = int(error.value.status)
    else:
        error.raiseException()
    if http_status >= 400:
        if not xml_payload:
            error.raiseException()
        try:
            fallback_error = errorClass(
                xml_payload, error.value.status, str(error.value),
                error.value.response)
        except (ParseError, AWSResponseParseError):
            error_message = http.RESPONSES.get(http_status)
            fallback_error = TwistedWebError(
                http_status, error_message, error.value.response)
        raise fallback_error
    elif 200 <= http_status < 300:
        return str(error.value)
    else:
        error.raiseException()


class BaseClient(object):
    """Create an AWS client.

    @param creds: User authentication credentials to use.
    @param endpoint: The service endpoint URI.
    @param query_factory: The class or function that produces a query
        object for making requests to the EC2 service.
    @param parser: A parser object for parsing responses from the EC2 service.
    """
    def __init__(self, creds=None, endpoint=None, query_factory=None,
                 parser=None):
        if creds is None:
            creds = AWSCredentials()
        if endpoint is None:
            endpoint = AWSServiceEndpoint()
        self.creds = creds
        self.endpoint = endpoint
        self.query_factory = query_factory
        self.parser = parser

class StreamingError(Exception):
    """
    Raised if more data or less data is received than expected.
    """

class StringIOBodyReceiver(Protocol):
    """
    Simple StringIO-based HTTP response body receiver.
    """
    finished = None
    content_length = None

    def __init__(self):
        self._buffer = StringIO()
        self._received = 0

    def dataReceived(self, bytes):
        streaming = self.content_length is UNKNOWN_LENGTH
        if not streaming and (self._received > self.content_length):
            self.transport.loseConnection()
            raise StreamingError(
                "Buffer overflow - received more data than "
                "Content-Length dictated: %d" % self.content_length)
        # TODO should be some limit on how much we receive
        self._buffer.write(bytes)
        self._received += len(bytes)

    def connectionLost(self, reason):
        reason.trap(ResponseDone)
        d = self.finished
        self.finished = None
        streaming = self.content_length is UNKNOWN_LENGTH
        if streaming or (self._received == self.content_length):
            d.callback(self._buffer.getvalue())
        else:
            f = failure.Failure(StreamingError("Connection lost before "
                "receiving all data"))
            d.errback(f)


class WebClientContextFactory(ClientContextFactory):

    def getContext(self, hostname, port):
        return ClientContextFactory.getContext(self)


class WebVerifyingContextFactory(VerifyingContextFactory):

    def getContext(self, hostname, port):
        return VerifyingContextFactory.getContext(self)


class BaseQuery(object):

    def __init__(self, action=None, creds=None, endpoint=None, reactor=None,
        body_producer=None, receiver_factory=None):
        if not action:
            raise TypeError("The query requires an action parameter.")
        self.action = action
        self.creds = creds
        self.endpoint = endpoint
        if reactor is None:
            from twisted.internet import reactor
        self.reactor = reactor
        self.request_headers = None
        self.response_headers = None
        self.body_producer = body_producer
        self.receiver_factory = receiver_factory or StringIOBodyReceiver

    def get_page(self, url, *args, **kwds):
        """
        Define our own get_page method so that we can easily override the
        factory when we need to. This was copied from the following:
            * twisted.web.client.getPage
            * twisted.web.client._makeGetterFactory
        """
        contextFactory = None
        scheme, host, port, path = parse(url)
        data = kwds.get('postdata', None)
        self._method = method = kwds.get('method', 'GET')
        self.request_headers = self._headers(kwds.get('headers', {}))
        if (self.body_producer is None) and (data is not None):
            self.body_producer = FileBodyProducer(StringIO(data))
        if scheme == "https":
            if self.endpoint.ssl_hostname_verification:
                contextFactory = WebVerifyingContextFactory(host)
            else:
                contextFactory = WebClientContextFactory()
            agent = Agent(self.reactor, contextFactory)
            d = agent.request(method, url, self.request_headers,
                self.body_producer)
        else:
            agent = Agent(self.reactor)
            d = agent.request(method, url, self.request_headers,
                self.body_producer)
        d.addCallback(self._handle_response)
        return d

    def _headers(self, headers_dict):
        """
        Convert dictionary of headers into twisted.web.client.Headers object.
        """
        return Headers(dict((k,[v]) for (k,v) in headers_dict.items()))

    def _unpack_headers(self, headers):
        """
        Unpack twisted.web.client.Headers object to dict. This is to provide
        backwards compatability.
        """
        return dict((k,v[0]) for (k,v) in headers.getAllRawHeaders())

    def get_request_headers(self, *args, **kwds):
        """
        A convenience method for obtaining the headers that were sent to the
        S3 server.

        The AWS S3 API depends upon setting headers. This method is provided as
        a convenience for debugging issues with the S3 communications.
        """
        if self.request_headers:
            return self._unpack_headers(self.request_headers)

    def _handle_response(self, response):
        """
        Handle the HTTP response by memoing the headers and then delivering
        bytes.
        """
        self.response_headers = headers = response.headers
        # XXX This workaround (which needs to be improved at that) for possible
        # bug in Twisted with new client:
        # http://twistedmatrix.com/trac/ticket/5476
        if self._method.upper() in ('HEAD', 'DELETE'):
            return succeed(None)
        receiver = self.receiver_factory()
        receiver.finished = d = Deferred()
        receiver.content_length = response.length
        response.deliverBody(receiver)
        return d

    def get_response_headers(self, *args, **kwargs):
        """
        A convenience method for obtaining the headers that were sent from the
        S3 server.

        The AWS S3 API depends upon setting headers. This method is used by the
        head_object API call for getting a S3 object's metadata.
        """
        if self.response_headers:
            return self._unpack_headers(self.response_headers)

