import attr

from txaws.testing.base import _ControllerState

@attr.s
class MemoryRoute53(object):
    def client(self, *a, **kw):
        return _MemoryRoute53Client(self, *a, **kw)


class Route53ClientState(object):
    _zones = attr.ib(default=pvector())


@attr.s
class _MemoryRoute53Client(object):
    _state = _ControllerState()

    _controller = attr.ib()
    creds = attr.ib()
    endpoint = attr.ib()

    def list_hosted_zones(self):
        return 
