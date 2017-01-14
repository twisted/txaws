# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Client wrapper for Amazon's Route53 (domain service).
"""

from __future__ import print_function, unicode_literals

__all__ = [
    "get_route53_client",
]

from io import BytesIO
from hashlib import sha256
from operator import itemgetter

import attr
from attr import validators

from zope.interface import implementer

from twisted.web.http import OK, CREATED
from twisted.web.client import FileBodyProducer
from twisted.internet.defer import succeed

from txaws.exception import AWSError
from txaws.client.base import RequestDetails, url_context, query, error_wrapper
from txaws.service import REGION_US_EAST_1, AWSServiceEndpoint
from txaws.util import XML

from ._util import maybe_bytes_to_unicode, to_xml, tags
from .model import HostedZone, Name, SOA, NS, A, CNAME
from .interface import IRRSetChange

# Route53 is has two endpoints both in us-east-1.
# http://docs.aws.amazon.com/general/latest/gr/rande.html#r53_region
_REGISTRATION_ENDPOINT = "https://route53domains.us-east-1.amazonaws.com/"
_OTHER_ENDPOINT = "https://route53.amazonaws.com/"

_NS = "https://route53.amazonaws.com/doc/2013-04-01/"

class Route53Error(AWSError):
    pass


def route53_error_wrapper(error):
    error_wrapper(error, Route53Error)


def get_route53_client(agent, region, cooperator=None):
    """
    Get a non-registration Route53 client.
    """
    if cooperator is None:
        from twisted.internet import task as cooperator
    return region.get_client(
        _Route53Client,
        agent=agent,
        creds=region.creds,
        region=REGION_US_EAST_1,
        endpoint=AWSServiceEndpoint(_OTHER_ENDPOINT),
        cooperator=cooperator,
    )


RECORD_TYPES = {
    u"SOA": SOA,
    u"NS": NS,
    u"A": A,
    u"CNAME": CNAME,
}


@attr.s(frozen=True)
class _Route53Client(object):
    agent = attr.ib()
    creds = attr.ib()
    region = attr.ib()
    endpoint = attr.ib()
    cooperator = attr.ib()

    def _details(self, op):
        content_sha256 = sha256(op.body).hexdigest().decode("ascii")
        body_producer = FileBodyProducer(
            BytesIO(op.body), cooperator=self.cooperator,
        )
        return RequestDetails(
            region=self.region,
            service=op.service,
            method=op.method,
            url_context=url_context(
                scheme=self.endpoint.scheme.decode("ascii"),
                host=self.endpoint.host.decode("ascii"),
                port=self.endpoint.port,
                path=op.path,
                query=op.query,
            ),
            body_producer=body_producer,
            content_sha256=content_sha256,
        )

    def _submit(self, details, ok_status):
        q = query(credentials=self.creds, details=details, ok_status=ok_status)
        d = q.submit(self.agent)
        d.addErrback(route53_error_wrapper)
        d.addCallback(itemgetter(1))
        d.addCallback(XML)
        return d

    def _op(self, op):
        details = self._details(op)
        d = self._submit(details=details, ok_status=op.ok_status)
        d.addCallback(op.extract_result)
        return d

    def create_hosted_zone(self, caller_reference, name):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_CreateHostedZone.html

        @type caller_reference: L{unicode}
        @type name: L{unicode}

        @return: A L{Deferred} that fires with a L{HostedZone}
            describing the created zone or with a L{Failure} if there
            is a problem.
        """
        d = _route53_op(
            method=b"POST",
            path=[u"2013-04-01", u"hostedzone"],
            body=tags.CreateHostedZoneRequest(xmlns=_NS)(
                tags.CallerReference(caller_reference),
                tags.Name(name),
                ),
            ok_status=(CREATED,),
            extract_result=self._handle_create_hosted_zone_response,
        )
        d.addCallback(self._op)
        return d

    def _handle_create_hosted_zone_response(self, document):
        # XXX Could extract some additional stuff
        # http://docs.aws.amazon.com/Route53/latest/APIReference/API_CreateHostedZone.html#API_CreateHostedZone_ResponseSyntax
        zone = document.find("./HostedZone")
        return hostedzone_from_element(zone)

    def list_hosted_zones(self):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_ListHostedZones.html

        @return: A L{list} of L{HostedZone} instances describing all
            existing hosted zones.
        """
        d = _route53_op(
            method=b"GET",
            path=[u"2013-04-01", u"hostedzone"],
            extract_result=self._handle_list_hosted_zones_response,
        )
        d.addCallback(self._op)
        return d

    def _handle_list_hosted_zones_response(self, document):
        result = []
        hosted_zones = document.iterfind("./HostedZones/HostedZone")
        for zone in hosted_zones:
            result.append(hostedzone_from_element(zone))
        return result

    def change_resource_record_sets(self, zone_id, changes):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_ChangeResourceRecordSets.html

        @type zone_id: L{unicode}

        @param changes: An iterable of L{IRRSetChange} providers.
        """
        d = _route53_op(
            method=b"POST",
            path=[u"2013-04-01", u"hostedzone", zone_id, u"rrset"],
            body=tags.ChangeResourceRecordSetsRequest(xmlns=_NS)(
                tags.ChangeBatch(
                    tags.Changes(list(
                        to_element(change)
                        for change in changes
                    ))
                )
            ),
        )
        d.addCallback(self._op)
        return d

    def list_resource_record_sets(self, zone_id, identifier=None, maxitems=None, name=None, type=None):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_ListResourceRecordSets.html

        @type zone_id: L{unicode}
        @type identifier: L{unicode}
        @type maxitems: L{int}
        @type name: L{Name}
        @type type: L{unicode}

        @return: A L{Deferred} that fires with a L{dict} mapping rrset
            L{Name}s to L{set}s of resource records.
        """
        args = []
        if identifier:
            args.append(("identifier", identifier))
        if maxitems:
            args.append(("maxitems", str(maxitems)))
        if name:
            args.append(("name", unicode(name)))
        if type:
            args.append(("type", type))

        d = _route53_op(
            method=b"GET",
            path=[u"2013-04-01", u"hostedzone", unicode(zone_id), u"rrset"],
            query=args,
            extract_result=self._handle_list_resource_record_sets_response
        )
        d.addCallback(self._op)
        return d

    def _handle_list_resource_record_sets_response(self, document):
        result = {}
        rrsets = document.iterfind("./ResourceRecordSets/ResourceRecordSet")
        for rrset in rrsets:
            name = Name(maybe_bytes_to_unicode(rrset.find("Name").text))
            type = rrset.find("Type").text
            records = rrset.iterfind("./ResourceRecords/ResourceRecord")
            result.setdefault(name, set()).update({
                RECORD_TYPES[type].from_element(element)
                for element
                in records
            })
        return result


    def delete_hosted_zone(self, zone_id):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_DeleteHostedZone.html

        @type zone_id: L{unicode}
        @return: A L{Deferred} that fires when the hosted zone has
            been deleted.
        """
        d = _route53_op(
            method=b"DELETE",
            path=[u"2013-04-01", u"hostedzone", zone_id],
        )
        d.addCallback(self._op)
        return d

