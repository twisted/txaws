# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for the S3 client(s).
"""

from io import BytesIO
from uuid import uuid4

from twisted.python.compat import unicode
from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks, gatherResults
from twisted.internet.task import cooperate
from twisted.web.client import FileBodyProducer

def s3_integration_tests(get_client):
    class S3IntegrationTests(TestCase):

        @inlineCallbacks
        def test_buckets(self):
            """
            S3 buckets exist in a collection which can be manipulated in the
            obvious ways using ``create_bucket``, ``list_buckets``,
            and ``delete_bucket``.
            """
            bucket_names = {
                str(uuid4()),
                str(uuid4()),
            }

            client = get_client(self)

            yield gatherResults([
                client.create_bucket(name)
                for name in bucket_names
            ])

            buckets = yield client.list_buckets()
            listed_names = {bucket.name for bucket in buckets}
            self.assertTrue(
                # Try to be robust against someone else creating
                # buckets at the same time.
                bucket_names.issubset(listed_names),
                "Expected created buckets {} to be found in bucket listing {}".format(
                    bucket_names, listed_names,
                ),
            )

            yield gatherResults([
                client.delete_bucket(name)
                for name in bucket_names
            ])

            buckets = yield client.list_buckets()
            listed_names = {bucket.name for bucket in buckets}
            self.assertFalse(
                any(name in listed_names for name in bucket_names),
                "Expected deleted buckets {} to not be found in bucket listing {}".format(
                    bucket_names, listed_names,
                ),
            )

        @inlineCallbacks
        def test_objects(self):
            """
            S3 objects exist as collections within individual buckets and can
            be manipulated in the obvious ways using ``put_object``,
            ``get_object``, ``get_bucket`` (for listing), and
            ``delete_object``.
            """
            bucket_name = str(uuid4())
            object_name = b"foo/bar"
            object_data = b"hello world"

            client = get_client(self)

            yield client.create_bucket(bucket_name)
            yield client.put_object(bucket_name, object_name, object_data)

            objects = yield client.get_bucket(bucket_name)
            created = list(
                obj for obj in objects.contents
                if obj.key == object_name
            )
            self.assertEqual(
                1, len(created),
                "Expected to find created object in listing {}".format(objects),
            )
            self.assertEqual(objects.is_truncated, u"false")

            self.assertEqual(str(len(object_data)), created[0].size)

            data = yield client.get_object(bucket_name, object_name)
            self.assertEqual(object_data, data)

            yield client.delete_object(bucket_name, object_name)

            objects = yield client.get_bucket(bucket_name)
            created = list(
                obj for obj in objects.contents
                if obj.key == object_name
            )
            self.assertEqual(
                [], created,
                "Expected to not find deleted objects in listing {}".format(objects),
            )

        def test_get_bucket_object_order(self):
            """
            The objects returned by C{get_bucket} are sorted lexicographically by their
            key.
            """
            bucket_name = unicode(uuid4())
            client = get_client(self)
            d = client.create_bucket(bucket_name)
            def created_bucket(ignored):
                return gatherResults([
                    client.put_object(bucket_name, u"b"),
                    client.put_object(bucket_name, u"a"),
                    client.put_object(bucket_name, u"c"),
            ])
            d.addCallback(created_bucket)
            def created_objects(ignored):
                return client.get_bucket(bucket_name)
            d.addCallback(created_objects)
            def got_objects(listing):
                self.assertEqual(
                    [u"a", u"b", u"c"],
                    list(item.key for item in listing.contents),
                )
            d.addCallback(got_objects)
            return d

        @inlineCallbacks
        def test_get_bucket_prefix(self):
            """
            A subset of S3 objects in a bucket can be retrieved by specifying a value
            for the ``prefix`` argument to ``get_bucket``.
            """
            bucket_name = unicode(uuid4())
            client = get_client(self)
            yield client.create_bucket(bucket_name)
            yield client.put_object(bucket_name, u"a", b"foo")
            yield client.put_object(bucket_name, u"b", b"bar")

            objects = yield client.get_bucket(bucket_name, prefix=b"a")
            self.assertEqual([b"a"], list(obj.key for obj in objects.contents))

        def test_get_bucket_location_empty(self):
            """
            When called for a bucket with no explicit location,
            C{get_bucket_location} returns a L{Deferred} that fires
            C{b""}.
            """
            bucket_name = unicode(uuid4())
            client = get_client(self)
            d = client.create_bucket(bucket_name)
            def created_bucket(ignored):
                return client.get_bucket_location(bucket_name)
            d.addCallback(created_bucket)
            def got_location(location):
                # Without a location set explicitly at creation time,
                # it has no location.
                self.assertEqual(b"", location)
            d.addCallback(got_location)
            return d


        def test_get_bucket_max_keys(self):
            """
            C{max_keys} can be passed to C{get_bucket} to limit the number of
            results.
            """
            bucket_name = unicode(uuid4())
            client = get_client(self)
            d = client.create_bucket(bucket_name)
            def created_bucket(ignored):
                # Put a few objects in it so we can retrieve some of them.
                return gatherResults(list(
                    client.put_object(bucket_name, unicode(i))
                    for i in range(3)
                ))
            d.addCallback(created_bucket)
            def put_objects(ignored):
                return client.get_bucket(bucket_name, max_keys=2)
            d.addCallback(put_objects)
            def got_objects(listing):
                self.assertEqual(2, len(listing.contents))
                self.assertEqual(listing.is_truncated, u"true")
            d.addCallback(got_objects)
            return d


        def test_get_bucket_marker(self):
            """
            C{marker} can be passed to C{get_bucket} to specify the key in the result
            listing with which to start (the key after the value of C{marker}).
            """
            bucket_name = unicode(uuid4())
            client = get_client(self)
            d = client.create_bucket(bucket_name)
            def created_bucket(ignored):
                # Put a few objects in it so we can retrieve some of them.
                return gatherResults(list(
                    client.put_object(bucket_name, unicode(i))
                    for i in range(3)
                ))
            d.addCallback(created_bucket)
            def created_objects(ignored):
                return client.get_bucket(bucket_name, marker=u"0")
            d.addCallback(created_objects)
            def got_objects(listing):
                self.assertEqual(listing.marker, u"0")
                self.assertEqual(u"1", listing.contents[0].key)
            d.addCallback(got_objects)
            return d


        def test_get_bucket_default_max_keys(self):
            """
            C{get_bucket} returns a limited number of results even if C{max_keys} is
            not specified.
            """
            max_keys = 1000
            bucket_name = unicode(uuid4())
            client = get_client(self)
            d = client.create_bucket(bucket_name)
            def created_bucket(ignored):
                # Put a bunch of objects.  The default limit is 1000.
                work = (
                    client.put_object(bucket_name, unicode(i).encode("ascii"))
                    for i in range(max_keys + 3)
                )
                return gatherResults([
                    cooperate(work).whenDone(),
                    cooperate(work).whenDone(),
                    cooperate(work).whenDone(),
                ])
            d.addCallback(created_bucket)
            def put_objects(ignored):
                return client.get_bucket(bucket_name)
            d.addCallback(put_objects)
            def got_objects(listing):
                self.assertEqual(max_keys, len(listing.contents))
            d.addCallback(got_objects)
            return d
        # It takes some while to create the thousand-plus objects.  Give the
        # test some extra time.
        test_get_bucket_default_max_keys.timeout = 300


        def test_put_object_errors(self):
            """
            C{put_object} raises L{ValueError} if called with two conflicting
            sources of object body data.
            """
            client = get_client(self)
            self.assertRaises(
                ValueError,
                client.put_object,
                "bucket", "object",
                # These two are mutually exclusive.
                data="asd", body_producer=FileBodyProducer(BytesIO(b"def")),
            )


        @inlineCallbacks
        def test_put_object_empty(self):
            """
            C{put_object} creates an empty object if passed neither C{body}
            nor C{body_producer}.
            """
            bucket_name = str(uuid4())
            object_name = b"empty_object"

            client = get_client(self)
            yield client.create_bucket(bucket_name)
            yield client.put_object(bucket_name, object_name)

            retrieved = yield client.get_object(bucket_name, object_name)
            self.assertEqual(b"", retrieved)


        @inlineCallbacks
        def test_put_object_body_producer(self):
            """
            C{put_object} accepts a C{body_producer} argument which is an
            L{IBodyProducer} which is used to provide the object's
            content.
            """
            bucket_name = str(uuid4())
            object_name = b"body_producer"
            object_data = b"some random bytes"

            client = get_client(self)

            yield client.create_bucket(bucket_name)
            yield client.put_object(
                bucket_name,
                object_name,
                body_producer=FileBodyProducer(BytesIO(object_data)),
            )

            retrieved = yield client.get_object(bucket_name, object_name)
            self.assertEqual(object_data, retrieved)


        @inlineCallbacks
        def test_object_encoded_chars(self):
            """
            C{get_object} and C{put_object} succeed with an object name that
            requires encoding.
            """
            bucket_name = str(uuid4())
            object_names = [
                b'object:with:colons',
                b'object with spaces',
                u'\N{SNOWMAN}'.encode('utf-8'),
                ]
            object_data = b'some text'
            object_type = b'application/x-txaws-integration-testing'

            client = get_client(self)
            yield client.create_bucket(bucket_name)
            for object_name in object_names:
                yield client.put_object(
                    bucket_name, object_name, object_data,
                    content_type=object_type)
            retrieved = yield gatherResults(
                [client.get_object(bucket_name, object_name)
                 for object_name in object_names],
                consumeErrors=True)
            self.assertEqual([object_data] * len(object_names), retrieved)


    return S3IntegrationTests
