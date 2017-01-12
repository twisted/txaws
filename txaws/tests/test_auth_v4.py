# Licenced under the txaws licence available at /LICENSE in the txaws source.
"""
Unit tests for AWS authorization, version 4.
"""

import datetime
import hashlib
import hmac
import urlparse

from twisted.trial import unittest

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
                             signed_headers=b"signed headers",
                             payload_hash=b"payload hash")


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


class AWS4FunctionTestCase(unittest.SynchronousTestCase):
    """
    Tests for AWS4 signing support functions.
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


class MakeCanonicalHeadersTestCase(unittest.SynchronousTestCase):
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
            headers={b"header": b"value",
                     b"signed-header": b"signed-value",
                     b"other-signed-header": b"other-signed-value"},
            headers_to_sign=(b"signed-header", b"other-signed-header"))
        self.assertEqual(canonical,
                         (b"other-signed-header:other-signed-value\n"
                          b"signed-header:signed-value\n"))

    def test_headers_sorted(self):
        """
        The canonical headers are sorted.
        """
        canonical = _make_canonical_headers(
            headers={b"b": b"2",
                     b"a": b"1",
                     b"c": b"3"},
            headers_to_sign=(b'a', b'b', b'c'))
        self.assertEqual(canonical, (b"a:1\n"
                                     b"b:2\n"
                                     b"c:3\n"))

    def _test_headers_multivalued(self, headers):
        """
        Internal support method for testing headers.

        @param headers: A dictionary with a single key, C{b'a'}, and
            the values C{b'b'} and C{b'c} in either a list or a tuple,
            or separated by newlines.
        @type headers: L{dict}
        """
        canonical = _make_canonical_headers(
            headers=headers,
            headers_to_sign=(b"a",),
        )
        self.assertEqual(canonical, b"a:b,c\n")

    def test_multivalued_list(self):
        """
        A Header with multiple values in a list has those values
        joined by a comma.
        """
        self._test_headers_multivalued({b'a': [b'b', b'c']})

    def test_multivalued_tuple(self):
        """
        A Header with multiple values in a tuple has those values
        joined by a comma.
        """
        self._test_headers_multivalued({b'a': (b'b', b'c')})

    def test_multiline(self):
        """
        A header whose value spans multiple lines has those lines
        joined by commas.
        """
        self._test_headers_multivalued({b'a': (b'b\nc')})

    def test_value_trimmed(self):
        """
        A header with interior spaces has those normalized to single
        spaces.
        """
        canonical = _make_canonical_headers(
            headers={b"a": b"b  c  d"},
            headers_to_sign=(b"a",),
        )
        self.assertEqual(canonical, "a:b c d\n")


class MakeSignedHeadersTestCase(unittest.TestCase):
    """
    Tests for L{_make_signed_headers}.
    """

    def test_only_names_included(self):
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


class MakeCanonicalURITestCase(unittest.SynchronousTestCase):
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

    def test_path_url_encoded(self):
        """
        A path is URL encoded when necessary.
        """
        parsed = urlparse.urlparse('https://www.amazon.com/\xe2')
        self.assertEqual(_make_canonical_uri(parsed),
                         "https://www.amazon.com/%E2")


class MakeCanonicalQueryStringTestCase(unittest.SynchronousTestCase):
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


class CanonicalRequestTestCase(unittest.SynchronousTestCase):
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
        self.assertEqual(self.request.serialize(),
                         (b"POST\n"
                          b"/\n"
                          b"qs\n"
                          b"headers\n"
                          b"signed headers\n"
                          b"payload hash"))

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

    def test_from_request_components(self):
        """
        An instance is created from the given payload hash and headers.
        """
        url = 'https://www.amazon.com/blah?b=2&b=1&a=0'

        canonical_request = _CanonicalRequest.from_request_components(
            method="POST",
            url=url,
            headers={b"header1": b"value1",
                     b"header2": b"value2"},
            headers_to_sign=(b"header1", b"header2"),
            payload_hash=b"abcdef",
        )
        self.assertEqual(canonical_request.method, "POST")
        self.assertEqual(canonical_request.canonical_uri,
                         "https://www.amazon.com/blah")
        self.assertEqual(canonical_request.canonical_query_string,
                         "a=0&b=1&b=2")
        self.assertEqual(canonical_request.canonical_headers,
                         (b"header1:value1\n"
                          b"header2:value2\n"))
        self.assertEqual(canonical_request.signed_headers, "header1;header2")
        self.assertEqual(canonical_request.payload_hash, b"abcdef")


    def test_from_request_components_unsigned_payload(self):
        """
        An instance is created with the magic "unsigned payload" string
        and the given headers.
        """
        url = 'https://www.amazon.com/blah?b=2&b=1&a=0'

        canonical_request = _CanonicalRequest.from_request_components(
            method="POST",
            url=url,
            headers={b"header1": b"value1",
                     b"header2": b"value2"},
            headers_to_sign=(b"header1", b"header2"),
            payload_hash=None,
        )
        self.assertEqual(canonical_request.method, "POST")
        self.assertEqual(canonical_request.canonical_uri,
                         "https://www.amazon.com/blah")
        self.assertEqual(canonical_request.canonical_query_string,
                         "a=0&b=1&b=2")
        self.assertEqual(canonical_request.canonical_headers,
                         (b"header1:value1\n"
                          b"header2:value2\n"))
        self.assertEqual(canonical_request.signed_headers, "header1;header2")
        self.assertEqual(canonical_request.payload_hash, b"UNSIGNED-PAYLOAD")

    def test_from_request_components_and_payload(self):
        """
        An instance is created from the given payload and headers.
        """
        url = 'https://www.amazon.com/blah?b=2&b=1&a=0'

        canonical_request = _CanonicalRequest.from_request_components_and_payload(
            method="POST",
            url=url,
            headers={b"header1": b"value1",
                     b"header2": b"value2"},
            headers_to_sign=(b"header1", b"header2"),
            payload=b"payload"
        )

        self.assertEqual(canonical_request.method, "POST")
        self.assertEqual(canonical_request.canonical_uri,
                         "https://www.amazon.com/blah")
        self.assertEqual(canonical_request.canonical_query_string,
                         "a=0&b=1&b=2")
        self.assertEqual(canonical_request.canonical_headers,
                         (b"header1:value1\n"
                          b"header2:value2\n"))
        self.assertEqual(canonical_request.signed_headers, "header1;header2")
        self.assertEqual(canonical_request.payload_hash,
                         "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9"
                         "b852d5a935e5")


class CredentialScopeTestCase(unittest.SynchronousTestCase):
    """
    Tests for L{_CredentialScope}.
    """

    def test_serialize(self):
        """
        A credential scope is serialized as a slash (C{/}) delimited
        sequence that ends with the special value C{aws4_request} and
        consists of:

            1. the date

            2. a region

            3. a service

        See
        U{http://docs.aws.amazon.com/general/latest/gr/sigv4_changes.html}
        """
        scope = _create_credential_scope_fixture()
        self.assertEqual(scope.serialize(),
                         "date stamp/region/service/aws4_request")


class CredentialTestCase(unittest.SynchronousTestCase):
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


class SignableAWS4HMAC256TokenTestCase(unittest.SynchronousTestCase):
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
        self.assertEqual(serialized,
                         (b"AWS4-HMAC-SHA256\n"
                          b"%(date)s\n"
                          b"%(scope)s\n"
                          b"%(request_hash)s" % {
                              b"date": self.amz_date,
                              b"scope": self.scope.serialize(),
                              b"request_hash": self.request.hash(),
                          }))

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


class MakeAuthorizationHeaderTestCase(unittest.TestCase):
    """
    Tests for L{_make_authorization_header}.
    """

    def setUp(self):
        self.region = REGION_US_EAST_1
        self.service = "dynamodb"

        self.request = _CanonicalRequest.from_request_components_and_payload(
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
