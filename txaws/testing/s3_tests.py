# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for the S3 client(s).
"""

from uuid import uuid4

from twisted.trial.unittest import TestCase

def s3_integration_tests(get_client):
    class S3IntegrationTests(TestCase):
        def test_list_buckets_empty(self):
            """
            If there are no buckets, ``list_buckets`` returns a ``Deferred``
            that fires with a list, maybe containing some buckets.
            """
            client = get_client(self)
            d = client.list_buckets()
            d.addCallback(self.assertIsInstance, list)
            return d

        def test_create_bucket(self):
            """
            After ``create_bucket`` succeeds, ``list_buckets`` returns a
            ``Deferred`` that fires with a list containing it.
            """
            bucket_name = str(uuid4())
            client = get_client(self)
            d = client.create_bucket(bucket_name)
            d.addCallback(lambda ignored: client.list_buckets())
            d.addCallback(lambda buckets: (bucket.name for bucket in buckets))
            d.addCallback(lambda names: self.assertIn(bucket_name, names))
            return d
    return S3IntegrationTests
