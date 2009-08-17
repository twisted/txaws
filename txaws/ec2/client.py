# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""EC2 client support."""

from base64 import b64encode
from urllib import quote

from twisted.web.client import getPage

from txaws import credentials
from txaws.util import iso8601time, XML


__all__ = ['EC2Client']


class Instance(object):
    """An Amazon EC2 Instance.

    @attrib instanceId: The instance ID of this instance.
    @attrib instanceState: The state of this instance.
    """
    def __init__(self, instanceId, instanceState):
        self.instanceId = instanceId
        self.instanceState = instanceState


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
        return d.addCallback(self._parse_Reservation)

    def _parse_Reservation(self, xml_bytes):
        root = XML(xml_bytes)
        result = []
        # May be a more elegant way to do this:
        for reservation in root.find(self.NS + 'reservationSet'):
            for instance in reservation.find(self.NS + 'instancesSet'):
                instanceId = instance.findtext(self.NS + 'instanceId')
                instanceState = instance.find(
                    self.NS + 'instanceState').findtext(self.NS + 'name')
                result.append(Instance(instanceId, instanceState))
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
            instanceId = instance.findtext(self.NS + 'instanceId')
            previousState = instance.find(
                self.NS + 'previousState').findtext(self.NS + 'name')
            shutdownState = instance.find(
                self.NS + 'shutdownState').findtext(self.NS + 'name')
            result.append((instanceId, previousState, shutdownState))
        return result


class Query(object):
    """A query that may be submitted to EC2."""

    def __init__(self, action, creds, other_params=None, time_tuple=None):
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

    def submit(self):
        """Submit this query.

        :return: A deferred from twisted.web.client.getPage
        """
        self.sign()
        url = 'http://%s%s?%s' % (self.host, self.uri,
            self.canonical_query_params())
        return getPage(url, method=self.method)
