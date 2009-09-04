# -*- coding: utf-8 -*-
# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Copyright (C) 2009 Thomas Hervé <thomas@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from datetime import datetime
import os

from twisted.internet import reactor
from twisted.internet.defer import succeed, Deferred
from twisted.python.filepath import FilePath
from twisted.web import server, static, util
from twisted.web.client import HTTPPageGetter, HTTPClientFactory
from twisted.web.http import Request, HTTPChannel, HTTPClient
from twisted.protocols.policies import WrappingFactory
from twisted.protocols.loopback import loopbackAsync
from twisted.test.proto_helpers import StringTransport

from txaws.credentials import AWSCredentials
from txaws.ec2 import client
from txaws.ec2.exception import EC2Error
from txaws.ec2.tests.payload import (
    sample_describe_instances_result, sample_terminate_instances_result,
    sample_ec2_error_message)
from txaws.service import AWSServiceEndpoint, EC2_ENDPOINT_US
from txaws.testing import payload
from txaws.testing.base import TXAWSTestCase


class FakeHTTPHandler(Request):
    status = 200

    def process(self):
        self.content.seek(0, 0)
        data = self.content.read()
        length = self.getHeader('Content-Length')
        request = "'''\n"+str(length)+"\n"+data+"'''\n"
        self.setResponseCode(self.status)
        self.setHeader("Request", self.uri)
        self.setHeader("Command", self.method)
        self.setHeader("Version", self.clientproto)
        self.setHeader("Content-Length", len(request))
        self.write(request)
        self.finish()


class FourOhHTTPHandler(FakeHTTPHandler):
    status = 400


class FiveOhHTTPHandler(FakeHTTPHandler):
    status = 500


class FakeHTTPPageGetter(HTTPPageGetter):

    transport = StringTransport


class FakeHTTPFactory(HTTPClientFactory):
#class FakeHTTPFactory(HTTPClient):

    #protocol = FakeHTTPPageGetter
    #test_payload = ""
    def __init__(self, test_payload, method=None):
        self.test_payload = test_payload
        self.method = method
        self.wasStarted = None
        self.wasStopped = None
        self.connectionFailed = None
        self.deferred = Deferred()

    def connectionMade(self):
        content_length = len(self.test_payload)
        self.sendCommand("GET", "/dummy")
        self.sendHeader("Content-Length", content_length)
        self.endHeaders()
        self.transport.write(self.test_payload)
        self.deferred.success("success")
"""
    def doStart(self):
        self.wasStarted = True

    def doStop(self):
        self.wasStopped = True

    def startedConnecting(self, *args):
        pass

    def clientConnectionFailed(self, *args):
        self.connectionFailed = True
        self.deferred.fail("failed")
"""

