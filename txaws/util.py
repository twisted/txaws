"""Generally useful utilities for AWS web services not specific to a service.

New things in this module should be of relevance to more than one of amazon's
services.
"""

from base64 import b64encode
from hashlib import sha1, md5
import hmac
import time

# Import XMLTreeBuilder from somwhere; here in one place to prevent duplication.
try:
    from xml.etree.ElementTree import XMLTreeBuilder
except ImportError:
    from elementtree.ElementTree import XMLTreeBuilder


__all__ = ["hmac_sha1", "iso8601time", "XML"]


def calculate_md5(data):
    digest = md5(data).digest()
    return b64encode(digest)


def hmac_sha1(secret, data):
    digest = hmac.new(secret, data, sha1).digest()
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
