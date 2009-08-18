# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import os

from twisted.internet.defer import succeed

from txaws.credentials import AWSCredentials
from txaws.ec2 import client
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
                    <productCodes/>
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


class TestEC2Client(TXAWSTestCase):
    
    def test_init_no_creds(self):
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'foo'
        os.environ['AWS_ACCESS_KEY_ID'] = 'bar'
        ec2 = client.EC2Client()
        self.assertNotEqual(None, ec2.creds)

    def test_init_no_creds_non_available_errors(self):
        self.assertRaises(ValueError, client.EC2Client)

    def test_init_explicit_creds(self):
        creds = 'foo'
        ec2 = client.EC2Client(creds=creds)
        self.assertEqual(creds, ec2.creds)

    def check_parsed_instances(self, results):
        instance = results[0]
        self.assertEquals(instance.instance_id, "i-abcdef01")
        self.assertEquals(instance.instance_state, "running")
        reservation = instance.reservation
        self.assertEquals(reservation.reservation_id, "r-cf24b1a6")
        self.assertEquals(reservation.owner_id, "123456789012")
        group = reservation.groups[0]
        self.assertEquals(group, "default")

    def test_parse_reservation(self):
        ec2 = client.EC2Client(creds='foo')
        results = ec2._parse_instances(sample_describe_instances_result)
        self.check_parsed_instances(results)

    def test_describe_instances(self):
        class StubQuery(object):
            def __init__(stub, action, creds):
                self.assertEqual(action, 'DescribeInstances')
                self.assertEqual('foo', creds)
            def submit(self):
                return succeed(sample_describe_instances_result)
        ec2 = client.EC2Client(creds='foo', query_factory=StubQuery)
        d = ec2.describe_instances()
        d.addCallback(self.check_parsed_instances)
        return d

    def test_terminate_instances(self):
        class StubQuery(object):
            def __init__(stub, action, creds, other_params):
                self.assertEqual(action, 'TerminateInstances')
                self.assertEqual('foo', creds)
                self.assertEqual(
                    {'InstanceId.1': 'i-1234', 'InstanceId.2': 'i-5678'},
                    other_params)
            def submit(self):
                return succeed(sample_terminate_instances_result)
        ec2 = client.EC2Client(creds='foo', query_factory=StubQuery)
        d = ec2.terminate_instances('i-1234', 'i-5678')
        def check_transition(changes):
            self.assertEqual([('i-1234', 'running', 'shutting-down'),
                ('i-5678', 'shutting-down', 'shutting-down')], sorted(changes))
        return d


class TestQuery(TXAWSTestCase):

    def setUp(self):
        TXAWSTestCase.setUp(self)
        self.creds = AWSCredentials('foo', 'bar')

    def test_init_minimum(self):
        query = client.Query('DescribeInstances', self.creds)
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

    def test_init_requires_creds(self):
        self.assertRaises(TypeError, client.Query, None)

    def test_init_other_args_are_params(self):
        query = client.Query('DescribeInstances', self.creds,
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
        query = client.Query('DescribeInstances', self.creds,
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
        query = client.Query('DescribeInstances', self.creds)
        self.assertEqual(all_unreserved, query.encode(all_unreserved))

    def test_encode_space(self):
        """This may be just 'url encode', but the AWS manual isn't clear."""
        query = client.Query('DescribeInstances', self.creds)
        self.assertEqual('a%20space', query.encode('a space'))

    def test_canonical_query(self):
        query = client.Query('DescribeInstances', self.creds,
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
        query = client.Query('DescribeInstances', self.creds,
            time_tuple=(2007,11,12,13,14,15,0,0,0))
        signing_text = ('GET\nec2.amazonaws.com\n/\n'
            'AWSAccessKeyId=foo&Action=DescribeInstances&'
            'SignatureMethod=HmacSHA1&SignatureVersion=2&'
            'Timestamp=2007-11-12T13%3A14%3A15Z&Version=2008-12-01')
        self.assertEqual(signing_text, query.signing_text())

    def test_sign(self):
        query = client.Query('DescribeInstances', self.creds,
            time_tuple=(2007,11,12,13,14,15,0,0,0))
        query.sign()
        self.assertEqual('4hEtLuZo9i6kuG3TOXvRQNOrE/U=',
            query.params['Signature'])
