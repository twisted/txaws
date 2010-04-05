# Copyright (c) 2009 Canonical Ltd <duncan.mcgreggor@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from twisted.trial.unittest import TestCase

from txaws.ec2.exception import EC2Error
from txaws.testing import payload
from txaws.util import XML


REQUEST_ID = "0ef9fc37-6230-4d81-b2e6-1b36277d4247"


class EC2ErrorTestCase(TestCase):

    def test_set_400_error(self):
        errorsXML = "<Error><Code>1</Code><Message>2</Message></Error>"
        xml = "<a><Errors>%s</Errors><b /></a>" % errorsXML
        error = EC2Error("<dummy />", 400)
        error._set_400_error(XML(xml))
        self.assertEquals(error.errors[0]["Code"], "1")
        self.assertEquals(error.errors[0]["Message"], "2")

    def test_has_error(self):
        errorsXML = "<Error><Code>Code1</Code><Message>2</Message></Error>"
        xml = "<a><Errors>%s</Errors><b /></a>" % errorsXML
        error = EC2Error(xml, 400)
        self.assertTrue(error.has_error("Code1"))

    def test_single_error(self):
        error = EC2Error(payload.sample_ec2_error_message, 400)
        self.assertEquals(len(error.errors), 1)

    def test_multiple_errors(self):
        error = EC2Error(payload.sample_ec2_error_messages, 400)
        self.assertEquals(len(error.errors), 2)

    def test_single_error_str(self):
        error = EC2Error(payload.sample_ec2_error_message, 400)
        self.assertEquals(str(error), "Error Message: Message for Error.Code")

    def test_multiple_errors_str(self):
        error = EC2Error(payload.sample_ec2_error_messages, 400)
        self.assertEquals(str(error), "Multiple EC2 Errors.")

    def test_single_error_repr(self):
        error = EC2Error(payload.sample_ec2_error_message, 400)
        self.assertEquals(
            repr(error),
            "<EC2Error object with Error code: Error.Code>")

    def test_multiple_errors_repr(self):
        error = EC2Error(payload.sample_ec2_error_messages, 400)
        self.assertEquals(repr(error), "<EC2Error object with Error count: 2>")

    def test_dupliate_keypair_result(self):
        error = EC2Error(payload.sample_duplicate_keypair_result, 400)
        self.assertEquals(
            error.get_error_messages(), "The key pair 'key1' already exists.")

    def test_dupliate_create_security_group_result(self):
        error = EC2Error(
            payload.sample_duplicate_create_security_group_result, 400)
        self.assertEquals(
            error.get_error_messages(),
            "The security group 'group1' already exists.")

    def test_invalid_create_security_group_result(self):
        error = EC2Error(
            payload.sample_invalid_create_security_group_result, 400)
        self.assertEquals(
            error.get_error_messages(),
            "Specified group name is a reserved name.")

    def test_invalid_client_token_id(self):
        error = EC2Error(payload.sample_invalid_client_token_result, 400)
        self.assertEquals(
            error.get_error_messages(),
            ("The AWS Access Key Id you provided does not exist in our "
             "records."))

    def test_restricted_resource_access_attempt(self):
        error = EC2Error(payload.sample_restricted_resource_result, 400)
        self.assertEquals(
            error.get_error_messages(),
            "Unauthorized attempt to access restricted resource")
