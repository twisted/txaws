from twisted.internet.defer import succeed, Deferred
from twisted.test.proto_helpers import StringTransport
from twisted.web.client import HTTPPageGetter, HTTPClientFactory
from twisted.web.http import Request


class FakeEC2Client(object):

    def __init__(self, creds, endpoint, instances=None):
        self.creds = creds
        self.endpoint = endpoint
        self.instances = instances or []

    def describe_instances(self):
        return succeed(self.instances)


class FakeHTTPHandler(Request):
    status = 200

    def process(self):
        self.content.seek(0, 0)
        data = self.content.read()
        length = self.getHeader('Content-Length')
        request = "'''\n"+str(length)+"\n"+data+"'''\n"
        self.setResponseCode(self.status)
        self.setHeader("Request", self.uri)
        self.setHeader("Command", self.method)
        self.setHeader("Version", self.clientproto)
        self.setHeader("Content-Length", len(request))
        self.write(request)
        self.finish()


class FourOhHTTPHandler(FakeHTTPHandler):
    status = 400


class FiveOhHTTPHandler(FakeHTTPHandler):
    status = 500


class FakeHTTPPageGetter(HTTPPageGetter):

    transport = StringTransport


class FakeHTTPFactory(HTTPClientFactory):
#class FakeHTTPFactory(HTTPClient):

    #protocol = FakeHTTPPageGetter
    #test_payload = ""
    def __init__(self, test_payload, method=None):
        self.test_payload = test_payload
        self.method = method
        self.wasStarted = None
        self.wasStopped = None
        self.connectionFailed = None
        self.deferred = Deferred()

    def connectionMade(self):
        content_length = len(self.test_payload)
        self.sendCommand("GET", "/dummy")
        self.sendHeader("Content-Length", content_length)
        self.endHeaders()
        self.transport.write(self.test_payload)
        self.deferred.success("success")
"""
    def doStart(self):
        self.wasStarted = True

    def doStop(self):
        self.wasStopped = True

    def startedConnecting(self, *args):
        pass

    def clientConnectionFailed(self, *args):
        self.connectionFailed = True
        self.deferred.fail("failed")
"""

class FactoryWrapper(object):

    def __init__(self, payload):
        self.payload = payload

    def __call__(self, url, *args, **kwds):
        FakeHTTPFactory.test_payload = self.payload
        return FakeHTTPFactory(url, *args, **kwds)


