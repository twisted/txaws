# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for ``txaws.testing.s3``.
"""

from txaws.credentials import AWSCredentials
from txaws.service import S3_ENDPOINT

from txaws.testing.s3 import MemoryS3
from txaws.testing.s3_tests import s3_integration_tests


def get_memory_client(case):
    s3 = MemoryS3()
    client, state = s3.client(
        AWSCredentials("fake access key", "fake secret key"),
        S3_ENDPOINT,
    )
    return client


class MemoryS3TestCase(s3_integration_tests(get_memory_client)):
    """
    Tests for the in-memory S3 test double.
    """
