# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import os

from twisted.web.client import _parse



__all__ = ["AWSServiceEndpoint", "AWSServiceRegion"]


REGION_US = "US"
REGION_EU = "EU"
EC2_ENDPOINT_US = "https://us-east-1.ec2.amazonaws.com/"
EC2_ENDPOINT_EU = "https://eu-west-1.ec2.amazonaws.com/"
DEFAULT_PORT = 80


class AWSServiceEndpoint(object):
    """
    @param uri: The URL for the service.
    @param method: The HTTP method used when accessing a service.
    """

    def __init__(self, uri="", method="GET"):
        self.host = ""
        self.port = DEFAULT_PORT
        self.path = "/"
        self.method = method
        self._parse_uri(uri)
        if not self.scheme:
            self.scheme = "http"

    def _parse_uri(self, uri):
        scheme, host, port, path = _parse(
            str(uri), defaultPort=DEFAULT_PORT)
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path

    def set_path(self, path):
        # XXX needs test!
        self.path = path

    def get_uri(self):
        """Get a URL representation of the service."""
        uri = "%s://%s" % (self.scheme, self.host)
        if self.port and self.port != DEFAULT_PORT:
            uri = "%s:%s" % (uri, self.port)
        return uri + self.path

# XXX needs tests!
class AWSServiceRegion(object):
    """
    This object represents a collection of client factories that use the same
    credentials. With Amazon, this collection is associated with a region
    (e.g., US or EU).
    """
    def __init__(self, creds=None, location=REGION_US):
        self.creds = creds
        self._clients = {}
        if region == REGION_US:
            ec2_endpoint = EC2_ENDPOINT_US
        elif region == REGION_EU:
            ec2_endpoint = EC2_ENDPOINT_EU
        self.ec2_endpoint = AWSServiceEndpoint(uri=ec2_endpoint)

    def get_client(self, cls, *args, **kwds):
        key = str(cls) + str(args) + str(kwds)
        instance = self._clients.get(key)
        if not instance:
            instance = cls(*args, **kwds)
        self._clients[key] = instance
        return instance

    def get_ec2_client(self, creds=None):
        from txaws.ec2.client import EC2Client

        if creds:
            self.creds = creds
        return self.get_client(EC2Client, creds=creds,
                               endpoint=self.ec2_endpoint, query_factory=None)

    def get_s3_client(self):
        raise NotImplementedError

    def get_simpledb_client(self):
        raise NotImplementedError

    def get_sqs_client(self):
        raise NotImplementedError

