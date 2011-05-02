# Copyright (C) 2009 Canonical Ltd
# Copyright (C) 2009 Duncan McGreggor <oubiwann@adytum.us>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from datetime import datetime

from twisted.internet.defer import succeed, fail
from twisted.python.failure import Failure
from twisted.web.error import Error

from txaws.ec2.model import Keypair, SecurityGroup


class FakeEC2Client(object):

    def __init__(self, creds, endpoint, instances=None, keypairs=None,
                 volumes=None, key_material="", security_groups=None,
                 snapshots=None, addresses=None, availability_zones=None,
                 query_factory=None, parser=None):

        self.creds = creds
        self.endpoint = endpoint
        self.query_factory = query_factory
        self.parser = parser

        self.instances = instances or []
        self.keypairs = keypairs or []
        self.keypairs_deleted = []
        self.volumes = volumes or []
        self.volumes_deleted = []
        self.key_material = key_material
        self.security_groups = security_groups or []
        self.security_groups_deleted = []
        self.snapshots = snapshots or []
        self.snapshots_deleted = []
        self.addresses = addresses or []
        self.availability_zones = availability_zones or []

    def describe_instances(self, *instances):
        return succeed(self.instances)

    def run_instances(self, image_id, min_count, max_count,
        security_groups=None, key_name=None, instance_type=None,
        user_data=None, availability_zone=None, kernel_id=None,
        ramdisk_id=None):
        return succeed(self.instances)

    def terminate_instances(self, *instance_ids):
        result = [(instance.instance_id, instance.instance_state,
                   u"shutting-down") for instance in self.instances]
        return succeed(result)

    def describe_keypairs(self):
        return succeed(self.keypairs)

    def create_keypair(self, name):
        keypair = Keypair(name, "fingerprint", self.key_material)
        return succeed(keypair)

    def delete_keypair(self, name):
        self.keypairs_deleted.append(name)
        return succeed(True)

    def describe_security_groups(self, names=None):
        return succeed(self.security_groups)

    def create_security_group(self, name, description):
        self.security_groups.append(SecurityGroup(name, description))
        return succeed(True)

    def delete_security_group(self, name):
        self.security_groups_deleted.append(name)
        return succeed(True)

    def describe_volumes(self, *volume_ids):
        return succeed(self.volumes)

    def create_volume(self, availability_zone, size=None, snapshot_id=None):
        return succeed(self.volumes[0])

    def attach_volume(self, volume_id, instance_id, device):
        return succeed({"status": u"attaching",
                        "attach_time": datetime(2007, 6, 6, 11, 10, 00)})

    def delete_volume(self, volume_id):
        self.volumes_deleted.append(volume_id)
        return succeed(True)

    def describe_snapshots(self, *snapshot_ids):
        return succeed(self.snapshots)

    def create_snapshot(self, volume_id):
        return succeed(self.snapshots[0])

    def delete_snapshot(self, volume_id):
        self.snapshots_deleted.append(volume_id)
        return succeed(True)

    def authorize_group_permission(self, group_name, source_group_name,
                                   source_group_owner_id):
        return succeed(True)

    def revoke_group_permission(self, group_name, source_group_name,
                                source_group_owner_id):
        return succeed(True)

    def authorize_ip_permission(self, group_name, protocol, from_port, to_port,
                                cidr_ip):
        return succeed(True)

    def revoke_ip_permission(self, group_name, protocol, from_port, to_port,
                             cidr_ip):
        return succeed(True)

    def describe_addresses(self, *addresses):
        return succeed(self.addresses)

    def allocate_address(self):
        return succeed(self.addresses[0][0])

    def release_address(self, address):
        return succeed(True)

    def associate_address(self, instance_id, address):
        return succeed(True)

    def disassociate_address(self, address):
        return succeed(True)

    def describe_availability_zones(self, *names):
        return succeed(self.availability_zones)


class FakePageGetter(object):

    def __init__(self, status, payload):
        self.status = status
        self.payload = payload

    def get_page(self, url, *args, **kwds):
        return succeed(self.payload)

    def get_page_with_exception(self, url, *args, **kwds):

        try:
            raise Error(self.status, "There's been an error", self.payload)
        except:
            failure = Failure()
        return fail(failure)
