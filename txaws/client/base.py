from twisted.internet import reactor, ssl
from twisted.web.client import HTTPClientFactory

from txaws.util import parse


class BaseClient(object):
    pass


class BaseQuery(object):

    def __init__(self, action=None, creds=None, endpoint=None):
        self.factory = HTTPClientFactory
        self.action = action
        self.creds = creds
        self.endpoint = endpoint

    def get_page(self, url, *args, **kwds):
        """
        Define our own get_page method so that we can easily override the
        factory when we need to. This was copied from the following:
            * twisted.web.client.getPage
            * twisted.web.client._makeGetterFactory
        """
        contextFactory = None
        scheme, host, port, path = parse(url)
        factory = self.factory(url, *args, **kwds)
        if scheme == 'https':
            contextFactory = ssl.ClientContextFactory()
            reactor.connectSSL(host, port, factory, contextFactory)
        else:
            reactor.connectTCP(host, port, factory)
        return factory.deferred
