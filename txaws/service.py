# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import warnings

from txaws.credentials import AWSCredentials
from txaws import regions
from txaws.util import parse


__all__ = ["AWSServiceEndpoint", "AWSServiceRegion", "REGION_US", "REGION_EU"]


REGION_US = "US"
REGION_EU = "EU"

REGION_US_EAST_1 = "us-east-1"
REGION_US_EAST_2 = "us-east-2"
REGION_US_WEST_1 = "us-west-1"
REGION_US_WEST_2 = "us-west-2"
REGION_CA_CENTRAL_1 = "ca-central-1"
REGION_AP_SOUTH_1 = "ap-south-1"
REGION_AP_NORTHEAST_1 = "ap-northeast-1"
REGION_AP_NORTHEAST_2 = "ap-northeast-2"
REGION_AP_SOUTHEAST_1 = "ap-southeast-1"
REGION_AP_SOUTHEAST_2 = "ap-southeast-2"
REGION_EU_CENTRAL_1 = "eu-central-1"
REGION_EU_WEST_1 = "eu-west-1"
REGION_EU_WEST_2 = "eu-west-2"
REGION_SA_EAST_1 = "sa-east-1"

EC2_ENDPOINT_US = "https://us-east-1.ec2.amazonaws.com/"
EC2_ENDPOINT_EU = "https://eu-west-1.ec2.amazonaws.com/"

S3_ENDPOINT = "https://s3.amazonaws.com/"


class AWSServiceEndpoint(object):
    """
    @param uri: The URL for the service.
    @param method: The HTTP method used when accessing a service.
    @param ssl_hostname_verification: Whether or not SSL hotname verification
        will be done when connecting to the endpoint.
    """

    def __init__(self, uri="", method="GET", ssl_hostname_verification=True):
        self.host = ""
        self.port = None
        self.path = "/"
        self.method = method
        self.ssl_hostname_verification = ssl_hostname_verification
        if not self.ssl_hostname_verification:
            warnings.warn(
                "Operating with certificate verification disabled!", stacklevel=2,
            )
        self._parse_uri(uri)
        if not self.scheme:
            self.scheme = "http"

    def _parse_uri(self, uri):
        scheme, host, port, path = parse(
            str(uri), defaultPort=False)
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path

    def set_host(self, host):
        self.host = host

    def get_host(self):
        return self.host

    def get_canonical_host(self):
        """
        Return the canonical host as for the Host HTTP header specification.
        """
        host = self.host.lower()
        if self.port is not None:
            host = "%s:%s" % (host, self.port)
        return host

    def set_canonical_host(self, canonical_host):
        """
        Set host and port from a canonical host string as for the Host HTTP
        header specification.
        """
        parts = canonical_host.lower().split(":")
        self.host = parts[0]
        if len(parts) > 1 and parts[1]:
            self.port = int(parts[1])
        else:
            self.port = None

    def set_path(self, path):
        self.path = path

    def get_uri(self):
        """Get a URL representation of the service."""
        uri = "%s://%s%s" % (self.scheme, self.get_canonical_host(), self.path)
        return uri

    def set_method(self, method):
        self.method = method


class AWSServiceRegion(object):
    """
    This object represents a collection of client factories that use the same
    credentials. With Amazon, this collection is associated with a region
    (e.g., US or EU).

    @param creds: an AWSCredentials instance, optional.
    @param access_key: The access key to use. This is only checked if no creds
        parameter was passed.
    @param secret_key: The secret key to use. This is only checked if no creds
        parameter was passed.
    @param region: a string value that represents the region that the
        associated creds will be used against a collection of services.
    @param uri: an endpoint URI that, if provided, will override the region
        parameter.
    @param method: The method argument forwarded to L{AWSServiceEndpoint}.
    """
    # XXX update unit test to check for both ec2 and s3 endpoints
    def __init__(self, creds=None, access_key="", secret_key="",
                 region=REGION_US, uri="", ec2_uri="", s3_uri="",
                 method="GET"):
        if not creds:
            creds = AWSCredentials(access_key, secret_key)
        self.creds = creds
        # Provide backwards compatibility for the "uri" parameter.
        if uri and not ec2_uri:
            ec2_uri = uri
        if not ec2_uri and region == REGION_US:
            ec2_uri = EC2_ENDPOINT_US
        elif not ec2_uri and region == REGION_EU:
            ec2_uri = EC2_ENDPOINT_EU
        if not s3_uri:
            s3_uri = S3_ENDPOINT
        self._clients = {}
        self.ec2_endpoint = AWSServiceEndpoint(uri=ec2_uri, method=method)
        self.s3_endpoint = AWSServiceEndpoint(uri=s3_uri, method=method)

    def get_client(self, cls, purge_cache=False, *args, **kwds):
        """
        This is a general method for getting a client: if present, it is pulled
        from the cache; if not, a new one is instantiated and then put into the
        cache. This method should not be called directly, but rather by other
        client-specific methods (e.g., get_ec2_client).
        """
        key = str(cls) + str(args) + str(kwds)
        instance = self._clients.get(key)
        if purge_cache or not instance:
            instance = cls(*args, **kwds)
        self._clients[key] = instance
        return instance


    def get_ec2_client(self, creds=None):
        from txaws.ec2.client import EC2Client

        if creds:
            self.creds = creds
        return self.get_client(EC2Client, creds=self.creds,
                               endpoint=self.ec2_endpoint, query_factory=None)

    def get_s3_client(self, creds=None):
        from txaws.s3.client import S3Client

        if creds:
            self.creds = creds
        return self.get_client(S3Client, creds=self.creds,
                               endpoint=self.s3_endpoint, query_factory=None)


    _agent = None
    def get_route53_client(self):
        from txaws.route53.client import get_route53_client

        if self._agent is None:
            from twisted.web.client import Agent
            from twisted.internet import reactor
            self._agent = Agent(reactor)

        return get_route53_client(self._agent, self)
