# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""EC2 client support."""

from datetime import datetime
from urllib import quote

from twisted.web.client import getPage

from txaws import credentials
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


class Volume(object):
    """An EBS volume instance."""

    def __init__(self, id, size, status, create_time):
        self.id = id
        self.size = size
        self.status = status
        self.create_time = create_time
        self.attachments = []


class Attachment(object):
    """An attachment of a L{Volume}."""

    def __init__(self, instance_id, snapshot_id, availability_zone, status,
                 attach_time):
        self.instance_id = instance_id
        self.snapshot_id = snapshot_id
        self.availability_zone = availability_zone
        self.status = status
        self.attach_time = attach_time


class Snapshot(object):
    """A snapshot of a L{Volume}."""

    def __init__(self, id, volume_id, status, start_time, progress):
        self.id = id
        self.volume_id = volume_id
        self.status = status
        self.start_time = start_time
        self.progress = progress


class EC2Client(object):
    """A client for EC2."""

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
        for reservation_data in root.find("reservationSet"):
            # Get the security group information.
            groups = []
            for group_data in reservation_data.find("groupSet"):
                group_id = group_data.findtext("groupId")
                groups.append(group_id)
            # Create a reservation object with the parsed data.
            reservation = Reservation(
                reservation_id=reservation_data.findtext("reservationId"),
                owner_id=reservation_data.findtext("ownerId"),
                groups=groups)
            # Get the list of instances.
            instances = []
            for instance_data in reservation_data.find("instancesSet"):
                instance_id = instance_data.findtext("instanceId")
                instance_state = instance_data.find(
                    "instanceState").findtext("name")
                instance_type = instance_data.findtext("instanceType")
                image_id = instance_data.findtext("imageId")
                private_dns_name = instance_data.findtext("privateDnsName")
                dns_name = instance_data.findtext("dnsName")
                key_name = instance_data.findtext("keyName")
                ami_launch_index = instance_data.findtext("amiLaunchIndex")
                launch_time = instance_data.findtext("launchTime")
                placement = instance_data.find("placement").findtext(
                    "availabilityZone")
                products = []
                for product_data in instance_data.find("productCodesSet"):
                    product_code = product_data.findtext("productCode")
                    products.append(product_code)
                kernel_id = instance_data.findtext("kernelId")
                ramdisk_id = instance_data.findtext("ramdiskId")
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
        q = self.query_factory('TerminateInstances', self.creds, instanceset)
        d = q.submit()
        return d.addCallback(self._parse_terminate_instances)

    def _parse_terminate_instances(self, xml_bytes):
        root = XML(xml_bytes)
        result = []
        # May be a more elegant way to do this:
        for instance in root.find("instancesSet"):
            instanceId = instance.findtext("instanceId")
            previousState = instance.find("previousState").findtext(
                "name")
            shutdownState = instance.find("shutdownState").findtext(
                "name")
            result.append((instanceId, previousState, shutdownState))
        return result

    def describe_volumes(self, *volume_ids):
        """Describe available volumes."""
        volumeset = {}
        for pos, volume_id in enumerate(volume_ids):
            volumeset["VolumeId.%d" % (pos + 1)] = volume_id
        q = self.query_factory("DescribeVolumes", self.creds, volumeset)
        d = q.submit()
        return d.addCallback(self._parse_volumes)

    def _parse_volumes(self, xml_bytes):
        root = XML(xml_bytes)
        result = []
        for volume_data in root.find("volumeSet"):
            volume_id = volume_data.findtext("volumeId")
            size = int(volume_data.findtext("size"))
            status = volume_data.findtext("status")
            create_time = volume_data.findtext("createTime")
            create_time = datetime.strptime(
                create_time[:19], "%Y-%m-%dT%H:%M:%S")
            volume = Volume(volume_id, size, status, create_time)
            result.append(volume)
            for attachment_data in volume_data.find("attachmentSet"):
                instance_id = attachment_data.findtext("instanceId")
                snapshot_id = attachment_data.findtext("snapshotId")
                availability_zone = attachment_data.findtext(
                    "availabilityZone")
                status = attachment_data.findtext("status")
                attach_time = attachment_data.findtext("attachTime")
                attach_time = datetime.strptime(
                    attach_time[:19], "%Y-%m-%dT%H:%M:%S")
                attachment = Attachment(
                    instance_id, snapshot_id, availability_zone, status,
                    attach_time)
                volume.attachments.append(attachment)
        return result

    def create_volume(self, availability_zone, size=None, snapshot_id=None):
        """Create a new volume."""
        params = {"AvailabilityZone": availability_zone}
        if ((snapshot_id is None and size is None) or
            (snapshot_id is not None and size is not None)):
            raise ValueError("Please provide either size or snapshot_id")
        if size is not None:
            params["Size"] = str(size)
        if snapshot_id is not None:
            params["SnapshotId"] = snapshot_id
        q = self.query_factory("CreateVolume", self.creds, params)
        d = q.submit()
        return d.addCallback(self._parse_create_volume)

    def _parse_create_volume(self, xml_bytes):
        root = XML(xml_bytes)
        volume_id = root.findtext("volumeId")
        size = int(root.findtext("size"))
        status = root.findtext("status")
        create_time = root.findtext("createTime")
        create_time = datetime.strptime(
            create_time[:19], "%Y-%m-%dT%H:%M:%S")
        volume = Volume(volume_id, size, status, create_time)
        return volume

    def delete_volume(self, volume_id):
        q = self.query_factory(
            "DeleteVolume", self.creds, {"VolumeId": volume_id})
        d = q.submit()
        return d.addCallback(self._parse_delete_volume)

    def _parse_delete_volume(self, xml_bytes):
        root = XML(xml_bytes)
        return root.findtext("return") == "true"

    def describe_snapshots(self):
        """Describe available snapshots."""
        q = self.query_factory("DescribeSnapshots", self.creds)
        d = q.submit()
        return d.addCallback(self._parse_snapshots)

    def _parse_snapshots(self, xml_bytes):
        root = XML(xml_bytes)
        result = []
        for snapshot_data in root.find("snapshotSet"):
            snapshot_id = snapshot_data.findtext("snapshotId")
            volume_id = snapshot_data.findtext("volumeId")
            status = snapshot_data.findtext("status")
            start_time = snapshot_data.findtext("startTime")
            start_time = datetime.strptime(
                start_time[:19], "%Y-%m-%dT%H:%M:%S")
            progress = snapshot_data.findtext("progress")[:-1]
            progress = float(progress or "0") / 100.
            snapshot = Snapshot(
                snapshot_id, volume_id, status, start_time, progress)
            result.append(snapshot)
        return result

    def create_snapshot(self, volume_id):
        """Create a new snapshot of an existing volume."""
        q = self.query_factory(
            "CreateSnapshot", self.creds, {"VolumeId": volume_id})
        d = q.submit()
        return d.addCallback(self._parse_create_snapshot)

    def _parse_create_snapshot(self, xml_bytes):
        root = XML(xml_bytes)
        snapshot_id = root.findtext("snapshotId")
        volume_id = root.findtext("volumeId")
        status = root.findtext("status")
        start_time = root.findtext("startTime")
        start_time = datetime.strptime(
            start_time[:19], "%Y-%m-%dT%H:%M:%S")
        progress = root.findtext("progress")[:-1]
        progress = float(progress or "0") / 100.
        return Snapshot(snapshot_id, volume_id, status, start_time, progress)

    def delete_snapshot(self, snapshot_id):
        """Remove a previously created snapshot."""
        q = self.query_factory(
            "DeleteSnapshot", self.creds, {"SnapshotId": snapshot_id})
        d = q.submit()
        return d.addCallback(self._parse_delete_snapshot)

    def _parse_delete_snapshot(self, xml_bytes):
        root = XML(xml_bytes)
        return root.findtext("return") == "true"

    def attach_volume(self, volume_id, instance_id, device):
        """Attach the given volume to the specified instance at C{device}."""
        q = self.query_factory(
            "AttachVolume", self.creds,
            {"VolumeId": volume_id, "InstanceId": instance_id,
             "Device": device})
        d = q.submit()
        return d.addCallback(self._parse_attach_volume)

    def _parse_attach_volume(self, xml_bytes):
        root = XML(xml_bytes)
        status = root.findtext("status")
        attach_time = root.findtext("attachTime")
        attach_time = datetime.strptime(
            attach_time[:19], "%Y-%m-%dT%H:%M:%S")
        return {"status": status, "attach_time": attach_time}


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
