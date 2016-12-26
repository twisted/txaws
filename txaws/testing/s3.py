"""
An in-memory implementation of the S3 client interface as an aid
to unit testing.
"""

__all__ = [
    "MemoryS3",
]

from weakref import WeakKeyDictionary

from twisted.internet.defer import succeed, fail

from txaws.s3.model import Bucket, BucketListing
from txaws.s3.exception import S3Error

def _rate_limited(f):
    def g(self, *a, **kw):
        if self._state.get_rate_limit_exceeded():
            return fail(S3Error("<slowdown/>", 400))
        return f(self, *a, **kw)
    return g


class MemoryS3(object):
    """
    ``MemoryS3`` is a factory for new S3 clients.
    """
    def __init__(self):
        self._state = WeakKeyDictionary()

    def get_state(self, client):
        return self._state.setdefault(client, _S3ClientState())

    def client(self, *a, **kw):
        client = _MemoryS3Client(self, *a, **kw)
        return client, self.get_state(client)


class S3ClientState(object):
    """
    ``_S3ClientState`` instances hold the ``_MemoryS3Client`` instance
    state that is specific to testing and does not exist on
    ``txaws.s3.S3Client`` instances.
    """
    from time import time

    rate_limited_exceeded = False

    def __init__(self):
        self.buckets = {}

    def set_rate_limit_exceeded(self):
        self.rate_limit_exceeded = True

    def clear_rate_limit_exceeded(self):
        self.rate_limit_exceeded = False

    def get_rate_limit_exceeded(self,):
        return self.rate_limit_exceeded


class _ControllerState(object):
    def __get__(self, oself, type):
        return oself._controller.get_state(oself)


class _MemoryS3Client(object):
    _state = ControllerState()

    def __init__(self, controller, creds, endpoint):
        self._controller = controller
        self.creds = creds
        self.endpoint = endpoint

    @_rate_limited
    def list_buckets(self):
        return succeed(self._state.buckets.keys())

    @_rate_limited
    def create_bucket(self, bucket):
        assert bucket not in self._state.buckets
        self._state.buckets[bucket] = dict(
            bucket=Bucket(bucket, self._state.time()),
            listing=BucketListing(bucket, None, None, None, False),
        )
        return succeed(None)

    @_rate_limited
    def delete_bucket(self, bucket):
        if self._state.buckets[bucket]["listing"].contents:
            return fail(S3Error("<notempty/>", 400))
        del self._state.buckets[bucket]
        return succeed(None)

    @_rate_limited
    def get_bucket(self, bucket):
        try:
            pieces = self._state.buckets[bucket]
        except KeyError:
            return fail(S3Error("<nosuchbucket/>", 400))
        return pieces["listing"]
