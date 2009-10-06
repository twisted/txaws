# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Copyright (C) 2009 Canonical Ltd
# Copyright (C) 2009 Duncan McGreggor <oubiwann@adytum.us>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""EC2 client support."""


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


class SecurityGroup(object):
    """An EC2 security group.

    @ivar owner_id: The AWS access key ID of the owner of this security group.
    @ivar name: The name of the security group.
    @ivar description: The description of this security group.
    @ivar allowed_groups: The sequence of L{UserIDGroupPair} instances for
        this security group.
    @ivar allowed_ips: The sequence of L{IPPermission} instances for this
        security group.
    """
    def __init__(self, name, description, owner_id="", groups=None, ips=None):
        self.name = name
        self.description = description
        self.owner_id = owner_id
        self.allowed_groups = groups or []
        self.allowed_ips = ips or []


class UserIDGroupPair(object):
    """A user ID/group name pair associated with a L{SecurityGroup}."""

    def __init__(self, user_id, group_name):
        self.user_id = user_id
        self.group_name = group_name


class IPPermission(object):
    """An IP permission associated with a L{SecurityGroup}."""

    def __init__(self, ip_protocol, from_port, to_port, cidr_ip):
        self.ip_protocol = ip_protocol
        self.from_port = from_port
        self.to_port = to_port
        self.cidr_ip = cidr_ip


class Volume(object):
    """An EBS volume instance."""

    def __init__(self, id, size, status, create_time, availability_zone,
                 snapshot_id):
        self.id = id
        self.size = size
        self.status = status
        self.create_time = create_time
        self.availability_zone = availability_zone
        self.snapshot_id = snapshot_id
        self.attachments = []


class Attachment(object):
    """An attachment of a L{Volume}."""

    def __init__(self, instance_id, device, status, attach_time):
        self.instance_id = instance_id
        self.device = device
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


class Keypair(object):
    """A convenience object for holding keypair data."""

    def __init__(self, name, fingerprint, material=None):
        self.name = name
        self.fingerprint = fingerprint
        self.material = material


class AvailabilityZone(object):
    """A convenience object for holding availability zone data."""

    def __init__(self, name, state):
        self.name = name
        self.state = state
