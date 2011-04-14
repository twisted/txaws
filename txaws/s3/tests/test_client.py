from twisted.internet.defer import succeed

from txaws.credentials import AWSCredentials
try:
    from txaws.s3 import client
except ImportError:
    s3clientSkip = ("S3Client couldn't be imported (perhaps because epsilon, "
                    "on which it depends, isn't present)")
else:
    s3clientSkip = None
from txaws.s3.acls import AccessControlPolicy
from txaws.s3.model import RequestPayment
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
        self.assertEquals(url_context.get_path(), "/mystuff")

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

URLContextTestCase.skip = s3clientSkip


class S3ClientTestCase(TXAWSTestCase):

    def setUp(self):
        TXAWSTestCase.setUp(self)
        self.creds = AWSCredentials(
            access_key="accessKey", secret_key="secretKey")
        self.endpoint = AWSServiceEndpoint()

    def test_list_buckets(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint):
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

            def __init__(query, action, creds, endpoint, bucket=None):
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

            def __init__(query, action, creds, endpoint, bucket=None):
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

    def test_get_bucket_location(self):
        """
        L{S3Client.get_bucket_location} creates a L{Query} to get a bucket's
        location.  It parses the returned C{LocationConstraint} XML document
        and returns a C{Deferred} that fires with the bucket's region.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None):
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

    def test_delete_bucket(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None):
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
                         object_name=None, data=""):
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
                         object_name=None, data=""):
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
                metadata=None):
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
                metadata=None):
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
                metadata=None, amz_headers=None):
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

    def test_copy_object(self):
        """
        L{S3Client.copy_object} creates a L{Query} to copy an object from one
        bucket to another.
        """

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                object_name=None, data=None, content_type=None,
                metadata=None, amz_headers=None):
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
                metadata=None, amz_headers=None):
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
                metadata=None):
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
                metadata=None):
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

    def test_get_object_acl(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None,
                         object_name=None, data=""):
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

S3ClientTestCase.skip = s3clientSkip


class QueryTestCase(TXAWSTestCase):

    creds = AWSCredentials(access_key="fookeyid", secret_key="barsecretkey")
    endpoint = AWSServiceEndpoint("https://choopy.s3.amazonaws.com/")

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
        headers = query.get_headers()
        self.assertEquals(headers.get("Content-Type"), "image/jpeg")
        self.assertEquals(headers.get("Content-Length"), 0)
        self.assertEquals(
            headers.get("Content-MD5"), "1B2M2Y8AsgTpgAmY7PhCfg==")
        self.assertTrue(len(headers.get("Date")) > 25)
        self.assertTrue(
            headers.get("Authorization").startswith("AWS fookeyid:"))
        self.assertTrue(len(headers.get("Authorization")) > 40)

    def test_get_headers_with_data(self):
        query = client.Query(
            action="GET", creds=self.creds, bucket="mystuff",
            object_name="/images/thing.jpg", data="BINARY IMAGE DATA")
        headers = query.get_headers()
        self.assertEquals(headers.get("Content-Type"), "image/jpeg")
        self.assertEquals(headers.get("Content-Length"), 17)
        self.assertTrue(len(headers.get("Date")) > 25)
        self.assertTrue(
            headers.get("Authorization").startswith("AWS fookeyid:"))
        self.assertTrue(len(headers.get("Authorization")) > 40)

    def test_get_canonicalized_amz_headers(self):
        query = client.Query(
            action="SomeThing", metadata={"a": 1, "b": 2, "c": 3})
        headers = query.get_headers()
        self.assertEquals(
            sorted(headers.keys()),
            ["Content-Length", "Content-MD5", "Date", "x-amz-meta-a",
             "x-amz-meta-b", "x-amz-meta-c"])
        amz_headers = query.get_canonicalized_amz_headers(headers)
        self.assertEquals(
            amz_headers,
            "x-amz-meta-a:1\nx-amz-meta-b:2\nx-amz-meta-c:3\n")

    def test_get_canonicalized_resource(self):
        query = client.Query(action="PUT", bucket="images")
        result = query.get_canonicalized_resource()
        self.assertEquals(result, "/images")

    def test_get_canonicalized_resource_with_object_name(self):
        query = client.Query(
            action="PUT", bucket="images", object_name="advicedog.jpg")
        result = query.get_canonicalized_resource()
        self.assertEquals(result, "/images/advicedog.jpg")

    def test_sign(self):
        query = client.Query(action="PUT", creds=self.creds)
        signed = query.sign({})
        self.assertEquals(signed, "H6UJCNHizzXZCGPl7wM6nL6tQdo=")

    def test_object_query(self):
        """
        Test that a request addressing an object is created correctly.
        """
        DATA = "objectData"
        DIGEST = "zhdB6gwvocWv/ourYUWMxA=="

        request = client.Query(
            action="PUT", bucket="somebucket", object_name="object/name/here",
            data=DATA, content_type="text/plain", metadata={"foo": "bar"},
            amz_headers={"acl": "public-read"}, creds=self.creds,
            endpoint=self.endpoint)
        request.sign = lambda headers: "TESTINGSIG="
        self.assertEqual(request.action, "PUT")
        headers = request.get_headers()
        self.assertNotEqual(headers.pop("Date"), "")
        self.assertEqual(headers, {"Authorization": "AWS fookeyid:TESTINGSIG=",
                                   "Content-Type": "text/plain",
                                   "Content-Length": len(DATA),
                                   "Content-MD5": DIGEST,
                                   "x-amz-meta-foo": "bar",
                                   "x-amz-acl": "public-read"})
        self.assertEqual(request.data, "objectData")

    def test_bucket_query(self):
        """
        Test that a request addressing a bucket is created correctly.
        """
        DIGEST = "1B2M2Y8AsgTpgAmY7PhCfg=="

        query = client.Query(
            action="GET", bucket="somebucket", creds=self.creds,
            endpoint=self.endpoint)
        query.sign = lambda headers: "TESTINGSIG="
        self.assertEqual(query.action, "GET")
        headers = query.get_headers()
        self.assertNotEqual(headers.pop("Date"), "")
        self.assertEqual(
            headers, {
            "Authorization": "AWS fookeyid:TESTINGSIG=",
            "Content-Length": 0,
            "Content-MD5": DIGEST})
        self.assertEqual(query.data, "")

    def test_submit(self):
        """
        Submitting the request should invoke getPage correctly.
        """
        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket):
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
        query.sign = lambda headers: "TESTINGSIG="
        query.date = "Wed, 28 Mar 2007 01:29:59 +0000"

        headers = query.get_headers()
        self.assertEqual(
            headers["Authorization"],
            "AWS fookeyid:TESTINGSIG=")

QueryTestCase.skip = s3clientSkip


class MiscellaneousTests(TXAWSTestCase):

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
