# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import os

from txaws.service import AWSService, ENV_ACCESS_KEY, ENV_SECRET_KEY
from txaws.tests import TXAWSTestCase


class AWSServiceTestCase(TXAWSTestCase):

    def setUp(self):
        self.service = AWSService("fookeyid", "barsecretkey",
                                  "http://my.service/da_endpoint")
        self.addCleanup(self.clean_environment)

    def clean_environment(self):
        if os.environ.has_key(ENV_ACCESS_KEY):
            del os.environ[ENV_ACCESS_KEY]
        if os.environ.has_key(ENV_SECRET_KEY):
            del os.environ[ENV_SECRET_KEY]

    def test_simple_creation(self):
        service = AWSService("fookeyid", "barsecretkey")
        self.assertEquals(service.access_key, "fookeyid")
        self.assertEquals(service.secret_key, "barsecretkey")
        self.assertEquals(service.schema, "")
        self.assertEquals(service.host, "")
        self.assertEquals(service.port, 80)
        self.assertEquals(service.endpoint, "/")
        self.assertEquals(service.method, "GET")

    def test_no_access_errors(self):
        # Without anything in os.environ, AWSService() blows up
        os.environ[ENV_SECRET_KEY] = "bar"
        self.assertRaises(ValueError, AWSService)

    def test_no_secret_errors(self):
        # Without anything in os.environ, AWSService() blows up
        os.environ[ENV_ACCESS_KEY] = "foo"
        self.assertRaises(ValueError, AWSService)

    def test_found_values_used(self):
        os.environ[ENV_ACCESS_KEY] = "foo"
        os.environ[ENV_SECRET_KEY] = "bar"
        service = AWSService()
        self.assertEqual("foo", service.access_key)
        self.assertEqual("bar", service.secret_key)
        self.clean_environment()

    def test_explicit_access_key(self):
        os.environ[ENV_SECRET_KEY] = "foo"
        service = AWSService(access_key="bar")
        self.assertEqual("foo", service.secret_key)
        self.assertEqual("bar", service.access_key)

    def test_explicit_secret_key(self):
        os.environ[ENV_ACCESS_KEY] = "bar"
        service = AWSService(secret_key="foo")
        self.assertEqual("foo", service.secret_key)
        self.assertEqual("bar", service.access_key)

    def test_parse_url(self):
        self.assertEquals(self.service.schema, "http")
        self.assertEquals(self.service.host, "my.service")
        self.assertEquals(self.service.port, 80)
        self.assertEquals(self.service.endpoint, "/da_endpoint")

    def test_parse_url_https_and_custom_port(self):
        service = AWSService("foo", "bar", "https://my.service:8080/endpoint")
        self.assertEquals(service.schema, "https")
        self.assertEquals(service.host, "my.service")
        self.assertEquals(service.port, 8080)
        self.assertEquals(service.endpoint, "/endpoint")

    def test_custom_method(self):
        service = AWSService("foo", "bar", "http://service/endpoint", "PUT")
        self.assertEquals(service.method, "PUT")

    def test_get_url(self):
        url = self.service.get_url()
        self.assertEquals(url, "http://my.service/da_endpoint")

    def test_get_url_custom_port(self):
        url = "https://my.service:8080/endpoint"
        service = AWSService("foo", "bar", url)
        new_url = service.get_url()
        self.assertEquals(new_url, url)
