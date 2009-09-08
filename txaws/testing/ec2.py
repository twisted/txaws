from twisted.internet.defer import succeed


class FakeEC2Client(object):

    def __init__(self, creds, endpoint, instances=None, keypairs=None,
                 volumes=None):
        self.creds = creds
        self.endpoint = endpoint
        self.instances = instances or []
        self.keypairs = keypairs or []
        self.volumes = volumes or []

    def describe_instances(self):
        return succeed(self.instances)

    def describe_keypairs(self):
        return succeed(self.keypairs)

    def describe_volumes(self):
        return succeed(self.volumes)

    def delete_volume(self, volume_id):
        return succeed(True)
