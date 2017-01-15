# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for the Route53 client(s).
"""

import attr
from time import time
from uuid import uuid4
from ipaddress import IPv4Address

from twisted.internet.defer import inlineCallbacks, gatherResults
from twisted.web.http import BAD_REQUEST
from twisted.trial.unittest import TestCase

from txaws.route53.model import (
    SOA, NS, A, CNAME, Name, create_rrset, upsert_rrset, delete_rrset,
)
from txaws.route53.client import (
    Route53Error,
)

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

        def _cleanup(self, client, zone_identifier):
            d = client.delete_hosted_zone(zone_identifier)
            d.addErrback(lambda err: None)
            return d

        @inlineCallbacks
        def test_resource_record_sets(self):
            zone_name = u"{}.example.invalid.".format(uuid4())
            cname = CNAME(canonical_name=Name(u"example.invalid."))
            client = get_client(self)
            zone = yield client.create_hosted_zone(u"{}".format(time()), zone_name)

            # At least try to clean up, to be as nice as possible.
            # This might fail and someone else might have to do the
            # cleanup - but it might not!
            self.addCleanup(lambda: self._cleanup(client, zone.identifier))

            create = create_rrset(
                Name(u"foo.{}".format(zone_name)),
                u"CNAME",
                60,
                [cname],
            )
            yield client.change_resource_record_sets(zone.identifier, [create])
            initial = yield client.list_resource_record_sets(zone.identifier)
            self.assertEqual(
                {cname},
                initial[Name(u"foo.{}".format(zone_name))],
            )

            # Zones start with an SOA and some NS records.
            soa = list(rr for rr in initial[Name(zone_name)] if isinstance(rr, SOA))
            self.assertEqual(len(soa), 1, "Expected one SOA record, got {}".format(soa))
            ns = list(rr for rr in initial[Name(zone_name)] if isinstance(rr, NS))
            self.assertNotEqual([], ns, "Expected some NS records, got none")

            # Unrecognized change type
            # XXX This depends on _ChangeRRSet using attrs.
            bogus = attr.assoc(create, action=u"BOGUS")
            d = client.change_resource_record_sets(zone.identifier, [bogus])
            error = yield self.assertFailure(d, Route53Error)
            self.assertEqual(BAD_REQUEST, int(error.status))

            created_a = A(IPv4Address(u"10.0.0.1"))
            upsert_create = upsert_rrset(
                Name(u"upsert.{}".format(zone_name)),
                u"A",
                60,
                [created_a],
            )
            updated_a = A(IPv4Address(u"10.0.0.2"))
            upsert_update = upsert_rrset(
                upsert_create.name,
                upsert_create.type,
                60,
                [updated_a],
            )
            yield client.change_resource_record_sets(zone.identifier, [upsert_create])
            rrsets = yield client.list_resource_record_sets(zone.identifier)
            self.assertEqual(rrsets[upsert_create.name], {created_a})

            yield client.change_resource_record_sets(zone.identifier, [upsert_update])
            rrsets = yield client.list_resource_record_sets(zone.identifier)
            self.assertEqual(rrsets[upsert_create.name], {updated_a})

            # Use the name and maxitems parameters to select exactly one resource record.
            rrsets = yield client.list_resource_record_sets(
                zone.identifier, maxitems=1, name=upsert_create.name, type=u"A",
            )
            self.assertEqual(rrsets, {upsert_create.name: {updated_a}})

            # It's invalid to specify type without name.
            d = client.list_resource_record_sets(zone.identifier, type=u"A")
            error = yield self.assertFailure(d, Route53Error)
            self.assertEqual(BAD_REQUEST, int(error.status))

            # It's invalid to delete the SOA record.
            d = client.change_resource_record_sets(
                zone.identifier, [
                    delete_rrset(
                        Name(zone_name),
                        u"SOA",
                        # XXX Magically matches AWS value
                        900,
                        soa,
                    ),
                ],
            )
            error = yield self.assertFailure(d, Route53Error)
            self.assertEqual(BAD_REQUEST, int(error.status))

            # Likewise, the NS records.
            d = client.change_resource_record_sets(
                zone.identifier, [
                    delete_rrset(
                        Name(zone_name),
                        u"NS",
                        # XXX Magically matches AWS value
                        172800,
                        ns,
                    ),
                ],
            )
            error = yield self.assertFailure(d, Route53Error)
            self.assertEqual(BAD_REQUEST, int(error.status))

            # Test deletion at the end so the zone is clean for the
            # naive cleanup logic.
            yield client.change_resource_record_sets(zone.identifier, [
                delete_rrset(
                    Name(u"foo.{}".format(zone_name)),
                    u"CNAME",
                    # XXX Matches creation above
                    60,
                    [cname],
                ),
                delete_rrset(
                    upsert_create.name,
                    upsert_create.type,
                    60,
                    [updated_a],
                ),
            ])
            rrsets = yield client.list_resource_record_sets(zone.identifier)
            self.assertNotIn(Name(u"foo.{}".format(zone_name)), rrsets)
            self.assertNotIn(upsert_create.name, rrsets)

            # Delete something that doesn't exist
            # Create something that already exists

    return Route53IntegrationTests
