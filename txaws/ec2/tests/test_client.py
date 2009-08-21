# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import os

from twisted.internet.defer import succeed

from txaws.ec2 import client
from txaws.ec2.service import EC2Service, US_EC2_HOST
from txaws.tests import TXAWSTestCase


sample_describe_instances_result = """<?xml version="1.0"?>
<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2008-12-01/">
    <requestId>52b4c730-f29f-498d-94c1-91efb75994cc</requestId>
    <reservationSet>
        <item>
            <reservationId>r-cf24b1a6</reservationId>
            <ownerId>123456789012</ownerId>
            <groupSet>
                <item>
                    <groupId>default</groupId>
                </item>
            </groupSet>
            <instancesSet>
                <item>
                    <instanceId>i-abcdef01</instanceId>
                    <imageId>ami-12345678</imageId>
                    <instanceState>
                        <code>16</code>
                        <name>running</name>
                    </instanceState>
                    <privateDnsName>domU-12-31-39-03-15-11.compute-1.internal</privateDnsName>
                    <dnsName>ec2-75-101-245-65.compute-1.amazonaws.com</dnsName>
                    <reason/>
                    <keyName>keyname</keyName>
                    <amiLaunchIndex>0</amiLaunchIndex>
                    <productCodesSet>
                        <item>
                            <productCode>774F4FF8</productCode>
                        </item>
                    </productCodesSet>

                    <instanceType>c1.xlarge</instanceType>
                    <launchTime>2009-04-27T02:23:18.000Z</launchTime>
                    <placement>
                        <availabilityZone>us-east-1c</availabilityZone>
                    </placement>
                    <kernelId>aki-b51cf9dc</kernelId>
                    <ramdiskId>ari-b31cf9da</ramdiskId>
                </item>
            </instancesSet>
        </item>
    </reservationSet>
</DescribeInstancesResponse>
"""


sample_terminate_instances_result = """<?xml version="1.0"?>
<TerminateInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2008-12-01/">
  <instancesSet>
    <item>
      <instanceId>i-1234</instanceId>
      <shutdownState>
        <code>32</code>
        <name>shutting-down</name>
      </shutdownState>
      <previousState>
        <code>16</code>
        <name>running</name>
      </previousState>
    </item>
    <item>
      <instanceId>i-5678</instanceId>
      <shutdownState>
        <code>32</code>
        <name>shutting-down</name>
      </shutdownState>
      <previousState>
        <code>32</code>
        <name>shutting-down</name>
      </previousState>
    </item>
  </instancesSet>
</TerminateInstancesResponse>
"""


class ReservationTestCase(TXAWSTestCase):

    def test_reservation_creation(self):
        reservation = client.Reservation(
            "id1", "owner", groups=["one", "two"])
        self.assertEquals(reservation.reservation_id, "id1")
        self.assertEquals(reservation.owner_id, "owner")
        self.assertEquals(reservation.groups, ["one", "two"])


class InstanceTestCase(TXAWSTestCase):

    def test_instance_creation(self):
        instance = client.Instance(
            "id1", "running", "type", "id2", "dns1", "dns2", "key", "ami",
            "time", "placement", ["prod1", "prod2"], "id3", "id4")
        self.assertEquals(instance.instance_id, "id1")
        self.assertEquals(instance.instance_state, "running")
        self.assertEquals(instance.instance_type, "type")
        self.assertEquals(instance.image_id, "id2")
        self.assertEquals(instance.private_dns_name, "dns1")
        self.assertEquals(instance.dns_name, "dns2")
        self.assertEquals(instance.key_name, "key")
        self.assertEquals(instance.ami_launch_index, "ami")
        self.assertEquals(instance.launch_time, "time")
        self.assertEquals(instance.placement, "placement")
        self.assertEquals(instance.product_codes, ["prod1", "prod2"])
        self.assertEquals(instance.kernel_id, "id3")
        self.assertEquals(instance.ramdisk_id, "id4")


