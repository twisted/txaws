from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint
from txaws.testing.ec2 import FakeEC2Client


class FakeAWSServiceRegion(object):

    instances = None
    keypairs = None
    volumes = None

    def __init__(self, access_key="", secret_key="", uri=""):
        self.access_key = access_key
        self.secret_key = secret_key
        self.uri = uri

    def get_ec2_client(self, *args, **kwds):

        creds = AWSCredentials(access_key=self.access_key,
                               secret_key=self.secret_key)
        endpoint = AWSServiceEndpoint(uri=self.uri)
        return FakeEC2Client(
            creds, endpoint, instances=self.instances, keypairs=self.keypairs,
            volumes=self.volumes)
