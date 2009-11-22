# Copyright (c) 2009 Canonical Ltd <duncan.mcgreggor@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from twisted.trial.unittest import TestCase

from txaws.exception import AWSResponseParseError
from txaws.s3.exception import S3Error
from txaws.testing import payload
from txaws.util import XML


REQUEST_ID = "0ef9fc37-6230-4d81-b2e6-1b36277d4247"


class S3ErrorTestCase(TestCase):

    def test_set_400_errors(self):
        xml = "<Error><Code>1</Code><Message>2</Message></Error>"
        error = S3Error("<dummy />")
        error._set_400_errors(XML(xml))
        self.assertEquals(error.errors[0]["Code"], "1")
        self.assertEquals(error.errors[0]["Message"], "2")

    def test_set_500_error(self):
        xml = "<Error><Code>500</Code><Message>Oops</Message></Error>"
        error = S3Error("<dummy />")
        error._set_500_error(XML(xml))
        self.assertEquals(error.errors[0]["Code"], "500")
        self.assertEquals(error.errors[0]["Message"], "Oops")

    def test_set_empty_errors(self):
        xml = "<a><Errors /><b /></a>"
        error = S3Error("<dummy />")
        error._set_400_errors(XML(xml))
        self.assertEquals(error.errors, [])

    def test_set_empty_error(self):
        xml = "<a><Errors><Error /><Error /></Errors><b /></a>"
        error = S3Error("<dummy />")
        error._set_400_errors(XML(xml))
        self.assertEquals(error.errors, [])

    def test_parse_without_xml(self):
        xml = "<dummy />"
        error = S3Error(xml)
        error.parse()
        self.assertEquals(error.original, xml)

    def test_parse_with_xml(self):
        xml1 = "<dummy1 />"
        xml2 = "<dummy2 />"
        error = S3Error(xml1)
        error.parse(xml2)
        self.assertEquals(error.original, xml2)

    def test_parse_html(self):
        xml = "<html><body>a page</body></html>"
        self.assertRaises(AWSResponseParseError, S3Error, xml)

    def test_has_error(self):
        xml = "<Error><Code>Code1</Code><Message>2</Message></Error>"
        error = S3Error(xml)
        self.assertTrue(error.has_error("Code1"))

    def test_empty_xml(self):
        self.assertRaises(ValueError, S3Error, "")

    def test_empty_error_node(self):
        xml = "<Error />"
        error = S3Error(xml)
        self.assertEquals(error.errors, [])

    def test_no_error_message_node(self):
        xml = "<Error><Code /></Error>"
        error = S3Error(xml)
        self.assertEquals(error.errors, [])

    def test_zero_get_error_messages(self):
        xml = "<Response><RequestID /></Response>"
        error = S3Error(xml)
        self.assertEquals(error.get_error_messages(), "Empty error list")

    def test_get_error_code(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result)
        self.assertEquals(error.get_error_code(), "InvalidAccessKeyId")

    def test_get_error_message(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result)
        self.assertEquals(
            error.get_error_message(),
            ("The AWS Access Key Id you provided does not exist in our "
             "records."))

    def test_error_count(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result)
        self.assertEquals(len(error.errors), 1)

    def test_error_repr(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result)
        self.assertEquals(
            repr(error),
            "<S3Error object with Error code: InvalidAccessKeyId>")

    def test_signature_mismatch_result(self):
        error = S3Error(payload.sample_s3_signature_mismatch)
        self.assertEquals(
            error.get_error_messages(), 
            ("The request signature we calculated does not match the "
             "signature you provided. Check your key and signing method."))

    def test_invalid_access_key_result(self):
        error = S3Error(payload.sample_s3_invalid_access_key_result)
        self.assertEquals(
            error.get_error_messages(),
            ("The AWS Access Key Id you provided does not exist in our "
             "records."))

    def test_internal_error_result(self):
        error = S3Error(payload.sample_server_internal_error_result)
        self.assertEquals(
            error.get_error_messages(),
            "We encountered an internal error. Please try again.")
