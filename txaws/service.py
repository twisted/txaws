# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import os

from twisted.web.client import _parse

from txaws.util import hmac_sha1

DEFAULT_PORT = 80
ENV_ACCESS_KEY = "AWS_ACCESS_KEY_ID"
ENV_SECRET_KEY = "AWS_SECRET_ACCESS_KEY"

class AWSService(object):
    """
    @param access_key: The access key to use. If None the environment
        variable AWS_ACCESS_KEY_ID is consulted.
    @param secret_key: The secret key to use. If None the environment
        variable AWS_SECRET_ACCESS_KEY is consulted.
    @param uri: The URL for the service.
    @param method: The HTTP method used when accessing a service.
    """
    default_host = ""
    default_schema = "https"

    def __init__(self, access_key="", secret_key="", uri="", method="GET"):
        self.access_key = access_key
        self.secret_key = secret_key
        self.schema = ""
        self.host = ""
        self.port = DEFAULT_PORT
        self.endpoint = "/"
        self.method = method
        self._process_creds()
        self._parse_uri(uri)
        if not self.host:
            self.host = self.default_host
        if not self.schema:
            self.schema = self.default_schema

    def _process_creds(self):
        # perform checks for access key
        if not self.access_key:
            self.access_key = os.environ.get(ENV_ACCESS_KEY)
        if not self.access_key:
            raise ValueError("Could not find %s" % ENV_ACCESS_KEY)
        # perform checks for secret key
        if not self.secret_key:
            self.secret_key = os.environ.get(ENV_SECRET_KEY)
        if not self.secret_key:
            raise ValueError("Could not find %s" % ENV_SECRET_KEY)

    def _parse_uri(self, uri):
        scheme, host, port, endpoint = _parse(
            str(uri), defaultPort=DEFAULT_PORT)
        self.schema = scheme
        self.host = host
        self.port = port
        self.endpoint = endpoint

    def get_uri(self):
        """Get a URL representation of the service."""
        uri = "%s://%s" % (self.schema, self.host)
        if self.port and self.port != DEFAULT_PORT:
            uri = "%s:%s" % (uri, self.port)
        return uri + self.endpoint

    def sign(self, bytes):
        """Sign some bytes."""
        return hmac_sha1(self.secret_key, bytes)
