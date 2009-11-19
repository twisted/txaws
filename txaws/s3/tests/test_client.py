from datetime import datetime

from epsilon.extime import Time

from twisted.internet.defer import succeed

from txaws.credentials import AWSCredentials
from txaws.s3 import client
from txaws.service import AWSServiceEndpoint
from txaws.testing import payload
from txaws.testing.base import TXAWSTestCase
from txaws.util import calculate_md5


class S3ClientTestCase(TXAWSTestCase):

    def setUp(self):
        TXAWSTestCase.setUp(self)
        self.creds = AWSCredentials(
            access_key="accessKey", secret_key="secretKey")
        self.endpoint = AWSServiceEndpoint()

    # we're getting rid of make_request
    def XXX_test_make_request(self):
        """
        Test that make_request passes in the credentials object.
        """
        """
        marker = object()

        def _cb(*a, **kw):
            self.assertEqual(kw["creds"], self.creds)
            self.assertEqual(kw["endpoint"], self.endpoint)
            return marker

        self.s3.request_factory = _cb
        self.assertIdentical(self.s3.make_request("GET"), marker)
        """
        class StubQuery(object):

            def __init__(stub, action, creds, endpoint):
                self.assertEquals(action, "")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")

            def submit(self):
                return succeed()

        creds = AWSCredentials("foo", "bar")
        ec2 = client.S3Client(creds, query_factory=StubQuery)
        d = ec2.describe_availability_zones(["us-east-1a"])
        d.addCallback(check_parsed_availability_zone)
        return d

    def test_list_buckets(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint):
                super(StubQuery, query).__init__(
                    action=action, creds=creds)
                self.assertEquals(action, "GET")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(query.get_path(), "/")
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
                self.assertEqual(
                    query.get_uri(), "https://mybucket.s3.amazonaws.com/")
                self.assertEqual(query.get_path(), "/")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, None)
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.create_bucket("mybucket")

    def test_delete_bucket(self):

        class StubQuery(client.Query):

            def __init__(query, action, creds, endpoint, bucket=None):
                super(StubQuery, query).__init__(
                    action=action, creds=creds, bucket=bucket)
                self.assertEquals(action, "DELETE")
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(
                    query.get_uri(), "https://mybucket.s3.amazonaws.com/")
                self.assertEqual(query.get_path(), "/")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, None)
                self.assertEqual(query.data, "")
                self.assertEqual(query.metadata, {})

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.delete_bucket("mybucket")

    def test_put_object(self):

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
                self.assertEqual(
                    query.get_uri(),
                    "https://mybucket.s3.amazonaws.com/objectname")
                self.assertEqual(query.get_path(), "/objectname")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "objectname")
                self.assertEqual(query.data, "some data")
                self.assertEqual(query.content_type, "text/plain")
                self.assertEqual(query.metadata, {"key": "some meta data"})

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.put_object(
            "mybucket", "objectname", "some data", content_type="text/plain",
            metadata={"key": "some meta data"})

    def test_get_object(self):

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
                self.assertEqual(
                    query.get_uri(),
                    "https://mybucket.s3.amazonaws.com/objectname")
                self.assertEqual(query.get_path(), "/objectname")
                self.assertEqual(query.bucket, "mybucket")
                self.assertEqual(query.object_name, "objectname")

            def submit(query):
                return succeed(None)

        creds = AWSCredentials("foo", "bar")
        s3 = client.S3Client(creds, query_factory=StubQuery)
        return s3.get_object("mybucket", "objectname")

    def test_head_object(self):
        self.s3.head_object("foobucket", "foo")
        req = self.s3._lastRequest
        self.assertTrue(req.submitted)
        self.assertEqual(req.action, "HEAD")
        self.assertEqual(req.bucket, "foobucket")
        self.assertEqual(req.object_name, "foo")

    def test_delete_object(self):
        self.s3.delete_object("foobucket", "foo")
        req = self.s3._lastRequest
        self.assertTrue(req.submitted)
        self.assertEqual(req.action, "DELETE")
        self.assertEqual(req.bucket, "foobucket")
        self.assertEqual(req.object_name, "foo")


