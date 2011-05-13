from pytz import UTC
from cStringIO import StringIO
from datetime import datetime

from twisted.trial.unittest import TestCase

from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint
from txaws.ec2.client import Query
from txaws.server.resource import QueryAPI


class FakeRequest(object):

    def __init__(self, params, endpoint):
        self.params = params
        self.endpoint = endpoint
        self.written = StringIO()
        self.finished = False
        self.code = None
        self.headers = {}

    @property
    def args(self):
        return dict((key, [value]) for key, value in self.params.iteritems())

    @property
    def method(self):
        return self.endpoint.method

    @property
    def path(self):
        return self.endpoint.path

    def write(self, content):
        assert isinstance(content, str), "Only strings should be written"
        self.written.write(content)

    def finish(self):
        if self.code is None:
            self.code = 200
        self.finished = True

    def setResponseCode(self, code):
        self.code = code

    def setHeader(self, key, value):
        self.headers[key] = value

    def getHeader(self, key):
        return self.headers.get(key)

    @property
    def response(self):
        return self.written.getvalue()


class TestPrincipal(object):

    def __init__(self, creds):
        self.creds = creds

    @property
    def access_key(self):
        return self.creds.access_key

    @property
    def secret_key(self):
        return self.creds.secret_key


class TestQueryAPI(QueryAPI):

    name = "test-api"
    actions = ["SomeAction"]
    signature_versions = (1, 2)
    signature_error = "Wrong signature"
    content_type = "text/plain"

    def __init__(self, *args, **kwargs):
        QueryAPI.__init__(self, *args, **kwargs)
        self.principal = None

    def execute(self, call):
        return "data"

    def get_principal(self, access_key):
        if self.principal and self.principal.access_key == access_key:
            return self.principal

    def dump_error(self, error, request):
        return str("%s - %s" % (error.code, error.message))


