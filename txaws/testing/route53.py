from itertools import count

import attr

from pyrsistent import discard, pvector, pmap, pset

from twisted.internet.defer import succeed, fail
from twisted.web.http import BAD_REQUEST, NOT_FOUND

from txaws.testing.base import MemoryClient, MemoryService
from txaws.route53.model import Name, RRSetKey, RRSet, SOA, NS, HostedZone, create_rrset
from txaws.route53.client import Route53Error

class MemoryRoute53(MemoryService):
    def __init__(self):
        super(MemoryRoute53, self).__init__(
            clientFactory=_MemoryRoute53Client,
            stateFactory=Route53ClientState,
        )


@attr.s
class Route53ClientState(object):
    """
    @ivar zones: A sequence of HostedZone instances representing the
        zones known to exist.

    @ivar rrsets: A mapping from zone identifiers to further mappings.
        The further mappings map an L{RRSetKey} instance to an L{RRSet}
        instance and represent the rrsets belonging to the
        corresponding zone.
    """
    _id = attr.ib(default=attr.Factory(count), init=False)

    zones = attr.ib(default=pvector())
    rrsets = attr.ib(default=pmap())

    def next_id(self):
        return u"/hostedzone/{:014d}".format(next(self._id))

    def get_rrsets(self, zone_id):
        if any(zone.identifier == zone_id for zone in self.zones):
            return self.rrsets.get(zone_id, pmap())
        # You cannot interact with rrsets unless a zone exists.
        return None

    def set_rrsets(self, zone_id, rrsets):
        self.rrsets = self.rrsets.set(zone_id, rrsets)


def _value_transform(pv, pred, transform):
    return pv.transform([lambda i: pred(pv[i])], transform)


@attr.s
class _MemoryRoute53Client(MemoryClient):
    endpoint = attr.ib()

    def create_hosted_zone(self, caller_reference, name):
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
                        records={
                            SOA(
                                mname=Name(text=u'ns-698.awsdns-23.net.example.invalid.'),
                                rname=Name(text=u'awsdns-hostmaster.amazon.com.example.invalid.'),
                                serial=1,
                                refresh=7200,
                                retry=900,
                                expire=1209600,
                                minimum=86400,
                            ),
                        },
                    ),
                ),
                create_rrset(
                    RRSet(
                        label=Name(name),
                        type=u"NS",
                        ttl=172800,
                        records={
                            NS(nameserver=Name(text=u'ns-698.awsdns-23.net.example.invalid.')),
                            NS(nameserver=Name(text=u'ns-1188.awsdns-20.org.examplie.invalid.')),
                        },
                    ),
                ),
            ],
        )
        return succeed(zone)

    def list_hosted_zones(self):
        return succeed(self._state.zones)

    def delete_hosted_zone(self, zone_id):
        self._state.zones = _value_transform(
            self._state.zones,
            lambda z: z.identifier == zone_id,
            discard,
        )
        return succeed(None)

    def change_resource_record_sets(self, zone_id, changes):
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
            name_limit = lambda n, v=name: n >= v
        type_limit = lambda t: True
        if type is not None:
            type_limit = lambda t, v=type: t >= v

        results = {}
        # XXX Wrong sort order
        for key, rrset in sorted(rrsets.items()):
            if name_limit(key.label) and type_limit(key.type):
                results[key] = rrset
                if maxitems_limit(len(results)):
                    break
        return succeed(pmap(results))


def _process_change(rrsets, change):
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
    if existing is not None:
        # You cannot create if it exists a already.
        raise _error
    return change


def _process_delete(existing, change):
    if change.type in (u"SOA", u"NS"):
        # You cannot delete the SOA record or the NS records.
        # XXX
        raise _error
    if existing == change:
        return discard
    # You must specify the rrset exactly to delete it.
    raise _error


def _process_upsert(existing, change):
    # Replace whatever was there with whatever was specified.
    return change



_change_processors = {
    U"create": _process_create,
    u"delete": _process_delete,
    u"upsert": _process_upsert,
}