class EC2ClientTestCase(TXAWSTestCase):
    
    def test_init_no_creds(self):
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'foo'
        os.environ['AWS_ACCESS_KEY_ID'] = 'bar'
        ec2 = client.EC2Client()
        self.assertNotEqual(None, ec2.service)

    def test_init_no_creds_non_available_errors(self):
        self.assertRaises(ValueError, client.EC2Client)

    def test_init_explicit_service(self):
        service = EC2Service("foo", "bar")
        ec2 = client.EC2Client(service=service)
        self.assertEqual(service, ec2.service)

    def check_parsed_instances(self, results):
        instance = results[0]
        self.assertEquals(instance.instance_id, "i-abcdef01")
        self.assertEquals(instance.instance_state, "running")
        reservation = instance.reservation
        self.assertEquals(reservation.reservation_id, "r-cf24b1a6")
        self.assertEquals(reservation.owner_id, "123456789012")
        group = reservation.groups[0]
        self.assertEquals(group, "default")
        self.assertEquals(instance.instance_id, "i-abcdef01")
        self.assertEquals(instance.instance_state, "running")
        self.assertEquals(instance.instance_type, "c1.xlarge")
        self.assertEquals(instance.image_id, "ami-12345678")
        self.assertEquals(
            instance.private_dns_name,
            "domU-12-31-39-03-15-11.compute-1.internal")
        self.assertEquals(
            instance.dns_name,
            "ec2-75-101-245-65.compute-1.amazonaws.com")
        self.assertEquals(instance.key_name, "keyname")
        self.assertEquals(instance.ami_launch_index, "0")
        self.assertEquals(instance.launch_time, "2009-04-27T02:23:18.000Z")
        self.assertEquals(instance.placement, "us-east-1c")
        self.assertEquals(instance.product_codes, ["774F4FF8"])
        self.assertEquals(instance.kernel_id, "aki-b51cf9dc")
        self.assertEquals(instance.ramdisk_id, "ari-b31cf9da")


    def test_parse_reservation(self):
        service = EC2Service("foo", "bar")
        ec2 = client.EC2Client(service=service)
        results = ec2._parse_instances(sample_describe_instances_result)
        self.check_parsed_instances(results)

    def test_describe_instances(self):
        class StubQuery(object):
            def __init__(stub, action, service):
                self.assertEqual(action, 'DescribeInstances')
                self.assertEqual(service.access_key, "foo")
                self.assertEqual(service.secret_key, "bar")
            def submit(self):
                return succeed(sample_describe_instances_result)
        service = EC2Service("foo", "bar")
        ec2 = client.EC2Client(service, query_factory=StubQuery)
        d = ec2.describe_instances()
        d.addCallback(self.check_parsed_instances)
        return d

    def test_terminate_instances(self):
        class StubQuery(object):
            def __init__(stub, action, service, other_params):
                self.assertEqual(action, 'TerminateInstances')
                self.assertEqual(service.access_key, "foo")
                self.assertEqual(service.secret_key, "bar")
                self.assertEqual(
                    {'InstanceId.1': 'i-1234', 'InstanceId.2': 'i-5678'},
                    other_params)
            def submit(self):
                return succeed(sample_terminate_instances_result)
        service = EC2Service("foo", "bar")
        ec2 = client.EC2Client(service=service, query_factory=StubQuery)
        d = ec2.terminate_instances('i-1234', 'i-5678')
        def check_transition(changes):
            self.assertEqual([('i-1234', 'running', 'shutting-down'),
                ('i-5678', 'shutting-down', 'shutting-down')], sorted(changes))
        return d


class QueryTestCase(TXAWSTestCase):

    def setUp(self):
        TXAWSTestCase.setUp(self)
        self.service = EC2Service('foo', 'bar')

    def test_init_minimum(self):
        query = client.Query('DescribeInstances', self.service)
        self.assertTrue('Timestamp' in query.params)
        del query.params['Timestamp']
        self.assertEqual(
            {'AWSAccessKeyId': 'foo',
             'Action': 'DescribeInstances',
             'SignatureMethod': 'HmacSHA1',
             'SignatureVersion': '2',
             'Version': '2008-12-01'},
            query.params)

    def test_init_requires_action(self):
        self.assertRaises(TypeError, client.Query)

    def test_init_requires_service_with_creds(self):
        self.assertRaises(TypeError, client.Query, None)

    def test_init_other_args_are_params(self):
        query = client.Query('DescribeInstances', self.service,
            {'InstanceId.0': '12345'},
            time_tuple=(2007,11,12,13,14,15,0,0,0))
        self.assertEqual(
            {'AWSAccessKeyId': 'foo',
             'Action': 'DescribeInstances',
             'InstanceId.0': '12345',
             'SignatureMethod': 'HmacSHA1',
             'SignatureVersion': '2',
             'Timestamp': '2007-11-12T13:14:15Z',
             'Version': '2008-12-01'},
            query.params)

    def test_sorted_params(self):
        query = client.Query('DescribeInstances', self.service,
            {'fun': 'games'},
            time_tuple=(2007,11,12,13,14,15,0,0,0))
        self.assertEqual([
            ('AWSAccessKeyId', 'foo'),
            ('Action', 'DescribeInstances'),
            ('SignatureMethod', 'HmacSHA1'),
            ('SignatureVersion', '2'),
            ('Timestamp', '2007-11-12T13:14:15Z'),
            ('Version', '2008-12-01'),
            ('fun', 'games'),
            ], query.sorted_params())

    def test_encode_unreserved(self):
        all_unreserved = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            'abcdefghijklmnopqrstuvwxyz0123456789-_.~')
        query = client.Query('DescribeInstances', self.service)
        self.assertEqual(all_unreserved, query.encode(all_unreserved))

    def test_encode_space(self):
        """This may be just 'url encode', but the AWS manual isn't clear."""
        query = client.Query('DescribeInstances', self.service)
        self.assertEqual('a%20space', query.encode('a space'))

    def test_canonical_query(self):
        query = client.Query('DescribeInstances', self.service,
            {'fu n': 'g/ames', 'argwithnovalue':'',
             'InstanceId.1': 'i-1234'},
            time_tuple=(2007,11,12,13,14,15,0,0,0))
        expected_query = ('AWSAccessKeyId=foo&Action=DescribeInstances'
            '&InstanceId.1=i-1234'
            '&SignatureMethod=HmacSHA1&SignatureVersion=2&'
            'Timestamp=2007-11-12T13%3A14%3A15Z&Version=2008-12-01&'
            'argwithnovalue=&fu%20n=g%2Fames')
        self.assertEqual(expected_query, query.canonical_query_params())

    def test_signing_text(self):
        query = client.Query('DescribeInstances', self.service,
            time_tuple=(2007,11,12,13,14,15,0,0,0))
        signing_text = ('GET\n%s\n/\n' % US_EC2_HOST + 
            'AWSAccessKeyId=foo&Action=DescribeInstances&'
            'SignatureMethod=HmacSHA1&SignatureVersion=2&'
            'Timestamp=2007-11-12T13%3A14%3A15Z&Version=2008-12-01')
        self.assertEqual(signing_text, query.signing_text())

    def test_sign(self):
        query = client.Query('DescribeInstances', self.service,
            time_tuple=(2007,11,12,13,14,15,0,0,0))
        query.sign()
        self.assertEqual('JuCpwFA2H4OVF3Ql/lAQs+V6iMc=',
            query.params['Signature'])
