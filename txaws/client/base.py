try:
    from xml.etree.ElementTree import ParseError
except ImportError:
    from xml.parsers.expat import ExpatError as ParseError

from twisted.internet import reactor, ssl
from twisted.web import http
from twisted.web.client import HTTPClientFactory
from twisted.web.error import Error as TwistedWebError

from txaws.util import parse
from txaws.credentials import AWSCredentials
from txaws.exception import AWSResponseParseError
from txaws.service import AWSServiceEndpoint


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


class BaseQuery(object):

    def __init__(self, action=None, creds=None, endpoint=None):
        if not action:
            raise TypeError("The query requires an action parameter.")
        self.factory = HTTPClientFactory
        self.action = action
        self.creds = creds
        self.endpoint = endpoint
        self.client = None

    def get_page(self, url, *args, **kwds):
        """
        Define our own get_page method so that we can easily override the
        factory when we need to. This was copied from the following:
            * twisted.web.client.getPage
            * twisted.web.client._makeGetterFactory
        """
        contextFactory = None
        scheme, host, port, path = parse(url)
        self.client = self.factory(url, *args, **kwds)
        if scheme == 'https':
            contextFactory = ssl.ClientContextFactory()
            reactor.connectSSL(host, port, self.client, contextFactory)
        else:
            reactor.connectTCP(host, port, self.client)
        return self.client.deferred

    def get_request_headers(self, *args, **kwds):
        """
        A convenience method for obtaining the headers that were sent to the
        S3 server.

        The AWS S3 API depends upon setting headers. This method is provided as
        a convenience for debugging issues with the S3 communications.
        """
        if self.client:
            return self.client.headers

    def get_response_headers(self, *args, **kwargs):
        """
        A convenience method for obtaining the headers that were sent from the
        S3 server.

        The AWS S3 API depends upon setting headers. This method is used by the
        head_object API call for getting a S3 object's metadata.
        """
        if self.client:
            return self.client.response_headers
