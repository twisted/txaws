# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Route53-related interface definitions.
"""

from zope.interface import Attribute, Interface

class IResourceRecordLoader(Interface):
    """
    An L{IResourceRecordLoader} provider can interpret the AWS Route53
    I{ResourceRecord} representation of a DNS resource record and construct an
    L{IBasicResourceRecord} provider from it.
    """
    def basic_from_element(element):
        """
        Convert an XML element representing a resource record into a Python object
        describing it.

        @param element: An ElementTree XML element representing an AWS Route53
            I{ResourceRecord} element.

        @return: An L{IBasicResourceRecord} provider.
        """

class IBasicResourceRecord(Interface):
    """
    An L{IBasicResourceRecord} provider represents a single `DNS resource
    record <https://tools.ietf.org/html/rfc2929#section-3>`_.
    """
    def to_text():
        """
        @return: The AWS Route53 I{ResourceRecord} I{Value} data representing this
            record.
        @rtype: L{bytes}

        @see: http://docs.aws.amazon.com/Route53/latest/APIReference/API_ResourceRecord.html
        """


class IRRSetChange(Interface):
    """
    An L{IRRSetChange} describes a change to one resource record set (rrset) in a
    Route53 hosted zone.  The change can be creation, deletion, or replacement
    ("upsert").

    Completely replacing an rrset is the only kind of change to an existing
    rrset that is allowed.
    """
    action = Attribute(
        "The kind of change this represents as a unicode string.  "
        "Either CREATE, DELETE, or UPSERT."
    )
    name = Attribute(
        "The name of the resource record set involved in the change "
        "as a Name instance."
    )
    type = Attribute(
        "The type of the resource record set as a unicode string.  "
        "For example, NS, SOA, AAAA, etc."
    )

    records = Attribute(
        "The resource records involved in the change as a list of "
        "IResourceRecord providers."
    )
