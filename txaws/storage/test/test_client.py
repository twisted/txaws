from datetime import datetime

from epsilon.extime import Time

from twisted.trial.unittest import TestCase
from twisted.internet.defer import succeed

from aws.s3.client import S3, S3Request, calculateMD5, hmac_sha1

class StubbedS3Request(S3Request):
    def getPage(self, url, method, postdata, headers):
        self.getPageArgs = (url, method, postdata, headers)
        return succeed('')


class RequestTests(TestCase):
    accessKey = '0PN5J17HBGZHT7JJ3X82'
    secretKey = 'uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o'

    def test_objectRequest(self):
        """
        Test that a request addressing an object is created correctly.
        """
        DATA = 'objectData'
        DIGEST = 'zhdB6gwvocWv/ourYUWMxA=='

        request = S3Request('PUT', 'somebucket', 'object/name/here', DATA, contentType='text/plain', metadata={'foo': 'bar'})
        self.assertEqual(request.verb, 'PUT')
        self.assertEqual(request.getURI(), 'https://s3.amazonaws.com/somebucket/object/name/here')
        headers = request.getHeaders()
        self.assertNotEqual(headers.pop('Date'), '')
        self.assertEqual(headers,
                         {'Content-Type': 'text/plain',
                          'Content-Length': len(DATA),
                          'Content-MD5': DIGEST,
                          'x-amz-meta-foo': 'bar'})
        self.assertEqual(request.data, 'objectData')

    def test_bucketRequest(self):
        """
        Test that a request addressing a bucket is created correctly.
        """
        DIGEST = '1B2M2Y8AsgTpgAmY7PhCfg=='

        request = S3Request('GET', 'somebucket')
        self.assertEqual(request.verb, 'GET')
        self.assertEqual(request.getURI(), 'https://s3.amazonaws.com/somebucket')
        headers = request.getHeaders()
        self.assertNotEqual(headers.pop('Date'), '')
        self.assertEqual(headers,
                         {'Content-Length': 0,
                          'Content-MD5': DIGEST})
        self.assertEqual(request.data, '')

    def test_submit(self):
        """
        Submitting the request should invoke getPage correctly.
        """
        request = StubbedS3Request('GET', 'somebucket')

        def _postCheck(result):
            self.assertEqual(result, '')

            url, method, postdata, headers = request.getPageArgs
            self.assertEqual(url, request.getURI())
            self.assertEqual(method, request.verb)
            self.assertEqual(postdata, request.data)
            self.assertEqual(headers, request.getHeaders())

        return request.submit().addCallback(_postCheck)

    def test_invalidAuthenticatedRequest(self):
        """
        An authenticated request must be supplied both private and public keys.
        """
        self.assertRaises(ValueError, S3Request, 'GET', accessKey='foo')
        self.assertRaises(ValueError, S3Request, 'GET', secretKey='foo')

    def test_authenticationTestCases(self):
        req = S3Request('GET', accessKey=self.accessKey, secretKey=self.secretKey)
        req.date = 'Wed, 28 Mar 2007 01:29:59 +0000'

        headers = req.getHeaders()
        self.assertEqual(headers['Authorization'], 'AWS 0PN5J17HBGZHT7JJ3X82:jF7L3z/FTV47vagZzhKupJ9oNig=')


class InertRequest(S3Request):
    """
    Inert version of S3Request.

    The submission action is stubbed out to return the provided response.
    """
    def __init__(self, *a, **kw):
        self.response = kw.pop('response')
        super(InertRequest, self).__init__(*a, **kw)

    def submit(self):
        """
        Return the canned result instead of performing a network operation.
        """
        return succeed(self.response)


class TestableS3(S3):
    """
    Testable version of S3.

    This subclass stubs requestFactory to use InertRequest, making it easy to
    assert things about the requests that are created in response to various
    operations.
    """
    response = None

    def requestFactory(self, *a, **kw):
        req = InertRequest(response=self.response, *a, **kw)
        self._lastRequest = req
        return req


