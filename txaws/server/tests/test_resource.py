from cStringIO import StringIO
from datetime import datetime

from dateutil.tz import tzutc
from dateutil.parser import parse

try:
    import json
except ImportError:
    import simplejson as json


from twisted.trial.unittest import TestCase
from twisted.python.reflect import safe_str

from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint
from txaws.ec2.client import Query, Signature
from txaws.server.method import Method
from txaws.server.registry import Registry
from txaws.server.resource import QueryAPI
from txaws.server.exception import APIError
from txaws import version
from txaws.util import iso8601time


class FakeRequest(object):

    def __init__(self, params, endpoint):
        self.params = params
        self.endpoint = endpoint
        self.written = StringIO()
        self.finished = False
        self.code = None
        self.headers = {"Host": endpoint.get_canonical_host()}

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


class TestMethod(Method):

    def invoke(self, call):
        return "data"


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

    signature_versions = (1, 2)
    content_type = "text/plain"

    def __init__(self, *args, **kwargs):
        QueryAPI.__init__(self, *args, **kwargs)
        self.principal = None

    def get_principal(self, access_key):
        if self.principal and self.principal.access_key == access_key:
            return self.principal

    def dump_error(self, error, request):
        return str("%s - %s" % (error.code, safe_str(error.message)))


class AlternativeWireFormatQueryAPI(TestQueryAPI):
    def __init__(self, registry):
        TestQueryAPI.__init__(self, registry=registry)

    def get_call_arguments(self, request):
        result = {
            "action": "SomeAction",
            "version": version.ec2_api,
            "signature_version": 2,
            "expires": None,
            "timestamp": parse(iso8601time(None)),
            "access_key_id": request.args["access_key"][0],
            "signature_method": "Hmacsha256",
            "signature_version": 2,
            "signature": request.args["signature"][0]}
        params = dict((k, v[-1]) for k, v in request.args.iteritems())
        raw = params.copy()
        raw.pop("signature")
        return {"transport_args": result,
                "handler_args": params,
                "raw_args": raw}


