# Licenced under the txaws licence available at /LICENSE in the txaws source.
"""
Integration tests for AWS authorization, version 4.

See
U{http://docs.aws.amazon.com/general/latest/gr/signature-v4-test-suite.html}
"""

import attr
import datetime
import re

from twisted.trial import unittest
from twisted.python import filepath
from twisted.internet.error import ConnectionDone
from twisted.web.http import HTTPChannel
from twisted.test.proto_helpers import StringTransport

from txaws._auth_v4 import (
    _CanonicalRequest,
    _CredentialScope,
    _make_authorization_header,
    makeDateStamp,
    makeAMZDate,
    _SignableAWS4HMAC256Token,
)
from txaws.credentials import AWSCredentials


_UNRESERVED_SKIP = "urllib.quote quotes unreserved characters."
_NOT_YET_SUPPORTED_SKIP = "Not yet supported."

_SKIPS = {
    "get-unreserved": _UNRESERVED_SKIP,
    "get-vanilla-query-unreserved": _UNRESERVED_SKIP,
    # path normalization needs to be conditional, as S3 URLs should
    # *not* be normalized.
    "normalize-path/get-relative": _NOT_YET_SUPPORTED_SKIP,
    "normalize-path/get-relative-relative": _NOT_YET_SUPPORTED_SKIP,
    "normalize-path/get-slash": _NOT_YET_SUPPORTED_SKIP,
    "normalize-path/get-slash-dot-slash": _NOT_YET_SUPPORTED_SKIP,
    "normalize-path/get-slash-pointless-dot": _NOT_YET_SUPPORTED_SKIP,
    "normalize-path/get-slashes": _NOT_YET_SUPPORTED_SKIP,
    "normalize-path/get-space": _NOT_YET_SUPPORTED_SKIP,
    "post-sts-token/post-sts-header-before": _NOT_YET_SUPPORTED_SKIP,
    "post-vanilla-query-nonunreserved": _UNRESERVED_SKIP,
    "post-vanilla-query-space": _NOT_YET_SUPPORTED_SKIP,
}


@attr.s(frozen=True)
class _AWSRequest(object):
    """
    An AWS request fixture.

    @ivar method: The request's method.
    @type method: L{bytes}

    @ivar path: The request's path.
    @type path: L{bytes}

    @ivar headers: The request's headers.
    @type headers: L{dict}

    @ivar body: The request's body.
    @type body: L{bytes}
    """
    method = attr.ib()
    path = attr.ib()
    headers = attr.ib()
    body = attr.ib()

    @classmethod
    def frombytes(cls, byte_string):
        """
        Parse an AWS request from a byte string.

        @param byte_string: The request as parsed from a C{.req} file.
        @type byte_string: L{bytes}

        @return: A request object.
        @rtype: L{_AWSRequest}
        """
        # Ensure there's a blank line so that status and header
        # parsing completes.
        blank_line = b'\n\n'
        if blank_line not in byte_string:
            byte_string += blank_line

        channel = HTTPChannel()
        channel.delimiter = b'\n'
        channel.makeConnection(StringTransport())
        channel.dataReceived(byte_string)
        channel.connectionLost(ConnectionDone())
        request = channel.requests[-1]

        method = request.method
        path = request.uri
        headers = dict(request.requestHeaders.getAllRawHeaders())
        # what comes after the empty line is a
        body = byte_string.split(blank_line, 1)[-1]

        return cls(method, path, headers, body)


class _AWS4TestSuiteTestCaseMixin(object):
    """
    Run AWS's V4 signature test suite.  This is a base class for
    auto-generated tests.

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
        Extract AWS request and canonical request fixtures from
        C{path}, and compare a L{_CanonicalRequest} instance
        constructed from the request to the canonical request.

        @return: The constructed canonical request
        @rtype: L{_CanonicalRequest}
        """
        request_path = self._globOne(path, '*.req')
        canonical_request_path = self._globOne(path, '*.creq')

        with request_path.open() as f:
            request = _AWSRequest.frombytes(f.read())

        with canonical_request_path.open() as f:
            serialized_canonical_request = f.read()

        canonical_request = _CanonicalRequest.from_request_components_and_payload(
            method=request.method,
            url=request.path,
            headers=request.headers,
            headers_to_sign=request.headers.keys(),
            payload=request.body,
        )

        self.assertEqual(canonical_request.serialize(),
                         serialized_canonical_request)
        return canonical_request

    def _test_string_to_sign(self, path, canonical_request):
        """
        Extract an AWS string-to-sign fixture from C{path} and compare it
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
        Extract an AWS authorization fixture from C{path} and compare
        it to the value returned from L{_make_authorization_header},
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


_RENAME_FILE = re.compile('[/-]')


def _build_test_method(test_suite_path, fixture_path):
    """
    Construct a test method, to be added to a
    L{_AWS4TestSuiteTestCaseMixin} subclass, that runs a test against
    the given fixture path.

    The test method's name will be its path, with slashes (C{/}) and
    dashes (C{-}) replaced with underscores (C{_})

    @param test_suite_path: The path to for the directory that
        contains I{all} AWS test suite fixtures.
    @type: test_suite_path: L{filepath.FilePath}

    @param: fixture_path: The path for the particular fixture that
        this test method will test.
    @type: fixture_path: L{filepath.FilePath}

    @return: A function intended to be used as test method.
    @rtype: L{types.FunctionType}
    """
    def method(self):
        self._test_case(fixture_path)

    relative = fixture_path.path.replace(test_suite_path.path, '').lstrip('/')
    skip_reason = _SKIPS.get(relative)
    if skip_reason:
        method.skip = skip_reason

    name = 'test_' + _RENAME_FILE.sub('_', relative)

    method.__name__ = name
    return method


def _collect_fixture_directories(path):
    """
    Yield all the AWS fixture directories under the given path.

    @param path: The path to for the directory that
        contains I{all} AWS test suite fixtures.
    @type: path: L{filepath.FilePath}

    @returns: All the unique fixture directories.
    @rtype: A L{list} of L{filepath.FilePath}s
    """
    seen = set()
    for descendent in path.walk(lambda path: path not in seen):
        # a directory is a fixture directory if it has a .req file in
        # it
        if descendent.globChildren("*.req"):
            seen.add(descendent)

    return sorted(seen)


def test_suite():
    """
    Generate a test suite from the fixture directory.
    """
    path = filepath.FilePath(__file__).parent().child(
        'aws4_testsuite').child('aws4_testsuite')

    methods = {}
    for fixture_path in _collect_fixture_directories(path):
        method = _build_test_method(path, fixture_path)
        methods[method.__name__] = method

    suite = unittest.TestSuite()
    suite.name = "test_aws4_testsuite"

    test_class = type("AWS4TestSuiteTestCase",
                      (_AWS4TestSuiteTestCaseMixin,
                       unittest.SynchronousTestCase),
                      methods)
    for method_name in sorted(methods):
        test = test_class(method_name)
        suite.addTest(test)

    if not methods:
        empty_tests = test_class()
        empty_tests.skip = "Missing AWS test suite directory: {}".format(
            path.path)
        suite.addTest(empty_tests)

    return suite
