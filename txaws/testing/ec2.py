from twisted.internet.defer import succeed


class FakeEC2Client(object):

    def __init__(self, creds, endpoint, instances=[]):
        self.creds = creds
        self.endpoint = endpoint
        self.instances = instances

    def describe_instances(self):
        return succeed(self.instances)