class QueryAPITestCase(TestCase):

    def setUp(self):
        super(QueryAPITestCase, self).setUp()
        self.registry = Registry()
        self.registry.add(TestMethod, action="SomeAction", version=None)
        self.api = TestQueryAPI(registry=self.registry)

    def test_handle(self):
        """
        L{QueryAPI.handle} forwards valid requests to L{QueryAPI.execute}.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertTrue(request.finished)
            self.assertEqual("data", request.response)
            self.assertEqual("4", request.headers["Content-Length"])
            self.assertEqual("text/plain", request.headers["Content-Type"])
            self.assertEqual(
                "nosniff", request.headers["X-Content-Type-Options"])
            self.assertEqual(200, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_custom_get_call_arguments(self):
        """
        L{QueryAPI.handle} uses L{QueryAPI.get_call_arguments} to get the
        arguments for a call.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        api = AlternativeWireFormatQueryAPI(self.registry)
        params = {"foo": "bar", "access_key": creds.access_key}
        signature = Signature(
            creds, endpoint, params.copy(),
            signature_method="Hmacsha256",
            signature_version=2)
        params["signature"] = signature.compute()
        request = FakeRequest(params, endpoint)

        def check(ignored):
            self.assertTrue(request.finished)
            self.assertEqual("data", request.response)
            self.assertEqual("4", request.headers["Content-Length"])
            self.assertEqual("text/plain", request.headers["Content-Type"])
            self.assertEqual(200, request.code)

        api.principal = TestPrincipal(creds)
        return api.handle(request).addCallback(check)

    def test_signature_verification_custom_get_call_arguments(self):
        """
        The 'raw_args' returned from L{QueryAPI.get_call_arguments} is used for
        signature verification.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        api = AlternativeWireFormatQueryAPI(self.registry)
        params = {"foo": "bar", "access_key": creds.access_key}
        signature = Signature(
            creds, endpoint, params.copy(),
            signature_method="Hmacsha256",
            signature_version=2)
        params["signature"] = signature.compute()
        params["foo"] = "HACKEDNOTBAR"
        request = FakeRequest(params, endpoint)

        def check(ignored):
            self.assertTrue(request.finished)
            self.assertIn("SignatureDoesNotMatch", request.response)

        api.principal = TestPrincipal(creds)
        return api.handle(request).addCallback(check)

    def test_handle_with_dump_result(self):
        """
        L{QueryAPI.handle} serializes the action result with C{dump_result}.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertEqual("data", json.loads(request.response))

        self.api.dump_result = json.dumps
        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_deprecated_actions(self):
        """
        L{QueryAPI.handle} supports the legacy 'actions' attribute.
        """
        self.api.actions = ["SomeAction"]
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertEqual("data", request.response)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_pass_params_to_call(self):
        """
        L{QueryAPI.handle} creates a L{Call} object with the correct
        parameters.
        """
        self.registry.add(TestMethod, "SomeAction", "1.2.3")
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint,
                      other_params={"Foo": "bar", "Version": "1.2.3"})
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def execute(call):
            self.assertEqual({"Foo": "bar"}, call.get_raw_params())
            self.assertIdentical(self.api.principal, call.principal)
            self.assertEqual("SomeAction", call.action)
            self.assertEqual("1.2.3", call.version)
            self.assertEqual(request.id, call.id)
            return "ok"

        def check(ignored):
            self.assertEqual("ok", request.response)
            self.assertEqual(200, request.code)

        self.api.execute = execute
        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_ensures_version_is_str(self):
        """
        L{QueryAPI.schema} coerces the Version parameter to a str, in order
        to let URLs built with it be str, as required by urllib.quote in
        python 2.7.
        """
        self.registry.add(TestMethod, "SomeAction", "1.2.3")
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint,
                      other_params={"Version": u"1.2.3"})
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def execute(call):
            self.assertEqual("1.2.3", call.version)
            self.assertIsInstance(call.version, str)
            return "ok"

        self.api.execute = execute
        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request)

    def test_handle_empty_request(self):
        """
        If an empty request is received a message describing the API is
        returned.
        """
        endpoint = AWSServiceEndpoint("http://uri")
        request = FakeRequest({}, endpoint)
        self.assertEqual("Query API Service", self.api.render(request))
        self.assertEqual("text/plain", request.headers["Content-Type"])
        self.assertEqual(None, request.code)

    def test_handle_with_signature_version_1(self):
        """SignatureVersion 1 is supported as well."""
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
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
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign(hash_type="sha1")
        request = FakeRequest(query.params, endpoint)

        def check(ignore):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_unsupported_version(self):
        """If signature versions is not supported an error is raised."""
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
            self.assertEqual("InvalidSignature - SignatureVersion '2' "
                             "not supported", request.response)
            self.assertEqual(403, request.code)

        self.api.signature_versions = (1,)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_internal_error(self):
        """
        If an unknown error occurs while handling the request,
        L{QueryAPI.handle} responds with HTTP status 500.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        self.api.execute = lambda call: 1 / 0

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(1, len(errors))
            self.assertTrue(request.finished)
            self.assertEqual("Server error", request.response)
            self.assertEqual(500, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_500_api_error(self):
        """
        If an L{APIError} is raised with a status code superior or equal to
        500, the error is logged on the server side.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def fail_execute(call):
            raise APIError(500, response="oops")
        self.api.execute = fail_execute

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(1, len(errors))
            self.assertTrue(request.finished)
            self.assertEqual("oops", request.response)
            self.assertEqual(500, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_parameter_error(self):
        """
        If an error occurs while parsing the parameters, L{QueryAPI.handle}
        responds with HTTP status 400.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        query.params.pop("Action")
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
            self.assertEqual("MissingParameter - The request must contain "
                             "the parameter Action (unicode)",
                             request.response)
            self.assertEqual(400, request.code)

        return self.api.handle(request).addCallback(check)

    def test_handle_error_is_api_content_type(self):
        """
        If an error occurs while parsing the parameters, L{QueryAPI.handle}
        responds with HTTP status 400, and the resulting response has a
        Content-Type header matching the content type defined in the QueryAPI.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        query.params.pop("Action")
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
            self.assertEqual(400, request.code)
            self.assertEqual(
                self.api.content_type, request.headers['Content-Type'])
            self.assertEqual(
                "nosniff", request.headers["X-Content-Type-Options"])

        return self.api.handle(request).addCallback(check)

    def test_handle_unicode_api_error(self):
        """
        If an L{APIError} contains a unicode message, L{QueryAPI} is able to
        protect itself from it.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def fail_execute(call):
            raise APIError(400, code="LangError",
                           message=u"\N{HIRAGANA LETTER A}dvanced")
        self.api.execute = fail_execute

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
            self.assertTrue(request.finished)
            self.assertTrue(request.response.startswith("LangError"))
            self.assertEqual(400, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_unicode_error(self):
        """
        If an arbitrary error raised by an API method contains a unicode
        message, L{QueryAPI} is able to protect itself from it.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def fail_execute(call):
            raise ValueError(u"\N{HIRAGANA LETTER A}dvanced")
        self.api.execute = fail_execute

        def check(ignored):
            [error] = self.flushLoggedErrors()
            self.assertIsInstance(error.value, ValueError)
            self.assertTrue(request.finished)
            self.assertEqual("Server error", request.response)
            self.assertEqual(500, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_unsupported_action(self):
        """Only actions registered in the L{Registry} are supported."""
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="FooBar", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
            self.assertEqual("InvalidAction - The action FooBar is not valid"
                             " for this web service.", request.response)
            self.assertEqual(400, request.code)

        return self.api.handle(request).addCallback(check)

    def test_handle_non_available_method(self):
        """Only actions registered in the L{Registry} are supported."""

        class NonAvailableMethod(Method):

            def is_available(self):
                return False

        self.registry.add(NonAvailableMethod, action="CantDoIt")
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="CantDoIt", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
            self.assertEqual("InvalidAction - The action CantDoIt is not "
                             "valid for this web service.", request.response)
            self.assertEqual(400, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_deprecated_actions_and_unsupported_action(self):
        """
        If the deprecated L{QueryAPI.actions} attribute is set, it will be
        used for looking up supported actions.
        """
        self.api.actions = ["SomeAction"]
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="FooBar", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
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
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
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
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        query.params["Signature"] = "wrong"
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
            self.assertEqual("SignatureDoesNotMatch - The request signature "
                             "we calculated does not match the signature you "
                             "provided. Check your key and signing method.",
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
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint,
                      other_params={"Timestamp": "2010-01-01T12:00:00Z",
                                    "Expires": "2010-01-01T12:00:00Z"})
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
            self.assertEqual(
                "InvalidParameterCombination - The parameter Timestamp"
                " cannot be used with the parameter Expires",
                request.response)
            self.assertEqual(400, request.code)

        return self.api.handle(request).addCallback(check)

    def test_handle_with_non_expired_signature(self):
        """
        If the request contains an Expires parameter with a time that is after
        the current time, everything is fine.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint,
                      other_params={"Expires": "2010-01-01T12:00:00Z"})
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        now = datetime(2009, 12, 31, tzinfo=tzutc())
        self.api.get_utc_time = lambda: now
        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_expired_signature(self):
        """
        If the request contains an Expires parameter with a time that is before
        the current time, an error is returned.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint,
                      other_params={"Expires": "2010-01-01T12:00:00Z"})
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            errors = self.flushLoggedErrors()
            self.assertEquals(0, len(errors))
            self.assertEqual(
                "RequestExpired - Request has expired. Expires date is"
                " 2010-01-01T12:00:00Z", request.response)
            self.assertEqual(400, request.code)

        now = datetime(2010, 1, 1, 12, 0, 1, tzinfo=tzutc())
        self.api.get_utc_time = lambda: now
        return self.api.handle(request).addCallback(check)

    def test_handle_with_post_method(self):
        """
        L{QueryAPI.handle} forwards valid requests using the HTTP POST method
        to L{QueryAPI.execute}.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://uri", method="POST")
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

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_endpoint_with_terminating_slash(self):
        """
        Check signature should handle a URI with a terminating slash.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://endpoint/")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)

        def check(ignored):
            self.assertEqual("data", request.response)
            self.assertEqual(200, request.code)

        self.api.principal = TestPrincipal(creds)
        return self.api.handle(request).addCallback(check)

    def test_handle_with_custom_path(self):
        """
        If L{QueryAPI.path} is not C{None} it will be used in place of
        the HTTP request path when calculating the signature.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://endpoint/path/")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)
        # Simulate a request rewrite, like apache would do
        request.endpoint.path = "/"

        def check(ignored):
            self.assertTrue(request.finished)
            self.assertEqual(200, request.code)

        self.api.principal = TestPrincipal(creds)
        self.api.path = "/path/"
        return self.api.handle(request).addCallback(check)

    def test_handle_with_custom_path_and_rest(self):
        """
        If L{QueryAPI.path} is not C{None} it will be used in place of
        the HTTP request path when calculating the signature. The rest
        of the path is appended as for the HTTP request.
        """
        creds = AWSCredentials("access", "secret")
        endpoint = AWSServiceEndpoint("http://endpoint/path/rest")
        query = Query(action="SomeAction", creds=creds, endpoint=endpoint)
        query.sign()
        request = FakeRequest(query.params, endpoint)
        # Simulate a request rewrite, like apache would do
        request.endpoint.path = "/rest"

        def check(ignored):
            self.assertTrue(request.finished)
            self.assertEqual(200, request.code)

        self.api.principal = TestPrincipal(creds)
        self.api.path = "/path/"
        return self.api.handle(request).addCallback(check)
