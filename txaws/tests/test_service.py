# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from txaws.credentials import AWSCredentials
from txaws.ec2.client import EC2Client
try:
    from txaws.s3.client import S3Client
except ImportError:
    s3clientSkip = ("S3Client couldn't be imported (perhaps because epsilon, "
                    "on which it depends, isn't present)")
else:
    s3clientSkip = None

from txaws.service import (AWSServiceEndpoint, AWSServiceRegion,
                           EC2_ENDPOINT_EU, EC2_ENDPOINT_US, REGION_EU)
from txaws.testing.base import TXAWSTestCase


class AWSServiceEndpointTestCase(TXAWSTestCase):

    def setUp(self):
        self.endpoint = AWSServiceEndpoint(uri="http://my.service/da_endpoint")

    def test_simple_creation(self):
        endpoint = AWSServiceEndpoint()
        self.assertEquals(endpoint.scheme, "http")
        self.assertEquals(endpoint.host, "")
        self.assertEquals(endpoint.port, None)
        self.assertEquals(endpoint.path, "/")
        self.assertEquals(endpoint.method, "GET")

    def test_custom_method(self):
        endpoint = AWSServiceEndpoint(
            uri="http://service/endpoint", method="PUT")
        self.assertEquals(endpoint.method, "PUT")

    def test_parse_uri(self):
        self.assertEquals(self.endpoint.scheme, "http")
        self.assertEquals(self.endpoint.host, "my.service")
        self.assertIdentical(self.endpoint.port, None)
        self.assertEquals(self.endpoint.path, "/da_endpoint")

    def test_parse_uri_https_and_custom_port(self):
        endpoint = AWSServiceEndpoint(uri="https://my.service:8080/endpoint")
        self.assertEquals(endpoint.scheme, "https")
        self.assertEquals(endpoint.host, "my.service")
        self.assertEquals(endpoint.port, 8080)
        self.assertEquals(endpoint.path, "/endpoint")

    def test_get_uri(self):
        uri = self.endpoint.get_uri()
        self.assertEquals(uri, "http://my.service/da_endpoint")

    def test_get_uri_custom_port(self):
        uri = "https://my.service:8080/endpoint"
        endpoint = AWSServiceEndpoint(uri=uri)
        new_uri = endpoint.get_uri()
        self.assertEquals(new_uri, uri)

    def test_set_host(self):
        self.assertEquals(self.endpoint.host, "my.service")
        self.endpoint.set_host("newhost.com")
        self.assertEquals(self.endpoint.host, "newhost.com")

    def test_get_host(self):
        self.assertEquals(self.endpoint.host, self.endpoint.get_host())

    def test_get_canonical_host(self):
        """
        If the port is not specified the canonical host is the same as
        the host.
        """
        uri = "http://my.service/endpoint"
        endpoint = AWSServiceEndpoint(uri=uri)
        self.assertEquals("my.service", endpoint.get_canonical_host())

    def test_get_canonical_host_with_non_default_port(self):
        """
        If the port is not the default, the canonical host includes it.
        """
        uri = "http://my.service:99/endpoint"
        endpoint = AWSServiceEndpoint(uri=uri)
        self.assertEquals("my.service:99", endpoint.get_canonical_host())

    def test_get_canonical_host_is_lower_case(self):
        """
        The canonical host is guaranteed to be lower case.
        """
        uri = "http://MY.SerVice:99/endpoint"
        endpoint = AWSServiceEndpoint(uri=uri)
        self.assertEquals("my.service:99", endpoint.get_canonical_host())

    def test_set_canonical_host(self):
        """
        The canonical host is converted to lower case.
        """
        endpoint = AWSServiceEndpoint()
        endpoint.set_canonical_host("My.Service")
        self.assertEquals("my.service", endpoint.host)
        self.assertIdentical(None, endpoint.port)

    def test_set_canonical_host_with_port(self):
        """
        The canonical host can optionally have a port.
        """
        endpoint = AWSServiceEndpoint()
        endpoint.set_canonical_host("my.service:99")
        self.assertEquals("my.service", endpoint.host)
        self.assertEquals(99, endpoint.port)

    def test_set_canonical_host_with_empty_port(self):
        """
        The canonical host can also have no port.
        """
        endpoint = AWSServiceEndpoint()
        endpoint.set_canonical_host("my.service:")
        self.assertEquals("my.service", endpoint.host)
        self.assertIdentical(None, endpoint.port)

    def test_set_path(self):
        self.endpoint.set_path("/newpath")
        self.assertEquals(
            self.endpoint.get_uri(),
            "http://my.service/newpath")

    def test_set_method(self):
        self.assertEquals(self.endpoint.method, "GET")
        self.endpoint.set_method("PUT")
        self.assertEquals(self.endpoint.method, "PUT")


