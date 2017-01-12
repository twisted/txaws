from __future__ import print_function, unicode_literals

__all__ = [
    "Name", "SOA", "NS",
    "get_route53_client",
]

from io import BytesIO
from urllib import urlencode
from functools import partial

import attr
from attr import validators

from botocore.auth import SigV4Auth
from botocore.credentials import Credentials

from twisted.web.http import OK, CREATED
from twisted.web.http_headers import Headers
from twisted.web.client import FileBodyProducer, readBody
from twisted.python.failure import Failure
from twisted.web.template import Tag, flattenString
from twisted.internet.defer import maybeDeferred

from txaws.client.base import BaseClient, BaseQuery
from txaws.service import AWSServiceEndpoint
from txaws.util import XML

from txaws.route53.model import HostedZone

_REGISTRATION_ENDPOINT = "https://route53domains.us-east-1.amazonaws.com/"
_OTHER_ENDPOINT = "https://route53.amazonaws.com/"

def get_route53_client(agent, aws, cooperator=None):
    """
    Get a non-registration Route53 client.
    """
    if cooperator is None:
        from twisted.internet import task as cooperator
    return aws.get_client(
        _Route53Client,
        agent=agent,
        creds=aws.creds,
        endpoint=AWSServiceEndpoint(_OTHER_ENDPOINT),
        cooperator=cooperator,
    )


@attr.s(frozen=True)
class Name(object):
    text = attr.ib(validator=validators.instance_of(unicode))

    def __str__(self):
        return self.text.encode("idna")


@attr.s(frozen=True)
class NS(object):
    nameserver = attr.ib(validator=validators.instance_of(Name))

    @classmethod
    def from_element(cls, e):
        return cls(Name(et_is_dumb(e.find("Value").text)))

    def to_string(self):
        return unicode(self.nameserver)

@attr.s(frozen=True)
class CNAME(object):
    canonical_name = attr.ib(validator=validators.instance_of(Name))

    @classmethod
    def from_element(cls, e):
        return cls(Name(et_is_dumb(e.find("Value").text)))
        
    def to_string(self):
        return unicode(self.canonical_name)

def et_is_dumb(bytes_or_text):
    if isinstance(bytes_or_text, bytes):
        return bytes_or_text.decode("utf-8")
    return bytes_or_text


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
    def from_element(cls, e):
        mname, rname, serial, refresh, retry, expire, minimum = et_is_dumb(e.find("Value").text).split()
        return cls(
            mname=Name(mname),
            rname=Name(rname),
            serial=int(serial),
            refresh=int(refresh),
            retry=int(retry),
            expire=int(expire),
            minimum=int(minimum),
        )

    def to_string(self):
        return u"{mname} {rname} {serial} {refresh} {retry} {expire} {minimum}".format(vars(self))


RECORD_TYPES = {
    u"SOA": SOA,
    u"NS": NS,
    u"CNAME": CNAME,
}

@attr.s(frozen=True)
class _Route53Client(object):
    agent = attr.ib()
    creds = attr.ib()
    endpoint = attr.ib()
    cooperator = attr.ib()

    def create_hosted_zone(self, caller_reference, name):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_CreateHostedZone.html
        """
        query = _CreateHostedZone(
            action="POST",
            creds=self.creds,
            endpoint=self.endpoint,
            args=(),
            cooperator=self.cooperator,
            caller_reference=caller_reference,
            name=name,
        )
        return query.submit(self.agent)
    
    def list_hosted_zones(self):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_ListHostedZones.html
        """
        query = _ListHostedZones(
            action="GET",
            creds=self.creds,
            endpoint=self.endpoint,
            args=(),
            cooperator=self.cooperator,
        )
        return query.submit(self.agent)


    def change_resource_record_sets(self, zone_id, changes):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_ChangeResourceRecordSets.html
        """
        query = _ChangeRRSets(
            action="POST",
            creds=self.creds,
            endpoint=self.endpoint,
            zone_id=zone_id,
            changes=changes,
            args=(),
            cooperator=self.cooperator,
        )
        return query.submit(self.agent)


    def list_resource_record_sets(self, zone_id, identifier=None, maxitems=None, name=None, type=None):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_ListResourceRecordSets.html
        """
        args = []
        if identifier:
            args.append(("identifier", identifier))
        if maxitems:
            args.append(("maxitems", str(maxitems)))
        if name:
            args.append(("name", name))
        if type:
            args.append(("type", type))

        query = _ListRRSets(
            action="GET",
            creds=self.creds,
            endpoint=self.endpoint,
            zone_id=zone_id,
            args=args,
            cooperator=self.cooperator,
        )
        return query.submit(self.agent)

    def delete_hosted_zone(self, zone_id):
        """
        http://docs.aws.amazon.com/Route53/latest/APIReference/API_DeleteHostedZone.html
        """
        query = _DeleteHostedZone(
            action="DELETE",
            creds=self.creds,
            endpoint=self.endpoint,
            zone_id=zone_id,
            args=(),
            cooperator=self.cooperator,
        )
        return query.submit(self.agent)


