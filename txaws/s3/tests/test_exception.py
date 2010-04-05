# Copyright (c) 2009 Canonical Ltd <duncan.mcgreggor@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from twisted.trial.unittest import TestCase

from txaws.s3.exception import S3Error
from txaws.testing import payload
from txaws.util import XML


REQUEST_ID = "0ef9fc37-6230-4d81-b2e6-1b36277d4247"


class S3ErrorTestCase(TestCase):

    def test_set_400_error(self):
        xml = "<Error><Code>1</Code><Message>2</Message></Error>"
        error = S3Error("<dummy />", 400)
        error._set_400_error(XML(xml))
        self.assertEquals(error.errors[0]["Code"], "1")
        self.assertEquals(error.errors[0]["Message"], "2")

    def test_get_error_code(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result, 400)
        self.assertEquals(error.get_error_code(), "InvalidAccessKeyId")

    def test_get_error_message(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result, 400)
        self.assertEquals(
            error.get_error_message(),
            ("The AWS Access Key Id you provided does not exist in our "
             "records."))

    def test_error_count(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result, 400)
        self.assertEquals(len(error.errors), 1)

    def test_error_repr(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result, 400)
        self.assertEquals(
            repr(error),
            "<S3Error object with Error code: InvalidAccessKeyId>")

    def test_signature_mismatch_result(self):
        error = S3Error(payload.sample_s3_signature_mismatch, 400)
        self.assertEquals(
            error.get_error_messages(),
            ("The request signature we calculated does not match the "
             "signature you provided. Check your key and signing method."))

    def test_invalid_access_key_result(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result, 400)
        self.assertEquals(
            error.get_error_messages(),
            ("The AWS Access Key Id you provided does not exist in our "
             "records."))

    def test_internal_error_result(self):
        error = S3Error(payload.sample_server_internal_error_result, 400)
        self.assertEquals(
            error.get_error_messages(),
            "We encountered an internal error. Please try again.")
