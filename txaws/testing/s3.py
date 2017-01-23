"""
An in-memory implementation of the S3 client interface as an aid
to unit testing.
"""

__all__ = [
    "MemoryS3",
]

from datetime import datetime

import attr

from dateutil.tz import tzutc

from twisted.internet.defer import succeed, fail

from txaws.s3.model import Bucket, BucketListing, BucketItem
from txaws.s3.exception import S3Error
from txaws.testing.base import MemoryClient, MemoryService

def _rate_limited(f):
    def g(self, *a, **kw):
        if self._state.get_rate_limit_exceeded():
            return fail(S3Error("<slowdown/>", 400))
        return f(self, *a, **kw)
    return g


class MemoryS3(MemoryService):
    """
    ``MemoryS3`` is a factory for new S3 clients.
    """
    def __init__(self):
        super(MemoryS3, self).__init__(
            client_factory=_MemoryS3Client,
            state_factory=S3ClientState,
        )

class S3ClientState(object):
    """
    ``S3ClientState`` instances hold the ``_MemoryS3Client`` instance
    state that is specific to testing and does not exist on
    ``txaws.s3.S3Client`` instances.
    """
    from time import time

    rate_limit_exceeded = False

    def __init__(self):
        self.buckets = {}
        self.objects = {}

    def set_rate_limit_exceeded(self):
        self.rate_limit_exceeded = True

    def clear_rate_limit_exceeded(self):
        self.rate_limit_exceeded = False

    def get_rate_limit_exceeded(self,):
        return self.rate_limit_exceeded


class _MemoryS3Client(MemoryClient):
    def __init__(self, controller, creds, endpoint):
        super(_MemoryS3Client, self).__init__(controller=controller, creds=creds)
        self.endpoint = endpoint

    @_rate_limited
    def list_buckets(self):
        return succeed(list(
            item["bucket"]
            for item
            in self._state.buckets.itervalues()
        ))

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

    @_rate_limited
    def get_bucket_location(self, bucket):
        return b""

    @_rate_limited
    def put_object(
            self, bucket, object_name,
            data=None, content_type=None,
            metadata={}, amz_headers={},
            body_producer=None,
    ):
        if data is not None and body_producer is not None:
            raise ValueError("data and body_producer are mutually exclusive")

        contents = self._state.buckets[bucket]["listing"].contents
        if contents is None:
            contents = []
            self._state.buckets[bucket]["listing"].contents = contents
        contents.append(BucketItem(
            key=object_name,
            modification_date=datetime.fromtimestamp(int(self._state.time()), tz=tzutc()),
            etag='"{}"'.format('a' * 32).encode('ascii'),
            size=str(len(data or "")),
            storage_class="STANDARD",
        ))
        if data is not None:
            self._store_object(bucket, object_name, data)
            return succeed(None)

        if body_producer is not None:
            data = []
            memory_consumer = _MemoryConsumer(buffer=data)
            finished = body_producer.startProducing(memory_consumer)
            finished.addCallback(
                lambda ignored: self._store_object(
                    bucket, object_name, b"".join(data),
                )
            )
            return finished

        self._store_object(bucket, object_name, b"")
        return succeed(None)


    def _store_object(self, bucket, obj, data):
        self._state.objects[bucket, obj] = data


    @_rate_limited
    def get_object(self, bucket, object_name):
        return self._state.objects[bucket, object_name]

    @_rate_limited
    def delete_object(self, bucket, object_name):
        del self._state.objects[bucket, object_name]
        contents = self._state.buckets[bucket]["listing"].contents
        for item in contents:
            if item.key == object_name:
                contents.remove(item)
                break


@attr.s
class _MemoryConsumer(object):
    _buffer = attr.ib(default=attr.Factory(list), repr=False)

    # Somehow we get away with a very incomplete IConsumer implementation.

    def write(self, data):
        self._buffer.append(data)