class FactoryWrapper(object):

    def __init__(self, payload):
        self.payload = payload

    def __call__(self, url, *args, **kwds):
        FakeHTTPFactory.test_payload = self.payload
        return FakeHTTPFactory(url, *args, **kwds)


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

    def check_parsed_instances_required(self, results):
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
        self.assertEquals(instance.key_name, None)
        self.assertEquals(instance.ami_launch_index, None)
        self.assertEquals(instance.launch_time, "2009-04-27T02:23:18.000Z")
        self.assertEquals(instance.placement, "us-east-1c")
        self.assertEquals(instance.product_codes, [])
        self.assertEquals(instance.kernel_id, None)
        self.assertEquals(instance.ramdisk_id, None)

    def test_parse_reservation(self):
        creds = AWSCredentials("foo", "bar")
        ec2 = client.EC2Client(creds=creds)
        results = ec2._parse_instances(
            payload.sample_describe_instances_result)
        self.check_parsed_instances(results)

    def test_describe_instances(self):
        class StubQuery(object):
            def __init__(stub, action, creds, endpoint):
                self.assertEqual(action, 'DescribeInstances')
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
            def submit(self):
                return succeed(payload.sample_describe_instances_result)
        creds = AWSCredentials("foo", "bar")
        ec2 = client.EC2Client(creds, query_factory=StubQuery)
        d = ec2.describe_instances()

        def check_instances(reservation):
            self.assertEqual(1, len(reservation))
            self.assertEqual('i-abcdef01', reservation[0].instance_id)
            self.assertEqual('running', reservation[0].instance_state)
        d.addCallback(self.check_parsed_instances)
        return d

    def test_describe_instances_required(self):
        class StubQuery(object):
            def __init__(stub, action, creds, endpoint):
                self.assertEqual(action, 'DescribeInstances')
                self.assertEqual(creds.access_key, "foo")
                self.assertEqual(creds.secret_key, "bar")
            def submit(self):
                return succeed(
                    payload.sample_required_describe_instances_result)
        creds = AWSCredentials("foo", "bar")
        ec2 = client.EC2Client(creds, query_factory=StubQuery)
        d = ec2.describe_instances()
        d.addCallback(self.check_parsed_instances_required)
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
                return succeed(payload.sample_terminate_instances_result)
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
        self.twisted_client_test_setup()
        self.cleanupServerConnections = 0

    def tearDown(self):
        """Copied from twisted.web.test.test_webclient."""
        # If the test indicated it might leave some server-side connections
        # around, clean them up.
        connections = self.wrapper.protocols.keys()
        # If there are fewer server-side connections than requested,
        # that's okay.  Some might have noticed that the client closed
        # the connection and cleaned up after themselves.
        for n in range(min(len(connections), self.cleanupServerConnections)):
            proto = connections.pop()
            #msg("Closing %r" % (proto,))
            proto.transport.loseConnection()
        if connections:
            #msg("Some left-over connections; this test is probably buggy.")
            pass
        return self.port.stopListening()

    def _listen(self, site):
        return reactor.listenTCP(0, site, interface="127.0.0.1")

    def twisted_client_test_setup(self):
        name = self.mktemp()
        os.mkdir(name)
        FilePath(name).child("file").setContent("0123456789")
        resource = static.File(name)
        resource.putChild("redirect", util.Redirect("/file"))
        self.site = server.Site(resource, timeout=None)
        self.wrapper = WrappingFactory(self.site)
        self.port = self._listen(self.wrapper)
        self.portno = self.port.getHost().port


    def get_url(self, path):
        return "http://127.0.0.1:%d/%s" % (self.portno, path)

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

    def test_get_page(self):
        """Copied from twisted.web.test.test_webclient."""
        factory_wrapper = FactoryWrapper(sample_ec2_error_message)
        query = client.Query(
            'DummyQuery', self.creds, self.endpoint,
            time_tuple=(2009,8,17,13,14,15,0,0,0),
            factory=factory_wrapper)
        deferred = query.get_page(self.get_url("file"))
        deferred.addCallback(self.assertEquals, "0123456789")
        return deferred

    def XXX_test_submit_400_raise_error(self):
        """A 4xx response status from EC2 should raise a txAWS EC2Error."""
        factory_wrapper = FactoryWrapper(sample_ec2_error_message)

        def _checkError(x):
            import pdb;pdb.set_trace()

        query = client.Query(
            'BadQuery', self.creds, self.endpoint,
            time_tuple=(2009,8,15,13,14,15,0,0,0),
            factory=factory_wrapper)
        return self.assertFailure(query.submit(), EC2Error)

    def skip_test_submit_400_check_payload_and_status(self):
        """
        """
        factory_wrapper = FactoryWrapper(sample_ec2_error_message)

        def _checkError(error):
            error_data = error.value.errors[0]
            self.assertEquals(error_data["Code"], "FakeRequestCode")
            self.assertEquals(error_data["Message"],
                              "Request has fakely erred.")

        query = client.Query(
            'BadQuery', self.creds, time_tuple=(2009,8,15,13,14,15,0,0,0),
            factory=factory_wrapper)
        deferred = query.submit()
        deferred.addErrback(_checkError)
        return deferred

    def test_submit_500(self):
        """
        A 5xx response status from EC2 should raise the original Twisted
        exception.
        """

class ClientTestCaseBase(TXAWSTestCase):

    def test_400_payload(self):
        def check_status(version, status, message):
            self.assertEquals(status, "400")

        def check_payload(data):
            expected = "'''\n%s\n%s'''\n" % (
                len(sample_ec2_error_message), sample_ec2_error_message)
            self.assertEquals(data, expected)
        server = HTTPChannel()
        server.requestFactory = FourOhHTTPHandler
        client = FakeHTTPFactory(sample_ec2_error_message)
        client.handleResponse = check_payload
        client.handleStatus = check_status
        return loopbackAsync(server, client)

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
                return succeed(payload.sample_describe_volumes_result)

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
                return succeed(payload.sample_describe_volumes_result)

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
                return succeed(payload.sample_describe_snapshots_result)

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
                return succeed(payload.sample_describe_snapshots_result)

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
                return succeed(payload.sample_create_volume_result)

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
                return succeed(payload.sample_create_volume_result)

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
                return succeed(payload.sample_delete_volume_result)

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
                return succeed(payload.sample_create_snapshot_result)

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
                return succeed(payload.sample_delete_snapshot_result)

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
                return succeed(payload.sample_attach_volume_result)

        def check_parsed_response(response):
            self.assertEquals(
                response,
                {"status": "attaching",
                 "attach_time": datetime(2008, 05, 07, 11, 51, 50)})

        ec2 = client.EC2Client(creds="foo", query_factory=StubQuery)
        d = ec2.attach_volume("vol-4d826724", "i-6058a509", "/dev/sdh")
        d.addCallback(check_parsed_response)
        return d
