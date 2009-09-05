from datetime import datetime

from epsilon.extime import Time

from twisted.internet.defer import succeed

from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint
from txaws.storage.client import S3, S3Request
from txaws.testing.base import TXAWSTestCase
from txaws.util import calculate_md5



class StubbedS3Request(S3Request):

    def get_page(self, url, method, postdata, headers):
        self.getPageArgs = (url, method, postdata, headers)
        return succeed("")


class RequestTestCase(TXAWSTestCase):

    creds = AWSCredentials(access_key="fookeyid", secret_key="barsecretkey")
    endpoint = AWSServiceEndpoint("https://s3.amazonaws.com/")

    def test_get_uri_with_endpoint(self):
        endpoint = AWSServiceEndpoint("http://localhost/")
        request = S3Request("PUT", endpoint=endpoint)
        self.assertEquals(request.endpoint.get_uri(), "http://localhost/")
        self.assertEquals(request.get_uri(), "http://localhost/")

    def test_get_uri_with_endpoint_bucket_and_object(self):
        endpoint = AWSServiceEndpoint("http://localhost/")
        request = S3Request("PUT", bucket="mybucket", object_name="myobject",
                            endpoint=endpoint)
        self.assertEquals(
            request.get_uri(),
            "http://localhost/mybucket/myobject")

    def test_get_uri_with_no_endpoint(self):
        request = S3Request("PUT")
        self.assertEquals(request.endpoint, None)
        self.assertEquals(request.get_uri(), "http:///")

    def test_get_path_with_bucket_and_object(self):
        request = S3Request("PUT", bucket="mybucket", object_name="myobject")
        self.assertEquals(request.get_path(), "/mybucket/myobject")

    def test_get_path_with_no_bucket_or_object(self):
        request = S3Request("PUT")
        self.assertEquals(request.get_path(), "/")

    def test_objectRequest(self):
        """
        Test that a request addressing an object is created correctly.
        """
        DATA = "objectData"
        DIGEST = "zhdB6gwvocWv/ourYUWMxA=="

        request = S3Request("PUT", "somebucket", "object/name/here", DATA,
                            content_type="text/plain", metadata={"foo": "bar"},
                            creds=self.creds, endpoint=self.endpoint)
        request.get_signature = lambda headers: "TESTINGSIG="
        self.assertEqual(request.verb, "PUT")
        self.assertEqual(
            request.get_uri(),
            "https://s3.amazonaws.com/somebucket/object/name/here")
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

    def test_bucketRequest(self):
        """
        Test that a request addressing a bucket is created correctly.
        """
        DIGEST = "1B2M2Y8AsgTpgAmY7PhCfg=="

        request = S3Request("GET", "somebucket", creds=self.creds,
                            endpoint=self.endpoint)
        request.get_signature = lambda headers: "TESTINGSIG="
        self.assertEqual(request.verb, "GET")
        self.assertEqual(
            request.get_uri(), "https://s3.amazonaws.com/somebucket")
        headers = request.get_headers()
        self.assertNotEqual(headers.pop("Date"), "")
        self.assertEqual(
            headers, {
            "Authorization": "AWS fookeyid:TESTINGSIG=",
            "Content-Length": 0,
            "Content-MD5": DIGEST})
        self.assertEqual(request.data, "")

    def test_submit(self):
        """
        Submitting the request should invoke getPage correctly.
        """
        request = StubbedS3Request("GET", "somebucket", creds=self.creds,
                                   endpoint=self.endpoint)

        def _postCheck(result):
            self.assertEqual(result, "")

            url, method, postdata, headers = request.getPageArgs
            self.assertEqual(url, request.get_uri())
            self.assertEqual(method, request.verb)
            self.assertEqual(postdata, request.data)
            self.assertEqual(headers, request.get_headers())

        return request.submit().addCallback(_postCheck)

    def test_authenticationTestCases(self):
        request = S3Request("GET", creds=self.creds, endpoint=self.endpoint)
        request.get_signature = lambda headers: "TESTINGSIG="
        request.date = "Wed, 28 Mar 2007 01:29:59 +0000"

        headers = request.get_headers()
        self.assertEqual(
            headers["Authorization"], 
            "AWS fookeyid:TESTINGSIG=")


class InertRequest(S3Request):
    """
    Inert version of S3Request.

    The submission action is stubbed out to return the provided response.
    """
    submitted = False

    def __init__(self, *a, **kw):
        self.response = kw.pop("response")
        super(InertRequest, self).__init__(*a, **kw)

    def submit(self):
        """
        Return the canned result instead of performing a network operation.
        """
        self.submitted = True
        return succeed(self.response)


