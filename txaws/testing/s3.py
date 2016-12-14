from twisted.internet.defer import succeed, fail

from txaws.s3.model import Bucket, BucketListing
from txaws.s3.exception import S3Error

def rate_limited(f):
    def g(self, *a, **kw):
        if get_rate_limit_exceeded(self):
            return fail(S3Error("<slowdown/>", 400))
        return f(self, *a, **kw)
    return g


class MemoryS3Client(object):
    from time import time

    def __init__(self, creds, endpoint):
        self.creds = creds
        self.endpoint = endpoint
        self.buckets = {}

    @rate_limited
    def list_buckets(self):
        return succeed(self.buckets.keys())

    @rate_limited
    def create_bucket(self, bucket):
        assert bucket not in self.buckets
        self.buckets[bucket] = dict(
            bucket=Bucket(bucket, self.time()),
            listing=BucketListing(bucket, None, None, None, False),
        )
        return succeed(None)

    @rate_limited
    def delete_bucket(self, bucket):
        if self.buckets[bucket]["listing"].contents:
            return fail(S3Error("<notempty/>", 400))
        del self.buckets[bucket]
        return succeed(None)

    @rate_limited
    def get_bucket(self, bucket):
        try:
            pieces = self.buckets[bucket]
        except KeyEror:
            return fail(S3Error("<nosuchbucket/>", 400))
        return pieces["listing"]


def set_rate_limit_exceeded(client):
    client._rate_limit_exceeded = True

def clear_rate_limit_exceeded(client):
    client._rate_limit_exceeded = False

def get_rate_limit_exceeded(client):
    return getattr(client, "_rate_limit_exceeded", False)
