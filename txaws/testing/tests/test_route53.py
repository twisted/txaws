# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for ``txaws.testing.route53``.
"""

from txaws.testing.integration import get_memory_service
from txaws.testing.route53_tests import route53_integration_tests

def get_memory_client(case):
    return get_memory_service(case).get_route53_client()


class MemoryRoute53TestCase(route53_integration_tests(get_memory_client)):
    """
    Tests for the in-memory Route53 test double.
    """
