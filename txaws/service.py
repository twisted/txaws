# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from twisted.web.client import _parse


DEFAULT_PORT = 80


class AWSService(object):
    """
    """
    def __init__(self, creds, url=""):
        self.creds = creds
        self.schema = ""
        self.host = ""
        self.port = DEFAULT_PORT
        self.endpoint = "/"
        self._parse_url(url)

    def _parse_url(self, url):
        scheme, host, port, endpoint = _parse(url, defaultPort=DEFAULT_PORT)
        self.schema = scheme
        self.host = host
        self.port = port
        self.endpoint = endpoint

    def get_url(self):
        url = "%s://%s" % (self.schema, self.host)
        if self.port and self.port != DEFAULT_PORT:
            url = "%s:%s" % (url, self.port)
        return url + self.endpoint
        
        

