import datetime
from hashlib import sha256
import warnings
from os import environ
from urllib import quote

from attr import assoc

from twisted.web.http_headers import Headers
from twisted.internet.defer import succeed

from txaws.credentials import AWSCredentials
from txaws.client.base import RequestDetails
from txaws.s3 import client
from txaws.s3.acls import AccessControlPolicy
from txaws.s3.model import (RequestPayment, MultipartInitiationResponse,
                            MultipartCompletionResponse)
from txaws.testing.producers import StringBodyProducer
from txaws.testing.s3_tests import s3_integration_tests
from txaws.service import AWSServiceEndpoint, AWSServiceRegion, REGION_US_EAST_1
from txaws.testing import payload
from txaws.testing.base import TXAWSTestCase
from txaws.testing.integration import get_live_service
from txaws.util import calculate_md5

EMPTY_CONTENT_SHA256 = sha256(b"").hexdigest().decode("ascii")

class URLContextTestCase(TXAWSTestCase):

    endpoint = AWSServiceEndpoint("https://s3.amazonaws.com/")

    def test_get_host_with_no_bucket(self):
        url_context = client.URLContext(self.endpoint)
        self.assertEquals(url_context.get_host(), b"s3.amazonaws.com")

    def test_get_host_with_bucket(self):
        url_context = client.URLContext(self.endpoint, "mystuff")
        self.assertEquals(url_context.get_host(), b"s3.amazonaws.com")

    def test_get_path_with_no_bucket(self):
        url_context = client.URLContext(self.endpoint)
        self.assertEquals(url_context.get_path(), b"/")

    def test_get_path_with_bucket(self):
        url_context = client.URLContext(self.endpoint, bucket="mystuff")
        self.assertEquals(url_context.get_path(), b"/mystuff/")

    def test_get_path_with_bucket_and_object(self):
        url_context = client.URLContext(
            self.endpoint, bucket="mystuff", object_name="/images/thing.jpg")
        self.assertEquals(url_context.get_host(), b"s3.amazonaws.com")
        self.assertEquals(url_context.get_path(), b"/mystuff/images/thing.jpg")

    def test_get_path_with_bucket_and_object_without_slash(self):
        url_context = client.URLContext(
            self.endpoint, bucket="mystuff", object_name="images/thing.jpg")
        self.assertEquals(url_context.get_host(), b"s3.amazonaws.com")
        self.assertEquals(url_context.get_path(), b"/mystuff/images/thing.jpg")

    def test_get_url_with_bucket_and_object_with_resource(self):
        url_context = client.URLContext(
            self.endpoint, bucket="mystuff", object_name="thing.jpg?acls")
        self.assertEquals(
            url_context.get_url(),
            b"https://s3.amazonaws.com/mystuff/thing.jpg?acls",
        )

    def test_get_url_with_bucket_and_query(self):
        url_context = client.URLContext(
            self.endpoint, bucket="mystuff", object_name="?max-keys=3")
        self.assertEquals(
            url_context.get_url(),
            b"https://s3.amazonaws.com/mystuff/?max-keys=3",
        )

    def test_get_url_with_custom_endpoint(self):
        endpoint = AWSServiceEndpoint("http://localhost/")
        url_context = client.URLContext(endpoint)
        self.assertEquals(url_context.get_url(), b"http://localhost/")

    def test_get_uri_with_endpoint_bucket_and_object(self):
        endpoint = AWSServiceEndpoint("http://localhost/")
        url_context = client.URLContext(
            endpoint, bucket="mydocs", object_name="notes.txt")
        self.assertEquals(
            url_context.get_url(),
            b"http://localhost/mydocs/notes.txt")

    def test_custom_port_endpoint(self):
        test_uri = b'http://0.0.0.0:12345/'
        endpoint = AWSServiceEndpoint(uri=test_uri)
        self.assertEquals(endpoint.port, 12345)
        self.assertEquals(endpoint.scheme, 'http')
        context = client.URLContext(service_endpoint=endpoint,
                bucket="foo",
                object_name="bar")
        self.assertEquals(context.get_host(), b'0.0.0.0')
        self.assertEquals(context.get_url(), test_uri + b'foo/bar')

    def test_custom_port_endpoint_https(self):
        test_uri = 'https://0.0.0.0:12345/'
        endpoint = AWSServiceEndpoint(uri=test_uri)
        self.assertEquals(endpoint.port, 12345)
        self.assertEquals(endpoint.scheme, 'https')
        context = client.URLContext(service_endpoint=endpoint,
                bucket="foo",
                object_name="bar")
        self.assertEquals(context.get_host(), b'0.0.0.0')
        self.assertEquals(context.get_url(), test_uri + b'foo/bar')

