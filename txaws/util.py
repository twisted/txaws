"""Generally useful utilities for AWS web services not specific to a service.

New things in this module should be of relevance to more than one of amazon's
services.
"""

__all__ = ['hmac_sha1']

from base64 import b64encode
from hashlib import sha1
import hmac

def hmac_sha1(secret, data):
    digest = hmac.new(secret, data, sha1).digest()
    return b64encode(digest)


