# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import os

from txaws.credentials import AWSCredentials
from txaws.ec2.client import EC2Client
from txaws.service import AWSServiceEndpoint, AWSServiceRegion, EC2_ENDPOINT_US
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


class AWSServiceRegionTestCase(TXAWSTestCase):

    def setUp(self):
        self.creds = AWSCredentials("foo", "bar")
        self.region = AWSServiceRegion(creds=self.creds)

    def test_simple_creation(self):
        self.assertEquals(self.creds, self.region.creds)
        self.assertEquals(self.region._clients, {})
        self.assertEquals(self.region.ec2_endpoint.get_uri(), EC2_ENDPOINT_US)

    def test_get_client_with_empty_cache(self):
        key = str(EC2Client) + str(self.creds) + str(self.region.ec2_endpoint)
        original_client = self.region._clients.get(key)
        new_client = self.region.get_client(
            EC2Client, self.creds, self.region.ec2_endpoint)
        self.assertEquals(original_client, None)
        self.assertNotEquals(original_client, new_client)
        self.assertTrue(isinstance(new_client, EC2Client))

    def test_get_client_from_cache(self):
        client1 = self.region.get_client(
            EC2Client, self.creds, self.region.ec2_endpoint)
        client2 = self.region.get_client(
            EC2Client, self.creds, self.region.ec2_endpoint)
        self.assertTrue(isinstance(client1, EC2Client))
        self.assertTrue(isinstance(client2, EC2Client))
        self.assertEquals(client2, client2)

    def test_get_ec2_client_from_cache(self):
        client1 = self.region.get_ec2_client(self.creds)
        client2 = self.region.get_ec2_client(self.creds)
        self.assertEquals(self.creds, self.region.creds)
        self.assertTrue(isinstance(client1, EC2Client))
        self.assertTrue(isinstance(client2, EC2Client))
        self.assertEquals(client2, client2)


    def test_get_s3_client(self):
        self.assertRaises(NotImplementedError, self.region.get_s3_client)

    def test_get_simpledb_client(self):
        self.assertRaises(NotImplementedError, self.region.get_simpledb_client)

    def test_get_sqs_client(self):
        self.assertRaises(NotImplementedError, self.region.get_sqs_client)