samples = {
    'ListAllMyBucketsResult':
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


class WrapperTests(TestCase):
    def setUp(self):
        self.s3 = TestableS3(accessKey='accessKey', secretKey='secretKey')

    def test_makeRequest(self):
        """
        Test that makeRequest passes in the service credentials.
        """
        marker = object()

        def _cb(*a, **kw):
            self.assertEqual(kw['accessKey'], 'accessKey')
            self.assertEqual(kw['secretKey'], 'secretKey')
            return marker

        self.s3.requestFactory = _cb
        self.assertIdentical(self.s3.makeRequest('GET'), marker)

    def test_listBuckets(self):
        self.s3.response = samples['ListAllMyBucketsResult']
        d = self.s3.listBuckets()

        req = self.s3._lastRequest
        self.assertEqual(req.verb, 'GET')
        self.assertEqual(req.bucket, None)
        self.assertEqual(req.objectName, None)

        def _checkResult(buckets):
            self.assertEqual(list(buckets),
                             [{'name': u'quotes',
                               'created': Time.fromDatetime(datetime(2006, 2, 3, 16, 45, 9))},
                              {'name': u'samples',
                               'created': Time.fromDatetime(datetime(2006, 2, 3, 16, 41, 58))}])
        return d.addCallback(_checkResult)

    def test_createBucket(self):
        self.s3.createBucket('foo')
        req = self.s3._lastRequest
        self.assertEqual(req.verb, 'PUT')
        self.assertEqual(req.bucket, 'foo')
        self.assertEqual(req.objectName, None)

    def test_deleteBucket(self):
        self.s3.deleteBucket('foo')
        req = self.s3._lastRequest
        self.assertEqual(req.verb, 'DELETE')
        self.assertEqual(req.bucket, 'foo')
        self.assertEqual(req.objectName, None)

    def test_putObject(self):
        self.s3.putObject('foobucket', 'foo', 'data', 'text/plain', {'foo': 'bar'})
        req = self.s3._lastRequest
        self.assertEqual(req.verb, 'PUT')
        self.assertEqual(req.bucket, 'foobucket')
        self.assertEqual(req.objectName, 'foo')
        self.assertEqual(req.data, 'data')
        self.assertEqual(req.contentType, 'text/plain')
        self.assertEqual(req.metadata, {'foo': 'bar'})

    def test_getObject(self):
        self.s3.getObject('foobucket', 'foo')
        req = self.s3._lastRequest
        self.assertEqual(req.verb, 'GET')
        self.assertEqual(req.bucket, 'foobucket')
        self.assertEqual(req.objectName, 'foo')

    def test_headObject(self):
        self.s3.headObject('foobucket', 'foo')
        req = self.s3._lastRequest
        self.assertEqual(req.verb, 'HEAD')
        self.assertEqual(req.bucket, 'foobucket')
        self.assertEqual(req.objectName, 'foo')

    def test_deleteObject(self):
        self.s3.deleteObject('foobucket', 'foo')
        req = self.s3._lastRequest
        self.assertEqual(req.verb, 'DELETE')
        self.assertEqual(req.bucket, 'foobucket')
        self.assertEqual(req.objectName, 'foo')


class MiscellaneousTests(TestCase):
    def test_contentMD5(self):
        self.assertEqual(calculateMD5('somedata'), 'rvr3UC1SmUw7AZV2NqPN0g==')

    def test_hmac_sha1(self):
        cases = [
            ('0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b'.decode('hex'), 'Hi There', 'thcxhlUFcmTii8C2+zeMjvFGvgA='),
            ('Jefe', 'what do ya want for nothing?', '7/zfauXrL6LSdBbV8YTfnCWafHk='),
            ('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'.decode('hex'), '\xdd' * 50, 'El1zQrmsEc2Ro5r0iqF7T2PxddM='),
            ]

        for key, data, expected in cases:
            self.assertEqual(hmac_sha1(key, data), expected)
