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

from ._util import maybe_bytes_to_unicode
from .interface import IResourceRecordLoader, IBasicResourceRecord, IRRSetChange
from ..client._validators import set_of

def _all(*vs):
    def validator(*a, **kw):
        for v in vs:
            v(*a, **kw)
    return validator


def _not_empty(attr, inst, value):
    if 0 == len(value):
        raise ValueError("Value must have length greater than 0")


@attr.s(frozen=True)
class Name(object):
    text = attr.ib(validator=_all(validators.instance_of(unicode), _not_empty))

    def __str__(self):
        return self.text.encode("idna")


@attr.s(frozen=True)
class RRSetKey(object):
    label = attr.ib()
    type = attr.ib()


@attr.s(frozen=True)
class RRSet(object):
    """
    https://tools.ietf.org/html/rfc2181#section-5
    """
    label = attr.ib(validator=validators.instance_of(Name))
    type = attr.ib(validator=validators.instance_of(unicode))
    ttl = attr.ib(validator=validators.instance_of(int))
    records = attr.ib(validator=set_of(validators.provides(IBasicResourceRecord)))


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
        mname, rname, serial, refresh, retry, expire, minimum = maybe_bytes_to_unicode(e.find("Value").text).split()
        return cls(
            mname=Name(mname),
            rname=Name(rname),
            serial=int(serial),
            refresh=int(refresh),
            retry=int(retry),
            expire=int(expire),
            minimum=int(minimum),
        )

    def to_text(self):
        return u"{mname} {rname} {serial} {refresh} {retry} {expire} {minimum}".format(
            **attr.asdict(self, recurse=False)
        )


@attr.s
class HostedZone(object):
    """
    http://docs.aws.amazon.com/Route53/latest/APIReference/API_HostedZone.html
    """
    name = attr.ib(validator=validators.instance_of(unicode))
    identifier = attr.ib(validator=validators.instance_of(unicode))
    rrset_count = attr.ib(validator=validators.instance_of(int))
    reference = attr.ib(validator=validators.instance_of(unicode))
