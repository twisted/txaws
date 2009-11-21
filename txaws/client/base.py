from twisted.internet import reactor, ssl
from twisted.web.client import HTTPClientFactory

from txaws.util import parse


class BaseClient(object):
    """Create an AWS client.

    @param creds: User authentication credentials to use.
    @param endpoint: The service endpoint URI.
    @param query_factory: The class or function that produces a query
        object for making requests to the EC2 service.
    """
    def __init__(self, creds=None, endpoint=None, query_factory=None):
        self.creds = creds
        self.endpoint = endpoint
        self.query_factory = query_factory


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

    # XXX needs unit test
    def get_request_headers(self):
        """
        A convenience method for obtaining the headers that were sent to the
        S3 server.

        The AWS S3 API depends upon setting headers. This method is provided as
        a convenience for debugging issues with the S3 communications.
        """
        if self.client:
            return self.client.headers

    # XXX needs unit test
    def get_response_headers(self, *args, **kwargs):
        """
        A convenience method for obtaining the headers that were sent from the
        S3 server.

        The AWS S3 API depends upon setting headers. This method is used by the
        head_object API call for getting a S3 object's metadata.
        """
        if self.client:
            return self.client.response_headers
