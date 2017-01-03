from itertools import count

import attr

from pyrsistent import discard, pvector

from twisted.internet.defer import succeed

from txaws.testing.base import MemoryClient, MemoryService
from txaws.route53.model import HostedZone

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

    def next_id(self):
        return u"/hostedzone/{:014d}".format(next(self._id))


def _value_transform(pv, pred, transform):
    return pv.transform([lambda i: pred(pv[i])], transform)

@attr.s
class _MemoryRoute53Client(MemoryClient):
    creds = attr.ib()
    endpoint = attr.ib()
    
    def create_hosted_zone(self, name):
        self._state.zones = self._state.zones.append(HostedZone(name=name, id=self._state.next_id()))
        return succeed(None)
    
    def list_hosted_zones(self):
        return succeed(self._state.zones)

    def delete_hosted_zone(self, id):
        self._state.zones = _value_transform(
            self._state.zones,
            lambda z: z.id == id,
            discard,
        )
        return succeed(None)
