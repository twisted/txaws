import attr

import datetime

import hashlib

import hmac

import os

import textwrap

from twisted.trial import unittest
from twisted.python import filepath

from txaws._auth_v4 import (
    _CanonicalRequest,
    _Credential,
    _CredentialScope,
    _SignableAWS4HMAC256Token,
    _make_authorization_header,
    _make_canonical_headers,
    _make_canonical_query_string,
    _make_canonical_uri,
    _make_signed_headers,
    getSignatureKey,
    makeAMZDate,
    makeDateStamp,
    sign,
)

from txaws.credentials import AWSCredentials

from txaws.service import REGION_US_EAST_1

import urlparse


def _create_canonical_request_fixture():
    """
    Make a L{_CanonicalRequest} instance with fixed data.

    @return: A canonical request.
    @rtype: L{_CanonicalRequest}
    """
    return _CanonicalRequest(method="POST",
                             canonical_uri="/",
                             canonical_query_string="qs",
                             canonical_headers="headers",
                             signed_headers="signed headers",
                             payload_hash="payload hash")


def _create_credential_scope_fixture():
    """
    Make a L{_CredentialScope} instance with fixed data.

    @return: A credential scope.
    @rtype: L{_CredentialScope}
    """
    return _CredentialScope(date_stamp="date stamp",
                            region="region",
                            service="service")


def _create_credential_fixture(scope):
    """
    Make a L{_Credential} instance with fixed data.

    @param scope: the scope for this credential instance
    @type scope: L{_CredentialScope}

    @return: A credential instance.
    @rtype: L{_Credential}
    """
    return _Credential(access_key="key",
                       credential_scope=scope)


class AWS4FunctionTest(unittest.SynchronousTestCase):
    """
    Tests for support functions for AWS4 signing.
    """

    def test_sign(self):
        """
        An SHA256 HMAC signature is returned.
        """
        self.assertEqual(sign("key", "msg"),
                         '-\x93\xcb\xc1\xbe\x16{\xcb\x167\xa4\xa2<\xbf\xf0\x1a'
                         'xx\xf0\xc5\x0e\xe83\x95N\xa5"\x1b\xb1\xb8\xc6(')

    def test_getSignatureKey(self):
        """
        A signature key generated from an AWS secret key, the current
        date, the region name, and the service name is returned.
        """
        self.assertEqual(getSignatureKey(key="key",
                                         dateStamp="dateStamp",
                                         regionName="region",
                                         serviceName="service"),
                         '\x85,P\x1e=\xba\xa4;\x13\xc6\r\xa6\x0f\xcd\xa1\xac*'
                         '\xd31I\xbbpX\x95x\x08\xb0mM\x85\xeft')

    def test_makeAMZDate(self):
        """
        A L{datetime.datetime} instance is formatted according to the
        convention for AMZ dates.
        """
        instant = datetime.datetime(2016, 11, 11, 2, 45, 50)
        self.assertEqual(makeAMZDate(instant), "20161111T024550Z")

    def test_makeDateStamp(self):
        """
        A L{datetime.datetime} instance is formatted according to the
        AWS V4 convention for date stamps.
        """
        instant = datetime.datetime(2016, 11, 11, 2, 45, 50)
        self.assertEqual(makeDateStamp(instant), "20161111")


class MakeCanonicalHeadersTests(unittest.SynchronousTestCase):
    """
    Tests for L{_make_canonical_headers}.
    """

    def test_whitespace(self):
        """
        Canonical headers end, but do not begin, with a newline.
        """
        canonical = _make_canonical_headers(
            headers={"header": "value"},
            headers_to_sign=("header",))
        self.assertTrue(canonical.endswith("\n"))
        self.assertFalse(canonical.startswith("\n"))

    def test_only_signed_headers_included(self):
        """
        Only headers that should be signed are included.
        """
        canonical = _make_canonical_headers(
            headers={"header": "value",
                     "signed-header": "signed-value",
                     "other-signed-header": "other-signed-value"},
            headers_to_sign=("signed-header", "other-signed-header"))
        self.assertEqual(canonical, textwrap.dedent("""\
        other-signed-header:other-signed-value
        signed-header:signed-value
        """))

    def test_headers_sorted(self):
        """
        The canonical headers are sorted.
        """
        canonical = _make_canonical_headers(
            headers={"b": "2",
                     "a": "1",
                     "c": "3"},
            headers_to_sign=('a', 'b', 'c'))
        self.assertEqual(canonical, textwrap.dedent("""\
        a:1
        b:2
        c:3
        """))


