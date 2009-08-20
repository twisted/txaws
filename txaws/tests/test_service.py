# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from txaws.credentials import AWSCredentials
from txaws.service import AWSService
from txaws.tests import TXAWSTestCase


class AWSServiceTestCase(TXAWSTestCase):

    def setUp(self):
        self.creds = AWSCredentials("foo", "secretfoo")
        self.service = AWSService(self.creds, "http://my.service/da_endpoint")

    def test_simple_creation(self):
        service = AWSService(self.creds)
        self.assertEquals(service.creds, self.creds)
        self.assertEquals(service.schema, "")
        self.assertEquals(service.host, "")
        self.assertEquals(service.port, 80)
        self.assertEquals(service.endpoint, "/")

    def test_parse_url(self):
        self.assertEquals(self.service.schema, "http")
        self.assertEquals(self.service.host, "my.service")
        self.assertEquals(self.service.port, 80)
        self.assertEquals(self.service.endpoint, "/da_endpoint")

    def test_parse_url_https_and_custom_port(self):
        service = AWSService(self.creds, "https://my.service:8080/endpoint")
        self.assertEquals(service.schema, "https")
        self.assertEquals(service.host, "my.service")
        self.assertEquals(service.port, 8080)
        self.assertEquals(service.endpoint, "/endpoint")

    def test_get_url(self):
        url = self.service.get_url()
        self.assertEquals(url, "http://my.service/da_endpoint")

    def test_get_url_custom_port(self):
        url = "https://my.service:8080/endpoint"
        service = AWSService(self.creds, url)
        new_url = service.get_url()
        self.assertEquals(new_url, url)
