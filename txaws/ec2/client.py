# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Copyright (C) 2009 Canonical Ltd
# Copyright (C) 2009 Duncan McGreggor <oubiwann@adytum.us>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""EC2 client support."""

from datetime import datetime
from urllib import quote

from twisted.internet import reactor, ssl
from twisted.web.client import HTTPClientFactory

from txaws import version
from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint
from txaws.util import iso8601time, parse, XML
from txaws.ec2 import model
from txaws.ec2.exception import EC2Error


__all__ = ["EC2Client"]


def ec2_error_wrapper(error):
    xml_payload = error.value.response
    http_status = None
    if hasattr(error.value, "status"):
        if error.value.status:
            http_status = int(error.value.status)
    if 400 <= http_status < 500:
        raise EC2Error(xml_payload, error.value.status, error.value.message,
                       error.value.response)
    else:
        error.raiseException()


class EC2Client(object):
    """A client for EC2."""

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
        q = self.query_factory("DescribeInstances", self.creds, self.endpoint)
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

        The following instance attributes are optional:
            * ami_launch_index
            * key_name
            * kernel_id
            * product_codes
            * ramdisk_id
            * reason
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
            reservation = model.Reservation(
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
                product_codes = instance_data.find("productCodes")
                if product_codes:
                    for product_data in instance_data.find("productCodes"):
                        products.append(product_data.text)
                kernel_id = instance_data.findtext("kernelId")
                ramdisk_id = instance_data.findtext("ramdiskId")
                instance = model.Instance(
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
        q = self.query_factory("TerminateInstances", self.creds, self.endpoint,
                               instanceset)
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

    def describe_security_groups(self, *names):
        """Describe security groups.

        @param names: Optionally, a list of security group names to describe.
            Defaults to all security groups in the account.
        @return: A C{Deferred} that will fire with a list of L{SecurityGroup}s
            retrieved from the cloud.
        """
        group_names = None
        if names:
            group_names = dict([("GroupName.%d" % (i+1), name)
                                for i, name in enumerate(names)])
        query = self.query_factory("DescribeSecurityGroups", self.creds,
                                   self.endpoint, group_names)
        d = query.submit()
        return d.addCallback(self._parse_security_groups)

    def _parse_security_groups(self, xml_bytes):
        """Parse the XML returned by the C{DescribeSecurityGroups} function.

        @param xml_bytes: XML bytes with a C{DescribeSecurityGroupsResponse}
            root element.
        @return: A list of L{SecurityGroup} instances.
        """
        root = XML(xml_bytes)
        result = []
        for group_info in root.findall("securityGroupInfo/item"):
            name = group_info.findtext("groupName")
            description = group_info.findtext("groupDescription")
            owner_id = group_info.findtext("ownerId")
            allowed_groups = {}
            allowed_ips = []
            ip_permissions = group_info.find("ipPermissions") or []
            for ip_permission in ip_permissions:
                ip_protocol = ip_permission.findtext("ipProtocol")
                from_port = int(ip_permission.findtext("fromPort"))
                to_port = int(ip_permission.findtext("toPort"))
                cidr_ip = ip_permission.findtext("ipRanges/item/cidrIp")
                allowed_ips.append(
                    model.IPPermission(
                        ip_protocol, from_port, to_port, cidr_ip))

                user_id = ip_permission.findtext("groups/item/userId")
                group_name = ip_permission.findtext("groups/item/groupName")
                if user_id and group_name:
                    key = (user_id, group_name)
                    if key not in allowed_groups:
                        user_group_pair = model.UserIDGroupPair(
                            user_id, group_name)
                        allowed_groups.setdefault(user_id, user_group_pair)

            security_group = model.SecurityGroup(
                name, description, owner_id=owner_id,
                groups=allowed_groups.values(), ips=allowed_ips)
            result.append(security_group)
        return result

    def describe_volumes(self, *volume_ids):
        """Describe available volumes."""
        volumeset = {}
        for pos, volume_id in enumerate(volume_ids):
            volumeset["VolumeId.%d" % (pos + 1)] = volume_id
        q = self.query_factory(
            "DescribeVolumes", self.creds, self.endpoint, volumeset)
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
            volume = model.Volume(volume_id, size, status, create_time)
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
                attachment = model.Attachment(
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
        q = self.query_factory(
            "CreateVolume", self.creds, self.endpoint, params)
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
        volume = model.Volume(volume_id, size, status, create_time)
        return volume

    def delete_volume(self, volume_id):
        q = self.query_factory(
            "DeleteVolume", self.creds, self.endpoint, {"VolumeId": volume_id})
        d = q.submit()
        return d.addCallback(self._parse_delete_volume)

    def _parse_delete_volume(self, xml_bytes):
        root = XML(xml_bytes)
        return root.findtext("return") == "true"

    def describe_snapshots(self, *snapshot_ids):
        """Describe available snapshots."""
        snapshot_set = {}
        for pos, snapshot_id in enumerate(snapshot_ids):
            snapshot_set["SnapshotId.%d" % (pos + 1)] = snapshot_id
        q = self.query_factory(
            "DescribeSnapshots", self.creds, self.endpoint, snapshot_set)
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
            snapshot = model.Snapshot(
                snapshot_id, volume_id, status, start_time, progress)
            result.append(snapshot)
        return result

    def create_snapshot(self, volume_id):
        """Create a new snapshot of an existing volume."""
        q = self.query_factory(
            "CreateSnapshot", self.creds, self.endpoint,
            {"VolumeId": volume_id})
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
        return model.Snapshot(
            snapshot_id, volume_id, status, start_time, progress)

    def delete_snapshot(self, snapshot_id):
        """Remove a previously created snapshot."""
        q = self.query_factory(
            "DeleteSnapshot", self.creds, self.endpoint,
            {"SnapshotId": snapshot_id})
        d = q.submit()
        return d.addCallback(self._parse_delete_snapshot)

    def _parse_delete_snapshot(self, xml_bytes):
        root = XML(xml_bytes)
        return root.findtext("return") == "true"

    def attach_volume(self, volume_id, instance_id, device):
        """Attach the given volume to the specified instance at C{device}."""
        q = self.query_factory(
            "AttachVolume", self.creds, self.endpoint,
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

    def describe_keypairs(self, *keypair_names):
        """Returns information about key pairs available."""
        keypair_set = {}
        for pos, keypair_name in enumerate(keypair_names):
            keypair_set["KeyPair.%d" % (pos + 1)] = keypair_name
        q = self.query_factory("DescribeKeyPairs", self.creds, self.endpoint,
                               keypair_set)
        d = q.submit()
        return d.addCallback(self._parse_describe_keypairs)

    def _parse_describe_keypairs(self, xml_bytes):
        results = []
        root = XML(xml_bytes)
        for keypair_data in root.find("keySet"):
            key_name = keypair_data.findtext("keyName")
            key_fingerprint = keypair_data.findtext("keyFingerprint")
            results.append(model.Keypair(key_name, key_fingerprint))
        return results

    def create_keypair(self, keypair_name):
        """
        Create a new 2048 bit RSA key pair and return a unique ID that can be
        used to reference the created key pair when launching new instances.
        """
        q = self.query_factory(
            "CreateKeyPair", self.creds, self.endpoint,
            {"KeyName": keypair_name})
        d = q.submit()
        return d.addCallback(self._parse_create_keypair)

    def _parse_create_keypair(self, xml_bytes):
        results = []
        keypair_data = XML(xml_bytes)
        key_name = keypair_data.findtext("keyName")
        key_fingerprint = keypair_data.findtext("keyFingerprint")
        key_material = keypair_data.findtext("keyMaterial")
        return model.Keypair(key_name, key_fingerprint, key_material)

    def delete_keypair(self, keypair_name):
        """Delete a given keypair."""
        q = self.query_factory(
            "DeleteKeyPair", self.creds, self.endpoint,
            {"KeyName": keypair_name})
        d = q.submit()
        return d.addCallback(self._parse_delete_keypair)

    def _parse_delete_keypair(self, xml_bytes):
        results = []
        keypair_data = XML(xml_bytes)
        result = keypair_data.findtext("return")
        if not result:
            result = False
        elif result.lower() == "true":
            result = True
        else:
            result = False
        return result


class Query(object):
    """A query that may be submitted to EC2."""

    def __init__(self, action, creds, endpoint, other_params=None,
                 time_tuple=None, api_version=None):
        """Create a Query to submit to EC2."""
        self.factory = HTTPClientFactory
        self.creds = creds
        self.endpoint = endpoint
        # Currently, txAWS only supports version 2008-12-01
        if api_version is None:
            api_version = version.aws_api
        self.params = {
            "Version": api_version,
            "SignatureVersion": "2",
            "SignatureMethod": "HmacSHA1",
            "Action": action,
            "AWSAccessKeyId": self.creds.access_key,
            "Timestamp": iso8601time(time_tuple),
            }
        if other_params:
            self.params.update(other_params)

    def canonical_query_params(self):
        """Return the canonical query params (used in signing)."""
        result = []
        for key, value in self.sorted_params():
            result.append("%s=%s" % (self.encode(key), self.encode(value)))
        return "&".join(result)

    def encode(self, a_string):
        """Encode a_string as per the canonicalisation encoding rules.

        See the AWS dev reference page 90 (2008-12-01 version).
        @return: a_string encoded.
        """
        return quote(a_string, safe="~")

    def signing_text(self):
        """Return the text to be signed when signing the query."""
        result = "%s\n%s\n%s\n%s" % (self.endpoint.method, self.endpoint.host,
                                     self.endpoint.path,
                                     self.canonical_query_params())
        return result

    def sign(self):
        """Sign this query using its built in credentials.

        This prepares it to be sent, and should be done as the last step before
        submitting the query. Signing is done automatically - this is a public
        method to facilitate testing.
        """
        self.params["Signature"] = self.creds.sign(self.signing_text())

    def sorted_params(self):
        """Return the query params sorted appropriately for signing."""
        return sorted(self.params.items())

    def get_page(self, url, *args, **kwds):
        """
        Define our own get_page method so that we can easily override the
        factory when we need to. This was copied from the following:
            * twisted.web.client.getPage
            * twisted.web.client._makeGetterFactory
        """
        contextFactory = None
        scheme, host, port, path = parse(url)
        factory = self.factory(url, *args, **kwds)
        if scheme == 'https':
            contextFactory = ssl.ClientContextFactory()
            reactor.connectSSL(host, port, factory, contextFactory)
        else:
            reactor.connectTCP(host, port, factory)
        return factory.deferred

    def submit(self):
        """Submit this query.

        @return: A deferred from get_page
        """
        self.sign()
        url = "%s?%s" % (self.endpoint.get_uri(),
                         self.canonical_query_params())
        deferred = self.get_page(url, method=self.endpoint.method)
        deferred.addErrback(ec2_error_wrapper)
        return deferred
