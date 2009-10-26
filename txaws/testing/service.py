from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint
from txaws.testing.ec2 import FakeEC2Client


class FakeAWSServiceRegion(object):

    key_material = ""

    def __init__(self, access_key="", secret_key="", uri="",
                 ec2_client_factory=None, keypairs=None, security_groups=None,
                 instances=None, volumes=None, snapshots=None,
                 availability_zones=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.uri = uri
        self.ec2_client = None
        if not ec2_client_factory:
            ec2_client_factory = FakeEC2Client
        self.ec2_client_factory = ec2_client_factory
        self.keypairs = keypairs
        self.security_groups = security_groups
        self.instances = instances
        self.volumes = volumes
        self.snapshots = snapshots
        self.availability_zones = availability_zones

    def get_ec2_client(self, *args, **kwds):

        creds = AWSCredentials(access_key=self.access_key,
                               secret_key=self.secret_key)
        endpoint = AWSServiceEndpoint(uri=self.uri)
        self.ec2_client = self.ec2_client_factory(
            creds, endpoint, instances=self.instances, keypairs=self.keypairs,
            volumes=self.volumes, key_material=self.key_material,
            security_groups=self.security_groups, snapshots=self.snapshots,
            availability_zones=self.availability_zones)
        return self.ec2_client