class TestableS3(S3):
    """
    Testable version of S3.

    This subclass stubs request_factory to use InertRequest, making it easy to
    assert things about the requests that are created in response to various
    operations.
    """
    response = None

    def request_factory(self, *a, **kw):
        req = InertRequest(response=self.response, *a, **kw)
        self._lastRequest = req
        return req


samples = {
    "ListAllMyBucketsResult":
    """<?xml version="1.0" encoding="UTF-8"?>
<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Owner>
    <ID>bcaf1ffd86f41caff1a493dc2ad8c2c281e37522a640e161ca5fb16fd081034f</ID>
    <DisplayName>webfile</DisplayName>
  </Owner>
  <Buckets>
    <Bucket>
      <Name>quotes</Name>
      <CreationDate>2006-02-03T16:45:09.000Z</CreationDate>
    </Bucket>
    <Bucket>
      <Name>samples</Name>
      <CreationDate>2006-02-03T16:41:58.000Z</CreationDate>
    </Bucket>
  </Buckets>
</ListAllMyBucketsResult>""",
    }


class WrapperTests(TXAWSTestCase):

    def setUp(self):
        TXAWSTestCase.setUp(self)
        self.creds = AWSCredentials(
            access_key="accessKey", secret_key="secretKey")
        self.endpoint = AWSServiceEndpoint()
        self.s3 = TestableS3(creds=self.creds, endpoint=self.endpoint)

    def test_make_request(self):
        """
        Test that make_request passes in the credentials object.
        """
        marker = object()

        def _cb(*a, **kw):
            self.assertEqual(kw["creds"], self.creds)
            self.assertEqual(kw["endpoint"], self.endpoint)
            return marker

        self.s3.request_factory = _cb
        self.assertIdentical(self.s3.make_request("GET"), marker)

    def test_list_buckets(self):
        self.s3.response = samples["ListAllMyBucketsResult"]
        d = self.s3.list_buckets()

        req = self.s3._lastRequest
        self.assertTrue(req.submitted)
        self.assertEqual(req.verb, "GET")
        self.assertEqual(req.bucket, None)
        self.assertEqual(req.object_name, None)

        def _check_result(buckets):
            self.assertEqual(
                list(buckets),
                [{"name": u"quotes",
                  "created": Time.fromDatetime(
                    datetime(2006, 2, 3, 16, 45, 9))},
                 {"name": u"samples",
                  "created": Time.fromDatetime(
                    datetime(2006, 2, 3, 16, 41, 58))}])
        return d.addCallback(_check_result)

    def test_create_bucket(self):
        self.s3.create_bucket("foo")
        req = self.s3._lastRequest
        self.assertTrue(req.submitted)
        self.assertEqual(req.verb, "PUT")
        self.assertEqual(req.bucket, "foo")
        self.assertEqual(req.object_name, None)

    def test_delete_bucket(self):
        self.s3.delete_bucket("foo")
        req = self.s3._lastRequest
        self.assertTrue(req.submitted)
        self.assertEqual(req.verb, "DELETE")
        self.assertEqual(req.bucket, "foo")
        self.assertEqual(req.object_name, None)

    def test_put_object(self):
        self.s3.put_object(
            "foobucket", "foo", "data", "text/plain", {"foo": "bar"})
        req = self.s3._lastRequest
        self.assertTrue(req.submitted)
        self.assertEqual(req.verb, "PUT")
        self.assertEqual(req.bucket, "foobucket")
        self.assertEqual(req.object_name, "foo")
        self.assertEqual(req.data, "data")
        self.assertEqual(req.content_type, "text/plain")
        self.assertEqual(req.metadata, {"foo": "bar"})

    def test_get_object(self):
        self.s3.get_object("foobucket", "foo")
        req = self.s3._lastRequest
        self.assertTrue(req.submitted)
        self.assertEqual(req.verb, "GET")
        self.assertEqual(req.bucket, "foobucket")
        self.assertEqual(req.object_name, "foo")

    def test_head_object(self):
        self.s3.head_object("foobucket", "foo")
        req = self.s3._lastRequest
        self.assertTrue(req.submitted)
        self.assertEqual(req.verb, "HEAD")
        self.assertEqual(req.bucket, "foobucket")
        self.assertEqual(req.object_name, "foo")

    def test_delete_object(self):
        self.s3.delete_object("foobucket", "foo")
        req = self.s3._lastRequest
        self.assertTrue(req.submitted)
        self.assertEqual(req.verb, "DELETE")
        self.assertEqual(req.bucket, "foobucket")
        self.assertEqual(req.object_name, "foo")


class MiscellaneousTests(TXAWSTestCase):

    def test_contentMD5(self):
        self.assertEqual(calculate_md5("somedata"), "rvr3UC1SmUw7AZV2NqPN0g==")
