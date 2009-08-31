# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from datetime import datetime
import os

from twisted.internet.defer import succeed

from txaws.credentials import AWSCredentials
from txaws.ec2 import client
from txaws.service import AWSServiceEndpoint, EC2_ENDPOINT_US
from txaws.testing.base import TXAWSTestCase


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


sample_describe_volumes_result = """<?xml version="1.0"?>
<DescribeVolumesResponse xmlns="http://ec2.amazonaws.com/doc/2008-12-01/">
  <volumeSet>
    <item>
      <volumeId>vol-4282672b</volumeId>
      <size>800</size>
      <status>in-use</status>
      <createTime>2008-05-07T11:51:50.000Z</createTime>
      <attachmentSet>
        <item>
          <volumeId>vol-4282672b</volumeId>
          <instanceId>i-6058a509</instanceId>
          <size>800</size>
          <snapshotId>snap-12345678</snapshotId>
          <availabilityZone>us-east-1a</availabilityZone>
          <status>attached</status>
          <attachTime>2008-05-07T12:51:50.000Z</attachTime>
        </item>
      </attachmentSet>
    </item>
  </volumeSet>
</DescribeVolumesResponse>
"""


sample_describe_snapshots_result = """<?xml version="1.0"?>
<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2008-12-01">
  <snapshotSet>
    <item>
      <snapshotId>snap-78a54011</snapshotId>
      <volumeId>vol-4d826724</volumeId>
      <status>pending</status>
      <startTime>2008-05-07T12:51:50.000Z</startTime>
      <progress>80%</progress>
    </item>
  </snapshotSet>
</DescribeSnapshotsResponse>
"""


sample_create_volume_result = """<?xml version="1.0"?>
<CreateVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2008-12-01">
  <volumeId>vol-4d826724</volumeId>
  <size>800</size>
  <status>creating</status>
  <createTime>2008-05-07T11:51:50.000Z</createTime>
  <availabilityZone>us-east-1a</availabilityZone>
  <snapshotId></snapshotId>
</CreateVolumeResponse>
"""


sample_delete_volume_result = """<?xml version="1.0"?>
<DeleteVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2008-12-01">
  <return>true</return>
</DeleteVolumeResponse>
"""


sample_create_snapshot_result = """<?xml version="1.0"?>
<CreateSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2008-12-01">
  <snapshotId>snap-78a54011</snapshotId>
  <volumeId>vol-4d826724</volumeId>
  <status>pending</status>
  <startTime>2008-05-07T12:51:50.000Z</startTime>
  <progress></progress>
</CreateSnapshotResponse>
"""


sample_delete_snapshot_result = """<?xml version="1.0"?>
<DeleteSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2008-12-01">
  <return>true</return>
</DeleteSnapshotResponse>
"""


