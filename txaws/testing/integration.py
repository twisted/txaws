from os import environ

from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceRegion
from txaws.testing.service import FakeAWSServiceRegion

def get_live_service(case):
    # Find credentials from the environment.
    #
    # To run this test, set TXAWS_INTEGRATION_AWS_ACCESS_KEY_ID
    # and TXAWS_INTEGRATION_AWS_SECRET_ACCESS_KEY to some
    # legitimate credentials.  It is probably a good idea to limit
    # what these credentials are allowed to do:
    #
    #    - in case they leak out of the test suite somehow
    #
    #    - in case the implementation is broken and does something destructive
    #
    #    - in case malicious code is inserted somehow (eg, you run
    #      tests on code submitted by another developer)
    #
    # As far as I can tell there's no way to isolate an API user
    # from _some_ of the parent account's S3 buckets.  Therefore,
    # isolation probably involves registering a new top-level AWS
    # account and dedicating it to testing purposes.
    try:
        access_key = environ["TXAWS_INTEGRATION_AWS_ACCESS_KEY_ID"]
        secret_key = environ["TXAWS_INTEGRATION_AWS_SECRET_ACCESS_KEY"]
    except KeyError as e:
        case.skipTest("Missing {} environment variable.".format(e))
    else:
        credentials = AWSCredentials(
            access_key=access_key,
            secret_key=secret_key,
        )
        return AWSServiceRegion(credentials)


def get_memory_service(case):
    return FakeAWSServiceRegion(
        access_key="fake access key",
        secret_key="fake secret key",
    )