class S3URLContextTestCase(TXAWSTestCase):
    """
    Tests for L{s3_url_context}.
    """
    def test_unicode_bucket(self):
        """
        If a unicode bucket is given, the resulting url is nevertheless
        bytes.
        """
        test_uri = b"https://0.0.0.0:12345/"
        endpoint = AWSServiceEndpoint(uri=test_uri)
        bucket = u"\N{SNOWMAN}"
        context = client.s3_url_context(endpoint, bucket)
        url = context.get_url()
        self.assertIsInstance(url, bytes)
        self.assertEqual(
            test_uri + quote(bucket.encode("utf-8"), safe=b"") + b"/",
            url,
        )

    def test_unicode_object_name(self):
        """
        If a unicode bucket is given, the resulting url is nevertheless
        bytes.
        """
        test_uri = b"https://0.0.0.0:12345/"
        endpoint = AWSServiceEndpoint(uri=test_uri)
        bucket = b"mybucket"
        object_name = u"\N{SNOWMAN}"
        context = client.s3_url_context(endpoint, bucket, object_name)
        url = context.get_url()
        self.assertIsInstance(url, bytes)
        self.assertEqual(
            test_uri + (bucket + b"/" + quote(object_name.encode("utf-8"), safe=b"")),
            url,
        )

def mock_query_factory(response_body):
    class Response(object):
        responseHeaders = Headers()

    class MockQuery(object):
        def __init__(self, credentials, details):
            self.__class__.credentials = credentials
            self.__class__.details = details

        def submit(self, agent, receiver_factory, utcnow):
            return succeed((Response(), response_body))
    return MockQuery