sample_attach_volume_result = """<?xml version="1.0"?>
<AttachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2008-12-01">
  <volumeId>vol-4d826724</volumeId>
  <instanceId>i-6058a509</instanceId>
  <device>/dev/sdh</device>
  <status>attaching</status>
  <attachTime>2008-05-07T11:51:50.000Z</attachTime>
</AttachVolumeResponse>
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
        self.assertNotEqual(None, ec2.creds)

    def test_init_no_creds_non_available_errors(self):
        self.assertRaises(ValueError, client.EC2Client)

    def test_init_explicit_creds(self):
        creds = AWSCredentials("foo", "bar")
        ec2 = client.EC2Client(creds=creds)
        self.assertEqual(creds, ec2.creds)

    def check_parsed_instances(self, results):
        instance = results[0]
        # check reservations
        reservation = instance.reservation
        self.assertEquals(reservation.reservation_id, "r-cf24b1a6")
        self.assertEquals(reservation.owner_id, "123456789012")
        # check groups
        group = reservation.groups[0]
        self.assertEquals(group, "default")
        # check instance
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
        creds = AWSCredentials("foo", "bar")
        ec2 = client.EC2Client(creds=creds)
        results = ec2._parse_instances(sample_describe_instances_result)
        self.check_parsed_instances(results)

    def test_describe_instances(self):
        class StubQuery(object):
            def __init__(stub, action, creds, endpoint):
                self.assertEqual(action, 'DescribeInstances')
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
            def submit(self):
                return succeed(sample_describe_instances_result)
        creds = AWSCredentials("foo", "bar")
        ec2 = client.EC2Client(creds, query_factory=StubQuery)
        d = ec2.describe_instances()
        d.addCallback(self.check_parsed_instances)
        return d

    def test_terminate_instances(self):
        class StubQuery(object):
            def __init__(stub, action, creds, endpoint, other_params):
                self.assertEqual(action, 'TerminateInstances')
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
                self.assertEqual(
                    {'InstanceId.1': 'i-1234', 'InstanceId.2': 'i-5678'},
                    other_params)
            def submit(self):
                return succeed(sample_terminate_instances_result)
        creds = AWSCredentials("foo", "bar")
        endpoint = AWSServiceEndpoint(uri=EC2_ENDPOINT_US)
        ec2 = client.EC2Client(creds=creds, endpoint=endpoint,
                               query_factory=StubQuery)
        d = ec2.terminate_instances('i-1234', 'i-5678')
        def check_transition(changes):
            self.assertEqual([('i-1234', 'running', 'shutting-down'),
                ('i-5678', 'shutting-down', 'shutting-down')], sorted(changes))
        return d


class QueryTestCase(TXAWSTestCase):

    def setUp(self):
        TXAWSTestCase.setUp(self)
        self.creds = AWSCredentials('foo', 'bar')
        self.endpoint = AWSServiceEndpoint(uri=EC2_ENDPOINT_US)

    def test_init_minimum(self):
        query = client.Query('DescribeInstances', self.creds, self.endpoint)
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
        query = client.Query('DescribeInstances', self.creds, self.endpoint,
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
        query = client.Query('DescribeInstances', self.creds, self.endpoint,
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
        query = client.Query('DescribeInstances', self.creds, self.endpoint)
        self.assertEqual(all_unreserved, query.encode(all_unreserved))

    def test_encode_space(self):
        """This may be just 'url encode', but the AWS manual isn't clear."""
        query = client.Query('DescribeInstances', self.creds, self.endpoint)
        self.assertEqual('a%20space', query.encode('a space'))

    def test_canonical_query(self):
        query = client.Query('DescribeInstances', self.creds, self.endpoint,
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
        query = client.Query('DescribeInstances', self.creds, self.endpoint,
            time_tuple=(2007,11,12,13,14,15,0,0,0))
        signing_text = ('GET\n%s\n/\n' % self.endpoint.host + 
            'AWSAccessKeyId=foo&Action=DescribeInstances&'
            'SignatureMethod=HmacSHA1&SignatureVersion=2&'
            'Timestamp=2007-11-12T13%3A14%3A15Z&Version=2008-12-01')
        self.assertEqual(signing_text, query.signing_text())

    def test_sign(self):
        query = client.Query('DescribeInstances', self.creds, self.endpoint,
            time_tuple=(2007,11,12,13,14,15,0,0,0))
        query.sign()
        self.assertEqual('JuCpwFA2H4OVF3Ql/lAQs+V6iMc=',
            query.params['Signature'])


class TestEBS(TXAWSTestCase):

    def check_parsed_volumes(self, volumes):
        self.assertEquals(len(volumes), 1)
        volume = volumes[0]
        self.assertEquals(volume.id, "vol-4282672b")
        self.assertEquals(volume.size, 800)
        self.assertEquals(volume.status, "in-use")
        create_time = datetime(2008, 05, 07, 11, 51, 50)
        self.assertEquals(volume.create_time, create_time)
        self.assertEquals(len(volume.attachments), 1)
        attachment = volume.attachments[0]
        self.assertEquals(attachment.instance_id, "i-6058a509")
        self.assertEquals(attachment.snapshot_id, "snap-12345678")
        self.assertEquals(attachment.availability_zone, "us-east-1a")
        self.assertEquals(attachment.status, "attached")
        attach_time = datetime(2008, 05, 07, 12, 51, 50)
        self.assertEquals(attachment.attach_time, attach_time)

    def test_describe_volumes(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "DescribeVolumes")
                self.assertEqual("foo", creds)
                self.assertEquals(params, {})

            def submit(self):
                return succeed(sample_describe_volumes_result)

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.describe_volumes()
        d.addCallback(self.check_parsed_volumes)
        return d

    def test_describe_specified_volumes(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "DescribeVolumes")
                self.assertEqual("foo", creds)
                self.assertEquals(
                    params,
                    {"VolumeId.1": "vol-4282672b"})

            def submit(self):
                return succeed(sample_describe_volumes_result)

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.describe_volumes("vol-4282672b")
        d.addCallback(self.check_parsed_volumes)
        return d

    def check_parsed_snapshots(self, snapshots):
        self.assertEquals(len(snapshots), 1)
        snapshot = snapshots[0]
        self.assertEquals(snapshot.id, "snap-78a54011")
        self.assertEquals(snapshot.volume_id, "vol-4d826724")
        self.assertEquals(snapshot.status, "pending")
        start_time = datetime(2008, 05, 07, 12, 51, 50)
        self.assertEquals(snapshot.start_time, start_time)
        self.assertEquals(snapshot.progress, 0.8)

    def test_describe_snapshots(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "DescribeSnapshots")
                self.assertEqual("foo", creds)
                self.assertEquals(params, {})

            def submit(self):
                return succeed(sample_describe_snapshots_result)

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.describe_snapshots()
        d.addCallback(self.check_parsed_snapshots)
        return d

    def test_describe_specified_snapshots(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "DescribeSnapshots")
                self.assertEqual("foo", creds)
                self.assertEquals(
                    params,
                    {"SnapshotId.1": "snap-78a54011"})

            def submit(self):
                return succeed(sample_describe_snapshots_result)

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.describe_snapshots("snap-78a54011")
        d.addCallback(self.check_parsed_snapshots)
        return d

    def test_create_volume(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "CreateVolume")
                self.assertEqual("foo", creds)
                self.assertEqual(
                    {"AvailabilityZone": "us-east-1", "Size": "800"},
                    params)

            def submit(self):
                return succeed(sample_create_volume_result)

        def check_parsed_volume(volume):
            self.assertEquals(volume.id, "vol-4d826724")
            self.assertEquals(volume.size, 800)
            create_time = datetime(2008, 05, 07, 11, 51, 50)
            self.assertEquals(volume.create_time, create_time)

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.create_volume("us-east-1", size=800)
        d.addCallback(check_parsed_volume)
        return d

    def test_create_volume_with_snapshot(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "CreateVolume")
                self.assertEqual("foo", creds)
                self.assertEqual(
                    {"AvailabilityZone": "us-east-1",
                     "SnapshotId": "snap-12345678"},
                    params)

            def submit(self):
                return succeed(sample_create_volume_result)

        def check_parsed_volume(volume):
            self.assertEquals(volume.id, "vol-4d826724")
            self.assertEquals(volume.size, 800)
            create_time = datetime(2008, 05, 07, 11, 51, 50)
            self.assertEquals(volume.create_time, create_time)

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.create_volume("us-east-1", snapshot_id="snap-12345678")
        d.addCallback(check_parsed_volume)
        return d

    def test_create_volume_no_params(self):
        ec2 = client.EC2Client(creds="foo")
        error = self.assertRaises(ValueError, ec2.create_volume, "us-east-1")
        self.assertEquals(
            str(error),
            "Please provide either size or snapshot_id")

    def test_create_volume_both_params(self):
        ec2 = client.EC2Client(creds="foo")
        error = self.assertRaises(ValueError, ec2.create_volume, "us-east-1",
                                  size=800, snapshot_id="snap-12345678")
        self.assertEquals(
            str(error),
            "Please provide either size or snapshot_id")

    def test_delete_volume(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "DeleteVolume")
                self.assertEqual("foo", creds)
                self.assertEqual(
                    {"VolumeId": "vol-4282672b"},
                    params)

            def submit(self):
                return succeed(sample_delete_volume_result)

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.delete_volume("vol-4282672b")
        d.addCallback(self.assertEquals, True)
        return d

    def test_create_snapshot(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "CreateSnapshot")
                self.assertEqual("foo", creds)
                self.assertEqual(
                    {"VolumeId": "vol-4d826724"},
                    params)

            def submit(self):
                return succeed(sample_create_snapshot_result)

        def check_parsed_snapshot(snapshot):
            self.assertEquals(snapshot.id, "snap-78a54011")
            self.assertEquals(snapshot.volume_id, "vol-4d826724")
            self.assertEquals(snapshot.status, "pending")
            start_time = datetime(2008, 05, 07, 12, 51, 50)
            self.assertEquals(snapshot.start_time, start_time)
            self.assertEquals(snapshot.progress, 0)

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.create_snapshot("vol-4d826724")
        d.addCallback(check_parsed_snapshot)
        return d

    def test_delete_snapshot(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "DeleteSnapshot")
                self.assertEqual("foo", creds)
                self.assertEqual(
                    {"SnapshotId": "snap-78a54011"},
                    params)

            def submit(self):
                return succeed(sample_delete_snapshot_result)

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.delete_snapshot("snap-78a54011")
        d.addCallback(self.assertEquals, True)
        return d

    def test_attach_volume(self):

        class StubQuery(object):
            def __init__(stub, action, creds, params):
                self.assertEqual(action, "AttachVolume")
                self.assertEqual("foo", creds)
                self.assertEqual(
                    {"VolumeId": "vol-4d826724", "InstanceId": "i-6058a509",
                     "Device": "/dev/sdh"},
                    params)

            def submit(self):
                return succeed(sample_attach_volume_result)

        def check_parsed_response(response):
            self.assertEquals(
                response,
                {"status": "attaching",
                 "attach_time": datetime(2008, 05, 07, 11, 51, 50)})

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.attach_volume("vol-4d826724", "i-6058a509", "/dev/sdh")
        d.addCallback(check_parsed_response)
        return d
