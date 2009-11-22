"""Generally useful utilities for AWS web services not specific to a service.

New things in this module should be of relevance to more than one of Amazon's
services.
"""

from base64 import b64encode
from hashlib import sha1, md5, sha256
import hmac
from urlparse import urlparse, urlunparse
import time

# Import XMLTreeBuilder from somewhere; here in one place to prevent
# duplication.
try:
    from xml.etree.ElementTree import XMLTreeBuilder
except ImportError:
    from elementtree.ElementTree import XMLTreeBuilder


__all__ = ["hmac_sha1", "hmac_sha256", "iso8601time", "calculate_md5", "XML"]


def calculate_md5(data):
    digest = md5(data).digest()
    return b64encode(digest)


def hmac_sha1(secret, data):
    digest = hmac.new(secret, data, sha1).digest()
    return b64encode(digest)


def hmac_sha256(secret, data):
    digest = hmac.new(secret, data, sha256).digest()
    return b64encode(digest)


def iso8601time(time_tuple):
    """Format time_tuple as a ISO8601 time string.

    :param time_tuple: Either None, to use the current time, or a tuple tuple.
    """
    if time_tuple:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time_tuple)
    else:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class NamespaceFixXmlTreeBuilder(XMLTreeBuilder):

    def _fixname(self, key):
        if "}" in key:
            key = key.split("}", 1)[1]
        return key


def XML(text):
    parser = NamespaceFixXmlTreeBuilder()
    parser.feed(text)
    return parser.close()


def parse(url, defaultPort=None):
    """
    Split the given URL into the scheme, host, port, and path.

    @type url: C{str}
    @param url: An URL to parse.

    @type defaultPort: C{int} or C{None}
    @param defaultPort: An alternate value to use as the port if the URL does
    not include one.

    @return: A four-tuple of the scheme, host, port, and path of the URL.  All
    of these are C{str} instances except for port, which is an C{int}.
    """
    url = url.strip()
    parsed = urlparse(url)
    scheme = parsed[0]
    path = urlunparse(("", "") + parsed[2:])
    if defaultPort is None:
        if scheme == "https":
            defaultPort = 443
        else:
            defaultPort = 80
    host, port = parsed[1], defaultPort
    if ":" in host:
        host, port = host.split(":")
        try:
            port = int(port)
        except ValueError:
            port = defaultPort
    if path == "":
        path = "/"
    return (str(scheme), str(host), port, str(path))