def require_status(status_codes):
    def check_status_code(response):
        if response.code not in status_codes:
            return readBody(response).addCallback(
                lambda body: Failure(
                    Exception(
                        "Unexpected status code: {} (expected {})\nBody: {}".format(
                            response.code, status_codes, body,
                        )
                    )
                )
            )
        return response
    return check_status_code


def annotate_request_uri(uri):
    def annotate(reason):
        # Hard to make a copy of a Failure with only minor changes.
        # In particular, there's no way to be sure to replicate the
        # traceback.  Failure.cleanFailure() may have thrown the real
        # traceback object and the fake stuff that it gets replaced
        # with isn't acceptable to Failure.__init__.  So ... mutate
        # this one in place.  What could go wrong?  XXX TODO Replace
        # this with Eliot!
        reason.value = Exception("while requesting", uri, reason.value)
        reason.type = Exception
        return reason
    return annotate


class _HeadersShim(object):
    def __init__(self, request_shim):
        self._request_shim = request_shim

    def __iter__(self):
        return iter(k for k in self._request_shim._headers.getAllRawHeaders())

    def __setitem__(self, key, value):
        self._request_shim._headers.setRawHeaders(key, [value])

    def items(self):
        return list(
            (k, v[0])
            for (k, v)
            in self._request_shim._headers.getAllRawHeaders()
        )

class _BotoAuthRequestShim(object):
    def __init__(self, method, url, headers, body):
        self.method = method
        self.url = url
        self.params = {}
        self.body = body
        self._headers = headers
        self.context = {}
        self.headers = _HeadersShim(self)



@attr.s(frozen=True)
class _Query(object):
    ok_status = (OK,)

    method = b"GET"

    action = attr.ib()
    creds = attr.ib()
    endpoint = attr.ib()
    args = attr.ib()

    cooperator = attr.ib()

    def path(self):
        raise NotImplementedError()

    def body(self):
        return None

    def submit(self, agent):
        base_uri = self.endpoint.get_uri()
        uri = base_uri + self.path() + b"?" + urlencode(self.args)
        d = maybeDeferred(self.body)
        d.addCallback(partial(self._request, agent, self.method, uri, Headers()))
        d.addCallback(require_status(self.ok_status))
        d.addCallback(self.parse)
        d.addErrback(annotate_request_uri(uri))
        return d

    def _request(self, agent, method, uri, headers, body):
        auth = SigV4Auth(
            Credentials(self.creds.access_key, self.creds.secret_key, None),
            "route53",
            "us-east-1",
        )
        auth.add_auth(_BotoAuthRequestShim(method, uri, headers, body))
        if body is None:
            bodyProducer = None
        else:
            bodyProducer = FileBodyProducer(
                BytesIO(body),
                cooperator=self.cooperator,
            )
        return agent.request(method, uri, headers, bodyProducer)

    def parse(self, response):
        d = readBody(response)
        d.addCallback(XML)
        d.addCallback(self._extract_result)
        return d


class _ListHostedZones(_Query):
    def path(self):
        return b"2013-04-01/hostedzone"


    def _extract_result(self, document):
        result = []
        hosted_zones = document.iterfind("./HostedZones/HostedZone")
        for zone in hosted_zones:
            result.append(hostedzone_from_element(zone))
        return result


