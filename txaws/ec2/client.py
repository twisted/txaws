# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""EC2 client support."""

from base64 import b64encode
from urllib import quote

from twisted.web.client import getPage

from txaws.service import AWSService
from txaws.util import iso8601time, XML


__all__ = ['EC2Client']


class Reservation(object):
    """An Amazon EC2 Reservation.

    @attrib reservation_id: Unique ID of the reservation.
    @attrib owner_id: AWS Access Key ID of the user who owns the reservation. 
    @attrib groups: A list of security groups.
    """
    def __init__(self, reservation_id, owner_id, groups=None):
        self.reservation_id = reservation_id
        self.owner_id = owner_id
        self.groups = groups or []


class Instance(object):
    """An Amazon EC2 Instance.

    @attrib instance_id: The instance ID of this instance.
    @attrib instance_state: The state of this instance.
    """

    def __init__(self, instance_id, instance_state, reservation=None):
        self.instance_id = instance_id
        self.instance_state = instance_state
        self.reservation = reservation


class EC2Client(object):
    """A client for EC2."""

    name_space = '{http://ec2.amazonaws.com/doc/2008-12-01/}'

    def __init__(self, service=None, query_factory=None):
        """Create an EC2Client.

        @param service: Explicit service to use.
        """
        if service is None:
            self.service = AWSService()
        else:
            self.service = service
        if query_factory is None:
            self.query_factory = Query
        else:
            self.query_factory = query_factory

    def describe_instances(self):
        """Describe current instances."""
        q = self.query_factory('DescribeInstances', self.service)
        d = q.submit()
        return d.addCallback(self._parse_instances)

    def _parse_instances(self, xml_bytes):
        """
        Parse the reservations XML payload that is returned from an AWS
        describeInstances API call.
       
        Instead of returning the reservations as the "top-most" object, we
        return the object that most developers and their code will be
        interested in: the instances. In instances reservation is available on
        the instance object.
        """
        root = XML(xml_bytes)
        results = []
        # May be a more elegant way to do this:
        for reservation_data in root.find(self.name_space + 'reservationSet'):
            # Get the security group information.
            groups = []
            for group_data in reservation_data.find(
                self.name_space + 'groupSet'):
                group_id = group_data.findtext(self.name_space + 'groupId')
                groups.append(group_id)
            # Create a reservation object with the parsed data.
            reservation = Reservation(
                reservation_id=reservation_data.findtext(
                    self.name_space + 'reservationId'),
                owner_id=reservation_data.findtext(
                    self.name_space + 'ownerId'),
                groups=groups)
            # Get the list of instances.
            instances = []
            for instance_data in reservation_data.find(
                self.name_space + 'instancesSet'):
                instance_id = instance_data.findtext(
                    self.name_space + 'instanceId')
                instance_state = instance_data.find(
                    self.name_space + 'instanceState').findtext(
                        self.name_space + 'name')
                instance = Instance(instance_id, instance_state,
                                    reservation=reservation)
                instances.append(instance)
            results.extend(instances)
        return results

    def terminate_instances(self, *instance_ids):
        """Terminate some instances.
        
        @param instance_ids: The ids of the instances to terminate.
        @return: A deferred which on success gives an iterable of
            (id, old-state, new-state) tuples.
        """
        instanceset = {}
        for pos, instance_id in enumerate(instance_ids):
            instanceset["InstanceId.%d" % (pos+1)] = instance_id
        q = self.query_factory('TerminateInstances', self.service, instanceset)
        d = q.submit()
        return d.addCallback(self._parse_terminate_instances)

    def _parse_terminate_instances(self, xml_bytes):
        root = XML(xml_bytes)
        result = []
        # May be a more elegant way to do this:
        for instance in root.find(self.name_space + 'instancesSet'):
            instanceId = instance.findtext(self.name_space + 'instanceId')
            previousState = instance.find(
                self.name_space + 'previousState').findtext(
                    self.name_space + 'name')
            shutdownState = instance.find(
                self.name_space + 'shutdownState').findtext(
                    self.name_space + 'name')
            result.append((instanceId, previousState, shutdownState))
        return result


class Query(object):
    """A query that may be submitted to EC2."""

    def __init__(self, action, service, other_params=None, time_tuple=None):
        """Create a Query to submit to EC2."""
        # Require params (2008-12-01 API):
        # Version, SignatureVersion, SignatureMethod, Action, AWSAccessKeyId,
        # Timestamp || Expires, Signature, 
        self.params = {'Version': '2008-12-01',
            'SignatureVersion': '2',
            'SignatureMethod': 'HmacSHA1',
            'Action': action,
            'AWSAccessKeyId': service.access_key,
            'Timestamp': iso8601time(time_tuple),
            }
        if other_params:
            self.params.update(other_params)
        self.method = 'GET'
        self.host = 'ec2.amazonaws.com'
        self.uri = '/'
        self.service = service

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
        """Sign this query using its built in service.
        
        This prepares it to be sent, and should be done as the last step before
        submitting the query. Signing is done automatically - this is a public
        method to facilitate testing.
        """
        self.params['Signature'] = self.service.sign(self.signing_text())

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