class AWSServiceRegionTestCase(TXAWSTestCase):

    def setUp(self):
        self.creds = AWSCredentials("foo", "bar")
        self.region = AWSServiceRegion(creds=self.creds)

    def test_simple_creation(self):
        self.assertEquals(self.creds, self.region.creds)
        self.assertEquals(self.region._clients, {})
        self.assertEquals(self.region.ec2_endpoint.get_uri(), EC2_ENDPOINT_US)

    def test_creation_with_keys(self):
        region = AWSServiceRegion(access_key="baz", secret_key="quux")
        self.assertEquals(region.creds.access_key, "baz")
        self.assertEquals(region.creds.secret_key, "quux")

    def test_creation_with_keys_and_creds(self):
        """
        creds take precedence over individual access key/secret key pairs.
        """
        region = AWSServiceRegion(self.creds, access_key="baz",
                                  secret_key="quux")
        self.assertEquals(region.creds.access_key, "foo")
        self.assertEquals(region.creds.secret_key, "bar")

    def test_creation_with_uri(self):
        region = AWSServiceRegion(
            creds=self.creds, ec2_uri="http://foo/bar")
        self.assertEquals(region.ec2_endpoint.get_uri(), "http://foo/bar")

    def test_creation_with_uri_backwards_compatible(self):
        region = AWSServiceRegion(
            creds=self.creds, uri="http://foo/bar")
        self.assertEquals(region.ec2_endpoint.get_uri(), "http://foo/bar")

    def test_creation_with_uri_and_region(self):
        region = AWSServiceRegion(
            creds=self.creds, region=REGION_EU, ec2_uri="http://foo/bar")
        self.assertEquals(region.ec2_endpoint.get_uri(), "http://foo/bar")

    def test_creation_with_region_override(self):
        region = AWSServiceRegion(creds=self.creds, region=REGION_EU)
        self.assertEquals(region.ec2_endpoint.get_uri(), EC2_ENDPOINT_EU)

    def test_get_ec2_client_with_empty_cache(self):
        key = str(EC2Client) + str(self.creds) + str(self.region.ec2_endpoint)
        original_client = self.region._clients.get(key)
        new_client = self.region.get_client(
            EC2Client, creds=self.creds, endpoint=self.region.ec2_endpoint)
        self.assertEquals(original_client, None)
        self.assertTrue(isinstance(new_client, EC2Client))
        self.assertNotEquals(original_client, new_client)

    def test_get_ec2_client_from_cache_default(self):
        client1 = self.region.get_ec2_client()
        client2 = self.region.get_ec2_client()
        self.assertTrue(isinstance(client1, EC2Client))
        self.assertTrue(isinstance(client2, EC2Client))
        self.assertEquals(client1, client2)

    def test_get_ec2_client_from_cache(self):
        client1 = self.region.get_client(
            EC2Client, creds=self.creds, endpoint=self.region.ec2_endpoint)
        client2 = self.region.get_client(
            EC2Client, creds=self.creds, endpoint=self.region.ec2_endpoint)
        self.assertTrue(isinstance(client1, EC2Client))
        self.assertTrue(isinstance(client2, EC2Client))
        self.assertEquals(client1, client2)

    def test_get_ec2_client_from_cache_with_purge(self):
        client1 = self.region.get_client(
            EC2Client, creds=self.creds, endpoint=self.region.ec2_endpoint,
            purge_cache=True)
        client2 = self.region.get_client(
            EC2Client, creds=self.creds, endpoint=self.region.ec2_endpoint,
            purge_cache=True)
        self.assertTrue(isinstance(client1, EC2Client))
        self.assertTrue(isinstance(client2, EC2Client))
        self.assertNotEquals(client1, client2)

    def test_get_s3_client_with_empty_cache(self):
        key = str(S3Client) + str(self.creds) + str(self.region.s3_endpoint)
        original_client = self.region._clients.get(key)
        new_client = self.region.get_client(
            S3Client, creds=self.creds, endpoint=self.region.s3_endpoint)
        self.assertEquals(original_client, None)
        self.assertTrue(isinstance(new_client, S3Client))
        self.assertNotEquals(original_client, new_client)
    test_get_s3_client_with_empty_cache.skip = s3clientSkip
