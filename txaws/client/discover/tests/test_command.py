# Copyright (C) 2010 Jamu Kakar <jkakar@kakar.ca>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""Unit tests for L{Command}."""

from cStringIO import StringIO

from twisted.internet.defer import succeed, fail
from twisted.web.error import Error

from txaws.client.discover.command import Command
from txaws.ec2.client import Query
from txaws.testing.base import TXAWSTestCase


class FakeHTTPClient(object):

    def __init__(self, status, url):
        self.status = status
        self.url = url


class CommandTest(TXAWSTestCase):

    def prepare_command(self, response, status, action, parameters={},
                        get_page=None, error=None):
        """Prepare a L{Command} for testing."""
        self.url = None
        self.method = None
        self.error = error
        self.response = response
        self.status = status
        self.output = StringIO()
        self.query = None
        if get_page is None:
            get_page = self.get_page
        self.get_page_function = get_page
        self.command = Command("key", "secret", "endpoint", action, parameters,
                               self.output, self.query_factory)

    def query_factory(self, other_params=None, time_tuple=None,
                      api_version=None, *args, **kwargs):
        """
        Create a query with a hard-coded time to generate a fake response.
        """
        time_tuple = (2010, 6, 4, 23, 40, 0, 0, 0, 0)
        self.query = Query(other_params, time_tuple, api_version,
                           *args, **kwargs)
        self.query.get_page = self.get_page_function
        return self.query

    def get_page(self, url, method=None, timeout=0):
        """Fake C{get_page} method simulates a successful request."""
        self.url = url
        self.method = method
        self.query.client = FakeHTTPClient(self.status, url)
        return succeed(self.response)

    def get_error_page(self, url, method=None, timeout=0):
        """Fake C{get_page} method simulates an error."""
        self.url = url
        self.method = method
        self.query.client = FakeHTTPClient(self.status, url)
        return fail(self.error or Exception(self.response))

    def test_run(self):
        """
        When a method is invoked its HTTP status code and response text is
        written to the output stream.
        """
        self.prepare_command("The response", 200, "DescribeRegions")

        def check(result):
            url = (
                "http://endpoint?AWSAccessKeyId=key&"
                "Action=DescribeRegions&"
                "Signature=uAlV2ALkp7qTxZrTNNuJhHl0i9xiTK5faZOhJTgGS1E%3D&"
                "SignatureMethod=HmacSHA256&SignatureVersion=2&"
                "Timestamp=2010-06-04T23%3A40%3A00Z&Version=2008-12-01")
            self.assertEqual("GET", self.method)
            self.assertEqual(url, self.url)
            self.assertEqual("URL: %s\n"
                             "\n"
                             "HTTP status code: 200\n"
                             "\n"
                             "The response\n" % url,
                             self.output.getvalue())

        deferred = self.command.run()
        deferred.addCallback(check)
        return deferred

    def test_run_with_parameters(self):
        """Extra method parameters are included in the request."""
        self.prepare_command("The response", 200, "DescribeRegions",
                             {"RegionName.0": "us-west-1"})

        def check(result):
            url = (
                "http://endpoint?AWSAccessKeyId=key&"
                "Action=DescribeRegions&RegionName.0=us-west-1&"
                "Signature=P6C7cQJ7j93uIJyv2dTbpQG3EI7ArGBJT%2FzVH%2BDFhyY%3D&"
                "SignatureMethod=HmacSHA256&SignatureVersion=2&"
                "Timestamp=2010-06-04T23%3A40%3A00Z&Version=2008-12-01")
            self.assertEqual("GET", self.method)
            self.assertEqual(url, self.url)
            self.assertEqual("URL: %s\n"
                             "\n"
                             "HTTP status code: 200\n"
                             "\n"
                             "The response\n" % url,
                             self.output.getvalue())

        deferred = self.command.run()
        deferred.addCallback(check)
        return deferred

    def test_run_with_error(self):
        """
        If an error message is returned by the backend cloud, it will be
        written to the output stream.
        """
        self.prepare_command("The error response", 400, "DescribeRegions",
                             {"RegionName.0": "us-west-1"},
                             self.get_error_page)

        def check(result):
            url = (
                "http://endpoint?AWSAccessKeyId=key&"
                "Action=DescribeRegions&RegionName.0=us-west-1&"
                "Signature=P6C7cQJ7j93uIJyv2dTbpQG3EI7ArGBJT%2FzVH%2BDFhyY%3D&"
                "SignatureMethod=HmacSHA256&SignatureVersion=2&"
                "Timestamp=2010-06-04T23%3A40%3A00Z&Version=2008-12-01")
            self.assertEqual("GET", self.method)
            self.assertEqual(url, self.url)
            self.assertEqual("URL: %s\n"
                             "\n"
                             "HTTP status code: 400\n"
                             "\n"
                             "The error response\n" % url,
                             self.output.getvalue())

        deferred = self.command.run()
        return self.assertFailure(deferred, Exception).addErrback(check)

    def test_run_with_error_strips_non_response_text(self):
        """
        The builtin L{AWSError} exception adds 'Error message: ' to beginning
        of the text retuned by the backend cloud.  This is stripped when the
        message is written to the output stream.
        """
        self.prepare_command("Error Message: The error response", 400,
                             "DescribeRegions", {"RegionName.0": "us-west-1"},
                             self.get_error_page)

        def check(result):
            url = (
                "http://endpoint?AWSAccessKeyId=key&"
                "Action=DescribeRegions&RegionName.0=us-west-1&"
                "Signature=P6C7cQJ7j93uIJyv2dTbpQG3EI7ArGBJT%2FzVH%2BDFhyY%3D&"
                "SignatureMethod=HmacSHA256&SignatureVersion=2&"
                "Timestamp=2010-06-04T23%3A40%3A00Z&Version=2008-12-01")
            self.assertEqual("GET", self.method)
            self.assertEqual(url, self.url)
            self.assertEqual("URL: %s\n"
                             "\n"
                             "HTTP status code: 400\n"
                             "\n"
                             "The error response\n" % url,
                             self.output.getvalue())

        deferred = self.command.run()
        deferred.addErrback(check)
        return deferred

    def test_run_with_error_payload(self):
        """
        If the returned HTTP error contains a payload, it's printed out.
        """
        self.prepare_command("Bad Request", 400,
                             "DescribeRegions", {"RegionName.0": "us-west-1"},
                             self.get_error_page, Error(400, None, "bar"))

        def check(result):
            url = (
                "http://endpoint?AWSAccessKeyId=key&"
                "Action=DescribeRegions&RegionName.0=us-west-1&"
                "Signature=P6C7cQJ7j93uIJyv2dTbpQG3EI7ArGBJT%2FzVH%2BDFhyY%3D&"
                "SignatureMethod=HmacSHA256&SignatureVersion=2&"
                "Timestamp=2010-06-04T23%3A40%3A00Z&Version=2008-12-01")
            self.assertEqual("GET", self.method)
            self.assertEqual(url, self.url)
            self.assertEqual("URL: %s\n"
                             "\n"
                             "HTTP status code: 400\n"
                             "\n"
                             "400 Bad Request\n"
                             "\n"
                             "bar\n" % url,
                             self.output.getvalue())

        deferred = self.command.run()
        deferred.addCallback(check)
        return deferred