class MakeSignedHeadersTests(unittest.TestCase):
    """
    Tests for L{_make_signed_headers}.
    """

    def test_only_names_include(self):
        """
        Only the headers' names are included.
        """
        signed_headers = _make_signed_headers(
            headers={"header": "value"},
            headers_to_sign=("header", "value"))
        self.assertIn(signed_headers, "header")
        self.assertNotIn(signed_headers, "value")

    def test_semicolon_delimited(self):
        """
        The headers are delimited by a semicolon.
        """
        signed_headers = _make_signed_headers(
            headers={"header1": "value",
                     "header2": "value"},
            headers_to_sign=("header1", "header2"))
        self.assertEqual(signed_headers, "header1;header2")

    def test_headers_sorted(self):
        """
        The headers are sorted.
        """
        signed_headers = _make_signed_headers(
            headers={"b": "2",
                     "a": "1",
                     "c": "3"},
            headers_to_sign=('a', 'b', 'c'))
        self.assertEqual(signed_headers, "a;b;c")

    def test_only_signed_headers_included(self):
        """
        Only the headers that should be signed are included.
        """
        signed_headers = _make_signed_headers(
            headers={"header": "value",
                     "signed-header": "signed-value",
                     "other-signed-header": "other-signed-value"},
            headers_to_sign=("signed-header", "other-signed-header"))
        self.assertEqual(signed_headers, 'other-signed-header;signed-header')


class MakeCanonicalURITests(unittest.SynchronousTestCase):
    """
    Tests for L{_make_canonical_uri}.
    """

    def test_empty_path(self):
        """
        A URL with an empty path has a canonical URI with an empty
        path.
        """
        self.assertEqual(
            _make_canonical_uri(urlparse.urlparse('https://www.amazon.com/')),
            "https://www.amazon.com/")

    def test_path(self):
        """
        A URL with a path has a canonical URI with the same path.
        """
        self.assertEqual(
            _make_canonical_uri(
                urlparse.urlparse('https://www.amazon.com/a/b')),
            "https://www.amazon.com/a/b")

    def test_path_not_normalized(self):
        """
        A URL whose path has duplicate slashes has a canonical URI
        with duplicated slashes.
        """
        self.assertEqual(
            _make_canonical_uri(
                urlparse.urlparse('https://www.amazon.com//a/b')),
            "https://www.amazon.com//a/b")

    def test_query_params_and_fragments_removed(self):
        """
        A URL's canonical URI has that URL's query string, parameters, and
        fragment removed.
        """
        parsed = urlparse.urlparse('https://www.amazon.com//a/b')
        parsed = parsed._replace(query="query=1",
                                 params="params",
                                 fragment="fragment")
        self.assertEqual(_make_canonical_uri(parsed),
                         "https://www.amazon.com//a/b")


class MakeCanonicalQueryStringTests(unittest.SynchronousTestCase):
    """
    Tests for L{_make_canonical_query_string}.
    """

    def test_blank_values_retained(self):
        """
        Blank query parameters are retained.
        """
        self.assertEqual(_make_canonical_query_string(
            urlparse.urlparse("https://www.amazon.com/path?q")),
                         "q=")

    def test_unique_query_parameters_sorted(self):
        """
        Unique query parameters are sorted.
        """
        self.assertEqual(
            _make_canonical_query_string(
                urlparse.urlparse('http://www.amazon.com/path?b=1&a=2')),
            "a=2&b=1",
        )

    def test_duplicate_query_parameters_sorted(self):
        """
        Duplicate query parameters are sorted.
        """
        self.assertEqual(
            _make_canonical_query_string(
                urlparse.urlparse('http://www.amazon.com/path?a=2&a=1&b=3')),
            "a=1&a=2&b=3",
        )

    def test_query_params_url_encoded(self):
        """
        Query parameters are URL encoded.
        """
        self.assertEqual(
            _make_canonical_query_string(
                urlparse.urlparse('http://www.amazon.com/path?%21=%25')),
            "%21=%25",
        )



