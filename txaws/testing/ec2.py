# Copyright (C) 2009 Canonical Ltd
# Copyright (C) 2009 Duncan McGreggor <oubiwann@adytum.us>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from twisted.internet.defer import succeed, fail
from twisted.python.failure import Failure
from twisted.web.error import Error

from txaws.ec2.model import Keypair

class FakeEC2Client(object):

    def __init__(self, creds, endpoint, instances=None, keypairs=None,
                 volumes=None, key_material="", security_groups=None,
                 snapshots=None):
        self.creds = creds
        self.endpoint = endpoint
        self.instances = instances or []
        self.keypairs = keypairs or []
        self.volumes = volumes or []
        self.keypairs_deleted = []
        self.key_material = key_material
        self.security_groups = security_groups or []
        self.snapshots = snapshots or []

    def describe_instances(self):
        return succeed(self.instances)

    def describe_keypairs(self):
        return succeed(self.keypairs)

    def create_keypair(self, name):
        keypair = Keypair(name, "fingerprint", self.key_material)
        return succeed(keypair)

    def delete_keypair(self, name):
        self.keypairs_deleted.append(name)
        return succeed(True)

    def describe_volumes(self):
        return succeed(self.volumes)

    def describe_snapshots(self):
        return succeed(self.snapshots)

    def delete_volume(self, volume_id):
        return succeed(True)

    def delete_snapshot(self, volume_id):
        return succeed(True)

    def create_volume(self, availability_zone, size=None, snapshot_id=None):
        return succeed(self.volumes[0])

    def describe_security_groups(self, names=None):
        return succeed(self.security_groups)


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

