# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for the Route53 client(s).
"""

from twisted.trial.unittest import TestCase

def route53_integration_tests(get_client):
    class Route53IntegrationTests(TestCase):
        def test_hosted_zones(self):
            """
            """
            class HostedZonesDriver(object):
                def __init__(self):
                    self.client = get_client()
                    self.name = u"{}.example.invalid.".format(randrange(maxint))
                    self.caller_reference = unicode(uuid4())

                def create(self):
                    return self.client.create_hosted_zone(
                        name=name, caller_reference=caller_reference,
                    )

                def check_create(self, ignored):
                    d = self.client.list_hosted_zones()
                    d.addCallback(
                        lambda zones: any(z.name == self.name for z in zones)
                    )
                    return d
                
            d = HostedZonesDriver()
            d.create()
            d.addCallback(d.check_created)
            d.addCallback(d.
            d.addCallback(check(.create_hosted_zone(
                
            )

        def test_list_hosted_zones(self):
            """
            ``list_hosted_zones`` returns a ``Deferred`` that fires with a
            ``list`` of ``HostedZone`` instances.
            """