class CanonicalRequestTests(unittest.SynchronousTestCase):
    """
    Tests for L{_CanonicalRequest}.
    """

    def setUp(self):
        self.request = _create_canonical_request_fixture()

    def test_serialize(self):
        """
        A canonical request is serialized as sequence of lines,
        consisting of:

            1. the request method

            2. the URI

            3. the query string (an empty line if not present)

            4. the canonical headers

            5. The signed headers

            6. The hex digest of the payload hash

        See
        U{http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html}
        """
        self.assertEqual(self.request.serialize(), textwrap.dedent("""\
        POST
        /
        qs
        headers
        signed headers
        payload hash"""))

    def test_hash(self):
        """
        A canonical request's hash is the SHA-256 of its serialization.
        """
        self.assertEqual(self.request.hash(),
                         hashlib.sha256(self.request.serialize()).hexdigest())

    def test_hash_sanity(self):
        """
        The fixture canonical request's hash matches a precalculated
        value.
        """
        self.assertEqual(self.request.hash(),
                         "273e3d9c0252e987180c1d05241ec5a7f8089b9c1652ccc09ccf"
                         "097d8cf33a4b")

    def test_from_payload_and_headers(self):
        """
        An instance is created from the given payload and headers.
        """
        url = 'https://www.amazon.com/blah?b=2&b=1&a=0'

        canonical_request = _CanonicalRequest.from_payload_and_headers(
            method="POST",
            url=url,
            headers={"header1": "value1",
                     "header2": "value2"},
            headers_to_sign=("header1", "header2"),
            payload="payload"
        )

        self.assertEqual(canonical_request.method, "POST")
        self.assertEqual(canonical_request.canonical_uri,
                         "https://www.amazon.com/blah")
        self.assertEqual(canonical_request.canonical_query_string,
                         "a=0&b=1&b=2")
        self.assertEqual(canonical_request.canonical_headers,
                         textwrap.dedent("""\
                         header1:value1
                         header2:value2
                         """))
        self.assertEqual(canonical_request.signed_headers, "header1;header2")
        self.assertEqual(canonical_request.payload_hash,
                         "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9"
                         "b852d5a935e5")


class CredentialScopeTests(unittest.SynchronousTestCase):
    """
    Tests for L{_CredentialScope}.
    """

    def test_serialize(self):
        """
        A credential scope is serialized as a slash (C{/}) delimited
        sequence that ends with the special value C{aws4_request} and
        consist of:

            1. the date

            2. a region

            3. a service

        See
        U{http://docs.aws.amazon.com/general/latest/gr/sigv4_changes.html}
        """
        scope = _create_credential_scope_fixture()
        self.assertEqual(scope.serialize(),
                         "date stamp/region/service/aws4_request")


class _CredentialTests(unittest.SynchronousTestCase):
    """
    Tests for L{_Credential}.
    """

    def test_serialize(self):
        """
        A version 4 authorization credential is serialized as slash
        (C{/}) delimited sequence, consisting of:

            1. an access key

            2. a credential scope
        """
        scope = _create_credential_scope_fixture()
        credential = _create_credential_fixture(scope)

        self.assertEqual(credential.serialize(), "key/" + scope.serialize())


