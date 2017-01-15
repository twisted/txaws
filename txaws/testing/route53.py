from itertools import count

import attr

from pyrsistent import discard, pvector, pmap, pset

from twisted.internet.defer import succeed, fail
from twisted.web.http import BAD_REQUEST

from txaws.testing.base import MemoryClient, MemoryService
from txaws.route53.model import Name, SOA, NS, HostedZone, create_rrset
from txaws.route53.client import Route53Error

class MemoryRoute53(MemoryService):
    def __init__(self):
        super(MemoryRoute53, self).__init__(
            clientFactory=_MemoryRoute53Client,
            stateFactory=Route53ClientState,
        )


@attr.s
class Route53ClientState(object):
    _id = attr.ib(default=attr.Factory(count), init=False)

    zones = attr.ib(default=pvector())
    rrsets = attr.ib(default=pmap())

    def next_id(self):
        return u"/hostedzone/{:014d}".format(next(self._id))


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
                    name=Name(name),
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
                create_rrset(
                    name=Name(name),
                    type=u"NS",
                    ttl=172800,
                    records={
                        NS(nameserver=Name(text=u'ns-698.awsdns-23.net.example.invalid.')),
                        NS(nameserver=Name(text=u'ns-1188.awsdns-20.org.examplie.invalid.')),
                    },
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
        rrsets = self._state.rrsets.get(zone_id, pmap())
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
        self._state.rrsets = self._state.rrsets.set(zone_id, rrsets)
        return succeed(None)

    def list_resource_record_sets(self, zone_id, maxitems=None, name=None, type=None):
        if name is None and type is not None:
            # http://docs.aws.amazon.com/Route53/latest/APIReference/API_ListResourceRecordSets.html
            #
            # If you specify Type but not Name
            #     Amazon Route 53 returns the InvalidInput error.
            return fail(_error)

        maxitems_limit = lambda n: not True
        if maxitems is not None:
            maxitems_limit = lambda n, v=maxitems: n == v
        name_limit = lambda n: True
        if name is not None:
            name_limit = lambda n, v=name: n >= v
        type_limit = lambda t: True
        if type is not None:
            type_limit = lambda t, v=type: t >= v

        count = 0
        results = {}
        # XXX Wrong sort order
        for (name, type), rrset in sorted(self._state.rrsets[zone_id].items()):
            if name_limit(name) and type_limit(type):
                results[name] = results.get(name, pset()) | pset(rrset)
                count += 1
                if maxitems_limit(count):
                    break
        return succeed(pmap(results))


def _process_change(rrsets, change):
    key = (change.name, change.type)
    existing = rrsets.get(key, pvector())
    try:
        transformation = _change_processors[change.action.lower()]
    except KeyError:
        raise _error
    return rrsets.transform(
        [key],
        transformation(existing, change),
    )

# Real AWS response blobs have some details.  Route53Error doesn't
# know how to parse this XML, though, so the details get lost for now.
_error = Route53Error(b'<?xml version="1.0"?>\n<ErrorResponse/>', BAD_REQUEST)

def _process_create(existing, change):
    return existing + change.records


def _process_delete(existing, change):
    if change.type in (u"SOA", u"NS"):
        # You cannot delete the SOA record or the NS records.
        # XXX
        raise _error
    deleted = list(rr for rr in existing if rr not in change.records)
    if deleted:
        return deleted
    return discard


def _process_upsert(existing, change):
    return change.records



_change_processors = {
    U"create": _process_create,
    u"delete": _process_delete,
    u"upsert": _process_upsert,
}
