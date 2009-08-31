from twisted.internet.defer import succeed


class FakeEC2Client(object):

    def __init__(self, creds, endpoint, instances=None):
        self.creds = creds
        self.endpoint = endpoint
        self.instances = instances or []

    def describe_instances(self):
        return succeed(self.instances)
