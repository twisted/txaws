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
from txaws.s3 import model
from txaws.s3.exception import S3Error
from txaws.service import AWSServiceEndpoint, S3_ENDPOINT
from txaws.util import XML, calculate_md5


def s3_error_wrapper(error):
    error_wrapper(error, S3Error)


class URLContext(object):
    """
    The hosts and the paths that form an S3 endpoint change depending upon the
    context in which they are called. Sometimes the bucket name is in the host,
    sometimes in the path. What's more, the behaviour against live AWS
    resources doesn't seem to match the AWS documentation.
    """
    def __init__(self, service_endpoint, bucket="", object_name=""):
        self.endpoint = service_endpoint
        self.bucket = bucket
        self.object_name = object_name

    def get_host(self):
        if not self.bucket:
            return self.endpoint.get_host()
        else:
            return "%s.%s" % (self.bucket, self.endpoint.get_host())

    def get_path(self):
        path = "/"
        if self.bucket is not None and self.object_name:
            if self.object_name.startswith("/"):
                path = self.object_name
            else:
                path += self.object_name
        return path

    def get_url(self):
        return "%s://%s%s" % (
            self.endpoint.scheme, self.get_host(), self.get_path())


class BucketURLContext(URLContext):
    """
    This URL context class provides a means of overriding the standard
    behaviour of the URLContext object so that when creating or deleting a
    bucket, the appropriate URL is obtained.

    When creating and deleting buckets on AWS, if the host is set as documented
    (bucketname.s3.amazonaws.com), a 403 error is returned. When, however, one
    sets the host without the bucket name prefix, the operation is completed
    successfully.
    """
    def get_host(self):
        return self.endpoint.get_host()

    def get_path(self):
        return "/%s" % (self.bucket)


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
            bucket = model.Bucket(name, date_time)
            buckets.append(bucket)
        return buckets

    def create_bucket(self, bucket):
        """
        Create a new bucket.
        """
        query = self.query_factory(
            action="PUT", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket)
        url_context = BucketURLContext(self.endpoint, bucket)
        return query.submit(url_context)

    def delete_bucket(self, bucket):
        """
        Delete a bucket.

        The bucket must be empty before it can be deleted.
        """
        query = self.query_factory(
            action="DELETE", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket)
        url_context = BucketURLContext(self.endpoint, bucket)
        return query.submit(url_context)

    def get_bucket(self, bucket):
        """
        Get a list of all the objects in a bucket.
        """
        query = self.query_factory(
            action="GET", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket)
        url_context = BucketURLContext(self.endpoint, bucket)
        d = query.submit(url_context)
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
            owner = model.ItemOwner(owner_id, owner_display_name)
            content_item = model.BucketItem(
                key, modification_date, etag, size, storage_class, owner)
            contents.append(content_item)

        common_prefixes = []
        for prefix_data in root.findall("CommonPrefixes"):
            common_prefixes.append(prefix_data.text)

        return model.BucketListing(
            name, prefix, marker, max_keys, is_truncated, contents,
            common_prefixes)

    def put_object(self, bucket, object_name, data, content_type=None,
                   metadata={}):
        """
        Put an object in a bucket.

        Any existing object of the same name will be replaced.
        """
        query = self.query_factory(
            action="PUT", creds=self.creds, endpoint=self.endpoint,
            bucket=bucket, object_name=object_name, data=data,
            content_type=content_type, metadata=metadata)
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


class Query(BaseQuery):
    """A query for submission to the S3 service."""

    def __init__(self, bucket=None, object_name=None, data="",
                 content_type=None, metadata={}, *args, **kwargs):
        super(Query, self).__init__(*args, **kwargs)
        self.bucket = bucket
        self.object_name = object_name
        self.data = data
        self.content_type = content_type
        self.metadata = metadata
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
        resource = "/"
        if self.bucket:
            resource += self.bucket
            if self.object_name:
                resource += "/%s" % self.object_name
        return resource

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
