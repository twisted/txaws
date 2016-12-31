import attr

@attr.s
class MemoryRoute53(object):
    agent = attr.ib()
    creds = attr.ib()
    endpoint = attr.ib()
    cooperator = attr.ib()

    _zones = attr.ib(default=pvector())

    def list_hosted_zones(self):
        return 
