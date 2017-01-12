# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for ``txaws.testing.s3``.
"""

from txaws.testing.integration import get_memory_service
from txaws.testing.s3_tests import s3_integration_tests


def get_memory_client(case):
    return get_memory_service(case).get_s3_client()



class MemoryS3TestCase(s3_integration_tests(get_memory_client)):
    """
    Tests for the in-memory S3 test double.
    """
