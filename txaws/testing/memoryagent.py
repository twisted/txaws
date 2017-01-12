# Copyright 2014-2016 ClusterHQ
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
In-memory ``IAgent`` implementation.

Originally from ``flocker/restapi/testtools.py``.
"""

from io import BytesIO
from itertools import count

from zope.interface import implementer

from twisted.internet.interfaces import IPushProducer
from twisted.internet.defer import Deferred, succeed
from twisted.internet.address import IPv4Address
from twisted.python.log import err
from twisted.web.client import ResponseDone
from twisted.web.server import NOT_DONE_YET, Request
from twisted.web.http import HTTPChannel, urlparse, unquote
from twisted.web.iweb import IAgent, IResponse
from twisted.web.http_headers import Headers
from twisted.web.resource import getChildForRequest
from twisted.test.proto_helpers import StringTransport
from twisted.python.failure import Failure


class EventChannel(object):
    """
    An L{EventChannel} provides one-to-many event publishing in a
    re-usable container.

    Any number of parties may subscribe to an event channel to receive
    the very next event published over it.  A subscription is a
    L{Deferred} which will get the next result and is then no longer
    associated with the L{EventChannel} in any way.

    Future events can be received by re-subscribing to the channel.

    @ivar _subscriptions: A L{list} of L{Deferred} instances which are waiting
        for the next event.
    """
    def __init__(self):
        self._subscriptions = []

    def _itersubscriptions(self):
        """
        Return an iterator over all current subscriptions after
        resetting internal subscription state to forget about all of
        them.
        """
        subscriptions = self._subscriptions[:]
        del self._subscriptions[:]
        return iter(subscriptions)

    def callback(self, value):
        """
        Supply a success value for the next event which will be published now.
        """
        for subscr in self._itersubscriptions():
            subscr.callback(value)

    def errback(self, reason=None):
        """
        Supply a failure value for the next event which will be published now.
        """
        for subscr in self._itersubscriptions():
            subscr.errback(reason)

    def subscribe(self):
        """
        Get a L{Deferred} which will fire with the next event on this channel.

        @rtype: L{Deferred}
        """
        d = Deferred(canceller=self._subscriptions.remove)
        self._subscriptions.append(d)
        return d


_dummyRequestCounter = iter(count())


def dummyRequest(method, path, headers, body=b""):
    """
    Construct a new dummy L{IRequest} provider.

    @param method: The HTTP method of the request.  For example, C{b"GET"}.
    @type method: L{bytes}

    @param path: The encoded path part of the URI of the request.  For example,
        C{b"/foo"}.
    @type path: L{bytes}

    @param headers: The headers of the request.
    @type headers: L{Headers}

    @param body: The bytes that make up the request body.
    @type body: L{bytes}

    @return: A L{IRequest} which can be used to render an L{IResource} using
        only in-memory data structures.
    """
    parsed = urlparse(path)
    if parsed.query:
        # Oops, dropped params.  Good thing no one cares.
        new_path = parsed.path + "?" + parsed.query
    else:
        new_path = parsed.path
    return _DummyRequest(
        next(_dummyRequestCounter),
        method, new_path, headers, body)


def render(resource, request):
    """
    Render an L{IResource} using a particular L{IRequest}.

    @raise ValueError: If L{IResource.render} returns an unsupported value.

    @return: A L{Deferred} that fires with C{None} when the response has been
        completely rendered.
    """
    result = resource.render(request)
    if isinstance(result, bytes):
        request.write(result)
        request.finish()
        return succeed(None)
    elif result is NOT_DONE_YET:
        if request._finished:
            return succeed(None)
        else:
            return request.notifyFinish()
    else:
        raise ValueError("Unexpected return value: %r" % (result,))


class _DummyRequest(Request):

    # Request has code and code_message attributes.  They're not part of
    # IRequest.  A bunch of existing code written against _DummyRequest used
    # the _code and _message attributes previously provided by _DummyRequest
    # (at least those names look like they're not part of the interface).
    # Preserve those attributes here but avoid re-implementing setResponseCode
    # or duplicating the state Request is keeping.
    @property
    def _code(self):
        return self.code

    @property
    def _message(self):
        return self.code_message

    def __init__(self, counter, method, path, headers, content):

        channel = HTTPChannel()
        host = IPv4Address(b"TCP", b"127.0.0.1", 80)
        channel.makeConnection(StringTransport(hostAddress=host))

        Request.__init__(self, channel, False)

        # An extra attribute for identifying this fake request
        self._counter = counter

        # Attributes a Request is supposed to have but we have to set ourselves
        # because the base class mixes together too much other logic with the
        # code that sets them.
        self.prepath = []
        self.requestHeaders = headers
        self.content = BytesIO(content)

        self.requestReceived(method, path, b"HTTP/1.1")

        # requestReceived initializes the path attribute for us (but not
        # postpath).
        self.postpath = list(map(unquote, self.path[1:].split(b'/')))

        # Our own notifyFinish / finish state because the inherited
        # implementation wants to write confusing stuff to the transport when
        # the request gets finished.
        self._finished = False
        self._finishedChannel = EventChannel()

        # Our own state for the response body so we don't have to dig it out of
        # the transport.
        self._responseBody = b""

    def process(self):
        """
        Don't do any processing.  Override the inherited implementation so it
        doesn't do any, either.
        """

    def finish(self):
        self._finished = True
        self._finishedChannel.callback(None)

    def notifyFinish(self):
        return self._finishedChannel.subscribe()

    # Not part of the interface but called by DeferredResource, used by
    # twisted.web.guard (therefore important to us)
    def processingFailed(self, reason):
        err(reason, "Processing _DummyRequest %d failed" % (self._counter,))

    def write(self, data):
        self._responseBody += data

    def render(self, resource):
        # TODO: Required by twisted.web.guard but not part of IRequest ???
        render(resource, self)


def asResponse(request):
    """
    Extract the response data stored on a request and create a real response
    object from it.

    @param request: A L{_DummyRequest} that has been rendered.

    @return: An L{IResponse} provider carrying all of the response information
        that was rendered onto C{request}.
    """
    return _MemoryResponse(
        b"HTTP/1.1", request.code, request.code_message,
        request.responseHeaders, None, None,
        request._responseBody)


@implementer(IResponse)
class _MemoryResponse(object):
    """
    An entirely in-memory response to an HTTP request. This is not tested
    because it should be moved to Twisted.
    """
    def __init__(self, version, code, phrase, headers, request,
                 previousResponse, responseBody):
        """
        @see: L{IResponse}

        @param responseBody: The body of the response.
        @type responseBody: L{bytes}
        """
        self.version = version
        self.code = code
        self.phrase = phrase
        self.headers = headers
        self.request = request
        self.length = len(responseBody)
        self._responseBody = responseBody
        self.setPreviousResponse(previousResponse)

    def deliverBody(self, protocol):
        """
        Immediately deliver the entire response body to C{protocol}.
        """
        protocol.makeConnection(_StubProducer())
        protocol.dataReceived(self._responseBody)
        protocol.connectionLost(Failure(ResponseDone()))

    def setPreviousResponse(self, response):
        self.previousResponse = response


@implementer(IPushProducer)
class _StubProducer(object):
    """
    A do-nothing producer that L{_MemoryResponse} can use while
    delivering response bodies.
    """
    def pauseProducing(self):
        pass

    def resumeProducing(self):
        pass

    def stopProducing(self):
        pass


@implementer(IAgent)
class MemoryAgent(object):
    """
    L{MemoryAgent} generates responses to requests by rendering an
    L{IResource} using those requests.

    @ivar resource: The root resource from which traversal for request
        dispatching/response starts.
    @type resource: L{IResource} provider
    """
    def __init__(self, resource):
        self.resource = resource

    def request(self, method, url, headers=None, bodyProducer=None):
        """
        Find the child of C{self.resource} for the given request and
        render it to generate a response.
        """
        if headers is None:
            headers = Headers()

        # Twisted Web server only supports dispatching requests after reading
        # the entire request body into memory.
        content = BytesIO()
        if bodyProducer is None:
            reading = succeed(None)
        else:
            reading = bodyProducer.startProducing(content)

        def finishedReading(ignored):
            request = dummyRequest(method, url, headers, content.getvalue())
            resource = getChildForRequest(self.resource, request)
            d = render(resource, request)
            d.addCallback(lambda ignored: request)
            return d
        rendering = reading.addCallback(finishedReading)

        def rendered(request):
            return _MemoryResponse(
                (b"HTTP", 1, 1),
                request._code,
                request._message,
                request.responseHeaders,
                request,
                None,
                request._responseBody)
        rendering.addCallback(rendered)
        return reading