class QueryAPITest(TestCase):

    def setUp(self):
        super(QueryAPITest, self).setUp()
        self.api = TestQueryAPI("http://uri")

    def test_handle(self):
        """
        L{QueryAPI.handle} forwards valid requests to L{QueryAPI.execute}.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertTrue(request.finished)
            self.assertEqual("data", request.response)
            self.assertEqual("4", request.headers["Content-Length"])
            self.assertEqual("text/plain", request.headers["Content-Type"])
            self.assertEqual(200, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_empty_request(self):
        """
        If an empty request is received a message describing the API is
        returned.
        """
        endpoint = AWSServiceEndpoint(self.api.uri)
        request = FakeRequest({}, endpoint)
        self.assertEqual("Query API at http://uri", self.api.render(request))
        self.assertEqual("text/plain", request.headers["Content-Type"])
        self.assertEqual(None, request.code)

    def test_handle_with_signature_version_1(self):
        """SignatureVersion 1 is supported as well."""
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint,
                      other_params={"SignatureVersion": "1"})
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignore):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_signature_sha1(self):
        """
        The C{HmacSHA1} signature method is supported, in which case the
        signing using sha1 instead.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign(hash_type="sha1")
        request = FakeRequest(query.params, endpoint)

        def check(ignore):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_unsupported_version(self):
        """Signature versions other than 1 and 2 result in errors."""
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        query.params["SignatureVersion"] = "0"
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.flushLoggedErrors()
            self.assertEqual("InvalidSignature - SignatureVersion '0' "
                             "not supported", request.response)
            self.assertEqual(403, request.code)

        return self.api.handle(request).addCallback(check)

    def test_handle_with_internal_error(self):
        """
        If an unknown error occurs while handling the request,
        L{QueryAPI.handle} responds with HTTP status 500.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        self.api.execute = lambda call: 1 / 0

        def check(ignored):
            self.flushLoggedErrors()
            self.assertTrue(request.finished)
            self.assertEqual("integer division or modulo by zero",
                             request.response)
            self.assertEqual(500, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_parameter_error(self):
        """
        If an error occurs while parsing the parameters, L{QueryAPI.handle}
        responds with HTTP status 400.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        query.params.pop("Action")
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.flushLoggedErrors()
            self.assertEqual("MissingParameter - The request must contain "
                             "the parameter Action", request.response)
            self.assertEqual(400, request.code)

        return self.api.handle(request).addCallback(check)

    def test_handle_with_unsupported_action(self):
        """Only actions listed in L{QueryAPI.actions} are supported."""
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="FooBar", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.flushLoggedErrors()
            self.assertEqual("InvalidAction - The action FooBar is not valid"
                             " for this web service.", request.response)
            self.assertEqual(400, request.code)

        return self.api.handle(request).addCallback(check)

    def test_handle_with_non_existing_user(self):
        """
        If no L{Principal} can be found with the given access key ID,
        L{QueryAPI.handle} responds with HTTP status 400.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.flushLoggedErrors()
            self.assertEqual("AuthFailure - No user with access key 'access'",
                             request.response)
            self.assertEqual(401, request.code)

        return self.api.handle(request).addCallback(check)

    def test_handle_with_wrong_signature(self):
        """
        If the signature in the request doesn't match the one calculated with
        the locally stored secret access key, and error is returned.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        query.params["Signature"] = "wrong"
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.flushLoggedErrors()
            self.assertEqual("SignatureDoesNotMatch - Wrong signature",
                             request.response)
            self.assertEqual(403, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_timestamp_and_expires(self):
        """
        If the request contains both Expires and Timestamp parameters,
        an error is returned.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint,
                      other_params={"Timestamp": "2010-01-01T12:00:00Z",
                                    "Expires": "2010-01-01T12:00:00Z"})
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.flushLoggedErrors()
            self.assertEqual(
                "InvalidParameterCombination - The parameter Timestamp"
                " cannot be used with the parameter Expires",
                request.response)
            self.assertEqual(400, request.code)

        return self.api.handle(request).addCallback(check)

    def test_handle_with_non_expired_signature(self):
        """
        If the request contains an Expires parameter with a time that is before
        the current time, everything is fine.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint,
                      other_params={"Expires": "2010-01-01T12:00:00Z"})
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        now = datetime(2009, 12, 31, tzinfo=UTC)
        self.api.get_utc_time = lambda: now
        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_expired_signature(self):
        """
        If the request contains an Expires parameter with a time that is before
        the current time, an error is returned.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint,
                      other_params={"Expires": "2010-01-01T12:00:00Z"})
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.flushLoggedErrors()
            self.assertEqual(
                "RequestExpired - Request has expired. Expires date is"
                " 2010-01-01T12:00:00Z", request.response)
            self.assertEqual(400, request.code)

        now = datetime(2010, 1, 1, 12, 0, 1, tzinfo=UTC)
        self.api.get_utc_time = lambda: now
        return self.api.handle(request).addCallback(check)

    def test_handle_with_post_method(self):
        """
        L{QueryAPI.handle} forwards valid requests using the HTTP POST method
        to L{QueryAPI.execute}.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint(self.api.uri, method="POST")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_port_number(self):
        """
        If the request Host header includes a port number, it's included
        in the text that get signed when checking the signature.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://endpoint:1234")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        self.api.uri = "http://endpoint:1234"
        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_endpoint_with_terminating_slash(self):
        """
        Check signature should handle a root_url with a terminating
        slash.
        """
        creds = AWSCredentials("access", "secret")
        uri = "http://endpoint"
        endpoint = AWSServiceEndpoint(uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        self.api.uri = "%s/" % uri
        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_root_url_with_path(self):
        """
        If the request goes through a proxy like Apache which rewrites part of
        the request so that we don't have the full URL, we still get the
        correct path using the C{uri} parameter and what's remain of the
        path.
        """
        creds = AWSCredentials("access", "secret")
        uri = "http://endpoint/cloud/test"
        endpoint = AWSServiceEndpoint(uri)
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        endpoint.path = "/test"
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        self.api.uri = uri
        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)