class SignableAWS4HMAC256TokenTests(unittest.SynchronousTestCase):
    """
    Tests for L{_SignableAWS4HMAC256Token}.
    """

    def setUp(self):
        self.amz_date = '20161227121212Z'
        self.scope = _create_credential_scope_fixture()
        self.request = _create_canonical_request_fixture()
        self.key = "some key"
        self.token = _SignableAWS4HMAC256Token(self.amz_date,
                                               self.scope,
                                               self.request)

    def test_serialize(self):
        """
        The token serializes to an ordered sequence of lines,
        consisting of:

            1. the algorithm (fixed to C{AWS-HMAC-SHA256})

            2. the UTC date and time

            3. a credential scope

            4. the hash of a canonical request

        See
        U{http://docs.aws.amazon.com/general/latest/gr/sigv4-create-string-to-sign.html}
        """
        serialized = self.token.serialize()
        self.assertEqual(serialized, textwrap.dedent("""\
        AWS4-HMAC-SHA256
        {date}
        {scope}
        {requestHash}""".format(date=self.amz_date,
                                scope=self.scope.serialize(),
                                requestHash=self.request.hash())))

    def test_signature(self):
        """
        The token's signature is the SHA-256 HMAC of its
        serialization.
        """
        serialized = self.token.serialize()
        serialized_hmac = hmac.new(self.key,
                                   serialized,
                                   hashlib.sha256).hexdigest()
        self.assertEqual(self.token.signature(self.key), serialized_hmac)

    def test_signature_sanity(self):
        """
        The fixture token's hash matches a precalculated value.
        """
        self.assertEqual(self.token.signature(self.key),
                         '5f2f6fc8cd86e51205f64e59c8b8d15ef1381fec001341e685ba'
                         'd17dffcd874f')


class MakeAuthorizationHeaderTests(unittest.TestCase):
    """
    Tests for L{_make_authorization_header}.
    """

    def setUp(self):
        self.region = REGION_US_EAST_1
        self.service = "dynamodb"

        self.request = _CanonicalRequest.from_payload_and_headers(
            method="POST",
            url="/",
            headers={
                "Some header": "X",
                "content-type": "some/type",
                "x-amz-target": "the target",
                "host": "host",
                "x-amz-date": "the date",
            },
            headers_to_sign=('content-type', 'host', 'x-amz-date',
                             'x-amz-security-token', 'x-amz-target'),
            payload="payload",
        )

        self.credentials = AWSCredentials(access_key="access key",
                                          secret_key="secret key")
        self.instant = datetime.datetime(2016, 11, 11, 2, 45, 50)

    def test_value(self):
        """
        An authorization header string is generated from the headers,
        payload, and current time.
        """
        header_value = _make_authorization_header(self.region,
                                                  self.service,
                                                  self.request,
                                                  self.credentials,
                                                  self.instant)
        expected = (
            'AWS4-HMAC-SHA256 '
            'Credential=access key/20161111/us-east-1/dynamodb/aws4_request, '
            'SignedHeaders=content-type;host;x-amz-date;x-amz-target, '
            'Signature=bf627437be9417f488eacc5c2bb0636229c80af5ed3c45d6e40688f'
            '3cdcf4247'
        )

        self.assertEqual(header_value, expected)


@attr.s
class _AWSRequest(object):
    """
    An AWS request fixture.
    """
    method = attr.ib()
    path = attr.ib()
    headers = attr.ib()
    body = attr.ib()

    @classmethod
    def fromstring(cls, string):
        """
        Parse an AWS request from a string (it's not a real HTTP
        request so it gets its own parser.
        """
        lines = iter(string.splitlines())
        status = next(lines)
        method, path, version = status.split()

        headers = {}
        for line in lines:
            if not line:
                break
            name, _, value = line.partition(':')
            headers[name] = value

        body = ''.join(lines)
        return cls(method, path, headers, body)


