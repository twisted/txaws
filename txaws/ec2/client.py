# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""EC2 client support."""

from base64 import b64encode
from urllib import quote

from twisted.web.client import getPage

from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint
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
    @attrib instance_state: The current state of this instance.
    @attrib instance_type: The instance type.
    @attrib image_id: Image ID of the AMI used to launch the instance.
    @attrib private_dns_name: The private DNS name assigned to the instance.
        This DNS name can only be used inside the Amazon EC2 network. This
        element remains empty until the instance enters a running state.
    @attrib dns_name: The public DNS name assigned to the instance. This DNS
        name is contactable from outside the Amazon EC2 network. This element
        remains empty until the instance enters a running state.
    @attrib key_name: If this instance was launched with an associated key
        pair, this displays the key pair name.
    @attrib ami_launch_index: The AMI launch index, which can be used to find
        this instance within the launch group.
    @attrib product_codes: Product codes attached to this instance.
    @attrib launch_time: The time the instance launched.
    @attrib placement: The location where the instance launched.
    @attrib kernel_id: Optional. Kernel associated with this instance.
    @attrib ramdisk_id: Optional. RAM disk associated with this instance.
    """
    def __init__(self, instance_id, instance_state, instance_type="",
                 image_id="", private_dns_name="", dns_name="", key_name="",
                 ami_launch_index="", launch_time="", placement="",
                 product_codes=[], kernel_id=None, ramdisk_id=None,
                 reservation=None):
        self.instance_id = instance_id
        self.instance_state = instance_state
        self.instance_type = instance_type
        self.image_id = image_id
        self.private_dns_name = private_dns_name
        self.dns_name = dns_name
        self.key_name = key_name
        self.ami_launch_index = ami_launch_index
        self.launch_time = launch_time
        self.placement = placement
        self.product_codes = product_codes
        self.kernel_id = kernel_id
        self.ramdisk_id = ramdisk_id
        self.reservation = reservation


class EC2Client(object):
    """A client for EC2."""

    name_space = '{http://ec2.amazonaws.com/doc/2008-12-01/}'

    def __init__(self, creds=None, endpoint=None, query_factory=None):
        """Create an EC2Client.

        @param creds: User authentication credentials to use.
        @param endpoint: The service endpoint URI.
        @param query_factory: The class or function that produces a query
            object for making requests to the EC2 service.
        """
        self.creds = creds or AWSCredentials()
        self.endpoint = endpoint or AWSServiceEndpoint()
        if query_factory is None:
            self.query_factory = Query
        else:
            self.query_factory = query_factory

    def describe_instances(self):
        """Describe current instances."""
        q = self.query_factory('DescribeInstances', self.creds, self.endpoint)
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
                instance_type = instance_data.findtext(
                    self.name_space + 'instanceType')
                image_id = instance_data.findtext(self.name_space + 'imageId')
                private_dns_name = instance_data.findtext(
                    self.name_space + 'privateDnsName')
                dns_name = instance_data.findtext(self.name_space + 'dnsName')
                key_name = instance_data.findtext(self.name_space + 'keyName')
                ami_launch_index = instance_data.findtext(
                    self.name_space + 'amiLaunchIndex')
                launch_time = instance_data.findtext(
                    self.name_space + 'launchTime')
                placement = instance_data.find(
                    self.name_space + 'placement').findtext(
                        self.name_space + 'availabilityZone')
                products = []
                for product_data in instance_data.find(
                    self.name_space + 'productCodesSet'):
                    product_code = product_data.findtext(
                        self.name_space + 'productCode')
                    products.append(product_code)
                kernel_id = instance_data.findtext(
                    self.name_space + 'kernelId')
                ramdisk_id = instance_data.findtext(
                    self.name_space + 'ramdiskId')
                instance = Instance(
                    instance_id, instance_state, instance_type, image_id,
                    private_dns_name, dns_name, key_name, ami_launch_index,
                    launch_time, placement, products, kernel_id, ramdisk_id,
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
        q = self.query_factory('TerminateInstances', self.creds, self.endpoint,
                               instanceset)
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

    def __init__(self, action, creds, endpoint, other_params=None,
                 time_tuple=None):
        """Create a Query to submit to EC2."""
        self.creds = creds
        self.endpoint = endpoint
        # Require params (2008-12-01 API):
        # Version, SignatureVersion, SignatureMethod, Action, AWSAccessKeyId,
        # Timestamp || Expires, Signature, 
        self.params = {
            'Version': '2008-12-01',
            'SignatureVersion': '2',
            'SignatureMethod': 'HmacSHA1',
            'Action': action,
            'AWSAccessKeyId': self.creds.access_key,
            'Timestamp': iso8601time(time_tuple),
            }
        if other_params:
            self.params.update(other_params)

    def canonical_query_params(self):
        """Return the canonical query params (used in signing)."""
        result = []
        for key, value in self.sorted_params():
            result.append('%s=%s' % (self.encode(key), self.encode(value)))
        return '&'.join(result)

    def encode(self, a_string):
        """Encode a_string as per the canonicalisation encoding rules.

        See the AWS dev reference page 90 (2008-12-01 version).
        @return: a_string encoded.
        """
        return quote(a_string, safe='~')

    def signing_text(self):
        """Return the text to be signed when signing the query."""
        result = "%s\n%s\n%s\n%s" % (self.endpoint.method, self.endpoint.host,
                                     self.endpoint.path,
                                     self.canonical_query_params())
        return result

    def sign(self):
        """Sign this query using its built in creds.
        
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

        @return: A deferred from twisted.web.client.getPage
        """
        self.sign()
        url = "%s?%s" % (self.endpoint.get_uri(), 
                         self.canonical_query_params())
        return getPage(url, method=self.endpoint.method)
