# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Copyright (C) 2009 Canonical Ltd
# Copyright (C) 2009 Duncan McGreggor <oubiwann@adytum.us>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""EC2 client support."""

from datetime import datetime
from urllib import quote
from base64 import b64encode

from txaws import version
from txaws.client.base import BaseClient, BaseQuery, error_wrapper
from txaws.ec2 import model
from txaws.ec2.exception import EC2Error
from txaws.util import iso8601time, XML


__all__ = ["EC2Client"]


def ec2_error_wrapper(error):
    error_wrapper(error, EC2Error)


class EC2Client(BaseClient):
    """A client for EC2."""

    def __init__(self, creds=None, endpoint=None, query_factory=None):
        if query_factory is None:
            query_factory = Query
        super(EC2Client, self).__init__(creds, endpoint, query_factory)

    def describe_instances(self, *instance_ids):
        """Describe current instances."""
        instances= {}
        for pos, instance_id in enumerate(instance_ids):
            instances["InstanceId.%d" % (pos + 1)] = instance_id
        query = self.query_factory(
            action="DescribeInstances", creds=self.creds,
            endpoint=self.endpoint, other_params=instances)
        d = query.submit()
        return d.addCallback(self._parse_describe_instances)

    def _parse_instances_set(self, root, reservation):
        instances = []
        for instance_data in root.find("instancesSet"):
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
        return instances

    def _parse_describe_instances(self, xml_bytes):
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
            instances = self._parse_instances_set(
                reservation_data, reservation)
            results.extend(instances)
        return results

    def run_instances(self, image_id, min_count, max_count,
        security_groups=None, key_name=None, instance_type=None,
        user_data=None, availability_zone=None, kernel_id=None,
        ramdisk_id=None):
        """Run new instances."""
        params = {"ImageId": image_id, "MinCount": str(min_count),
                  "MaxCount": str(max_count)}
        if security_groups is not None:
            for i, name in enumerate(security_groups):
                params["SecurityGroup.%d" % (i + 1)] = name
        if key_name is not None:
            params["KeyName"] = key_name
        if user_data is not None:
            params["UserData"] = b64encode(user_data)
        if instance_type is not None:
            params["InstanceType"] = instance_type
        if availability_zone is not None:
            params["Placement.AvailabilityZone"] = availability_zone
        if kernel_id is not None:
            params["KernelId"] = kernel_id
        if ramdisk_id is not None:
            params["RamdiskId"] = ramdisk_id
        query = self.query_factory(
            action="RunInstances", creds=self.creds, endpoint=self.endpoint, 
            other_params=params)
        d = query.submit()
        return d.addCallback(self._parse_run_instances)

    def _parse_run_instances(self, xml_bytes):
        """
        Parse the reservations XML payload that is returned from an AWS
        RunInstances API call.
        """
        root = XML(xml_bytes)
        # Get the security group information.
        groups = []
        for group_data in root.find("groupSet"):
            group_id = group_data.findtext("groupId")
            groups.append(group_id)
        # Create a reservation object with the parsed data.
        reservation = model.Reservation(
            reservation_id=root.findtext("reservationId"),
            owner_id=root.findtext("ownerId"),
            groups=groups)
        # Get the list of instances.
        instances = self._parse_instances_set(root, reservation)
        return instances

    def terminate_instances(self, *instance_ids):
        """Terminate some instances.

        @param instance_ids: The ids of the instances to terminate.
        @return: A deferred which on success gives an iterable of
            (id, old-state, new-state) tuples.
        """
        instances = {}
        for pos, instance_id in enumerate(instance_ids):
            instances["InstanceId.%d" % (pos+1)] = instance_id
        query = self.query_factory(
            action="TerminateInstances", creds=self.creds,
            endpoint=self.endpoint, other_params=instances)
        d = query.submit()
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
        group_names = {}
        if names:
            group_names = dict([("GroupName.%d" % (i+1), name)
                                for i, name in enumerate(names)])
        query = self.query_factory(
            action="DescribeSecurityGroups", creds=self.creds,
            endpoint=self.endpoint, other_params=group_names)
        d = query.submit()
        return d.addCallback(self._parse_describe_security_groups)

    def _parse_describe_security_groups(self, xml_bytes):
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
                user_id = ip_permission.findtext("groups/item/userId")
                group_name = ip_permission.findtext("groups/item/groupName")
                if user_id and group_name:
                    key = (user_id, group_name)
                    if key not in allowed_groups:
                        user_group_pair = model.UserIDGroupPair(
                            user_id, group_name)
                        allowed_groups.setdefault(user_id, user_group_pair)
                else:
                    ip_protocol = ip_permission.findtext("ipProtocol")
                    from_port = int(ip_permission.findtext("fromPort"))
                    to_port = int(ip_permission.findtext("toPort"))
                    cidr_ip = ip_permission.findtext("ipRanges/item/cidrIp")
                    allowed_ips.append(
                        model.IPPermission(
                            ip_protocol, from_port, to_port, cidr_ip))

            security_group = model.SecurityGroup(
                name, description, owner_id=owner_id,
                groups=allowed_groups.values(), ips=allowed_ips)
            result.append(security_group)
        return result

    def create_security_group(self, name, description):
        """Create security group.

        @param name: Name of the new security group.
        @param description: Description of the new security group.
        @return: A C{Deferred} that will fire with a truth value for the
            success of the operation.
        """
        parameters = {"GroupName":  name, "GroupDescription": description}
        query = self.query_factory(
            action="CreateSecurityGroup", creds=self.creds,
            endpoint=self.endpoint, other_params=parameters)
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def _parse_truth_return(self, xml_bytes):
        root = XML(xml_bytes)
        return root.findtext("return") == "true"

    def delete_security_group(self, name):
        """
        @param name: Name of the new security group.
        @return: A C{Deferred} that will fire with a truth value for the
            success of the operation.
        """
        parameter = {"GroupName":  name}
        query = self.query_factory(
            action="DeleteSecurityGroup", creds=self.creds,
            endpoint=self.endpoint, other_params=parameter)
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def authorize_security_group(
        self, group_name, source_group_name="", source_group_owner_id="",
        ip_protocol="", from_port="", to_port="", cidr_ip=""):
        """
        There are two ways to use C{authorize_security_group}:
            1) associate an existing group (source group) with the one that you
            are targeting (group_name) with an authorization update; or
            2) associate a set of IP permissions with the group you are
            targeting with an authorization update.

        @param group_name: The group you will be modifying with a new
            authorization.

        Optionally, the following parameters:
        @param source_group_name: Name of security group to authorize access to
            when operating on a user/group pair.
        @param source_group_owner_id: Owner of security group to authorize
            access to when operating on a user/group pair.

        If those parameters are not specified, then the following must be:
        @param ip_protocol: IP protocol to authorize access to when operating
            on a CIDR IP.
        @param from_port: Bottom of port range to authorize access to when
            operating on a CIDR IP. This contains the ICMP type if ICMP is
            being authorized.
        @param to_port: Top of port range to authorize access to when operating
            on a CIDR IP. This contains the ICMP code if ICMP is being
            authorized.
        @param cidr_ip: CIDR IP range to authorize access to when operating on
            a CIDR IP.

        @return: A C{Deferred} that will fire with a truth value for the
            success of the operation.
        """
        if source_group_name and source_group_owner_id:
            parameters = {
                "SourceSecurityGroupName": source_group_name,
                "SourceSecurityGroupOwnerId": source_group_owner_id,
                }
        elif ip_protocol and from_port and to_port and cidr_ip:
            parameters = {
                "IpProtocol": ip_protocol,
                "FromPort": from_port,
                "ToPort": to_port,
                "CidrIp": cidr_ip,
                }
        else:
            msg = ("You must specify either both group parameters or "
                   "all the ip parameters.")
            raise ValueError(msg)
        parameters["GroupName"] = group_name
        query = self.query_factory(
            action="AuthorizeSecurityGroupIngress", creds=self.creds,
            endpoint=self.endpoint, other_params=parameters)
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def authorize_group_permission(
        self, group_name, source_group_name, source_group_owner_id):
        """
        This is a convenience function that wraps the "authorize group"
        functionality of the C{authorize_security_group} method.

        For an explanation of the parameters, see C{authorize_security_group}.
        """
        d = self.authorize_security_group(
            group_name,
            source_group_name=source_group_name,
            source_group_owner_id=source_group_owner_id)
        return d

    def authorize_ip_permission(
        self, group_name, ip_protocol, from_port, to_port, cidr_ip):
        """
        This is a convenience function that wraps the "authorize ip
        permission" functionality of the C{authorize_security_group} method.

        For an explanation of the parameters, see C{authorize_security_group}.
        """
        d = self.authorize_security_group(
            group_name,
            ip_protocol=ip_protocol, from_port=from_port, to_port=to_port,
            cidr_ip=cidr_ip)
        return d

    def revoke_security_group(
        self, group_name, source_group_name="", source_group_owner_id="",
        ip_protocol="", from_port="", to_port="", cidr_ip=""):
        """
        There are two ways to use C{revoke_security_group}:
            1) associate an existing group (source group) with the one that you
            are targeting (group_name) with the revoke update; or
            2) associate a set of IP permissions with the group you are
            targeting with a revoke update.

        @param group_name: The group you will be modifying with an
            authorization removal.

        Optionally, the following parameters:
        @param source_group_name: Name of security group to revoke access from
            when operating on a user/group pair.
        @param source_group_owner_id: Owner of security group to revoke
            access from when operating on a user/group pair.

        If those parameters are not specified, then the following must be:
        @param ip_protocol: IP protocol to revoke access from when operating
            on a CIDR IP.
        @param from_port: Bottom of port range to revoke access from when
            operating on a CIDR IP. This contains the ICMP type if ICMP is
            being revoked.
        @param to_port: Top of port range to revoke access from when operating
            on a CIDR IP. This contains the ICMP code if ICMP is being
            revoked.
        @param cidr_ip: CIDR IP range to revoke access from when operating on
            a CIDR IP.

        @return: A C{Deferred} that will fire with a truth value for the
            success of the operation.
        """
        if source_group_name and source_group_owner_id:
            parameters = {
                "SourceSecurityGroupName": source_group_name,
                "SourceSecurityGroupOwnerId": source_group_owner_id,
                }
        elif ip_protocol and from_port and to_port and cidr_ip:
            parameters = {
                "IpProtocol": ip_protocol,
                "FromPort": from_port,
                "ToPort": to_port,
                "CidrIp": cidr_ip,
                }
        else:
            msg = ("You must specify either both group parameters or "
                   "all the ip parameters.")
            raise ValueError(msg)
        parameters["GroupName"] = group_name
        query = self.query_factory(
            action="RevokeSecurityGroupIngress", creds=self.creds,
            endpoint=self.endpoint, other_params=parameters)
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def revoke_group_permission(
        self, group_name, source_group_name, source_group_owner_id):
        """
        This is a convenience function that wraps the "authorize group"
        functionality of the C{authorize_security_group} method.

        For an explanation of the parameters, see C{revoke_security_group}.
        """
        d = self.revoke_security_group(
            group_name,
            source_group_name=source_group_name,
            source_group_owner_id=source_group_owner_id)
        return d

    def revoke_ip_permission(
        self, group_name, ip_protocol, from_port, to_port, cidr_ip):
        """
        This is a convenience function that wraps the "authorize ip
        permission" functionality of the C{authorize_security_group} method.

        For an explanation of the parameters, see C{revoke_security_group}.
        """
        d = self.revoke_security_group(
            group_name,
            ip_protocol=ip_protocol, from_port=from_port, to_port=to_port,
            cidr_ip=cidr_ip)
        return d

    def describe_volumes(self, *volume_ids):
        """Describe available volumes."""
        volumeset = {}
        for pos, volume_id in enumerate(volume_ids):
            volumeset["VolumeId.%d" % (pos + 1)] = volume_id
        query = self.query_factory(
            action="DescribeVolumes", creds=self.creds, endpoint=self.endpoint,
            other_params=volumeset)
        d = query.submit()
        return d.addCallback(self._parse_describe_volumes)

    def _parse_describe_volumes(self, xml_bytes):
        root = XML(xml_bytes)
        result = []
        for volume_data in root.find("volumeSet"):
            volume_id = volume_data.findtext("volumeId")
            size = int(volume_data.findtext("size"))
            status = volume_data.findtext("status")
            availability_zone = volume_data.findtext("availabilityZone")
            snapshot_id = volume_data.findtext("snapshotId")
            create_time = volume_data.findtext("createTime")
            create_time = datetime.strptime(
                create_time[:19], "%Y-%m-%dT%H:%M:%S")
            volume = model.Volume(
                volume_id, size, status, create_time, availability_zone,
                snapshot_id)
            result.append(volume)
            for attachment_data in volume_data.find("attachmentSet"):
                instance_id = attachment_data.findtext("instanceId")
                status = attachment_data.findtext("status")
                device = attachment_data.findtext("device")
                attach_time = attachment_data.findtext("attachTime")
                attach_time = datetime.strptime(
                    attach_time[:19], "%Y-%m-%dT%H:%M:%S")
                attachment = model.Attachment(
                    instance_id, device, status, attach_time)
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
        query = self.query_factory(
            action="CreateVolume", creds=self.creds, endpoint=self.endpoint,
            other_params=params)
        d = query.submit()
        return d.addCallback(self._parse_create_volume)

    def _parse_create_volume(self, xml_bytes):
        root = XML(xml_bytes)
        volume_id = root.findtext("volumeId")
        size = int(root.findtext("size"))
        status = root.findtext("status")
        create_time = root.findtext("createTime")
        availability_zone = root.findtext("availabilityZone")
        snapshot_id = root.findtext("snapshotId")
        create_time = datetime.strptime(
            create_time[:19], "%Y-%m-%dT%H:%M:%S")
        volume = model.Volume(
            volume_id, size, status, create_time, availability_zone,
            snapshot_id)
        return volume

    def delete_volume(self, volume_id):
        query = self.query_factory(
            action="DeleteVolume", creds=self.creds, endpoint=self.endpoint,
            other_params={"VolumeId": volume_id})
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def describe_snapshots(self, *snapshot_ids):
        """Describe available snapshots."""
        snapshot_set = {}
        for pos, snapshot_id in enumerate(snapshot_ids):
            snapshot_set["SnapshotId.%d" % (pos + 1)] = snapshot_id
        query = self.query_factory(
            action="DescribeSnapshots", creds=self.creds,
            endpoint=self.endpoint, other_params=snapshot_set)
        d = query.submit()
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
        query = self.query_factory(
            action="CreateSnapshot", creds=self.creds, endpoint=self.endpoint,
            other_params={"VolumeId": volume_id})
        d = query.submit()
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
        query = self.query_factory(
            action="DeleteSnapshot", creds=self.creds, endpoint=self.endpoint,
            other_params={"SnapshotId": snapshot_id})
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def attach_volume(self, volume_id, instance_id, device):
        """Attach the given volume to the specified instance at C{device}."""
        query = self.query_factory(
            action="AttachVolume", creds=self.creds, endpoint=self.endpoint,
            other_params={"VolumeId": volume_id, "InstanceId": instance_id,
                          "Device": device})
        d = query.submit()
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
        keypairs = {}
        for index, keypair_name in enumerate(keypair_names):
            keypairs["KeyPair.%d" % (index + 1)] = keypair_name
        query = self.query_factory(
            action="DescribeKeyPairs", creds=self.creds,
            endpoint=self.endpoint, other_params=keypairs)
        d = query.submit()
        return d.addCallback(self._parse_describe_keypairs)

    def _parse_describe_keypairs(self, xml_bytes):
        results = []
        root = XML(xml_bytes)
        keypairs = root.find("keySet")
        if not keypairs:
            return results
        for keypair_data in keypairs:
            key_name = keypair_data.findtext("keyName")
            key_fingerprint = keypair_data.findtext("keyFingerprint")
            results.append(model.Keypair(key_name, key_fingerprint))
        return results

    def create_keypair(self, keypair_name):
        """
        Create a new 2048 bit RSA key pair and return a unique ID that can be
        used to reference the created key pair when launching new instances.
        """
        query = self.query_factory(
            action="CreateKeyPair", creds=self.creds, endpoint=self.endpoint,
            other_params={"KeyName": keypair_name})
        d = query.submit()
        return d.addCallback(self._parse_create_keypair)

    def _parse_create_keypair(self, xml_bytes):
        keypair_data = XML(xml_bytes)
        key_name = keypair_data.findtext("keyName")
        key_fingerprint = keypair_data.findtext("keyFingerprint")
        key_material = keypair_data.findtext("keyMaterial")
        return model.Keypair(key_name, key_fingerprint, key_material)

    def delete_keypair(self, keypair_name):
        """Delete a given keypair."""
        query = self.query_factory(
            action="DeleteKeyPair", creds=self.creds, endpoint=self.endpoint,
            other_params={"KeyName": keypair_name})
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def allocate_address(self):
        """
        Acquire an elastic IP address to be attached subsequently to EC2
        instances.

        @return: the IP address allocated.
        """
        # XXX remove empty other_params
        query = self.query_factory(
            action="AllocateAddress", creds=self.creds, endpoint=self.endpoint, 
            other_params={})
        d = query.submit()
        return d.addCallback(self._parse_allocate_address)

    def _parse_allocate_address(self, xml_bytes):
        address_data = XML(xml_bytes)
        return address_data.findtext("publicIp")

    def release_address(self, address):
        """
        Release a previously allocated address returned by C{allocate_address}.

        @return: C{True} if the operation succeeded.
        """
        query = self.query_factory(
            action="ReleaseAddress", creds=self.creds, endpoint=self.endpoint,
            other_params={"PublicIp": address})
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def associate_address(self, instance_id, address):
        """
        Associate an allocated C{address} with the instance identified by
        C{instance_id}.

        @return: C{True} if the operation succeeded.
        """
        query = self.query_factory(
            action="AssociateAddress", creds=self.creds,
            endpoint=self.endpoint,
            other_params={"InstanceId": instance_id, "PublicIp": address})
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def disassociate_address(self, address):
        """
        Disassociate an address previously associated with
        C{associate_address}. This is an idempotent operation, so it can be
        called several times without error.
        """
        query = self.query_factory(
            action="DisassociateAddress", creds=self.creds,
            endpoint=self.endpoint, other_params={"PublicIp": address})
        d = query.submit()
        return d.addCallback(self._parse_truth_return)

    def describe_addresses(self, *addresses):
        """
        List the elastic IPs allocated in this account.

        @param addresses: if specified, the addresses to get information about.

        @return: a C{list} of (address, instance_id). If the elastic IP is not
            associated currently, C{instance_id} will be C{None}.
        """
        address_set = {}
        for pos, address in enumerate(addresses):
            address_set["PublicIp.%d" % (pos + 1)] = address
        query = self.query_factory(
            action="DescribeAddresses", creds=self.creds,
            endpoint=self.endpoint, other_params=address_set)
        d = query.submit()
        return d.addCallback(self._parse_describe_addresses)

    def _parse_describe_addresses(self, xml_bytes):
        results = []
        root = XML(xml_bytes)
        for address_data in root.find("addressesSet"):
            address = address_data.findtext("publicIp")
            instance_id = address_data.findtext("instanceId")
            results.append((address, instance_id))
        return results

    def describe_availability_zones(self, names=None):
        zone_names = None
        if names:
            zone_names = dict([("ZoneName.%d" % (i+1), name)
                                for i, name in enumerate(names)])
        query = self.query_factory(
            action="DescribeAvailabilityZones", creds=self.creds,
            endpoint=self.endpoint, other_params=zone_names)
        d = query.submit()
        return d.addCallback(self._parse_describe_availability_zones)

    def _parse_describe_availability_zones(self, xml_bytes):
        results = []
        root = XML(xml_bytes)
        for zone_data in root.find("availabilityZoneInfo"):
            zone_name = zone_data.findtext("zoneName")
            zone_state = zone_data.findtext("zoneState")
            results.append(model.AvailabilityZone(zone_name, zone_state))
        return results


