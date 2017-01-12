# Copyright (C) 2008 Tristan Seligmann <mithrandi@mithrandi.net>
# Copyright (C) 2009 Canonical Ltd
# Copyright (C) 2009 Duncan McGreggor <oubiwann@adytum.us>
# Copyright (C) 2012 New Dream Network (DreamHost)
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Client wrapper for Amazon's Simple Storage Service.

API stability: unstable.

Various API-incompatible changes are planned in order to expose missing
functionality in this wrapper.
"""

from io import BytesIO
import datetime
import mimetypes
import warnings
from operator import itemgetter

from incremental import Version

from twisted.python.deprecate import deprecatedModuleAttribute
from twisted.web.http import datetimeToString
from twisted.web.http_headers import Headers
from twisted.web.client import FileBodyProducer
from twisted.internet import task

import hashlib
from hashlib import sha256

from urllib import urlencode, unquote
from dateutil.parser import parse as parseTime

from txaws.client.base import (
    _URLContext, BaseClient, BaseQuery, error_wrapper,
    RequestDetails, query,
)
from txaws.s3.acls import AccessControlPolicy
from txaws.s3.model import (
    Bucket, BucketItem, BucketListing, ItemOwner, LifecycleConfiguration,
    LifecycleConfigurationRule, NotificationConfiguration, RequestPayment,
    VersioningConfiguration, WebsiteConfiguration, MultipartInitiationResponse,
    MultipartCompletionResponse)
from txaws import _auth_v4
from txaws.s3.exception import S3Error
from txaws.service import AWSServiceEndpoint, REGION_US_EAST_1, S3_ENDPOINT
from txaws.util import XML


def _to_dict(headers):
    return {k: vs[0] for (k, vs) in headers.getAllRawHeaders()}

def s3_error_wrapper(error):
    error_wrapper(error, S3Error)


class S3Client(BaseClient):
    """A client for S3."""

    def __init__(self, creds=None, endpoint=None, query_factory=None,
                 receiver_factory=None, agent=None, utcnow=None,
                 cooperator=None):
        if query_factory is None:
            query_factory = query
        self.agent = agent
        self.utcnow = utcnow
        if cooperator is None:
            cooperator = task
        self._cooperator = cooperator
        super(S3Client, self).__init__(creds, endpoint, query_factory,
                                       receiver_factory=receiver_factory)

    def _submit(self, query):
        d = query.submit(self.agent, self.receiver_factory, self.utcnow)
        d.addErrback(s3_error_wrapper)
        return d


    def _query_factory(self, details, **kw):
        return self.query_factory(credentials=self.creds, details=details, **kw)


    def _details(self, **kw):
        body = kw.pop("body", None)
        body_producer = kw.pop("body_producer", None)
        amz_headers = kw.pop("amz_headers", {})

        # It makes no sense to specify both.  That makes it ambiguous
        # what data should make up the request body.
        if body is not None and body_producer is not None:
            raise ValueError("data and body_producer are mutually exclusive")

        # If the body was specified as a string, we can compute a hash
        # of it and sign the hash along with the rest.  That protects
        # against replay attacks with different content.
        #
        # If the body was specified as a producer, we can't really do
        # this. :( The producer may generate large amounts of data
        # which we can't hold in memory and it may not be replayable.
        # AWS requires the signature in the header so there's no way
        # to both hash/sign and avoid buffering everything in memory.
        #
        # The saving grace is that we'll only issue requests over TLS
        # after verifying the AWS certificate and requests with a date
        # (included in the signature) more than 15 minutes in the past
        # are rejected. :/
        if body is not None:
            content_sha256 = sha256(body).hexdigest().decode("ascii")
            body_producer = FileBodyProducer(BytesIO(body), cooperator=self._cooperator)
        elif body_producer is None:
            # Just as important is to include the empty content hash
            # for all no-body requests.
            content_sha256 = sha256(b"").hexdigest().decode("ascii")
        else:
            # Tell AWS we're not trying to sign the payload.
            content_sha256 = None

        return RequestDetails(
            region=REGION_US_EAST_1,
            service=b"s3",
            body_producer=body_producer,
            amz_headers=amz_headers,
            content_sha256=content_sha256,
            **kw
        )


    def _url_context(self, *a, **kw):
        return s3_url_context(self.endpoint, *a, **kw)


    def _headers(self, content_type):
        if content_type is None:
            return Headers()
        return Headers({u"content-type": [content_type]})


    def list_buckets(self):
        """
        List all buckets.

        Returns a list of all the buckets owned by the authenticated sender of
        the request.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(),
        )
        query = self._query_factory(details)
        d = self._submit(query)
        d.addCallback(self._parse_list_buckets)
        return d

    def _parse_list_buckets(self, (response, xml_bytes)):
        """
        Parse XML bucket list response.
        """
        root = XML(xml_bytes)
        buckets = []
        for bucket_data in root.find("Buckets"):
            name = bucket_data.findtext("Name")
            date_text = bucket_data.findtext("CreationDate")
            date_time = parseTime(date_text)
            bucket = Bucket(name, date_time)
            buckets.append(bucket)
        return buckets

    def create_bucket(self, bucket):
        """
        Create a new bucket.
        """
        details = self._details(
            method=b"PUT",
            url_context=self._url_context(bucket=bucket),
        )
        query = self._query_factory(details)
        return self._submit(query)

    def delete_bucket(self, bucket):
        """
        Delete a bucket.

        The bucket must be empty before it can be deleted.
        """
        details = self._details(
            method=b"DELETE",
            url_context=self._url_context(bucket=bucket),
        )
        query = self._query_factory(details)
        return self._submit(query)

    def get_bucket(self, bucket, marker=None, max_keys=None):
        """
        Get a list of all the objects in a bucket.

        @param marker: If given, indicate a position in the overall
            results where the results of this call should begin.  The
            first result is the first object that sorts greater than
            this marker.
        @type marker: L{bytes} or L{NoneType}

        @param max_keys: If given, the maximum number of objects to
            return.
        @type max_keys: L{int} or L{NoneType}

        @return: A L{Deferred} that fires with a L{BucketListing}
            describing the result.

        @see: U{http://docs.aws.amazon.com/AmazonS3/latest/API/RESTBucketGET.html}
        """
        args = []
        if marker is not None:
            args.append(("marker", marker))
        if max_keys is not None:
            args.append(("max-keys", "%d" % (max_keys,)))
        if args:
            object_name = "?" + urlencode(args)
        else:
            object_name = None
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name=object_name),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_get_bucket)
        return d

    def _parse_get_bucket(self, (response, xml_bytes)):
        root = XML(xml_bytes)
        name = root.findtext("Name")
        prefix = root.findtext("Prefix")
        marker = root.findtext("Marker")
        max_keys = root.findtext("MaxKeys")
        is_truncated = root.findtext("IsTruncated")
        contents = []

        for content_data in root.findall("Contents"):
            key = content_data.findtext("Key")
            date_text = content_data.findtext("LastModified")
            modification_date = parseTime(date_text)
            etag = content_data.findtext("ETag")
            size = content_data.findtext("Size")
            storage_class = content_data.findtext("StorageClass")
            owner_id = content_data.findtext("Owner/ID")
            owner_display_name = content_data.findtext("Owner/DisplayName")
            owner = ItemOwner(owner_id, owner_display_name)
            content_item = BucketItem(key, modification_date, etag, size,
                                      storage_class, owner)
            contents.append(content_item)

        common_prefixes = []
        for prefix_data in root.findall("CommonPrefixes"):
            common_prefixes.append(prefix_data.text)

        return BucketListing(name, prefix, marker, max_keys, is_truncated,
                             contents, common_prefixes)

    def get_bucket_location(self, bucket):
        """
        Get the location (region) of a bucket.

        @param bucket: The name of the bucket.
        @return: A C{Deferred} that will fire with the bucket's region.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name="?location"),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_bucket_location)
        return d

    def _parse_bucket_location(self, (response, xml_bytes)):
        """Parse a C{LocationConstraint} XML document."""
        root = XML(xml_bytes)
        return root.text or ""

    def get_bucket_lifecycle(self, bucket):
        """
        Get the lifecycle configuration of a bucket.

        @param bucket: The name of the bucket.
        @return: A C{Deferred} that will fire with the bucket's lifecycle
        configuration.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name="?lifecycle"),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_lifecycle_config)
        return d

    def _parse_lifecycle_config(self, (response, xml_bytes)):
        """Parse a C{LifecycleConfiguration} XML document."""
        root = XML(xml_bytes)
        rules = []

        for content_data in root.findall("Rule"):
            id = content_data.findtext("ID")
            prefix = content_data.findtext("Prefix")
            status = content_data.findtext("Status")
            expiration = int(content_data.findtext("Expiration/Days"))
            rules.append(
                LifecycleConfigurationRule(id, prefix, status, expiration))

        return LifecycleConfiguration(rules)

    def get_bucket_website_config(self, bucket):
        """
        Get the website configuration of a bucket.

        @param bucket: The name of the bucket.
        @return: A C{Deferred} that will fire with the bucket's website
        configuration.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name='?website'),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_website_config)
        return d

    def _parse_website_config(self, (response, xml_bytes)):
        """Parse a C{WebsiteConfiguration} XML document."""
        root = XML(xml_bytes)
        index_suffix = root.findtext("IndexDocument/Suffix")
        error_key = root.findtext("ErrorDocument/Key")

        return WebsiteConfiguration(index_suffix, error_key)

    def get_bucket_notification_config(self, bucket):
        """
        Get the notification configuration of a bucket.

        @param bucket: The name of the bucket.
        @return: A C{Deferred} that will request the bucket's notification
        configuration.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name="?notification"),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_notification_config)
        return d

    def _parse_notification_config(self, (response, xml_bytes)):
        """Parse a C{NotificationConfiguration} XML document."""
        root = XML(xml_bytes)
        topic = root.findtext("TopicConfiguration/Topic")
        event = root.findtext("TopicConfiguration/Event")

        return NotificationConfiguration(topic, event)

    def get_bucket_versioning_config(self, bucket):
        """
        Get the versioning configuration of a bucket.

        @param bucket: The name of the bucket.  @return: A C{Deferred} that
        will request the bucket's versioning configuration.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name="?versioning"),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_versioning_config)
        return d

    def _parse_versioning_config(self, (response, xml_bytes)):
        """Parse a C{VersioningConfiguration} XML document."""
        root = XML(xml_bytes)
        mfa_delete = root.findtext("MfaDelete")
        status = root.findtext("Status")

        return VersioningConfiguration(mfa_delete=mfa_delete, status=status)

    def get_bucket_acl(self, bucket):
        """
        Get the access control policy for a bucket.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name="?acl"),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_acl)
        return d

    def put_bucket_acl(self, bucket, access_control_policy):
        """
        Set access control policy on a bucket.
        """
        data = access_control_policy.to_xml()
        details = self._details(
            method=b"PUT",
            url_context=self._url_context(bucket=bucket, object_name=b"?acl"),
            body=data,
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_acl)
        return d

    def _parse_acl(self, (response, xml_bytes)):
        """
        Parse an C{AccessControlPolicy} XML document and convert it into an
        L{AccessControlPolicy} instance.
        """
        return AccessControlPolicy.from_xml(xml_bytes)

    def put_object(self, bucket, object_name, data=None, content_type=None,
                   metadata={}, amz_headers={}, body_producer=None):
        """
        Put an object in a bucket.

        An existing object with the same name will be replaced.

        @param bucket: The name of the bucket.
        @param object: The name of the object.
        @param data: The data to write.
        @param content_type: The type of data being written.
        @param metadata: A C{dict} used to build C{x-amz-meta-*} headers.
        @param amz_headers: A C{dict} used to build C{x-amz-*} headers.
        @return: A C{Deferred} that will fire with the result of request.
        """
        details = self._details(
            method=b"PUT",
            url_context=self._url_context(bucket=bucket, object_name=object_name),
            headers=self._headers(content_type),
            metadata=metadata,
            amz_headers=amz_headers,
            body=data,
            body_producer=body_producer,
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(itemgetter(1))
        return d

    def copy_object(self, source_bucket, source_object_name, dest_bucket=None,
                    dest_object_name=None, metadata={}, amz_headers={}):
        """
        Copy an object stored in S3 from a source bucket to a destination
        bucket.

        @param source_bucket: The S3 bucket to copy the object from.
        @param source_object_name: The name of the object to copy.
        @param dest_bucket: Optionally, the S3 bucket to copy the object to.
            Defaults to C{source_bucket}.
        @param dest_object_name: Optionally, the name of the new object.
            Defaults to C{source_object_name}.
        @param metadata: A C{dict} used to build C{x-amz-meta-*} headers.
        @param amz_headers: A C{dict} used to build C{x-amz-*} headers.
        @return: A C{Deferred} that will fire with the result of request.
        """
        dest_bucket = dest_bucket or source_bucket
        dest_object_name = dest_object_name or source_object_name
        amz_headers["copy-source"] = "/%s/%s" % (source_bucket,
                                                 source_object_name)
        details = self._details(
            method=b"PUT",
            url_context=self._url_context(
                bucket=dest_bucket, object_name=dest_object_name,
            ),
            metadata=metadata,
            amz_headers=amz_headers,
        )
        d = self._submit(self._query_factory(details))
        return d

    def get_object(self, bucket, object_name):
        """
        Get an object from a bucket.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name=object_name),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(itemgetter(1))
        return d

    def head_object(self, bucket, object_name):
        """
        Retrieve object metadata only.
        """
        details = self._details(
            method=b"HEAD",
            url_context=self._url_context(bucket=bucket, object_name=object_name),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(lambda (response, body): _to_dict(response.responseHeaders))
        return d

    def delete_object(self, bucket, object_name):
        """
        Delete an object from a bucket.

        Once deleted, there is no method to restore or undelete an object.
        """
        details = self._details(
            method=b"DELETE",
            url_context=self._url_context(bucket=bucket, object_name=object_name),
        )
        d = self._submit(self._query_factory(details))
        return d

    def put_object_acl(self, bucket, object_name, access_control_policy):
        """
        Set access control policy on an object.
        """
        data = access_control_policy.to_xml()
        details = self._details(
            method=b"PUT",
            url_context=self._url_context(
                bucket=bucket, object_name='%s?acl' % (object_name,),
            ),
            body=data,
        )
        query = self._query_factory(details)
        d = self._submit(query)
        d.addCallback(self._parse_acl)
        return d

    def get_object_acl(self, bucket, object_name):
        """
        Get the access control policy for an object.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name='%s?acl' % (object_name,)),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_acl)
        return d

    def put_request_payment(self, bucket, payer):
        """
        Set request payment configuration on bucket to payer.

        @param bucket: The name of the bucket.
        @param payer: The name of the payer.
        @return: A C{Deferred} that will fire with the result of the request.
        """
        data = RequestPayment(payer).to_xml()
        details = self._details(
            method=b"PUT",
            url_context=self._url_context(bucket=bucket, object_name="?requestPayment"),
            body=data,
        )
        d = self._submit(self._query_factory(details))
        return d

    def get_request_payment(self, bucket):
        """
        Get the request payment configuration on a bucket.

        @param bucket: The name of the bucket.
        @return: A C{Deferred} that will fire with the name of the payer.
        """
        details = self._details(
            method=b"GET",
            url_context=self._url_context(bucket=bucket, object_name="?requestPayment"),
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(self._parse_get_request_payment)
        return d

    def _parse_get_request_payment(self, (response, xml_bytes)):
        """
        Parse a C{RequestPaymentConfiguration} XML document and extract the
        payer.
        """
        return RequestPayment.from_xml(xml_bytes).payer

    def init_multipart_upload(self, bucket, object_name, content_type=None,
                              amz_headers={}, metadata={}):
        """
        Initiate a multipart upload to a bucket.

        @param bucket: The name of the bucket
        @param object_name: The object name
        @param content_type: The Content-Type for the object
        @param metadata: C{dict} containing additional metadata
        @param amz_headers: A C{dict} used to build C{x-amz-*} headers.
        @return: C{str} upload_id
        """
        objectname_plus = '%s?uploads' % object_name
        details = self._details(
            method=b"POST",
            url_context=self._url_context(bucket=bucket, object_name=objectname_plus),
            headers=self._headers(content_type),
            metadata=metadata,
            amz_headers=amz_headers,
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(
            lambda (response, body): MultipartInitiationResponse.from_xml(body)
        )
        return d

    def upload_part(self, bucket, object_name, upload_id, part_number,
                    data=None, content_type=None, metadata={},
                    body_producer=None):
        """
        Upload a part of data corresponding to a multipart upload.

        @param bucket: The bucket name
        @param object_name: The object name
        @param upload_id: The multipart upload id
        @param part_number: The part number
        @param data: Data (optional, requires body_producer if not specified)
        @param content_type: The Content-Type
        @param metadata: Additional metadata
        @param body_producer: an C{IBodyProducer} (optional, requires data if
            not specified)
        @return: the C{Deferred} from underlying query.submit() call
        """
        parms = 'partNumber=%s&uploadId=%s' % (str(part_number), upload_id)
        objectname_plus = '%s?%s' % (object_name, parms)
        details = self._details(
            method=b"PUT",
            url_context=self._url_context(bucket=bucket, object_name=objectname_plus),
            headers=self._headers(content_type),
            metadata=metadata,
            body=data,
        )
        d = self._submit(self._query_factory(details))
        d.addCallback(lambda (response, data): _to_dict(response.responseHeaders))
        return d

    def complete_multipart_upload(self, bucket, object_name, upload_id,
                                  parts_list, content_type=None, metadata={}):
        """
        Complete a multipart upload.

        N.B. This can be possibly be a slow operation.

        @param bucket: The bucket name
        @param object_name: The object name
        @param upload_id: The multipart upload id
        @param parts_list: A List of all the parts
            (2-tuples of part sequence number and etag)
        @param content_type: The Content-Type of the object
        @param metadata: C{dict} containing additional metadata
        @return: a C{Deferred} that fires after request is complete
        """
        data = self._build_complete_multipart_upload_xml(parts_list)
        objectname_plus = '%s?uploadId=%s' % (object_name, upload_id)
        details = self._details(
            method=b"POST",
            url_context=self._url_context(bucket=bucket, object_name=objectname_plus),
            headers=self._headers(content_type),
            metadata=metadata,
            body=data,
        )
        d = self._submit(self._query_factory(details))
        # TODO - handle error responses
        d.addCallback(
            lambda (response, body): MultipartCompletionResponse.from_xml(body)
        )
        return d

    def _build_complete_multipart_upload_xml(self, parts_list):
        xml = []
        parts_list.sort(key=lambda p: int(p[0]))
        xml.append('<CompleteMultipartUpload>')
        for pt in parts_list:
            xml.append('<Part>')
            xml.append('<PartNumber>%s</PartNumber>' % pt[0])
            xml.append('<ETag>%s</ETag>' % pt[1])
            xml.append('</Part>')
        xml.append('</CompleteMultipartUpload>')
        return '\n'.join(xml)


class Query(BaseQuery):
    """A query for submission to the S3 service."""

    def __init__(self, bucket=None, object_name=None, data="",
                 content_type=None, metadata={}, amz_headers={},
                 body_producer=None, *args, **kwargs):
        super(Query, self).__init__(*args, **kwargs)

        # data might be None or "", alas.
        if data and body_producer is not None:
            raise ValueError("data and body_producer are mutually exclusive.")

        self.bucket = bucket
        self.object_name = object_name
        self.data = data
        self.body_producer = body_producer
        self.content_type = content_type
        self.metadata = metadata
        self.amz_headers = amz_headers
        self._date = datetimeToString()
        if not self.endpoint or not self.endpoint.host:
            self.endpoint = AWSServiceEndpoint(S3_ENDPOINT)
        self.endpoint.set_method(self.action)

    @property
    def date(self):
        """
        Return the date and emit a deprecation warning.
        """
        warnings.warn("txaws.s3.client.Query.date is a deprecated attribute",
                      DeprecationWarning,
                      stacklevel=2)
        return self._date

    @date.setter
    def date(self, value):
        """
        Set the date.

        @param value: The new date for this L{Query}.
        @type value: L{str}
        """
        self._date = value

    def set_content_type(self):
        """
        Set the content type based on the file extension used in the object
        name.
        """
        if self.object_name and not self.content_type:
            # XXX nothing is currently done with the encoding... we may
            # need to in the future
            self.content_type, encoding = mimetypes.guess_type(
                self.object_name, strict=False)

    def get_headers(self, instant):
        """
        Build the list of headers needed in order to perform S3 operations.
        """
        headers = {'x-amz-date': _auth_v4.makeAMZDate(instant)}
        if self.body_producer is None:
            data = self.data
            if data is None:
                data = b""
            headers["x-amz-content-sha256"] = hashlib.sha256(data).hexdigest()
        else:
            data = None
            headers["x-amz-content-sha256"] = b"UNSIGNED-PAYLOAD"
        for key, value in self.metadata.iteritems():
            headers["x-amz-meta-" + key] = value
        for key, value in self.amz_headers.iteritems():
            headers["x-amz-" + key] = value

        # Before we check if the content type is set, let's see if we can set
        # it by guessing the the mimetype.
        self.set_content_type()
        if self.content_type is not None:
            headers["Content-Type"] = self.content_type
        if self.creds is not None:
            headers["Authorization"] = self.sign(
                headers,
                data,
                s3_url_context(self.endpoint, self.bucket, self.object_name),
                instant,
                method=self.action)
        return headers

    def sign(self, headers, data, url_context, instant, method,
             region=REGION_US_EAST_1):
        """Sign this query using its built in credentials."""
        headers["host"] = url_context.get_encoded_host()

        if data is None:
            request = _auth_v4._CanonicalRequest.from_request_components(
                method=method,
                url=url_context.get_encoded_path(),
                headers=headers,
                headers_to_sign=('host', 'x-amz-date'),
                payload_hash=None,
            )
        else:
            request = _auth_v4._CanonicalRequest.from_request_components_and_payload(
                method=method,
                url=url_context.get_encoded_path(),
                headers=headers,
                headers_to_sign=('host', 'x-amz-date'),
                payload=data,
            )

        return _auth_v4._make_authorization_header(
            region=region,
            service="s3",
            canonical_request=request,
            credentials=self.creds,
            instant=instant)

    def submit(self, url_context=None, utcnow=datetime.datetime.utcnow):
        """Submit this query.

        @return: A deferred from get_page
        """
        if not url_context:
            url_context = s3_url_context(
                self.endpoint, self.bucket, self.object_name)
        d = self.get_page(
            url_context.get_encoded_url(),
            method=self.action,
            postdata=self.data or b"",
            headers=self.get_headers(utcnow()),
        )

        return d.addErrback(s3_error_wrapper)


def s3_url_context(service_endpoint, bucket=None, object_name=None):
    """
    Create a URL based on the given service endpoint and suitable for
    the given bucket or object.

    @param service_endpoint: The service endpoint on which to base the
        resulting URL.
    @type service_endpoint: L{AWSServiceEndpoint}

    @param bucket: If given, the name of a bucket to reference.
    @type bucket: L{unicode}

    @param object_name: If given, the name of an object or object
        subresource to reference.
    @type object_name: L{unicode}
    """

    # Define our own query parser which can handle the consequences of
    # `?acl` and such (subresources).  At its best, parse_qsl doesn't
    # let us differentiate between these and empty values (such as
    # `?acl=`).
    def p(s):
        results = []
        args = s.split(u"&")
        for a in args:
            pieces = a.split(u"=")
            if len(pieces) == 1:
                results.append((unquote(pieces[0]),))
            elif len(pieces) == 2:
                results.append(tuple(map(unquote, pieces)))
            else:
                raise Exception("oh no")
        return results

    query = []
    path = []
    if bucket is None:
        path.append(u"")
    else:
        if isinstance(bucket, bytes):
            bucket = bucket.decode("utf-8")
        path.append(bucket)
        if object_name is None:
            path.append(u"")
        else:
            if isinstance(object_name, bytes):
                object_name = object_name.decode("utf-8")
            if u"?" in object_name:
                object_name, query = object_name.split(u"?", 1)
                query = p(query)
            object_name_components = object_name.split(u"/")
            if object_name_components[0] == u"":
                object_name_components.pop(0)
            if object_name_components:
                path.extend(object_name_components)
            else:
                path.append(u"")
    return _S3URLContext(
        scheme=service_endpoint.scheme.decode("utf-8"),
        host=service_endpoint.get_host().decode("utf-8"),
        port=service_endpoint.port,
        path=path,
        query=query,
    )


class _S3URLContext(_URLContext):
    # Backwards compatibility layer.  For deprecation.  s3_url_context
    # should just return an _URLContext and application code should
    # interact with that interface.
    def get_host(self):
        return self.get_encoded_host()

    def get_path(self):
        return self.get_encoded_path()

    def get_url(self):
        return self.get_encoded_url()


# Backwards compatibility layer.  For deprecation.
def URLContext(service_endpoint, bucket=None, object_name=None):
    args = (service_endpoint,)
    for s in (bucket, object_name):
        if s is not None:
            args += (s.decode("utf-8"),)
    return s3_url_context(*args)


deprecatedModuleAttribute(
    Version("txAWS", 0, 3, 0),
    "See txaws.s3.client.query",
    __name__,
    "Query",
)

deprecatedModuleAttribute(
    Version("txAWS", 0, 3, 0),
    "See txaws.s3.client.s3_url_context",
    __name__,
    "URLContext",
)