class S3ClientTestCase(TXAWSTestCase):

    def setUp(self):
        TXAWSTestCase.setUp(self)
        self.endpoint = AWSServiceEndpoint()

    def test_list_buckets(self):
        query_factory = mock_query_factory(payload.sample_list_buckets_result)

        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

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
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.list_buckets()
        d.addCallback(check_query_args)
        d.addCallback(check_list_buckets)
        return d

    def test_create_bucket(self):
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"PUT",
                    url_context=client.s3_url_context(self.endpoint, "mybucket"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )

            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.create_bucket("mybucket")
        d.addCallback(check_query_args)
        return d

    def test_get_bucket(self):
        query_factory = mock_query_factory(payload.sample_get_bucket_result)

        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

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
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_pagination(self):
        """
        L{S3Client.get_bucket} accepts C{marker} and C{max_keys} arguments
        to control pagination of results.
        """
        query_factory = mock_query_factory(payload.sample_get_bucket_result)
        def check_query_args(passthrough):
            self.assertEqual(
                b"http:///mybucket/?marker=abcdef&max-keys=42",
                query_factory.details.url_context.get_encoded_url(),
            )
            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket("mybucket", marker="abcdef", max_keys=42)
        d.addCallback(check_query_args)
        return d

    def test_get_bucket_location(self):
        """
        L{S3Client.get_bucket_location} creates a L{Query} to get a bucket's
        location.  It parses the returned C{LocationConstraint} XML document
        and returns a C{Deferred} that requests the bucket's location
        constraint.
        """
        query_factory = mock_query_factory(payload.sample_get_bucket_location_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?location"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_results(location_constraint):
            self.assertEquals(location_constraint, "EU")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_location("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_lifecycle_multiple_rules(self):
        """
        L{S3Client.get_bucket_lifecycle} creates a L{Query} to get a bucket's
        lifecycle.  It parses the returned C{LifecycleConfiguration} XML
        document and returns a C{Deferred} that requests the bucket's lifecycle
        configuration with multiple rules.
        """
        query_factory = mock_query_factory(payload.sample_s3_get_bucket_lifecycle_multiple_rules_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?lifecycle"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_results(lifecycle_config):
            self.assertTrue(len(lifecycle_config.rules) == 2)
            rule = lifecycle_config.rules[1]
            self.assertEquals(rule.id, 'another-id')
            self.assertEquals(rule.prefix, 'another-logs')
            self.assertEquals(rule.status, 'Disabled')
            self.assertEquals(rule.expiration, 37)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_lifecycle("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_lifecycle(self):
        """
        L{S3Client.get_bucket_lifecycle} creates a L{Query} to get a bucket's
        lifecycle.  It parses the returned C{LifecycleConfiguration} XML
        document and returns a C{Deferred} that requests the bucket's lifecycle
        configuration.
        """
        query_factory = mock_query_factory(payload.sample_s3_get_bucket_lifecycle_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?lifecycle"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_results(lifecycle_config):
            rule = lifecycle_config.rules[0]
            self.assertEquals(rule.id, '30-day-log-deletion-rule')
            self.assertEquals(rule.prefix, 'logs')
            self.assertEquals(rule.status, 'Enabled')
            self.assertEquals(rule.expiration, 30)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_lifecycle("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_website_config(self):
        """
        L{S3Client.get_bucket_website_config} creates a L{Query} to get a
        bucket's website configurtion.  It parses the returned
        C{WebsiteConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's website configuration.
        """
        query_factory = mock_query_factory(payload.sample_s3_get_bucket_website_no_error_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?website"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_results(website_config):
            self.assertEquals(website_config.index_suffix, "index.html")
            self.assertEquals(website_config.error_key, None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_website_config("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_website_config_with_error_doc(self):
        """
        L{S3Client.get_bucket_website_config} creates a L{Query} to get a
        bucket's website configurtion.  It parses the returned
        C{WebsiteConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's website configuration with the error document.
        """
        query_factory = mock_query_factory(payload.sample_s3_get_bucket_website_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?website"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_results(website_config):
            self.assertEquals(website_config.index_suffix, "index.html")
            self.assertEquals(website_config.error_key, "404.html")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_website_config("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_notification_config(self):
        """
        L{S3Client.get_bucket_notification_config} creates a L{Query} to get a
        bucket's notification configuration.  It parses the returned
        C{NotificationConfiguration} XML document and returns a C{Deferred}
        that requests the bucket's notification configuration.
        """
        query_factory = mock_query_factory(payload.sample_s3_get_bucket_notification_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?notification"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_results(notification_config):
            self.assertEquals(notification_config.topic, None)
            self.assertEquals(notification_config.event, None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_notification_config("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_notification_config_with_topic(self):
        """
        L{S3Client.get_bucket_notification_config} creates a L{Query} to get a
        bucket's notification configuration.  It parses the returned
        C{NotificationConfiguration} XML document and returns a C{Deferred}
        that requests the bucket's notification configuration with a topic.
        """
        query_factory = mock_query_factory(payload.sample_s3_get_bucket_notification_with_topic_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?notification"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough


        def check_results(notification_config):
            self.assertEquals(notification_config.topic,
                              "arn:aws:sns:us-east-1:123456789012:myTopic")
            self.assertEquals(notification_config.event,
                              "s3:ReducedRedundancyLostObject")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_notification_config("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_versioning_config(self):
        """
        L{S3Client.get_bucket_versioning_configuration} creates a L{Query} to
        get a bucket's versioning status.  It parses the returned
        C{VersioningConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's versioning configuration.
        """
        query_factory = mock_query_factory(payload.sample_s3_get_bucket_versioning_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?versioning"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_results(versioning_config):
            self.assertEquals(versioning_config.status, None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_versioning_config("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_versioning_config_enabled(self):
        """
        L{S3Client.get_bucket_versioning_config} creates a L{Query} to get a
        bucket's versioning configuration.  It parses the returned
        C{VersioningConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's versioning configuration that has a enabled
        C{Status}.
        """
        query_factory = mock_query_factory(payload.sample_s3_get_bucket_versioning_enabled_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?versioning"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_results(versioning_config):
            self.assertEquals(versioning_config.status, 'Enabled')

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_versioning_config("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_get_bucket_versioning_config_mfa_disabled(self):
        """
        L{S3Client.get_bucket_versioning_config} creates a L{Query} to get a
        bucket's versioning configuration.  It parses the returned
        C{VersioningConfiguration} XML document and returns a C{Deferred} that
        requests the bucket's versioning configuration that has a disabled
        C{MfaDelete}.
        """
        query_factory = mock_query_factory(payload.sample_s3_get_bucket_versioning_mfa_disabled_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?versioning"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_results(versioning_config):
            self.assertEquals(versioning_config.mfa_delete, 'Disabled')

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_versioning_config("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_results)
        return d

    def test_delete_bucket(self):
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"DELETE",
                    url_context=client.s3_url_context(self.endpoint, "mybucket"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.delete_bucket("mybucket")
        d.addCallback(check_query_args)
        return d

    def test_put_bucket_acl(self):
        query_factory = mock_query_factory(payload.sample_access_control_policy_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"PUT",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?acl"),
                    content_sha256=sha256(
                        payload.sample_access_control_policy_result
                    ).hexdigest().decode("ascii"),
                ),
                assoc(query_factory.details, body_producer=None),
            )
            return passthrough

        def check_result(result):
            self.assertIsInstance(result, AccessControlPolicy)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        policy = AccessControlPolicy.from_xml(
            payload.sample_access_control_policy_result)
        d = s3.put_bucket_acl("mybucket", policy)
        d.addCallback(check_query_args)
        d.addCallback(check_result)
        return d

    def test_get_bucket_acl(self):
        query_factory = mock_query_factory(payload.sample_access_control_policy_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?acl"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_result(result):
            self.assert_(isinstance(result, AccessControlPolicy))

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_bucket_acl("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_result)
        return d

    def test_put_request_payment(self):
        """
        L{S3Client.put_request_payment} creates a L{Query} to set payment
        information.  An C{RequestPaymentConfiguration} XML document is built
        and sent to the endpoint and a C{Deferred} is returned that fires with
        the results of the request.
        """
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            xml = ("<RequestPaymentConfiguration "
                   'xmlns="http://s3.amazonaws.com/doc/2006-03-01/">\n'
                   "  <Payer>Requester</Payer>\n"
                   "</RequestPaymentConfiguration>")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"PUT",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?requestPayment"),
                    content_sha256=sha256(xml).hexdigest().decode("ascii"),
                ),
                assoc(query_factory.details, body_producer=None),
            )
            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.put_request_payment("mybucket", "Requester")
        d.addCallback(check_query_args)
        return d

    def test_get_request_payment(self):
        """
        L{S3Client.get_request_payment} creates a L{Query} to get payment
        information.  It parses the returned C{RequestPaymentConfiguration}
        XML document and returns a C{Deferred} that fires with the payer's
        name.
        """
        query_factory = mock_query_factory(payload.sample_request_payment)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "?requestPayment"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_request_payment(result):
            self.assertEquals(result, "Requester")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_request_payment("mybucket")
        d.addCallback(check_query_args)
        d.addCallback(check_request_payment)
        return d

    def test_put_object(self):
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"PUT",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "objectname"),
                    headers=Headers({u"content-type": [u"text/plain"]}),
                    metadata={"key": "some meta data"},
                    amz_headers={
                        "acl": "public-read",
                    },
                    content_sha256=sha256(b"some data").hexdigest().decode("ascii"),
                ),
                assoc(query_factory.details, body_producer=None),
            )
            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.put_object(
            "mybucket", "objectname", "some data",
            content_type="text/plain",
            metadata={"key": "some meta data"},
            amz_headers={"acl": "public-read"},
        )
        d.addCallback(check_query_args)
        return d

    def test_put_object_with_custom_body_producer(self):
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"PUT",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "objectname"),
                    headers=Headers({u"content-type": [u"text/plain"]}),
                    metadata={"key": "some meta data"},
                    amz_headers={
                        "acl": "public-read",
                    },
                    body_producer=string_producer,
                ),
                query_factory.details,
            )

        string_producer = StringBodyProducer("some data")
        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.put_object(
            "mybucket", "objectname",
            content_type="text/plain",
            metadata={"key": "some meta data"},
            amz_headers={"acl": "public-read"},
            body_producer=string_producer,
        )
        d.addCallback(check_query_args)
        return d

    def test_copy_object(self):
        """
        L{S3Client.copy_object} creates a L{Query} to copy an object from one
        bucket to another.
        """
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"PUT",
                    url_context=client.s3_url_context(self.endpoint, "newbucket", "newobjectname"),
                    metadata={"key": "some meta data"},
                    amz_headers={
                        "copy-source": "/mybucket/objectname",
                    },
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.copy_object(
            "mybucket", "objectname", "newbucket",
            "newobjectname",
            metadata={"key": "some meta data"},
        )
        d.addCallback(check_query_args)
        return d

    def test_get_object(self):
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "objectname"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_object("mybucket", "objectname")
        d.addCallback(check_query_args)
        return d

    def test_head_object(self):
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"HEAD",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "objectname"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.head_object("mybucket", "objectname")
        d.addCallback(check_query_args)
        return d

    def test_delete_object(self):
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"DELETE",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "objectname"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.delete_object("mybucket", "objectname")
        d.addCallback(check_query_args)
        return d

    def test_put_object_acl(self):
        query_factory = mock_query_factory(payload.sample_access_control_policy_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"PUT",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "myobject?acl"),
                    content_sha256=sha256(
                        payload.sample_access_control_policy_result
                    ).hexdigest().decode("ascii"),
                ),
                assoc(query_factory.details, body_producer=None),
            )
            return passthrough

        def check_result(result):
            self.assertIsInstance(result, AccessControlPolicy)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        policy = AccessControlPolicy.from_xml(
            payload.sample_access_control_policy_result)
        d = s3.put_object_acl("mybucket", "myobject", policy)
        d.addCallback(check_query_args)
        d.addCallback(check_result)
        return d

    def test_get_object_acl(self):
        query_factory = mock_query_factory(payload.sample_access_control_policy_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"GET",
                    url_context=client.s3_url_context(self.endpoint, "mybucket", "myobject?acl"),
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_result(result):
            self.assertIsInstance(result, AccessControlPolicy)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.get_object_acl("mybucket", "myobject")
        d.addCallback(check_query_args)
        d.addCallback(check_result)
        return d

    def test_init_multipart_upload(self):
        query_factory = mock_query_factory(payload.sample_s3_init_multipart_upload_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"POST",
                    url_context=client.s3_url_context(
                        self.endpoint, "example-bucket", "example-object?uploads",
                    ),
                    amz_headers={
                        "acl": "public",
                    },
                    content_sha256=EMPTY_CONTENT_SHA256,
                ),
                query_factory.details,
            )
            return passthrough

        def check_result(result):
            self.assert_(isinstance(result, MultipartInitiationResponse))
            self.assertEqual(result.bucket, "example-bucket")
            self.assertEqual(result.object_name, "example-object")
            self.assertEqual(result.upload_id, "deadbeef")

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.init_multipart_upload("example-bucket", "example-object",
            amz_headers={"acl": "public"})
        d.addCallback(check_query_args)
        d.addCallback(check_result)
        return d

    def test_upload_part(self):
        query_factory = mock_query_factory(None)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"PUT",
                    url_context=client.s3_url_context(
                        self.endpoint, "example-bucket", "example-object?partNumber=3&uploadId=testid"
                    ),
                    content_sha256=sha256(b"some data").hexdigest().decode("ascii"),
                ),
                assoc(query_factory.details, body_producer=None),
            )
            return passthrough

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.upload_part(
            "example-bucket", "example-object", "testid", 3, "some data",
        )
        d.addCallback(check_query_args)
        return d

    def test_complete_multipart_upload(self):
        query_factory = mock_query_factory(payload.sample_s3_complete_multipart_upload_result)
        def check_query_args(passthrough):
            self.assertEqual(query_factory.credentials.access_key, "foo")
            self.assertEqual(query_factory.credentials.secret_key, "bar")
            xml = (
                "<CompleteMultipartUpload>\n"
                "<Part>\n<PartNumber>1</PartNumber>\n<ETag>a</ETag>\n"
                "</Part>\n<Part>\n<PartNumber>2</PartNumber>\n"
                "<ETag>b</ETag>\n</Part>\n</CompleteMultipartUpload>"
            )
            self.assertEqual(
                RequestDetails(
                    service=b"s3",
                    region=REGION_US_EAST_1,
                    method=b"POST",
                    url_context=client.s3_url_context(
                        self.endpoint, "example-bucket", "example-object?uploadId=testid"
                    ),
                    content_sha256=sha256(xml).hexdigest().decode("ascii"),
                ),
                assoc(query_factory.details, body_producer=None),
            )
            return passthrough

        def check_result(result):
            self.assert_(isinstance(result, MultipartCompletionResponse))
            self.assertEqual(result.bucket, "example-bucket")
            self.assertEqual(result.object_name, "example-object")
            self.assertEqual(result.location,
                "http://example-bucket.s3.amazonaws.com/example-object")
            self.assertEqual(result.etag,
                '"3858f62230ac3c915f300c664312c11f-9"')

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=query_factory)
        d = s3.complete_multipart_upload(
            "example-bucket",
            "example-object",
            "testid", [(1, "a"), (2, "b")]
        )
        d.addCallback(check_query_args)
        d.addCallback(check_result)
        return d



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



def get_live_client(case):
    return get_live_service(case).get_s3_client()


class LiveS3TestCase(s3_integration_tests(get_live_client)):
    """
    Tests for the real S3 implementation against AWS itself.
    """
