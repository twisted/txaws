# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for the Route53 client(s).
"""

from uuid import uuid4

from twisted.internet.defer import inlineCallbacks, gatherResults

from twisted.trial.unittest import TestCase

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

            yield gatherResults([
                client.create_hosted_zone(name)
                for name in zone_names
            ])
    return Route53IntegrationTests
