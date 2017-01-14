from itertools import count

import attr

from pyrsistent import discard, pvector, pmap, pset

from twisted.internet.defer import succeed, fail
from twisted.web.http import BAD_REQUEST

from txaws.testing.base import MemoryClient, MemoryService
from txaws.route53.model import HostedZone
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
        self._state.zones = self._state.zones.append(HostedZone(
            name=name,
            reference=caller_reference,
            identifier=self._state.next_id(),
            # Hosted zones start with SOA and NS rrsets.
            rrset_count=2,
        ))
        return succeed(self._state.zones[-1])
    
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
            self._state.rrsets = self._state.rrsets.set(zone_id, rrsets)
        return succeed(None)

    def list_resource_record_sets(self, zone_id):
        return succeed(pmap({
            name: pset(rrset)
            for (name, type), rrset in self._state.rrsets[zone_id].items()
        }))


def _process_change(rrsets, change):
    key = (change.name, change.type)
    existing = rrsets.get(key, pvector())
    try:
        transformation = _change_processors[change.action.lower()]
    except KeyError:
        # The real AWS response blob has some details.  Route53Error
        # doesn't know how to parse this XML, though, so the details
        # get lost for now.
        raise Route53Error(b'<?xml version="1.0"?>\n<ErrorResponse/>', BAD_REQUEST)
    return rrsets.transform(
        [key],
        transformation(existing, change),
    )


def _process_create(existing, change):
    return existing + change.records


def _process_delete(existing, change):
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