def _route53_op(body=None, **kw):
    op = _Op(service=b"route53", **kw)
    if body is None:
        return succeed(op)
    d = to_xml(body)
    d.addCallback(lambda body: attr.assoc(op, body=body))
    return d

@attr.s
class _Op(object):
    service = attr.ib()
    method = attr.ib()
    path = attr.ib()
    query = attr.ib(default=attr.Factory(list))
    body = attr.ib(default=b"")
    ok_status = attr.ib(default=(OK,))
    extract_result = attr.ib(default=lambda document: None)


def hostedzone_from_element(zone):
    return HostedZone(
        name=maybe_bytes_to_unicode(zone.find("Name").text),
        identifier=maybe_bytes_to_unicode(zone.find("Id").text).replace(u"/hostedzone/", u""),
        rrset_count=int(zone.find("ResourceRecordSetCount").text),
        reference=maybe_bytes_to_unicode(zone.find("CallerReference").text),
    )


def to_element(change):
    """
    @param change: An L{IRRSetChange} provider.

    @return: The L{twisted.web.template} element which describes this
        change.
    """
    return tags.Change(
        tags.Action(
            change.action,
        ),
        tags.ResourceRecordSet(
            tags.Name(
                unicode(change.name),
            ),
            tags.Type(
                change.type,
            ),
            tags.TTL(
                unicode(60 * 60 * 24),
            ),
            tags.ResourceRecords(list(
                tags.ResourceRecord(tags.Value(rr.to_string()))
                for rr
                in change.records
            ))
        ),
    )


@implementer(IRRSetChange)
@attr.s(frozen=True)
class _ChangeRRSet(object):
    action = attr.ib()
    name = attr.ib(validator=validators.instance_of(Name))
    type = attr.ib()
    records = attr.ib()


def create_rrset(name, type, rrset):
    return _ChangeRRSet(u"CREATE", name, type, rrset)


def delete_rrset(name, type, rrset):
    return _ChangeRRSet(u"DELETE", name, type, rrset)


def upsert_rrset(name, type, rrset):
    return _ChangeRRSet(u"UPSERT", name, type, rrset)