@attr.s(frozen=True)
class _RRSets(_Query):
    zone_id = attr.ib()

    def path(self):
        return u"2013-04-01/hostedzone/{zone_id}/rrset".format(
            zone_id=self.zone_id
        ).encode("ascii")



from twisted.web.template import Tag

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

class _XMLBodyMixin(object):
    def body(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>\n"""
        d = flattenString(None, self._xml_request_body())
        d.addCallback(lambda body: xml + body)
        return d


@attr.s(frozen=True)
class _DeleteHostedZone(_Query):
    zone_id = attr.ib()

    method = b"DELETE"

    def path(self):
        return u"2013-04-01/hostedzone/{zone_id}".format(
            zone_id=self.zone_id
        ).encode("ascii")

    def _extract_result(self, document):
        return None


def hostedzone_from_element(zone):
    return HostedZone(
        name=et_is_dumb(zone.find("Name").text),
        identifier=et_is_dumb(zone.find("Id").text).replace(u"/hostedzone/", u""),
        rrset_count=int(zone.find("ResourceRecordSetCount").text),
        reference=et_is_dumb(zone.find("CallerReference").text),
    )


@attr.s(frozen=True)
class _CreateHostedZone(_XMLBodyMixin, _Query):
    ok_status = (CREATED,)

    method = b"POST"

    caller_reference = attr.ib()
    name = attr.ib()
    
    def path(self):
        return b"2013-04-01/hostedzone"

    def _xml_request_body(self):
        ns = "https://route53.amazonaws.com/doc/2013-04-01/"
        return tags.CreateHostedZoneRequest(xmlns=ns)(
            tags.CallerReference(self.caller_reference),
            tags.Name(self.name),
        )

    def _extract_result(self, document):
        # XXX Could extract some additional stuff
        # http://docs.aws.amazon.com/Route53/latest/APIReference/API_CreateHostedZone.html#API_CreateHostedZone_ResponseSyntax
        zone = document.find("./HostedZone")
        return hostedzone_from_element(zone)


@attr.s(frozen=True)
class _ChangeRRSets(_XMLBodyMixin, _RRSets):
    changes = attr.ib()

    method = b"POST"

    def _xml_request_body(self):
        ns = "https://route53.amazonaws.com/doc/2013-04-01/"
        return tags.ChangeResourceRecordSetsRequest(xmlns=ns)(
            tags.ChangeBatch(
                tags.Changes(list(
                    change.to_element()
                    for change in self.changes
                ))
            )
        )

    def _extract_result(self, document):
        # XXX Could parse the ChangeInfo and pass some details on
        return None


class _ListRRSets(_RRSets):
    def _extract_result(self, document):
        result = {}
        rrsets = document.iterfind("./ResourceRecordSets/ResourceRecordSet")
        for rrset in rrsets:
            name = Name(et_is_dumb(rrset.find("Name").text))
            type = rrset.find("Type").text
            records = rrset.iterfind("./ResourceRecords/ResourceRecord")
            result.setdefault(name, set()).update({
                RECORD_TYPES[type].from_element(element)
                for element
                in records
            })
        return result


@attr.s(frozen=True)
class _ChangeRRSet(object):
    action = attr.ib()
    name = attr.ib(validator=validators.instance_of(Name))
    type = attr.ib()
    rrset = attr.ib()

    def to_element(self):
        return tags.Change(
            tags.Action(
                self.action,
            ),
            tags.ResourceRecordSet(
                tags.Name(
                    unicode(self.name),
                ),
                tags.Type(
                    unicode(self.type),
                ),
                tags.TTL(
                    unicode(60 * 60 * 24),
                ),
                tags.ResourceRecords(list(
                    tags.ResourceRecord(tags.Value(rr.to_string()))
                    for rr
                    in self.rrset
                ))
            ),
        )

def create_rrset(name, type, rrset):
    return _ChangeRRSet(u"CREATE", name, type, rrset)


def upsert_rrset(name, type, rrset):
    pass


def delete_rrset(name, type, rrset):
    return _ChangeRRSet(u"DELETE", name, type, rrset)


def create_alias_rrset(name, type, alias):
    pass


def create_failover_rrset(name, type, failover):
    pass


def create_geolocation_rrset(name, type, geolocation):
    pass


def create_latency_based_rrset(name, type, latency):
    pass


