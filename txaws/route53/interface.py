from zope.interface import Attribute, Interface

class IResourceRecord(Interface):
    # XXX from_string instead
    def from_element(element):
        pass

    def to_string():
        pass


class IRRSetChange(Interface):
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
