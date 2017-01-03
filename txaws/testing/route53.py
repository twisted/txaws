import attr

from pyrsistent import pvector

from txaws.testing.base import MemoryClient, MemoryService

class MemoryRoute53(MemoryService):
    def __init__(self):
        super(MemoryRoute53, self).__init__(
            clientFactory=_MemoryRoute53Client,
            stateFactory=Route53ClientState,
        )


@attr.s
class Route53ClientState(object):
    _zones = attr.ib(default=pvector())


@attr.s
class _MemoryRoute53Client(MemoryClient):
    creds = attr.ib()
    endpoint = attr.ib()
    
    def create_hosted_zone(self, name):
        pass
    
    def list_hosted_zones(self):
        return 
