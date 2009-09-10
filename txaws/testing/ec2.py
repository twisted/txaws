from twisted.internet.defer import succeed, fail
from twisted.python.failure import Failure
from twisted.web.error import Error


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

