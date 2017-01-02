# Copyright (C) 2009 Canonical Ltd
# Copyright (C) 2009 Duncan McGreggor <oubiwann@adytum.us>
# Copyright (C) 2011 Drew Smathers <drew.smathers@gmail.com>
# Copyright (C) 2012 New Dream Network (DreamHost)
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from datetime import datetime

import attr
from attr import validators

from txaws.util import XML


@attr.s
class Bucket(object):
    """
    An Amazon S3 storage bucket.
    """
    name = attr.ib()
    creation_date = attr.ib()


@attr.s
class ItemOwner(object):
    """
    The owner of a content item.
    """
    id = attr.ib()
    display_name = attr.ib()


@attr.s
class BucketItem(object):
    """
    The contents of an Amazon S3 bucket.
    """
    key = attr.ib()
    modification_date = attr.ib(validator=validators.instance_of(datetime))
    etag = attr.ib()
    size = attr.ib(validator=validators.instance_of(bytes))
    storage_class = attr.ib()
    owner = attr.ib(
        validator=validators.optional(validators.instance_of(ItemOwner)),
        default=None,
    )


@attr.s
class BucketListing(object):
    """
    A mapping for the data in a bucket listing.
    """
    name = attr.ib()
    prefix = attr.ib()
    marker = attr.ib()
    max_keys = attr.ib()
    is_truncated = attr.ib()
    contents = attr.ib(default=None)
    common_prefixes = attr.ib(default=None)


class LifecycleConfiguration(object):
    """
    Returns the lifecycle configuration information set on the bucket.
    """
    def __init__(self, rules):
        self.rules = rules


class LifecycleConfigurationRule(object):
    """
    Container for elements that describe a lifecycle rule.
    """
    def __init__(self, id, prefix, status, expiration):
        self.id = id
        self.prefix = prefix
        self.status = status
        self.expiration = expiration


class WebsiteConfiguration(object):
    """
    A mapping for the data in a bucket website configuration.
    """
    def __init__(self, index_suffix, error_key=None):
        self.index_suffix = index_suffix
        self.error_key = error_key


class NotificationConfiguration(object):
    """
    A mapping for the data in a bucket notification configuration.
    """
    def __init__(self, topic=None, event=None):
        self.topic = topic
        self.event = event


class VersioningConfiguration(object):
    """
    Container for the bucket versioning configuration.

    According to Amazon:

    C{MfaDelete}: This element is only returned if the bucket has been
    configured with C{MfaDelete}. If the bucket has never been so configured,
    this element is not returned. The possible values are None, "Disabled" or
    "Enabled".

    C{Status}: If the bucket has never been so configured, this element is not
    returned. The possible values are None, "Suspended" or "Enabled".
    """
    def __init__(self, mfa_delete=None, status=None):
        self.mfa_delete = mfa_delete
        self.status = status


class FileChunk(object):
    """
    An Amazon S3 file chunk.

    S3 returns file chunks, 10 MB at a time, until the entire file is returned.
    These chunks need to be assembled once they are all returned.
    """


class RequestPayment(object):
    """
    A payment request.

    @param payer: One of 'Requester' or 'BucketOwner'.
    """

    payer_choices = ("Requester", "BucketOwner")

    def __init__(self, payer):
        if payer not in self.payer_choices:
            raise ValueError("Invalid value for payer: `%s`. Must be one of "
                             "%s." % (payer, ",".join(self.payer_choices)))
        self.payer = payer

    def to_xml(self):
        """
        Convert this request into a C{RequestPaymentConfiguration} XML
        document.
        """
        return ("<RequestPaymentConfiguration "
                  'xmlns="http://s3.amazonaws.com/doc/2006-03-01/">\n'
                "  <Payer>%s</Payer>\n"
                "</RequestPaymentConfiguration>" % self.payer)

    @classmethod
    def from_xml(cls, xml_bytes):
        """
        Create an instance from a C{RequestPaymentConfiguration} XML document.
        """
        root = XML(xml_bytes)
        return cls(root.findtext("Payer"))


class MultipartInitiationResponse(object):
    """
    A response to Initiate Multipart Upload
    """

    def __init__(self, bucket, object_name, upload_id):
        """
        @param bucket: The bucket name
        @param object_name: The object name
        @param upload_id: The upload id
        """
        self.bucket = bucket
        self.object_name = object_name
        self.upload_id = upload_id

    @classmethod
    def from_xml(cls, xml_bytes):
        """
        Create an instance of this from XML bytes.

        @param xml_bytes: C{str} bytes of XML to parse
        @return: an instance of L{MultipartInitiationResponse}
        """
        root = XML(xml_bytes)
        return cls(root.findtext('Bucket'),
                   root.findtext('Key'),
                   root.findtext('UploadId'))


class MultipartCompletionResponse(object):
    """
    Represents a response to Complete Multipart Upload
    """

    def __init__(self, location, bucket, object_name, etag):
        """
        @param location: The URI identifying newly created object
        @param bucket: The bucket name
        @param object_name: The object name / key
        @param etag: The entity tag
        """
        self.location = location
        self.bucket = bucket
        self.object_name = object_name
        self.etag = etag

    @classmethod
    def from_xml(cls, xml_bytes):
        """
        Create an instance of this class from XML bytes.

        @param xml_bytes: C{str} bytes of XML to parse
        @return: an instance of L{MultipartCompletionResponse}
        """
        root = XML(xml_bytes)
        return cls(root.findtext('Location'),
                   root.findtext('Bucket'),
                   root.findtext('Key'),
                   root.findtext('ETag'))

