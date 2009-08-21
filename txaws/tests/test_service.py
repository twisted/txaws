# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import os

from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint, AWSServiceRegion
from txaws.tests import TXAWSTestCase

class AWSServiceEndpointTestCase(TXAWSTestCase):

    def setUp(self):
        self.endpoint = AWSServiceEndpoint(uri="http://my.service/da_endpoint")

    def test_simple_creation(self):
        endpoint = AWSServiceEndpoint()
        self.assertEquals(endpoint.scheme, "http")
        self.assertEquals(endpoint.host, "")
        self.assertEquals(endpoint.port, 80)
        self.assertEquals(endpoint.path, "/")
        self.assertEquals(endpoint.method, "GET")

    def test_parse_uri(self):
        self.assertEquals(self.endpoint.scheme, "http")
        self.assertEquals(self.endpoint.host, "my.service")
        self.assertEquals(self.endpoint.port, 80)
        self.assertEquals(self.endpoint.path, "/da_endpoint")

    def test_parse_uri_https_and_custom_port(self):
        endpoint = AWSServiceEndpoint(uri="https://my.service:8080/endpoint")
        self.assertEquals(endpoint.scheme, "https")
        self.assertEquals(endpoint.host, "my.service")
        self.assertEquals(endpoint.port, 8080)
        self.assertEquals(endpoint.path, "/endpoint")

    def test_custom_method(self):
        endpoint = AWSServiceEndpoint(uri="http://service/endpoint",
                                      method="PUT")
        self.assertEquals(endpoint.method, "PUT")

    def test_get_uri(self):
        uri = self.endpoint.get_uri()
        self.assertEquals(uri, "http://my.service/da_endpoint")

    def test_get_uri_custom_port(self):
        uri = "https://my.service:8080/endpoint"
        endpoint = AWSServiceEndpoint(uri=uri)
        new_uri = endpoint.get_uri()
        self.assertEquals(new_uri, uri)

    def test_set_path(self):
        original_path = self.endpoint.path
        self.endpoint.set_path("/newpath")
        self.assertEquals(
            self.endpoint.get_uri(),
            "http://my.service/newpath")
