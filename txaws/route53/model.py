# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Simple model objects related to Route53 interactions.
"""

__all__ = [
    "Name", "SOA", "NS", "A", "CNAME",
    "HostedZone",
]

from ipaddress import IPv4Address

from zope.interface import implementer, provider

import attr
from attr import validators

from constantly import Names, NamedConstant

from ._util import maybe_bytes_to_unicode
from .interface import IResourceRecordLoader, IBasicResourceRecord, IRRSetChange
from ..client._validators import set_of

@attr.s(frozen=True)
class Name(object):
    text = attr.ib(
        convert=lambda v: v + u"." if not v.endswith(u".") else v,
        validator=validators.instance_of(unicode),
    )

    def __str__(self):
        return self.text.encode("idna")


@attr.s(frozen=True)
class RRSetKey(object):
    label = attr.ib()
    type = attr.ib()



class RRSetType(Names):
    RESOURCE = NamedConstant()
    ALIAS = NamedConstant()



@attr.s(frozen=True)
class RRSet(object):
    """
    https://tools.ietf.org/html/rfc2181#section-5
    http://docs.aws.amazon.com/Route53/latest/APIReference/API_ResourceRecord.html

    @ivar name: The label (name) of the resource record set involved in the change.
    @type name: L{Name}

    @ivar type: The type of the resource record set. For example, NS, SOA, AAAA, etc.
    @type type: L{unicode}

    @ivar ttl: The time-to-live for this resource record set.
    @type ttl: L{int}

    @ivar records: The resource records involved in the change.
    @type records: L{list} of L{IResourceRecord} providers
    """
    type = RRSetType.RESOURCE

    label = attr.ib(validator=validators.instance_of(Name))
    type = attr.ib(validator=validators.instance_of(unicode))
    ttl = attr.ib(validator=validators.instance_of(int))
    records = attr.ib(validator=set_of(validators.provides(IBasicResourceRecord)))



@attr.s(frozen=True)
class AliasRRSet(object):
    """
    http://docs.aws.amazon.com/Route53/latest/APIReference/API_AliasTarget.html

    @ivar dns_name: The target of the alias (of variable meaning; see AWS
        docs).
    @type dns_name: L{Name}

    @ivar evaluate_target_health: Inherit health of the target.
    @type evaluate_target_health: L{bool}

    @ivar hosted_zone_id: Scope information for interpreting C{dns_name} (of
        variable meaning; see AWS docs).
    @type hosted_zone_id: L{unicode}
    """
    type = type = RRSetType.ALIAS

    label = attr.ib(validator=validators.instance_of(Name))
    type = attr.ib(validator=validators.instance_of(unicode))
    dns_name = attr.ib(validator=validators.instance_of(Name))
    evaluate_target_health = attr.ib(validator=validators.instance_of(bool))
    hosted_zone_id = attr.ib(validator=validators.instance_of(unicode))



@implementer(IRRSetChange)
@attr.s(frozen=True)
class _ChangeRRSet(object):
    action = attr.ib()
    rrset = attr.ib(validator=validators.instance_of(RRSet))



def create_rrset(rrset):
    return _ChangeRRSet(u"CREATE", rrset)


def delete_rrset(rrset):
    return _ChangeRRSet(u"DELETE", rrset)


def upsert_rrset(rrset):
    return _ChangeRRSet(u"UPSERT", rrset)


@provider(IResourceRecordLoader)
@implementer(IBasicResourceRecord)
@attr.s(frozen=True)
class NS(object):
    nameserver = attr.ib(validator=validators.instance_of(Name))

    @classmethod
    def basic_from_element(cls, e):
        return cls(Name(maybe_bytes_to_unicode(e.find("Value").text)))

    def to_text(self):
        return unicode(self.nameserver)


@provider(IResourceRecordLoader)
@implementer(IBasicResourceRecord)
@attr.s(frozen=True)
class A(object):
    address = attr.ib(validator=validators.instance_of(IPv4Address))

    @classmethod
    def basic_from_element(cls, e):
        return cls(IPv4Address(maybe_bytes_to_unicode(e.find("Value").text)))

    def to_text(self):
        return unicode(self.address)

@provider(IResourceRecordLoader)
@implementer(IBasicResourceRecord)
@attr.s(frozen=True)
class CNAME(object):
    canonical_name = attr.ib(validator=validators.instance_of(Name))

    @classmethod
    def basic_from_element(cls, e):
        return cls(Name(maybe_bytes_to_unicode(e.find("Value").text)))

    def to_text(self):
        return unicode(self.canonical_name)

@provider(IResourceRecordLoader)
@implementer(IBasicResourceRecord)
@attr.s(frozen=True)
class SOA(object):
    mname = attr.ib(validator=validators.instance_of(Name))
    rname = attr.ib(validator=validators.instance_of(Name))
    serial = attr.ib(validator=validators.instance_of(int))
    refresh = attr.ib(validator=validators.instance_of(int))
    retry = attr.ib(validator=validators.instance_of(int))
    expire = attr.ib(validator=validators.instance_of(int))
    minimum = attr.ib(validator=validators.instance_of(int))

    @classmethod
    def basic_from_element(cls, e):
        text = maybe_bytes_to_unicode(e.find("Value").text)
        parts = dict(zip(_SOA_FIELDS, text.split()))
        return cls(
            Name(parts["mname"]),
            Name(parts["rname"]),
            int(parts["serial"]),
            int(parts["refresh"]),
            int(parts["retry"]),
            int(parts["expire"]),
            int(parts["minimum"]),
        )

    def to_text(self):
        return u"{mname} {rname} {serial} {refresh} {retry} {expire} {minimum}".format(
            **attr.asdict(self, recurse=False)
        )

_SOA_FIELDS = list(field.name for field in attr.fields(SOA))


@attr.s
class HostedZone(object):
    """
    http://docs.aws.amazon.com/Route53/latest/APIReference/API_HostedZone.html
    """
    name = attr.ib(validator=validators.instance_of(unicode))
    identifier = attr.ib(validator=validators.instance_of(unicode))
    rrset_count = attr.ib(validator=validators.instance_of(int))
    reference = attr.ib(validator=validators.instance_of(unicode))
