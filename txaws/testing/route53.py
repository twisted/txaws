# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
An in-memory implementation of the Route53 client interface as an aid to
unit testing.
"""

from itertools import count

import attr

from pyrsistent import discard, pvector, pmap, pset

from twisted.internet.defer import succeed, fail
from twisted.web.http import BAD_REQUEST, NOT_FOUND

from txaws.testing.base import MemoryClient, MemoryService
from txaws.route53.model import Name, RRSetKey, RRSet, SOA, NS, HostedZone, create_rrset
from txaws.route53.client import Route53Error


class MemoryRoute53(MemoryService):
    """
    L{MemoryRoute53} can create in-memory verified fakes of the Route53
    client.
    """
    def __init__(self):
        super(MemoryRoute53, self).__init__(
            client_factory=_MemoryRoute53Client,
            state_factory=Route53ClientState,
        )


@attr.s
class Route53ClientState(object):
    """
    L{Route53ClientState} holds all of the Route53 state associated with a
    single account.  This allows multiple clients with the same credentials to
    share state while hiding one account's state from other accounts (just as
    AWS does).

    @ivar soa_records: The SOA records (1) which will be put in all newly
        created hosted zones.

    @ivar ns_records: The NS records which will be put in all newly created
        hosted zones.

    @ivar zones: A sequence of HostedZone instances representing the
        zones known to exist.
    @type zones: L{pyrsistent.PVector}

    @ivar rrsets: A mapping from zone identifiers to further mappings.
        The further mappings map an L{RRSetKey} instance to an L{RRSet}
        instance and represent the rrsets belonging to the
        corresponding zone.
    @type rrsets: L{pyrsistent.PMap}
    """
    soa_records = {
        SOA(
            mname=Name(text=u'ns-698.awsdns-23.net.example.invalid.'),
            rname=Name(text=u'awsdns-hostmaster.amazon.com.example.invalid.'),
            serial=1,
            refresh=7200,
            retry=900,
            expire=1209600,
            minimum=86400,
        ),
    }

    ns_records = {
        NS(nameserver=Name(text=u'ns-698.awsdns-23.net.example.invalid.')),
        NS(nameserver=Name(text=u'ns-1188.awsdns-20.org.examplie.invalid.')),
    }

    _id = attr.ib(default=attr.Factory(count), init=False)

    zones = attr.ib(default=pvector())
    rrsets = attr.ib(default=pmap())
    def next_id(self):
        """
        Assign and return a new, unique hosted zone identifier.

        @rtype: L{unicode}
        """
        return u"/hostedzone/{:014d}".format(next(self._id))


    def get_rrsets(self, zone_id):
        """
        Retrieve all the rrsets that belong to the given zone.

        @param zone_id: The zone to inspect.
        @type zone_id: L{unicode}

        @return: L{None} if the zone is not found.  Otherwise, a L{PMap}
            mapping L{RRSetKey} to L{RRSet}.
        """
        if any(zone.identifier == zone_id for zone in self.zones):
            return self.rrsets.get(zone_id, pmap())
        # You cannot interact with rrsets unless a zone exists.
        return None


    def set_rrsets(self, zone_id, rrsets):
        """
        Specify all the rrsets that belong to the given zone.

        @param zone_id: The zone to modify.
        @type zone_id: L{unicode}

        @param rrsets: A L{PMap} mapping L{RRSetKey} to L{RRSet}.
        """
        self.rrsets = self.rrsets.set(zone_id, rrsets)



def _value_transform(pv, pred, transform):
    """
    Perform a transformation on elements of a L{pyrsistent.PVector}.

    @param pv: The vector.
    @type pv: L{pyrsistent.PVector}

    @param pred: A predicate on values of C{pv}.
    @type pred: A callable accepting values like those in C{pv} and return
        L{bool}

    @param transform: A transformation which will be applied to elements of
        C{pv} for which C{pred} returns C{True}.

    @return: A L{pyrsistent.PVector} like C{pv} but with C{transform} applied
        to some number of elements.
    """
    return pv.transform([lambda i: pred(pv[i])], transform)


@attr.s
class _MemoryRoute53Client(MemoryClient):
    """
    An in-memory fake of L{txaws.route53.client._Route53Client}.

    This essentially implements the same API-facing logic as AWS Route53 by
    manipulating local, in-memory state (mappings, vectors, etc).  It does not
    actually provide Route53 service (ie, you cannot host real domains with
    this) but as far as API interactions go, it is intended to be
    indistinguishable from the real AWS Route53.
    """
    endpoint = attr.ib()

    def create_hosted_zone(self, caller_reference, name):
        """
        @see: L{txaws.route53.client._Route53Client.create_hosted_zone}
        """
        zone = HostedZone(
            name=name,
            reference=caller_reference,
            identifier=self._state.next_id(),
            # Hosted zones start with SOA and NS rrsets.
            rrset_count=2,
        )
        self._state.zones = self._state.zones.append(zone)
        self.change_resource_record_sets(
            zone.identifier, [
                create_rrset(
                    RRSet(
                        label=Name(name),
                        type=u"SOA",
                        ttl=900,
                        records=self._state.soa_records,
                    ),
                ),
                create_rrset(
                    RRSet(
                        label=Name(name),
                        type=u"NS",
                        ttl=172800,
                        records=self._state.ns_records,
                    ),
                ),
            ],
        )
        return succeed(zone)

    def list_hosted_zones(self):
        """
        @see: L{txaws.route53.client._Route53Client.list_hosted_zones}
        """
        return succeed(self._state.zones)

    def delete_hosted_zone(self, zone_id):
        """
        @see: L{txaws.route53.client._Route53Client.delete_hosted_zone}
        """
        self._state.zones = _value_transform(
            self._state.zones,
            lambda z: z.identifier == zone_id,
            discard,
        )
        return succeed(None)

    def change_resource_record_sets(self, zone_id, changes):
        """
        @see: L{txaws.route53.client._Route53Client.change_resource_record_sets}
        """
        rrsets = self._state.get_rrsets(zone_id)
        if rrsets is None:
            return fail(_not_found)

        for change in changes:
            try:
                rrsets = _process_change(rrsets, change)
            except:
                return fail()
        # http://docs.aws.amazon.com/Route53/latest/APIReference/API_ChangeResourceRecordSets.html
        #
        # When using the Amazon Route 53 API to change resource record
        # sets, Amazon Route 53 either makes all or none of the
        # changes in a change batch request.
        self._state.set_rrsets(zone_id, rrsets)
        return succeed(None)

    def list_resource_record_sets(self, zone_id, maxitems=None, name=None, type=None):
        """
        @see: L{txaws.route53.client._Route53Client.list_resource_record_sets}
        """
        if name is None and type is not None:
            # http://docs.aws.amazon.com/Route53/latest/APIReference/API_ListResourceRecordSets.html
            #
            # If you specify Type but not Name
            #     Amazon Route 53 returns the InvalidInput error.
            return fail(_error)

        rrsets = self._state.get_rrsets(zone_id)
        if rrsets is None:
            return fail(_not_found)

        maxitems_limit = lambda n: not True
        if maxitems is not None:
            maxitems_limit = lambda n, v=maxitems: n == v
        name_limit = lambda n: True
        if name is not None:
            start_value = _reverse_dns_labels(name)
            name_limit = lambda n, v=start_value: _reverse_dns_labels(n) >= v
        type_limit = lambda t: True
        if type is not None:
            type_limit = lambda t, v=type: t >= v

        results = {}
        for key, rrset in sorted(rrsets.items(), key=_reverse_dns_labels):
            if name_limit(key.label) and type_limit(key.type):
                results[key] = rrset
                if maxitems_limit(len(results)):
                    break
        return succeed(pmap(results))


def _reverse_dns_labels(name):
    """
    Helper to sort L{Name} instances according to the AWS Route53 rules.

    @type name: L{Name}
    @rtype: L{unicode}
    """
    return u"".join(unicode(name).split(u".")[-2::-1]) + u"."


def _process_change(rrsets, change):
    """
    Apply an L{IRRSetChange} to some L{RRSet}s.

    @param rrsets: The starting data to which to apply changes.
    @type rrsets: A L{pyrsistent.PMap} of L{RRSetKey} to L{RRSet}.

    @param change: The change to apply.
    @type change: L{IRRSetChange} provider

    @return: The changed rrsets.
    @rtype: L{pyrsistent.PMap} of L{RRSetKey} to L{RRSet}.
    """
    key = RRSetKey(change.rrset.label, change.rrset.type)
    existing = rrsets.get(key, None)
    try:
        transformation = _change_processors[change.action.lower()]
    except KeyError:
        raise _error
    return rrsets.transform(
        [key],
        transformation(existing, change.rrset),
    )

# Real AWS response blobs have some details.  Route53Error doesn't
# know how to parse this XML, though, so the details get lost for now.
_error = Route53Error(b'<?xml version="1.0"?>\n<ErrorResponse/>', BAD_REQUEST)
_not_found = Route53Error(b'<?xml version="1.0"?>\n<ErrorResponse/>', NOT_FOUND)

def _process_create(existing, change):
    """
    Process a I{CREATE} change.
    """
    if existing is not None:
        # You cannot create if it exists a already.
        raise _error
    return change


def _process_delete(existing, change):
    """
    Process a I{DELETE} change.
    """
    if change.type in (u"SOA", u"NS"):
        # The hosted zone itself must always have an SOA and an NS.  It is an
        # error to attempt to delete either of those.
        #
        # However, there may be NS records for subdomains of the hosted zone
        # (ie, delegations).  It's okay to delete those.  We're not quite
        # smart enough to recognize that case here.
        #
        # https://github.com/twisted/txaws/issues/40
        raise _error
    if existing == change:
        return discard
    # You must specify the rrset exactly to delete it.
    raise _error


def _process_upsert(existing, change):
    """
    Process an I{UPSERT} change.
    """
    # Replace whatever was there with whatever was specified.
    return change



_change_processors = {
    U"create": _process_create,
    u"delete": _process_delete,
    u"upsert": _process_upsert,
}
