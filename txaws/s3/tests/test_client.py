import datetime
from hashlib import sha256
import warnings

from twisted.internet.defer import succeed

from txaws.credentials import AWSCredentials
try:
    from txaws.s3 import client
except ImportError:
    s3clientSkip = ("S3Client couldn't be imported (perhaps because dateutil, "
                    "on which it depends, isn't present)")
else:
    s3clientSkip = None
from txaws.s3.acls import AccessControlPolicy
from txaws.s3.model import (RequestPayment, MultipartInitiationResponse,
                            MultipartCompletionResponse)
from txaws.testing.producers import StringBodyProducer
from txaws.service import AWSServiceEndpoint
from txaws.testing import payload
from txaws.testing.base import TXAWSTestCase
from txaws.util import calculate_md5


class URLContextTestCase(TXAWSTestCase):

    endpoint = AWSServiceEndpoint("https://s3.amazonaws.com/")

    def test_get_host_with_no_bucket(self):
        url_context = client.URLContext(self.endpoint)
        self.assertEquals(url_context.get_host(), "s3.amazonaws.com")

    def test_get_host_with_bucket(self):
        url_context = client.URLContext(self.endpoint, "mystuff")
        self.assertEquals(url_context.get_host(), "s3.amazonaws.com")

    def test_get_path_with_no_bucket(self):
        url_context = client.URLContext(self.endpoint)
        self.assertEquals(url_context.get_path(), "/")

    def test_get_path_with_bucket(self):
        url_context = client.URLContext(self.endpoint, bucket="mystuff")
        self.assertEquals(url_context.get_path(), "/mystuff/")

    def test_get_path_with_bucket_and_object(self):
        url_context = client.URLContext(
            self.endpoint, bucket="mystuff", object_name="/images/thing.jpg")
        self.assertEquals(url_context.get_host(), "s3.amazonaws.com")
        self.assertEquals(url_context.get_path(), "/mystuff/images/thing.jpg")

    def test_get_path_with_bucket_and_object_without_slash(self):
        url_context = client.URLContext(
            self.endpoint, bucket="mystuff", object_name="images/thing.jpg")
        self.assertEquals(url_context.get_host(), "s3.amazonaws.com")
        self.assertEquals(url_context.get_path(), "/mystuff/images/thing.jpg")

    def test_get_url_with_custom_endpoint(self):
        endpoint = AWSServiceEndpoint("http://localhost/")
        url_context = client.URLContext(endpoint)
        self.assertEquals(url_context.endpoint.get_uri(), "http://localhost/")
        self.assertEquals(url_context.get_url(), "http://localhost/")

    def test_get_uri_with_endpoint_bucket_and_object(self):
        endpoint = AWSServiceEndpoint("http://localhost/")
        url_context = client.URLContext(
            endpoint, bucket="mydocs", object_name="notes.txt")
        self.assertEquals(
            url_context.get_url(),
            "http://localhost/mydocs/notes.txt")

    def test_custom_port_endpoint(self):
        test_uri = 'http://0.0.0.0:12345/'
        endpoint = AWSServiceEndpoint(uri=test_uri)
        self.assertEquals(endpoint.port, 12345)
        self.assertEquals(endpoint.scheme, 'http')
        context = client.URLContext(service_endpoint=endpoint,
                bucket="foo",
                object_name="bar")
        self.assertEquals(context.get_host(), '0.0.0.0')
        self.assertEquals(context.get_url(), test_uri + 'foo/bar')

    def test_custom_port_endpoint_https(self):
        test_uri = 'https://0.0.0.0:12345/'
        endpoint = AWSServiceEndpoint(uri=test_uri)
        self.assertEquals(endpoint.port, 12345)
        self.assertEquals(endpoint.scheme, 'https')
        context = client.URLContext(service_endpoint=endpoint,
                bucket="foo",
                object_name="bar")
        self.assertEquals(context.get_host(), '0.0.0.0')
        self.assertEquals(context.get_url(), test_uri + 'foo/bar')


URLContextTestCase.skip = s3clientSkip


