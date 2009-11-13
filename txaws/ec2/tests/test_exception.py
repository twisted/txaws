# Copyright (c) 2009 Canonical Ltd <duncan.mcgreggor@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from twisted.trial.unittest import TestCase

from txaws.ec2.exception import EC2Error
from txaws.exception import AWSResponseParseError
from txaws.testing import payload
from txaws.util import XML


REQUEST_ID = "0ef9fc37-6230-4d81-b2e6-1b36277d4247"


class EC2ErrorTestCase(TestCase):

    def test_creation(self):
        error = EC2Error("<dummy1 />", 400, "Not Found", "<dummy2 />")
        self.assertEquals(error.status, 400)
        self.assertEquals(error.response, "<dummy2 />")
        self.assertEquals(error.original, "<dummy1 />")
        self.assertEquals(error.errors, [])
        self.assertEquals(error.request_id, "")

    def test_node_to_dict(self):
        xml = "<parent><child1>text1</child1><child2>text2</child2></parent>"
        error = EC2Error("<dummy />")
        data = error._node_to_dict(XML(xml))
        self.assertEquals(data, {"child1": "text1", "child2": "text2"})

    def test_set_request_id(self):
        xml = "<a><b /><RequestID>%s</RequestID></a>" % REQUEST_ID
        error = EC2Error("<dummy />")
        error._set_request_id(XML(xml))
        self.assertEquals(error.request_id, REQUEST_ID)

    def test_set_400_errors(self):
        errorsXML = "<Error><Code>1</Code><Message>2</Message></Error>"
        xml = "<a><Errors>%s</Errors><b /></a>" % errorsXML
        error = EC2Error("<dummy />")
        error._set_400_errors(XML(xml))
        self.assertEquals(error.errors[0]["Code"], "1")
        self.assertEquals(error.errors[0]["Message"], "2")

    def test_set_host_id(self):
        host_id = "ASD@#FDG$E%FG"
        xml = "<a><b /><HostID>%s</HostID></a>" % host_id
        error = EC2Error("<dummy />")
        error._set_host_id(XML(xml))
        self.assertEquals(error.host_id, host_id)

    def test_set_500_error(self):
        xml = "<Error><Code>500</Code><Message>Oops</Message></Error>"
        error = EC2Error("<dummy />")
        error._set_500_error(XML(xml))
        self.assertEquals(error.errors[0]["Code"], "500")
        self.assertEquals(error.errors[0]["Message"], "Oops")

    def test_set_empty_errors(self):
        xml = "<a><Errors /><b /></a>"
        error = EC2Error("<dummy />")
        error._set_400_errors(XML(xml))
        self.assertEquals(error.errors, [])

    def test_set_empty_error(self):
        xml = "<a><Errors><Error /><Error /></Errors><b /></a>"
        error = EC2Error("<dummy />")
        error._set_400_errors(XML(xml))
        self.assertEquals(error.errors, [])

    def test_parse_without_xml(self):
        xml = "<dummy />"
        error = EC2Error(xml)
        error.parse()
        self.assertEquals(error.original, xml)

    def test_parse_with_xml(self):
        xml1 = "<dummy1 />"
        xml2 = "<dummy2 />"
        error = EC2Error(xml2)
        error.parse(xml2)
        self.assertEquals(error.original, xml2)

    def test_parse_html(self):
        xml = "<html><body>a page</body></html>"
        self.assertRaises(AWSResponseParseError, EC2Error, xml)

    def test_has_error(self):
        errorsXML = "<Error><Code>Code1</Code><Message>2</Message></Error>"
        xml = "<a><Errors>%s</Errors><b /></a>" % errorsXML
        error = EC2Error(xml)
        self.assertTrue(error.has_error("Code1"))

    def test_single_error(self):
        error = EC2Error(payload.sample_ec2_error_message)
        self.assertEquals(len(error.errors), 1)

    def test_multiple_errors(self):
        error = EC2Error(payload.sample_ec2_error_messages)
        self.assertEquals(len(error.errors), 2)

    def test_empty_xml(self):
        self.assertRaises(ValueError, EC2Error, "")

    def test_no_request_id(self):
        errors = "<Errors><Error><Code /><Message /></Error></Errors>"
        xml = "<Response>%s<RequestID /></Response>" % errors
        error = EC2Error(xml)
        self.assertEquals(error.request_id, "")

    def test_no_request_id_node(self):
        errors = "<Errors><Error><Code /><Message /></Error></Errors>"
        xml = "<Response>%s</Response>" % errors
        error = EC2Error(xml)
        self.assertEquals(error.request_id, "")

    def test_no_errors_node(self):
        xml = "<Response><RequestID /></Response>"
        error = EC2Error(xml)
        self.assertEquals(error.errors, [])

    def test_no_error_node(self):
        xml = "<Response><Errors /><RequestID /></Response>"
        error = EC2Error(xml)
        self.assertEquals(error.errors, [])

    def test_no_error_code_node(self):
        errors = "<Errors><Error><Message /></Error></Errors>"
        xml = "<Response>%s<RequestID /></Response>" % errors
        error = EC2Error(xml)
        self.assertEquals(error.errors, [])

    def test_no_error_message_node(self):
        errors = "<Errors><Error><Code /></Error></Errors>"
        xml = "<Response>%s<RequestID /></Response>" % errors
        error = EC2Error(xml)
        self.assertEquals(error.errors, [])

    def test_single_get_error_codes(self):
        error = EC2Error(payload.sample_ec2_error_message)
        self.assertEquals(error.get_error_codes(), "Error.Code")

    def test_multiple_get_error_codes(self):
        error = EC2Error(payload.sample_ec2_error_messages)
        self.assertEquals(error.get_error_codes(), 2)

    def test_zero_get_error_codes(self):
        xml = "<Response><RequestID /></Response>"
        error = EC2Error(xml)
        self.assertEquals(error.get_error_codes(), None)

    def test_single_get_error_messages(self):
        error = EC2Error(payload.sample_ec2_error_message)
        self.assertEquals(error.get_error_messages(), "Message for Error.Code")

    def test_multiple_get_error_messages(self):
        error = EC2Error(payload.sample_ec2_error_messages)
        self.assertEquals(error.get_error_messages(), "Multiple EC2 Errors")

    def test_zero_get_error_messages(self):
        xml = "<Response><RequestID /></Response>"
        error = EC2Error(xml)
        self.assertEquals(error.get_error_messages(), "Empty error list")

    def test_single_error_str(self):
        error = EC2Error(payload.sample_ec2_error_message)
        self.assertEquals(str(error), "Error Message: Message for Error.Code")

    def test_multiple_errors_str(self):
        error = EC2Error(payload.sample_ec2_error_messages)
        self.assertEquals(str(error), "Multiple EC2 Errors.")

    def test_single_error_repr(self):
        error = EC2Error(payload.sample_ec2_error_message)
        self.assertEquals(
            repr(error),
            "<EC2Error object with Error code: Error.Code>")

    def test_multiple_errors_repr(self):
        error = EC2Error(payload.sample_ec2_error_messages)
        self.assertEquals(repr(error), "<EC2Error object with Error count: 2>")

    def test_dupliate_keypair_result(self):
        error = EC2Error(payload.sample_duplicate_keypair_result)
        self.assertEquals(
            error.get_error_messages(), "The key pair 'key1' already exists.")

    def test_dupliate_create_security_group_result(self):
        error = EC2Error(payload.sample_duplicate_create_security_group_result)
        self.assertEquals(
            error.get_error_messages(),
            "The security group 'group1' already exists.")

    def test_invalid_create_security_group_result(self):
        error = EC2Error(payload.sample_invalid_create_security_group_result)
        self.assertEquals(
            error.get_error_messages(),
            "Specified group name is a reserved name.")

    def test_invalid_client_token_id(self):
        error = EC2Error(payload.sample_invalid_client_token_result)
        self.assertEquals(
            error.get_error_messages(),
            ("The AWS Access Key Id you provided does not exist in our "
             "records."))

    def test_restricted_resource_access_attempt(self):
        error = EC2Error(payload.sample_restricted_resource_result)
        self.assertEquals(
            error.get_error_messages(), 
            "Unauthorized attempt to access restricted resource")
