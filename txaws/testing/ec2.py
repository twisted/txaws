from twisted.internet.defer import succeed


class FakeEC2Client(object):

    def __init__(self, creds, endpoint, instances=None, keypairs=[]):
        self.creds = creds
        self.endpoint = endpoint
        self.instances = instances or []
        self.keypairs = keypairs

    def describe_instances(self):
        return succeed(self.instances)

    def describe_keypairs(self):
        return succeed(self.keypairs)