class AWS4TestSuite(unittest.SynchronousTestCase):
    """
    Run AWS's V4 signature test suite against L{txaws._auth_v4}.

    See
    U{http://docs.aws.amazon.com/general/latest/gr/signature-v4-test-suite.html}
    """

    def setUp(self):
        self.region = 'us-east-1'
        self.service = 'service'
        self.instant = datetime.datetime(2015, 8, 30, 12, 36, 0)

        self.credential_scope = _CredentialScope(makeDateStamp(self.instant),
                                                 self.region,
                                                 self.service)

        self.access_key = 'AKIDEXAMPLE'
        self.secret_key = 'wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY'
        self.credentials = AWSCredentials(self.access_key, self.secret_key)

        aws4_testsuite_path = os.environ.get("AWS4_TEST_SUITE_PATH")
        if not aws4_testsuite_path:
            raise unittest.SkipTest(
                "AWS4_TEST_SUITE_PATH environment variable not set")

        self.path = filepath.FilePath(aws4_testsuite_path).child(
            'aws4_testsuite')

        if not self.path.isdir():
            raise unittest.SkipTest(
                "Missing AWS test suite directory: {}".format(self.path.path))

    def _globOne(self, path, glob):
        """
        Glob exactly one match under a given path.

        @param path: The path under which to apply the glob.
        @type path: L{filepath.FilePath}

        @param glob: The glob to apply.
        @type glob: L{str}

        @return: The matched path.
        @rtype: L{filepath.FilePath}
        """
        paths = path.globChildren(glob)
        self.assertEqual(
            len(paths), 1,
            "{} did not match exactly one file in {}.".format(glob,
                                                              path))
        return paths[0]

    def _test_canonical_request(self, path):
        """
        Extract AWS request and canonical request fixtures from path,
        and compare a L{_CanonicalRequest} instance constructed from
        the request to the canonical request.

        @return: The constructed canonical request
        @rtype: L{_CanonicalRequest}
        """
        request_path = self._globOne(path, '*.req')
        canonical_request_path = self._globOne(path, '*.creq')

        with request_path.open() as f:
            request = _AWSRequest.fromstring(f.read())

        with canonical_request_path.open() as f:
            serialized_canonical_request = f.read()

        canonical_request = _CanonicalRequest.from_payload_and_headers(
            method=request.method,
            url=request.path,
            headers=request.headers,
            headers_to_sign=request.headers.keys(),
            payload=request.body)

        self.assertEqual(canonical_request.serialize(),
                         serialized_canonical_request)
        return canonical_request

    def _test_string_to_sign(self, path, canonical_request):
        """
        Extract an AWS string-to-sign fixture from path and compare it
        to a L{_SignableAWS4HMAC256Token} constructed from the
        provided canonical request.
        """
        string_to_sign_path = self._globOne(path, "*.sts")

        with string_to_sign_path.open() as f:
            string_to_sign = f.read()

        token = _SignableAWS4HMAC256Token(
            makeAMZDate(self.instant),
            credential_scope=self.credential_scope,
            canonical_request=canonical_request)

        self.assertEqual(token.serialize(), string_to_sign)

    def _test_authorization(self, path, canonical_request):
        """
        Extract an AWS authorization fixture from path and compare it
        to the value returned from L{_make_authorization_header},
        constructed from the provided canonical request.
        """

        authorization_path = self._globOne(path, '*.authz')

        with authorization_path.open() as f:
            expected_authorization = f.read()

        signed = _make_authorization_header(self.region,
                                            self.service,
                                            canonical_request,
                                            self.credentials,
                                            self.instant)

        self.assertEqual(signed, expected_authorization)

    def _test_case(self, path):
        canonical_request = self._test_canonical_request(path)
        self._test_string_to_sign(path, canonical_request)
        self._test_authorization(path, canonical_request)

    def test_get_vanilla(self):
        self._test_case(self.path.child("get-vanilla"))

    def test_post_vanilla(self):
        self._test_case(self.path.child("post-vanilla"))

    def test_post_x_www_form_urlencoded(self):
        self._test_case(self.path.child("post-x-www-form-urlencoded"))

    def test_post_x_www_form_urlencoded_parameters(self):
        self._test_case(
            self.path.child("post-x-www-form-urlencoded-parameters"))

    def test_get_vanilla_empty_query_key(self):
        self._test_case(self.path.child("get-vanilla-empty-query-key"))

    def test_get_vanilla_query(self):
        self._test_case(self.path.child("get-vanilla-query"))

    def test_post_vanilla_query(self):
        self._test_case(self.path.child("post-vanilla-query"))

    def test_get_vanilla_query_order_key_case(self):
        self._test_case(self.path.child("get-vanilla-query-order-key-case"))

    def test_get_vanilla_utf8_query(self):
        self._test_case(self.path.child("get-vanilla-utf8-query"))
