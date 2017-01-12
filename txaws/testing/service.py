from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint
from txaws.testing.ec2 import FakeEC2Client
from txaws.testing.route53 import MemoryRoute53
from txaws.testing.s3 import MemoryS3

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

        self.s3 = MemoryS3()
        self.route53 = MemoryRoute53()

        self._creds = AWSCredentials(
            access_key=self.access_key,
            secret_key=self.secret_key,
        )
        self._endpoint = AWSServiceEndpoint(uri=self.uri)

    def get_ec2_client(self, *args, **kwds):
        self.ec2_client = self.ec2_client_factory(
            self._creds, self._endpoint,
            instances=self.instances, keypairs=self.keypairs,
            volumes=self.volumes, key_material=self.key_material,
            security_groups=self.security_groups, snapshots=self.snapshots,
            availability_zones=self.availability_zones)
        return self.ec2_client

    def get_route53_client(self, creds=None):
        if creds is None:
            creds = self._creds
        self.route53_client, self.route53_state = self.route53.client(self, creds)
        return self.route53_client

    def get_s3_client(self, creds=None):
        if creds is None:
            creds = self._creds
        self.s3_client, self.s3_state = self.s3.client(creds, self._endpoint)
        return self.s3_client