class Query(BaseQuery):
    """A query that may be submitted to EC2."""

    def __init__(self, other_params=None, time_tuple=None, api_version=None,
                 *args, **kwargs):
        """Create a Query to submit to EC2."""
        super(Query, self).__init__(*args, **kwargs)
        # Currently, txAWS only supports version 2008-12-01
        if api_version is None:
            api_version = version.ec2_api
        self.params = {
            "Version": api_version,
            "SignatureVersion": "2",
            "SignatureMethod": "HmacSHA256",
            "Action": self.action,
            "AWSAccessKeyId": self.creds.access_key,
            "Timestamp": iso8601time(time_tuple),
            }
        if other_params:
            self.params.update(other_params)

    def get_canonical_query_params(self):
        """Return the canonical query params (used in signing)."""
        result = []
        for key, value in self.sorted_params():
            result.append("%s=%s" % (self.encode(key), self.encode(value)))
        return "&".join(result)

    def encode(self, string):
        """Encode a_string as per the canonicalisation encoding rules.

        See the AWS dev reference page 90 (2008-12-01 version).
        @return: a_string encoded.
        """
        return quote(string, safe="~")

    def signing_text(self):
        """Return the text to be signed when signing the query."""
        result = "%s\n%s\n%s\n%s" % (self.endpoint.method, self.endpoint.host,
                                     self.endpoint.path,
                                     self.get_canonical_query_params())
        return result

    def sorted_params(self):
        """Return the query parameters sorted appropriately for signing."""
        return sorted(self.params.items())

    def sign(self):
        """Sign this query using its built in credentials.

        This prepares it to be sent, and should be done as the last step before
        submitting the query. Signing is done automatically - this is a public
        method to facilitate testing.
        """
        self.params["Signature"] = self.creds.sign(self.signing_text())

    def submit(self):
        """Submit this query.

        @return: A deferred from get_page
        """
        self.sign()
        url = "%s?%s" % (self.endpoint.get_uri(),
                         self.get_canonical_query_params())
        d = self.get_page(url, method=self.endpoint.method)
        return d.addErrback(ec2_error_wrapper)
