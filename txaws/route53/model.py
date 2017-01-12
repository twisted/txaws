# Licenced under the txaws licence available at /LICENSE in the txaws source.

import attr
from attr import validators

@attr.s
class HostedZone(object):
    """
    http://docs.aws.amazon.com/Route53/latest/APIReference/API_HostedZone.html
    """
    name = attr.ib(validator=validators.instance_of(unicode))
    identifier = attr.ib(validator=validators.instance_of(unicode))
    rrset_count = attr.ib(validator=validators.instance_of(int))
    reference = attr.ib(validator=validators.instance_of(unicode))
