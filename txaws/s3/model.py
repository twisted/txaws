# Copyright (C) 2009 Canonical Ltd
# Copyright (C) 2009 Duncan McGreggor <oubiwann@adytum.us>
# Copyright (C) 2011 Drew Smathers <drew.smathers@gmail.com>
# Copyright (C) 2012 New Dream Network (DreamHost)
# Licenced under the txaws licence available at /LICENSE in the txaws source.
from txaws.util import XML


class Bucket(object):
    """
    An Amazon S3 storage bucket.
    """
    def __init__(self, name, creation_date):
        self.name = name
        self.creation_date = creation_date


class ItemOwner(object):
    """
    The owner of a content item.
    """
    def __init__(self, id, display_name):
        self.id = id
        self.display_name = display_name


class BucketItem(object):
    """
    The contents of an Amazon S3 bucket.
    """
    def __init__(self, key, modification_date, etag, size, storage_class,
                 owner=None):
        self.key = key
        self.modification_date = modification_date
        self.etag = etag
        self.size = size
        self.storage_class = storage_class
        self.owner = owner


class BucketListing(object):
    """
    A mapping for the data in a bucket listing.
    """
    def __init__(self, name, prefix, marker, max_keys, is_truncated,
                 contents=None, common_prefixes=None):
        self.name = name
        self.prefix = prefix
        self.marker = marker
        self.max_keys = max_keys
        self.is_truncated = is_truncated
        self.contents = contents
        self.common_prefixes = common_prefixes


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
