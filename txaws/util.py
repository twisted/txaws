"""Generally useful utilities for AWS web services not specific to a service.

New things in this module should be of relevance to more than one of amazon's
services.
"""

__all__ = ['hmac_sha1', 'iso8601time']

import time
import hmac
from hashlib import sha1, md5
from base64 import b64encode

# Import XML from somwhere; here in one place to prevent duplication.
try:
    from xml.etree.ElementTree import XML
except ImportError:
    from elementtree.ElementTree import XML


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