class S3ClientTestCase(TXAWSTestCase):

    def setUp(self):
        TXAWSTestCase.setUp(self)
        self.creds = AWSCredentials(
            access_key="accessKey", secret_key="secretKey")
        self.endpoint = AWSServiceEndpoint()

    def test_list_buckets(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint,
                body_producer=None, receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, None)
                self.assertEqual(query.object_name, None)
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})

            def submit(query):
                return succeed(payload.sample_list_buckets_result)

        def check_list_buckets(results):
            bucket1, bucket2 = results
            self.assertEquals(bucket1.name, "quotes")
            self.assertEquals(
                bucket1.creation_date.timetuple(),
                (2006, 2, 3, 16, 45, 9, 4, 34, 0))
            self.assertEquals(bucket2.name, "samples")
            self.assertEquals(
                bucket2.creation_date.timetuple(),
                (2006, 2, 3, 16, 41, 58, 4, 34, 0))

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.list_buckets()
        return d.addCallback(check_list_buckets)

    def test_create_bucket(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                body_producer=None, receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket)
                self.assertEquals(action, "PUT")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, None)
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})

            def submit(query, url_context=None):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.create_bucket("mybucket")

    def test_get_bucket(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                body_producer=None, receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, None)
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})

            def submit(query, url_context=None):
                return succeed(payload.sample_get_bucket_result)

        def check_results(listing):
            self.assertEquals(listing.name, "mybucket")
            self.assertEquals(listing.prefix, "N")
            self.assertEquals(listing.marker, "Ned")
            self.assertEquals(listing.max_keys, "40")
            self.assertEquals(listing.is_truncated, "false")
            self.assertEquals(len(listing.contents), 2)
            content1 = listing.contents[0]
            self.assertEquals(content1.key, "Nelson")
            self.assertEquals(
                content1.modification_date.timetuple(),
                (2006, 1, 1, 12, 0, 0, 6, 1, 0))
            self.assertEquals(
                content1.etag, '"828ef3fdfa96f00ad9f27c383fc9ac7f"')
            self.assertEquals(content1.size, "5")
            self.assertEquals(content1.storage_class, "STANDARD")
            owner = content1.owner
            self.assertEquals(owner.id,
                              "bcaf1ffd86f41caff1a493dc2ad8c2c281e37522a640e16"
                              "1ca5fb16fd081034f")
            self.assertEquals(owner.display_name, "webfile")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_pagination(self):
        """
        L{S3Client.get_bucket} accepts C{marker} and C{max_keys} arguments
        to control pagination of results.
        """
        class StubQuery(client.Query):
            def submit(query, url_context):
                self.assertEqual(
                    "http:///mybucket/?marker=abcdef&max-keys=42",
                    url_context.get_url(),
                )
                return succeed(payload.sample_get_bucket_result)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket("mybucket", marker="abcdef", max_keys=42)
        return d

    def test_get_bucket_location(self):
        """
        L{S3Client.get_bucket_location} creates a L{Query} to get a bucket's
        location.  It parses the returned C{LocationConstraint} XML document
        and returns a C{Deferred} that requests the bucket's location
        constraint.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?location")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(payload.sample_get_bucket_location_result)

        def check_results(location_constraint):
            self.assertEquals(location_constraint, "EU")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_location("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_lifecycle_multiple_rules(self):
        """
        L{S3Client.get_bucket_lifecycle} creates a L{Query} to get a bucket's
        lifecycle.  It parses the returned C{LifecycleConfiguration} XML
        document and returns a C{Deferred} that requests the bucket's lifecycle
        configuration with multiple rules.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?lifecycle")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(payload.
                    sample_s3_get_bucket_lifecycle_multiple_rules_result)

        def check_results(lifecycle_config):
            self.assertTrue(len(lifecycle_config.rules) == 2)
            rule = lifecycle_config.rules[1]
            self.assertEquals(rule.id, 'another-id')
            self.assertEquals(rule.prefix, 'another-logs')
            self.assertEquals(rule.status, 'Disabled')
            self.assertEquals(rule.expiration, 37)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_lifecycle("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_lifecycle(self):
        """
        L{S3Client.get_bucket_lifecycle} creates a L{Query} to get a bucket's
        lifecycle.  It parses the returned C{LifecycleConfiguration} XML
        document and returns a C{Deferred} that requests the bucket's lifecycle
        configuration.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?lifecycle")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(payload.sample_s3_get_bucket_lifecycle_result)

        def check_results(lifecycle_config):
            rule = lifecycle_config.rules[0]
            self.assertEquals(rule.id, '30-day-log-deletion-rule')
            self.assertEquals(rule.prefix, 'logs')
            self.assertEquals(rule.status, 'Enabled')
            self.assertEquals(rule.expiration, 30)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_lifecycle("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_website_config(self):
        """
        L{S3Client.get_bucket_website_config} creates a L{Query} to get a
        bucket's website configurtion.  It parses the returned
        C{WebsiteConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's website configuration.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?website")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(payload.
                    sample_s3_get_bucket_website_no_error_result)

        def check_results(website_config):
            self.assertEquals(website_config.index_suffix, "index.html")
            self.assertEquals(website_config.error_key, None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_website_config("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_website_config_with_error_doc(self):
        """
        L{S3Client.get_bucket_website_config} creates a L{Query} to get a
        bucket's website configurtion.  It parses the returned
        C{WebsiteConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's website configuration with the error document.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?website")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(payload.sample_s3_get_bucket_website_result)

        def check_results(website_config):
            self.assertEquals(website_config.index_suffix, "index.html")
            self.assertEquals(website_config.error_key, "404.html")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_website_config("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_notification_config(self):
        """
        L{S3Client.get_bucket_notification_config} creates a L{Query} to get a
        bucket's notification configuration.  It parses the returned
        C{NotificationConfiguration} XML document and returns a C{Deferred}
        that requests the bucket's notification configuration.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?notification")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(payload.
                               sample_s3_get_bucket_notification_result)

        def check_results(notification_config):
            self.assertEquals(notification_config.topic, None)
            self.assertEquals(notification_config.event, None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_notification_config("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_notification_config_with_topic(self):
        """
        L{S3Client.get_bucket_notification_config} creates a L{Query} to get a
        bucket's notification configuration.  It parses the returned
        C{NotificationConfiguration} XML document and returns a C{Deferred}
        that requests the bucket's notification configuration with a topic.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?notification")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(
                    payload.
                        sample_s3_get_bucket_notification_with_topic_result)

        def check_results(notification_config):
            self.assertEquals(notification_config.topic,
                              "arn:aws:sns:us-east-1:123456789012:myTopic")
            self.assertEquals(notification_config.event,
                              "s3:ReducedRedundancyLostObject")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_notification_config("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_versioning_config(self):
        """
        L{S3Client.get_bucket_versioning_configuration} creates a L{Query} to
        get a bucket's versioning status.  It parses the returned
        C{VersioningConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's versioning configuration.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?versioning")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(payload.sample_s3_get_bucket_versioning_result)

        def check_results(versioning_config):
            self.assertEquals(versioning_config.status, None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_versioning_config("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_versioning_config_enabled(self):
        """
        L{S3Client.get_bucket_versioning_config} creates a L{Query} to get a
        bucket's versioning configuration.  It parses the returned
        C{VersioningConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's versioning configuration that has a enabled
        C{Status}.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?versioning")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(payload.
                               sample_s3_get_bucket_versioning_enabled_result)

        def check_results(versioning_config):
            self.assertEquals(versioning_config.status, 'Enabled')

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_versioning_config("mybucket")
        return d.addCallback(check_results)

    def test_get_bucket_versioning_config_mfa_disabled(self):
        """
        L{S3Client.get_bucket_versioning_config} creates a L{Query} to get a
        bucket's versioning configuration.  It parses the returned
        C{VersioningConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's versioning configuration that has a disabled
        C{MfaDelete}.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?versioning")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {})

            def submit(query, url_context=None):
                return succeed(
                    payload.
                        sample_s3_get_bucket_versioning_mfa_disabled_result)

        def check_results(versioning_config):
            self.assertEquals(versioning_config.mfa_delete, 'Disabled')

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        d = s3.get_bucket_versioning_config("mybucket")
        return d.addCallback(check_results)

    def test_delete_bucket(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                body_producer=None, receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket)
                self.assertEquals(action, "DELETE")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, None)
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})

            def submit(query, url_context=None):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.delete_bucket("mybucket")

    def test_put_bucket_acl(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, data="", body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name,
                    data=data)
                self.assertEquals(action, "PUT")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?acl")
                self.assertEqual(query.data,
                                 payload.sample_access_control_policy_result)
                self.assertEqual(query.metadata, {})

            def submit(query, url_context=None):
                return succeed(payload.sample_access_control_policy_result)

        def check_result(result):
            self.assert_(isinstance(result, AccessControlPolicy))

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        policy = AccessControlPolicy.from_xml(
            payload.sample_access_control_policy_result)
        return s3.put_bucket_acl("mybucket", policy).addCallback(check_result)

    def test_get_bucket_acl(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, data="", receiver_factory=None,
                         body_producer=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name,
                                                 data=data)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?acl")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})

            def submit(query, url_context=None):
                return succeed(payload.sample_access_control_policy_result)

        def check_result(result):
            self.assert_(isinstance(result, AccessControlPolicy))

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.get_bucket_acl("mybucket").addCallback(check_result)

    def test_put_request_payment(self):
        """
        L{S3Client.put_request_payment} creates a L{Query} to set payment
        information.  An C{RequestPaymentConfiguration} XML document is built
        and sent to the endpoint and a C{Deferred} is returned that fires with
        the results of the request.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                object_name=None, data=None, content_type=None,
                metadata=None, body_producer=None, receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket,
                    object_name=object_name, data=data,
                    content_type=content_type, metadata=metadata)
                self.assertEqual(action, "PUT")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?requestPayment")
                xml = ("<RequestPaymentConfiguration "
                         'xmlns="http://s3.amazonaws.com/doc/2006-03-01/">\n'
                       "  <Payer>Requester</Payer>\n"
                       "</RequestPaymentConfiguration>")
                self.assertEqual(query.data, xml)
                self.assertEqual(query.metadata, None)

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.put_request_payment("mybucket", "Requester")

    def test_get_request_payment(self):
        """
        L{S3Client.get_request_payment} creates a L{Query} to get payment
        information.  It parses the returned C{RequestPaymentConfiguration}
        XML document and returns a C{Deferred} that fires with the payer's
        name.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                object_name=None, data=None, content_type=None,
                metadata=None, body_producer=None, receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket,
                    object_name=object_name, data=data,
                    content_type=content_type, metadata=metadata)
                self.assertEqual(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "?requestPayment")
                self.assertEqual(query.metadata, None)

            def submit(query):
                return succeed(payload.sample_request_payment)

        def check_request_payment(result):
            self.assertEquals(result, "Requester")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        deferred = s3.get_request_payment("mybucket")
        return deferred.addCallback(check_request_payment)

    def test_put_object(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                object_name=None, data=None, content_type=None,
                metadata=None, amz_headers=None, body_producer=None,
                receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket,
                    object_name=object_name, data=data,
                    content_type=content_type, metadata=metadata,
                    amz_headers=amz_headers)
                self.assertEqual(action, "PUT")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "objectname")
                self.assertEqual(query.data, "some data")
                self.assertEqual(query.content_type, "text/plain")
                self.assertEqual(query.metadata, {"key": "some meta data"})
                self.assertEqual(query.amz_headers, {"acl": "public-read"})

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.put_object("mybucket", "objectname", "some data",
                             content_type="text/plain",
                             metadata={"key": "some meta data"},
                             amz_headers={"acl": "public-read"})

    def test_put_object_with_custom_body_producer(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                object_name=None, data=None, content_type=None,
                metadata=None, amz_headers=None, body_producer=None,
                receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket,
                    object_name=object_name, data=data,
                    content_type=content_type, metadata=metadata,
                    amz_headers=amz_headers, body_producer=body_producer)
                self.assertEqual(action, "PUT")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "objectname")
                self.assertEqual(query.content_type, "text/plain")
                self.assertEqual(query.metadata, {"key": "some meta data"})
                self.assertEqual(query.amz_headers, {"acl": "public-read"})
                self.assertIdentical(body_producer, string_producer)

            def submit(query):
                return succeed(None)


        string_producer = StringBodyProducer("some data")
        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.put_object("mybucket", "objectname",
                             content_type="text/plain",
                             metadata={"key": "some meta data"},
                             amz_headers={"acl": "public-read"},
                             body_producer=string_producer)

    def test_copy_object(self):
        """
        L{S3Client.copy_object} creates a L{Query} to copy an object from one
        bucket to another.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                object_name=None, data=None, content_type=None,
                metadata=None, amz_headers=None, body_producer=None,
                receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket,
                    object_name=object_name, data=data,
                    content_type=content_type, metadata=metadata,
                    amz_headers=amz_headers)
                self.assertEqual(action, "PUT")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "newbucket")
                self.assertEqual(query.object_name, "newobjectname")
                self.assertEqual(query.data, None)
                self.assertEqual(query.content_type, None)
                self.assertEqual(query.metadata, {"key": "some meta data"})
                self.assertEqual(query.amz_headers,
                                 {"copy-source": "/mybucket/objectname"})

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.copy_object("mybucket", "objectname", "newbucket",
                              "newobjectname",
                              metadata={"key": "some meta data"})

    def test_get_object(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                object_name=None, data=None, content_type=None,
                metadata=None, amz_headers=None, body_producer=None,
                receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket,
                    object_name=object_name, data=data,
                    content_type=content_type, metadata=metadata)
                self.assertEqual(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "objectname")

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.get_object("mybucket", "objectname")

    def test_head_object(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                object_name=None, data=None, content_type=None,
                metadata=None, body_producer=None, receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket,
                    object_name=object_name, data=data,
                    content_type=content_type, metadata=metadata)
                self.assertEqual(action, "HEAD")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "objectname")

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.head_object("mybucket", "objectname")

    def test_delete_object(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                object_name=None, data=None, content_type=None,
                metadata=None, body_producer=None, receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket,
                    object_name=object_name, data=data,
                    content_type=content_type, metadata=metadata)
                self.assertEqual(action, "DELETE")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "objectname")

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.delete_object("mybucket", "objectname")

    def test_put_object_acl(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, data="", body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name,
                                                 data=data)
                self.assertEquals(action, "PUT")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "myobject?acl")
                self.assertEqual(query.data,
                                 payload.sample_access_control_policy_result)
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.metadata, {})

            def submit(query, url_context=None):
                return succeed(payload.sample_access_control_policy_result)

        def check_result(result):
            self.assert_(isinstance(result, AccessControlPolicy))

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        policy = AccessControlPolicy.from_xml(
            payload.sample_access_control_policy_result)
        deferred = s3.put_object_acl("mybucket", "myobject", policy)
        return deferred.addCallback(check_result)

    def test_get_object_acl(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, data="", body_producer=None,
                         receiver_factory=None):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name,
                                                 data=data)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "myobject?acl")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})

            def submit(query, url_context=None):
                return succeed(payload.sample_access_control_policy_result)

        def check_result(result):
            self.assert_(isinstance(result, AccessControlPolicy))

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        deferred = s3.get_object_acl("mybucket", "myobject")
        return deferred.addCallback(check_result)

    def test_init_multipart_upload(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, data="", body_producer=None,
                         content_type=None, receiver_factory=None, metadata={},
                         amz_headers={}):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 amz_headers=amz_headers,
                                                 object_name=object_name,
                                                 data=data)
                self.assertEquals(action, "POST")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "example-bucket")
                self.assertEqual(query.object_name, "example-object?uploads")
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})
                self.assertEqual(query.amz_headers, {"acl": "public"})

            def submit(query, url_context=None):
                return succeed(payload.sample_s3_init_multipart_upload_result)


        def check_result(result):
            self.assert_(isinstance(result, MultipartInitiationResponse))
            self.assertEqual(result.bucket, "example-bucket")
            self.assertEqual(result.object_name, "example-object")
            self.assertEqual(result.upload_id, "deadbeef")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        deferred = s3.init_multipart_upload("example-bucket", "example-object",
            amz_headers={"acl": "public"})
        return deferred.addCallback(check_result)

    def test_upload_part(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, data="", body_producer=None,
                         content_type=None, receiver_factory=None, metadata={}):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name,
                                                 data=data)
                self.assertEquals(action, "PUT")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "example-bucket")
                self.assertEqual(query.object_name,
                    "example-object?partNumber=3&uploadId=testid")
                self.assertEqual(query.data, "some data")
                self.assertEqual(query.metadata, {})

            def submit(query, url_context=None):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.upload_part("example-bucket", "example-object", "testid", 3,
                              "some data")

    def test_complete_multipart_upload(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, data="", body_producer=None,
                         content_type=None, receiver_factory=None, metadata={}):
                super(StubQuery, query).__init__(action=action, creds=creds,
                                                 bucket=bucket,
                                                 object_name=object_name,
                                                 data=data)
                self.assertEquals(action, "POST")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.bucket, "example-bucket")
                self.assertEqual(query.object_name,
                    "example-object?uploadId=testid")
                self.assertEqual(query.data, "<CompleteMultipartUpload>\n"
                    "<Part>\n<PartNumber>1</PartNumber>\n<ETag>a</ETag>\n"
                    "</Part>\n<Part>\n<PartNumber>2</PartNumber>\n"
                    "<ETag>b</ETag>\n</Part>\n</CompleteMultipartUpload>")
                self.assertEqual(query.metadata, {})

            def submit(query, url_context=None):
                return succeed(
                    payload.sample_s3_complete_multipart_upload_result)


        def check_result(result):
            self.assert_(isinstance(result, MultipartCompletionResponse))
            self.assertEqual(result.bucket, "example-bucket")
            self.assertEqual(result.object_name, "example-object")
            self.assertEqual(result.location,
                "http://example-bucket.s3.amazonaws.com/example-object")
            self.assertEqual(result.etag,
                '"3858f62230ac3c915f300c664312c11f-9"')

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        deferred = s3.complete_multipart_upload("example-bucket",
                                                "example-object",
                                                "testid", [(1, "a"), (2, "b")])
        return deferred.addCallback(check_result)


S3ClientTestCase.skip = s3clientSkip


class QueryTestCase(TXAWSTestCase):

    creds = AWSCredentials(access_key="fookeyid", secret_key="barsecretkey")
    endpoint = AWSServiceEndpoint("https://choopy.s3.amazonaws.com/")
    utc_instant = datetime.datetime(2015, 8, 30, 12, 36)

    def fake_sign(self, headers, data, url_context, instant, method):
        return "Authorization header"

    def test_default_creation(self):
        query = client.Query(action="PUT")
        self.assertEquals(query.bucket, None)
        self.assertEquals(query.object_name, None)
        self.assertEquals(query.data, "")
        self.assertEquals(query.content_type, None)
        self.assertEquals(query.metadata, {})

    def test_default_endpoint(self):
        query = client.Query(action="PUT")
        self.assertEquals(self.endpoint.host, "choopy.s3.amazonaws.com")
        self.assertEquals(query.endpoint.host, "s3.amazonaws.com")
        self.assertEquals(self.endpoint.method, "GET")
        self.assertEquals(query.endpoint.method, "PUT")

    def test_set_content_type_no_object_name(self):
        query = client.Query(action="PUT")
        query.set_content_type()
        self.assertEquals(query.content_type, None)

    def test_set_content_type(self):
        query = client.Query(action="PUT", object_name="advicedog.jpg")
        query.set_content_type()
        self.assertEquals(query.content_type, "image/jpeg")

    def test_set_content_type_with_content_type_already_set(self):
        query = client.Query(
            action="PUT", object_name="data.txt", content_type="text/csv")
        query.set_content_type()
        self.assertNotEquals(query.content_type, "text/plain")
        self.assertEquals(query.content_type, "text/csv")

    def test_get_headers(self):
        query = client.Query(
            action="GET", creds=self.creds, bucket="mystuff",
            object_name="/images/thing.jpg")

        headers = query.get_headers(self.utc_instant)
        self.assertEquals(headers.get("Content-Type"), "image/jpeg")
        self.assertEquals(
            headers.get("x-amz-content-sha256"),
            sha256(b"").hexdigest(),
        )
        self.assertEqual(headers.get("x-amz-date"), "20150830T123600Z")
        self.assertTrue(
            headers.get("Authorization").startswith("AWS4-HMAC-SHA256"))
        self.assertTrue(len(headers.get("Authorization")) > 40)

    def test_get_headers_with_data(self):
        query = client.Query(
            action="PUT", creds=self.creds, bucket="mystuff",
            object_name="/images/thing.jpg", data="BINARY IMAGE DATA")

        headers = query.get_headers(self.utc_instant)
        self.assertEquals(headers.get("Content-Type"), "image/jpeg")
        self.assertEqual(headers.get("x-amz-date"), "20150830T123600Z")
        self.assertTrue(
            headers.get("Authorization").startswith("AWS4-HMAC-SHA256"))
        self.assertTrue(len(headers.get("Authorization")) > 40)

    def test_sign(self):
        query = client.Query(action="PUT", creds=self.creds, data="data")
        signed = query.sign(headers={"x-amz-date": "20150830T123600Z"},
                            data="some data",
                            url_context=client.URLContext(query.endpoint,
                                                          query.bucket,
                                                          query.object_name),
                            instant=self.utc_instant,
                            method=query.action)
        self.assertEquals(
            signed,
            'AWS4-HMAC-SHA256 '
            'Credential=fookeyid/20150830/us-east-1/s3/aws4_request, '
            'SignedHeaders=host;x-amz-date, '
            'Signature=99e8224887926c76e8e3053cf10f26249798fe2274d717b7d28e6ef'
            '3311d1735')

    def test_object_query(self):
        """
        Test that a request addressing an object is created correctly.
        """
        DATA = b"objectData"
        DIGEST = sha256(DATA).hexdigest()

        request = client.Query(
            action="PUT", bucket="somebucket", object_name="object/name/here",
            data=DATA, content_type="text/plain", metadata={"foo": "bar"},
            amz_headers={"acl": "public-read"}, creds=self.creds,
            endpoint=self.endpoint)
        request.sign = self.fake_sign
        self.assertEqual(request.action, "PUT")
        headers = request.get_headers(self.utc_instant)
        self.assertNotEqual(headers.pop("x-amz-date"), "")
        self.assertEqual(headers,
                         {"Authorization": "Authorization header",
                          "Content-Type": "text/plain",
                          "x-amz-content-sha256": DIGEST,
                          "x-amz-meta-foo": "bar",
                          "x-amz-acl": "public-read"})
        self.assertEqual(request.data, "objectData")

    def test_bucket_query(self):
        """
        Test that a request addressing a bucket is created correctly.
        """
        DIGEST = ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b785"
                  "2b855")

        query = client.Query(
            action="GET", bucket="somebucket", creds=self.creds,
            endpoint=self.endpoint)
        query.sign = self.fake_sign
        self.assertEqual(query.action, "GET")
        headers = query.get_headers(self.utc_instant)
        self.assertNotEqual(headers.pop("x-amz-date"), "")
        self.assertEqual(
            headers, {
            "Authorization": "Authorization header",
            "x-amz-content-sha256": DIGEST})
        self.assertEqual(query.data, "")

    def test_submit(self):
        """
        Submitting the request should invoke getPage correctly.
        """
        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket,
                body_producer=None, receiver_factory=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "fookeyid")
                self.assertEqual(creds.secret_key, "barsecretkey")
                self.assertEqual(query.bucket, "somebucket")
                self.assertEqual(query.object_name, None)
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})

            def submit(query):
                return succeed("")

        query = StubQuery(action="GET", creds=self.creds,
                          endpoint=self.endpoint, bucket="somebucket")
        return query.submit()

    def test_authentication(self):
        query = client.Query(
            action="GET", creds=self.creds, endpoint=self.endpoint)
        query.sign = self.fake_sign

        headers = query.get_headers(self.utc_instant)
        self.assertEqual(
            headers["Authorization"],
            "Authorization header")

    def test_date_attribute_deprecated(self):
        query = client.Query(
            action="GET", creds=self.creds, endpoint=self.endpoint)

        with warnings.catch_warnings(record=True) as caught_warnings:
            self.assertGreater(len(query.date), 20)

        self.assertEqual(len(caught_warnings), 1)
        (warning,) = caught_warnings
        self.assertTrue(issubclass(warning.category, DeprecationWarning))
        self.assertEqual(
            str(warning.message),
            "txaws.s3.client.Query.date is a deprecated attribute")

    def test_date_attribute_settable(self):
        query = client.Query(
            action="GET", creds=self.creds, endpoint=self.endpoint)

        query.date = "XYZ"

        with warnings.catch_warnings(record=True):
            self.assertEqual(query.date, "XYZ")


QueryTestCase.skip = s3clientSkip


class MiscellaneousTestCase(TXAWSTestCase):

    def test_content_md5(self):
        self.assertEqual(calculate_md5("somedata"), "rvr3UC1SmUw7AZV2NqPN0g==")

    def test_request_payment_enum(self):
        """
        Only 'Requester' or 'BucketOwner' may be provided when a
        L{RequestPayment} is instantiated.
        """
        RequestPayment("Requester")
        RequestPayment("BucketOwner")
        self.assertRaises(ValueError, RequestPayment, "Bob")