class QueryTestCase(TXAWSTestCase):

    creds = AWSCredentials(access_key="fookeyid", secret_key="barsecretkey")
    endpoint = AWSServiceEndpoint("https://s3.amazonaws.com/")

    def test_get_host_with_no_bucket(self):
        query = client.Query(action="GET")
        self.assertEquals(query.get_host(), "s3.amazonaws.com")

    def test_get_host_with_bucket(self):
        query = client.Query(action="GET", bucket="mystuff")
        self.assertEquals(query.get_host(), "mystuff.s3.amazonaws.com")

    def test_get_path_with_no_bucket(self):
        query = client.Query(action="GET")
        self.assertEquals(query.get_path(), "/")

    def test_get_path_with_bucket(self):
        query = client.Query(action="GET", bucket="mystuff")
        self.assertEquals(query.get_path(), "/")

    def test_get_path_with_bucket_and_object(self):
        query = client.Query(
            action="GET", bucket="mystuff", object_name="/images/thing.jpg")
        self.assertEquals(query.get_host(), "mystuff.s3.amazonaws.com")
        self.assertEquals(query.get_path(), "/images/thing.jpg")

    def test_get_path_with_bucket_and_object_without_slash(self):
        query = client.Query(
            action="GET", bucket="mystuff", object_name="images/thing.jpg")
        self.assertEquals(query.get_host(), "mystuff.s3.amazonaws.com")
        self.assertEquals(query.get_path(), "/images/thing.jpg")

    def test_get_uri_with_no_endpoint(self):
        query = client.Query(action="GET")
        self.assertEquals(
            query.endpoint.get_uri(), "https://s3.amazonaws.com/")
        self.assertEquals(query.get_uri(), "https://s3.amazonaws.com/")

    def test_get_uri_with_endpoint(self):
        endpoint = AWSServiceEndpoint("http://localhost/")
        query = client.Query(action="PUT", endpoint=endpoint)
        self.assertEquals(query.endpoint.get_uri(), "http://localhost/")
        self.assertEquals(query.get_uri(), "http://localhost/")

    def test_get_uri_with_endpoint_bucket_and_object(self):
        endpoint = AWSServiceEndpoint("http://localhost/")
        query = client.Query(
            action="PUT", bucket="mydocs", object_name="notes.txt",
            endpoint=endpoint)
        self.assertEquals(
            query.get_uri(),
            "http://mydocs.localhost/notes.txt")

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

    def test_object_query(self):
        """
        Test that a request addressing an object is created correctly.
        """
        DATA = "objectData"
        DIGEST = "zhdB6gwvocWv/ourYUWMxA=="

        request = client.Query(
            action="PUT", bucket="somebucket", object_name="object/name/here",
            data=DATA, content_type="text/plain", metadata={"foo": "bar"},
            creds=self.creds, endpoint=self.endpoint)
        request.sign = lambda headers: "TESTINGSIG="
        self.assertEqual(request.action, "PUT")
        self.assertEqual(
            request.get_uri(),
            "https://somebucket.s3.amazonaws.com/object/name/here")
        headers = request.get_headers()
        self.assertNotEqual(headers.pop("Date"), "")
        self.assertEqual(
            headers, {
                "Authorization": "AWS fookeyid:TESTINGSIG=",
                "Content-Type": "text/plain",
                "Content-Length": len(DATA),
                "Content-MD5": DIGEST,
                "x-amz-meta-foo": "bar"})
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
        self.assertEqual(
            query.get_uri(), "https://somebucket.s3.amazonaws.com/")
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
                self.assertEqual(query.get_path(), "/")
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


class MiscellaneousTests(TXAWSTestCase):

    def test_content_md5(self):
        self.assertEqual(calculate_md5("somedata"), "rvr3UC1SmUw7AZV2NqPN0g==")
