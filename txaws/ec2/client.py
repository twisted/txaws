# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""EC2 client support."""

from base64 import b64encode
from urllib import quote

from twisted.web.client import _makeGetterFactory, HTTPClientFactory

from txaws import credentials
from txaws.util import iso8601time, XML
from txaws.ec2.exception import EC2Error


def ec2_error_wrapper(error):
    xmlPayload = error.value.response
    httpStatus = int(error.value.status)
    if httpStatus >= 500:
        # raise the original Twisted exception
        error.raiseException()
    elif httpStatus >= 400:
        raise EC2Error(xmlPayload)


__all__ = ['EC2Client']


class Instance(object):
    """An Amazon EC2 Instance.

    @attrib instance_id: The instance ID of this instance.
    @attrib instance_state: The state of this instance.
    """

    def __init__(self, instance_id, instance_state):
        self.instance_id = instance_id
        self.instance_state = instance_state


class EC2Client(object):
    """A client for EC2."""

    NS = '{http://ec2.amazonaws.com/doc/2008-12-01/}'

    def __init__(self, creds=None, query_factory=None):
        """Create an EC2Client.

        @param creds: Explicit credentials to use. If None, credentials are
            inferred as per txaws.credentials.AWSCredentials.
        """
        if creds is None:
            self.creds = credentials.AWSCredentials()
        else:
            self.creds = creds
        if query_factory is None:
            self.query_factory = Query
        else:
            self.query_factory = query_factory

    def describe_instances(self):
        """Describe current instances."""
        q = self.query_factory('DescribeInstances', self.creds)
        d = q.submit()
        return d.addCallback(self._parse_reservation)

    def _parse_reservation(self, xml_bytes):
        root = XML(xml_bytes)
        result = []
        # May be a more elegant way to do this:
        for reservation in root.find(self.NS + 'reservationSet'):
            for instance in reservation.find(self.NS + 'instancesSet'):
                instance_id = instance.findtext(self.NS + 'instanceId')
                instance_state = instance.find(
                    self.NS + 'instanceState').findtext(self.NS + 'name')
                result.append(Instance(instance_id, instance_state))
        return result

    def terminate_instances(self, *instance_ids):
        """Terminate some instances.
        
        @param instance_ids: The ids of the instances to terminate.
        @return: A deferred which on success gives an iterable of
            (id, old-state, new-state) tuples.
        """
        instanceset = {}
        for pos, instance_id in enumerate(instance_ids):
            instanceset["InstanceId.%d" % (pos+1)] = instance_id
        q = self.query_factory('TerminateInstances', self.creds, instanceset)
        d = q.submit()
        return d.addCallback(self._parse_terminate_instances)

    def _parse_terminate_instances(self, xml_bytes):
        root = XML(xml_bytes)
        result = []
        # May be a more elegant way to do this:
        for instance in root.find(self.NS + 'instancesSet'):
            instance_id = instance.findtext(self.NS + 'instance_id')
            previousState = instance.find(
                self.NS + 'previousState').findtext(self.NS + 'name')
            shutdownState = instance.find(
                self.NS + 'shutdownState').findtext(self.NS + 'name')
            result.append((instance_id, previousState, shutdownState))
        return result


class Query(object):
    """A query that may be submitted to EC2."""

    def __init__(self, action, creds, other_params=None, time_tuple=None,
                 factory=HTTPClientFactory):
        """Create a Query to submit to EC2."""
        # Require params (2008-12-01 API):
        # Version, SignatureVersion, SignatureMethod, Action, AWSAccessKeyId,
        # Timestamp || Expires, Signature, 
        self.params = {'Version': '2008-12-01',
            'SignatureVersion': '2',
            'SignatureMethod': 'HmacSHA1',
            'Action': action,
            'AWSAccessKeyId': creds.access_key,
            'Timestamp': iso8601time(time_tuple),
            }
        if other_params:
            self.params.update(other_params)
        self.method = 'GET'
        self.host = 'ec2.amazonaws.com'
        self.uri = '/'
        self.creds = creds
        self.factory = factory

    def canonical_query_params(self):
        """Return the canonical query params (used in signing)."""
        result = []
        for key, value in self.sorted_params():
            result.append('%s=%s' % (self.encode(key), self.encode(value)))
        return '&'.join(result)

    def encode(self, a_string):
        """Encode a_string as per the canonicalisation encoding rules.

        See the AWS dev reference page 90 (2008-12-01 version).
        :return: a_string encoded.
        """
        return quote(a_string, safe='~')

    def signing_text(self):
        """Return the text to be signed when signing the query."""
        result = "%s\n%s\n%s\n%s" % (self.method, self.host, self.uri,
            self.canonical_query_params())
        return result

    def sign(self):
        """Sign this query using its built in credentials.
        
        This prepares it to be sent, and should be done as the last step before
        submitting the query. Signing is done automatically - this is a public
        method to facilitate testing.
        """
        self.params['Signature'] = self.creds.sign(self.signing_text())

    def sorted_params(self):
        """Return the query params sorted appropriately for signing."""
        return sorted(self.params.items())

    def get_page(self, url, *args, **kwds):
        """
        Define our own get_page method so that we can easily override the
        factory when we need to.
        """
        return _makeGetterFactory(url, self.factory, *args, **kwds).deferred

    def submit(self):
        """Submit this query.

        @return: A deferred from get_page
        """
        self.sign()
        url = 'http://%s%s?%s' % (self.host, self.uri,
            self.canonical_query_params())
        deferred = self.get_page(url, method=self.method)
        deferred.addErrback(ec2_error_wrapper)
        return deferred
