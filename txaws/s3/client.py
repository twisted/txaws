# Copyright (C) 2008 Tristan Seligmann <mithrandi@mithrandi.net>
# Copyright (C) 2009 Canonical Ltd
# Copyright (C) 2009 Duncan McGreggor <oubiwann@adytum.us>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Client wrapper for Amazon's Simple Storage Service.

API stability: unstable.

Various API-incompatible changes are planned in order to expose missing
functionality in this wrapper.
"""
import mimetypes

from twisted.web.http import datetimeToString

from epsilon.extime import Time

from txaws.client.base import BaseClient, BaseQuery, error_wrapper
from txaws.s3.acls import AccessControlPolicy
from txaws.s3.model import (
    Bucket, BucketItem, BucketListing, ItemOwner, RequestPayment)
from txaws.s3.exception import S3Error
from txaws.service import AWSServiceEndpoint, S3_ENDPOINT
from txaws.util import XML, calculate_md5


def s3_error_wrapper(error):
    error_wrapper(error, S3Error)


class URLContext(object):
    """
    The hosts and the paths that form an S3 endpoint change depending upon the
    context in which they are called.  While S3 supports bucket names in the
    host name, we use the convention of providing it in the path so that
    using IP addresses and alternative implementations of S3 actually works
    (e.g. Walrus).
    """
    def __init__(self, service_endpoint, bucket="", object_name=""):
        self.endpoint = service_endpoint
        self.bucket = bucket
        self.object_name = object_name

    def get_host(self):
        return self.endpoint.get_host()

    def get_path(self):
        path = "/"
        if self.bucket is not None:
            path += self.bucket
        if self.bucket is not None and self.object_name:
            if not self.object_name.startswith("/"):
                path += "/"
            path += self.object_name
        elif self.bucket is not None and not path.endswith("/"):
            path += "/"
        return path

    def get_url(self):
        if self.endpoint.port is not None:
            return "%s://%s:%d%s" % (
                self.endpoint.scheme, self.get_host(), self.endpoint.port, self.get_path())
        else:
            return "%s://%s%s" % (
                self.endpoint.scheme, self.get_host(), self.get_path())


class S3Client(BaseClient):
    """A client for S3."""

    def __init__(self, creds=None, endpoint=None, query_factory=None):
        if query_factory is None:
            query_factory = Query
        super(S3Client, self).__init__(creds, endpoint, query_factory)

    def list_buckets(self):
        """
        List all buckets.

        Returns a list of all the buckets owned by the authenticated sender of
        the request.
        """
        query = self.query_factory(
            action="GET", creds=self.creds, endpoint=self.endpoint)
        d = query.submit()
        return d.addCallback(self._parse_list_buckets)

    def _parse_list_buckets(self, xml_bytes):
        """
        Parse XML bucket list response.
        """
        root = XML(xml_bytes)
        buckets = []
        for bucket_data in root.find("Buckets"):
            name = bucket_data.findtext("Name")
            date_text = bucket_data.findtext("CreationDate")
            date_time = Time.fromISO8601TimeAndDate(date_text).asDatetime()
            bucket = Bucket(name, date_time)
            buckets.append(bucket)
        return buckets

    def create_bucket(self, bucket):
        """
        Create a new bucket.
        """
        query = self.query_factory(
            action="PUT", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket)
        return query.submit()

    def delete_bucket(self, bucket):
        """
        Delete a bucket.

        The bucket must be empty before it can be deleted.
        """
        query = self.query_factory(
            action="DELETE", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket)
        return query.submit()

    def get_bucket(self, bucket):
        """
        Get a list of all the objects in a bucket.
        """
        query = self.query_factory(
            action="GET", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket)
        d = query.submit()
        return d.addCallback(self._parse_get_bucket)

    def _parse_get_bucket(self, xml_bytes):
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
            modification_date = Time.fromISO8601TimeAndDate(
                date_text).asDatetime()
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
        query = self.query_factory(action="GET", creds=self.creds,
                                   endpoint=self.endpoint, bucket=bucket,
                                   object_name="?location")
        d = query.submit()
        return d.addCallback(self._parse_bucket_location)

    def _parse_bucket_location(self, xml_bytes):
        """Parse a C{LocationConstraint} XML document."""
        root = XML(xml_bytes)
        return root.text or ""

    def get_bucket_acl(self, bucket):
        """
        Get the access control policy for a bucket.
        """
        query = self.query_factory(
            action='GET', creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name='?acl')
        return query.submit().addCallback(self._parse_acl)

    def put_bucket_acl(self, bucket, access_control_policy):
        """
        Set access control policy on a bucket.
        """
        data = access_control_policy.to_xml()
        query = self.query_factory(
            action='PUT', creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name='?acl', data=data)
        return query.submit().addCallback(self._parse_acl)

    def _parse_acl(self, xml_bytes):
        """
        Parse an C{AccessControlPolicy} XML document and convert it into an
        L{AccessControlPolicy} instance.
        """
        return AccessControlPolicy.from_xml(xml_bytes)

    def put_object(self, bucket, object_name, data, content_type=None,
                   metadata={}, amz_headers={}):
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
        query = self.query_factory(
            action="PUT", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name=object_name, data=data,
            content_type=content_type, metadata=metadata,
            amz_headers=amz_headers)
        return query.submit()

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
        query = self.query_factory(
            action="PUT", creds=self.creds, endpoint=self.endpoint,
            bucket=dest_bucket, object_name=dest_object_name,
            metadata=metadata, amz_headers=amz_headers)
        return query.submit()

    def get_object(self, bucket, object_name):
        """
        Get an object from a bucket.
        """
        query = self.query_factory(
            action="GET", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name=object_name)
        return query.submit()

    def head_object(self, bucket, object_name):
        """
        Retrieve object metadata only.
        """
        query = self.query_factory(
            action="HEAD", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name=object_name)
        d = query.submit()
        return d.addCallback(query.get_response_headers)

    def delete_object(self, bucket, object_name):
        """
        Delete an object from a bucket.

        Once deleted, there is no method to restore or undelete an object.
        """
        query = self.query_factory(
            action="DELETE", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name=object_name)
        return query.submit()

    def get_object_acl(self, bucket, object_name):
        """
        Get the access control policy for an object.
        """
        query = self.query_factory(
            action='GET', creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name='%s?acl' % object_name)
        return query.submit().addCallback(self._parse_acl)

    def put_request_payment(self, bucket, payer):
        """
        Set request payment configuration on bucket to payer.

        @param bucket: The name of the bucket.
        @param payer: The name of the payer.
        @return: A C{Deferred} that will fire with the result of the request.
        """
        data = RequestPayment(payer).to_xml()
        query = self.query_factory(
            action="PUT", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name="?requestPayment", data=data)
        return query.submit()

    def get_request_payment(self, bucket):
        """
        Get the request payment configuration on a bucket.

        @param bucket: The name of the bucket.
        @return: A C{Deferred} that will fire with the name of the payer.
        """
        query = self.query_factory(
            action="GET", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name="?requestPayment")
        return query.submit().addCallback(self._parse_get_request_payment)

    def _parse_get_request_payment(self, xml_bytes):
        """
        Parse a C{RequestPaymentConfiguration} XML document and extract the
        payer.
        """
        return RequestPayment.from_xml(xml_bytes).payer


class Query(BaseQuery):
    """A query for submission to the S3 service."""

    def __init__(self, bucket=None, object_name=None, data="",
                 content_type=None, metadata={}, amz_headers={}, *args,
                 **kwargs):
        super(Query, self).__init__(*args, **kwargs)
        self.bucket = bucket
        self.object_name = object_name
        self.data = data
        self.content_type = content_type
        self.metadata = metadata
        self.amz_headers = amz_headers
        self.date = datetimeToString()
        if not self.endpoint or not self.endpoint.host:
            self.endpoint = AWSServiceEndpoint(S3_ENDPOINT)
        self.endpoint.set_method(self.action)

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

    def get_headers(self):
        """
        Build the list of headers needed in order to perform S3 operations.
        """
        headers = {"Content-Length": len(self.data),
                   "Content-MD5": calculate_md5(self.data),
                   "Date": self.date}
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
            signature = self.sign(headers)
            headers["Authorization"] = "AWS %s:%s" % (
                self.creds.access_key, signature)
        return headers

    def get_canonicalized_amz_headers(self, headers):
        """
        Get the headers defined by Amazon S3.
        """
        headers = [
            (name.lower(), value) for name, value in headers.iteritems()
            if name.lower().startswith("x-amz-")]
        headers.sort()
        # XXX missing spec implementation:
        # 1) txAWS doesn't currently combine headers with the same name
        # 2) txAWS doesn't currently unfold long headers
        return "".join("%s:%s\n" % (name, value) for name, value in headers)

    def get_canonicalized_resource(self):
        """
        Get an S3 resource path.
        """
        path = "/"
        if self.bucket is not None:
            path += self.bucket
        if self.bucket is not None and self.object_name:
            if not self.object_name.startswith("/"):
                path += "/"
            path += self.object_name
        elif self.bucket is not None and not path.endswith("/"):
            path += "/"
        return path

    def sign(self, headers):
        """Sign this query using its built in credentials."""
        text = (self.action + "\n" +
                headers.get("Content-MD5", "") + "\n" +
                headers.get("Content-Type", "") + "\n" +
                headers.get("Date", "") + "\n" +
                self.get_canonicalized_amz_headers(headers) +
                self.get_canonicalized_resource())
        return self.creds.sign(text, hash_type="sha1")

    def submit(self, url_context=None):
        """Submit this query.

        @return: A deferred from get_page
        """
        if not url_context:
            url_context = URLContext(
                self.endpoint, self.bucket, self.object_name)
        d = self.get_page(
            url_context.get_url(), method=self.action, postdata=self.data,
            headers=self.get_headers())
        return d.addErrback(s3_error_wrapper)
