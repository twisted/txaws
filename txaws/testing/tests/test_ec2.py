# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for ``txaws.testing.ec2``.
"""

from txaws.testing.integration import get_memory_service
from txaws.testing.ec2_tests import ec2_integration_tests


def get_memory_client(case):
    return get_memory_service(case).get_ec2_client()



class MemoryEC2TestCase(ec2_integration_tests(get_memory_client)):
    """
    Tests for the in-memory EC2 test double.
    """
