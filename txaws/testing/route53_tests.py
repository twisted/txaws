# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for the Route53 client(s).
"""

from time import time
from uuid import uuid4

from twisted.internet.defer import inlineCallbacks, gatherResults

from twisted.trial.unittest import TestCase

from txaws.route53.client import CNAME, Name, create_rrset, delete_rrset

def route53_integration_tests(get_client):
    class Route53IntegrationTests(TestCase):
        @inlineCallbacks
        def test_hosted_zones(self):
            """
            Route53 hosted zones exist in a collection which can be
            manipulated in the obvious ways using
            ``create_hosted_zone``, ``list_hosted_zones``, and
            ``delete_hosted_zone``.
            """
            zone_names = {
                u"{}.example.invalid.".format(unicode(uuid4())),
                u"{}.example.invalid.".format(unicode(uuid4())),
            }

            client = get_client(self)

            created_zones = yield gatherResults([
                client.create_hosted_zone(u"{}-{}".format(time(), n), name)
                for n, name in enumerate(zone_names)
            ])

            listed_zones = yield client.list_hosted_zones()
            listed_names = {zone.name for zone in listed_zones}
            self.assertTrue(
                zone_names.issubset(listed_names),
                "Expected created zones {} to be founded in zone listing {}".format(
                    zone_names, listed_names,
                ),
            )
            
            yield gatherResults(list(
                client.delete_hosted_zone(zone.identifier)
                for zone in created_zones
            ))

            listed_zones = yield client.list_hosted_zones()
            listed_names = {zone.name for zone in listed_zones}
            self.assertFalse(
                any(name in listed_names for name in zone_names),
                "Expected deleted zones {} to not be found in zone listing {}".format(
                    zone_names, listed_names,
                ),
            )

        @inlineCallbacks
        def test_resource_record_sets(self):
            zone_name = u"{}.example.invalid.".format(uuid4())
            cname = CNAME(canonical_name=Name(u"example.invalid."))
            client = get_client(self)
            zone = yield client.create_hosted_zone(u"{}".format(time()), zone_name)

            # At least try to clean up, to be as nice as possible.
            # This might fail and someone else might have to do the
            # cleanup - but it might not!
            self.addCleanup(lambda: client.delete_hosted_zone(zone.identifier))

            yield client.change_resource_record_sets(zone.identifier, [
                create_rrset(
                    u"foo.{}".format(zone_name),
                    u"CNAME",
                    [cname],
                )
            ])
            rrsets = yield client.list_resource_record_sets(zone.identifier)
            self.assertEqual(
                {cname},
                rrsets[Name(u"foo.{}".format(zone_name))],
            )
            yield client.change_resource_record_sets(zone.identifier, [
                delete_rrset(
                    u"foo.{}".format(zone_name),
                    u"CNAME",
                    [cname],
                ),
            ])
            rrsets = yield client.list_resource_record_sets(zone.identifier)
            self.assertNotIn(Name(u"foo.{}".format(zone_name)), rrsets)

            
            
    return Route53IntegrationTests
