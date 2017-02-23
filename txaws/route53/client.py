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

from twisted.python.log import msg
from twisted.web.http import OK, CREATED
from twisted.web.client import FileBodyProducer
from twisted.internet.defer import succeed
from twisted.internet import task

from txaws.exception import AWSError
from txaws.client.base import RequestDetails, url_context, query, error_wrapper
from txaws.service import REGION_US_EAST_1, AWSServiceEndpoint
from txaws.util import XML

from ._util import maybe_bytes_to_unicode, to_xml, tags
from .model import (
    HostedZone, RRSetType, RRSetKey, RRSet, AliasRRSet, Name, SOA, NS, A, CNAME,
)

# Route53 is has two endpoints both in us-east-1.
# http://docs.aws.amazon.com/general/latest/gr/rande.html#r53_region
_REGISTRATION_ENDPOINT = "https://route53domains.us-east-1.amazonaws.com/"
_OTHER_ENDPOINT = "https://route53.amazonaws.com/"

_NS = "https://route53.amazonaws.com/doc/2013-04-01/"

class Route53Error(AWSError):
    """
    L{Route53Error} is the base exception type for all errors returned from
    the AWS Route53 service.
    """


def route53_error_wrapper(error):
    error_wrapper(error, Route53Error)


def get_route53_client(agent, region, cooperator=None):
    """
    Get a non-registration Route53 client.
    """
    if cooperator is None:
        cooperator = task
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
    """
    @ivar agent: An agent to use to issue HTTP(S) requests.
    @type agent: L{IAgent} provider

    @ivar creds: The AWS credentials to use to authenticate requests.
    @type creds: L{AWSCredentials}

    @ivar region: The name of the AWS region to which to issue requests.
    @type region: L{bytes}

    @ivar endpoint: The AWS service endpoint to which to issue requests.
    @type endpoint: L{AWSServiceEndpoint}

    @ivar cooperator: The scheduler to use for streaming large request bodies.
    @type cooperator: L{twisted.internet.task.Cooperator}
    """
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
                tags.Name(name.encode("idna").decode("ascii")),
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

        @param changes: An iterable of L{txaws.route53.interface.IRRSetChange} providers.
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

    def list_resource_record_sets(self, zone_id, maxitems=None, name=None, type=None):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_ListResourceRecordSets.html

        @type zone_id: L{unicode}
        @type maxitems: L{int}
        @type name: L{Name}
        @type type: L{unicode}

        @return: A L{Deferred} that fires with a L{dict} mapping
            L{RRSetKey} instances to corresponding L{RRSet} instances.
        """
        args = []
        if maxitems:
            args.append((u"maxitems", u"{}".format(maxitems)))
        if name:
            args.append((u"name", unicode(name)))
        if type:
            args.append((u"type", type))

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
            label = Name(maybe_bytes_to_unicode(rrset.find("Name").text).encode("ascii").decode("idna"))
            type = maybe_bytes_to_unicode(rrset.find("Type").text)

            for kind in RRSetType.iterconstants():
                value = self._get_rrset(kind, label, type, rrset)
                if value is not None:
                    key = RRSetKey(label, type)
                    result[key] = value
                    break
            else:
                # We didn't find anything we recognize.
                msg(
                    format=(
                        u"list_resource_record_sets() dropping unsupported "
                        u"ResourceRecordSet type in result "
                        u"(children=%(children)s)"
                    ),
                    children=rrset.getchildren(),
                )
        return result

    def _get_rrset(self, kind, label, type, rrset):
        return getattr(self, "_get_rrset_" + kind.name)(label, type, rrset)


    def _get_rrset_RESOURCE(self, label, type, rrset):
        # http://docs.aws.amazon.com/Route53/latest/APIReference/API_ResourceRecord.html
        resourcerecords = rrset.find("./ResourceRecords")
        if resourcerecords is None:
            return None
        records = resourcerecords.iterfind("./ResourceRecord")
        # The docs say TTL is optional but I think that means rrsets that
        # contain something other than ResourceRecord may not have it.
        # Hopefully it's always present for ResourceRecord-tyle
        # ResourceRecordSets?
        ttl = int(rrset.find("TTL").text)
        return RRSet(
            label=label,
            type=type,
            ttl=ttl,
            records={
                RECORD_TYPES[type].basic_from_element(element)
                for element
                in records
            },
        )


    def _get_rrset_ALIAS(self, label, type, rrset):
        # http://docs.aws.amazon.com/Route53/latest/APIReference/API_AliasTarget.html
        aliastarget = rrset.find("./AliasTarget")
        if aliastarget is None:
            return None
        return AliasRRSet(
            label=label,
            type=type,
            dns_name=Name(maybe_bytes_to_unicode(aliastarget.find("DNSName").text)),
            evaluate_target_health={
                "true": True, "false": False,
            }.get(aliastarget.find("EvaluateTargetHealth").text),
            hosted_zone_id=maybe_bytes_to_unicode(aliastarget.find("HostedZoneId").text),
        )


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
    """
    Construct an L{_Operation} representing a I{Route53} service API call.
    """
    op = _Operation(service=b"route53", **kw)
    if body is None:
        return succeed(op)
    d = to_xml(body)
    d.addCallback(lambda body: attr.assoc(op, body=body))
    return d

@attr.s
class _Operation(object):
    """
    Supply the details necessary to make an API call.

    @ivar service: The name of the AWS service the operation belongs to.
    @type service: L{bytes}

    @ivar method: The HTTP method of the operatiom.
    @type method: L{bytes}

    @ivar path: The path component of the request URI.
    @type path: L{list} opf L{unicode}

    @ivar query: The query parameters of the request.
    @type query: L{list} of L{tuple} of L{unicode}

    @ivar body: A document to serialize into the request body.
    @type body: L{twisted.web.template.Tag}

    @ivar ok_status: The HTTP response status codes which are considered
        successes for this operation.
    @type ok_status: L{tuple} of L{int}

    @ivar extract_result: A one-argument callable which is passed the parsed
        response document and can extract results and restructure them to be
        returned to application code.
    """
    service = attr.ib()
    method = attr.ib()
    path = attr.ib()
    query = attr.ib(default=attr.Factory(list))
    body = attr.ib(default=b"")
    ok_status = attr.ib(default=(OK,))
    extract_result = attr.ib(default=lambda document: None)


def hostedzone_from_element(zone):
    """
    Construct a L{HostedZone} instance from a I{HostedZone} XML element.
    """
    return HostedZone(
        name=maybe_bytes_to_unicode(zone.find("Name").text).encode("ascii").decode("idna"),
        identifier=maybe_bytes_to_unicode(zone.find("Id").text).replace(u"/hostedzone/", u""),
        rrset_count=int(zone.find("ResourceRecordSetCount").text),
        reference=maybe_bytes_to_unicode(zone.find("CallerReference").text),
    )


def to_element(change):
    """
    @param change: An L{txaws.route53.interface.IRRSetChange} provider.

    @return: The L{twisted.web.template} element which describes this
        change.
    """
    return tags.Change(
        tags.Action(
            change.action,
        ),
        tags.ResourceRecordSet(
            tags.Name(
                unicode(change.rrset.label),
            ),
            tags.Type(
                change.rrset.type,
            ),
            tags.TTL(
                u"{}".format(change.rrset.ttl),
            ),
            tags.ResourceRecords(list(
                tags.ResourceRecord(tags.Value(rr.to_text()))
                for rr
                in sorted(change.rrset.records)
            ))
        ),
    )
