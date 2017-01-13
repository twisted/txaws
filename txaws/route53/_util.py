# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Assorted helper functionality for the Route53 implementation.
"""

__all__ = [
    "maybe_bytes_to_unicode", "to_xml", "tags",
]

from twisted.internet.defer import succeed
from twisted.web.template import Tag, flattenString

def maybe_bytes_to_unicode(bytes_or_text):
    if isinstance(bytes_or_text, bytes):
        return bytes_or_text.decode("utf-8")
    return bytes_or_text

def to_xml(body_element):
    doctype = b"""<?xml version="1.0" encoding="UTF-8"?>\n"""
    if body_element is None:
        return succeed(b"")
    d = flattenString(None, body_element)
    d.addCallback(lambda flattened: doctype + flattened)
    return d

class _TagFactory(object):
    """
    A factory for L{Tag} objects; the implementation of the L{tags} object.

    This allows for the syntactic convenience of C{from twisted.web.html import
    tags; tags.a(href="linked-page.html")}, where 'a' can be basically any HTML
    tag.

    The class is not exposed publicly because you only ever need one of these,
    and we already made it for you.

    @see: L{tags}
    """
    def __getattr__(self, tagName):
        # allow for E.del as E.del_
        tagName = tagName.rstrip('_')
        return Tag(tagName)

tags = _TagFactory()
