# Copyright (c) 2009 Canonical Ltd <duncan.mcgreggor@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from twisted.trial.unittest import TestCase

from txaws.exception import AWSError
from txaws.exception import AWSResponseParseError
from txaws.util import XML


REQUEST_ID = "0ef9fc37-6230-4d81-b2e6-1b36277d4247"


class AWSErrorTestCase(TestCase):

    def test_creation(self):
        error = AWSError("<dummy1 />", 500, "Server Error", "<dummy2 />")
        self.assertEquals(error.status, 500)
        self.assertEquals(error.response, "<dummy2 />")
        self.assertEquals(error.original, "<dummy1 />")
        self.assertEquals(error.errors, [])
        self.assertEquals(error.request_id, "")

    def test_node_to_dict(self):
        xml = "<parent><child1>text1</child1><child2>text2</child2></parent>"
        error = AWSError("<dummy />", 400)
        data = error._node_to_dict(XML(xml))
        self.assertEquals(data, {"child1": "text1", "child2": "text2"})

    def test_set_request_id(self):
        xml = "<a><b /><RequestID>%s</RequestID></a>" % REQUEST_ID
        error = AWSError("<dummy />", 400)
        error._set_request_id(XML(xml))
        self.assertEquals(error.request_id, REQUEST_ID)

    def test_set_host_id(self):
        host_id = "ASD@#FDG$E%FG"
        xml = "<a><b /><HostID>%s</HostID></a>" % host_id
        error = AWSError("<dummy />", 400)
        error._set_host_id(XML(xml))
        self.assertEquals(error.host_id, host_id)

    def test_set_empty_errors(self):
        xml = "<a><Errors /><b /></a>"
        error = AWSError("<dummy />", 500)
        error._set_500_error(XML(xml))
        self.assertEquals(error.errors, [])

    def test_set_empty_error(self):
        xml = "<a><Errors><Error /><Error /></Errors><b /></a>"
        error = AWSError("<dummy />", 500)
        error._set_500_error(XML(xml))
        self.assertEquals(error.errors, [])

    def test_parse_without_xml(self):
        xml = "<dummy />"
        error = AWSError(xml, 400)
        error.parse()
        self.assertEquals(error.original, xml)

    def test_parse_with_xml(self):
        xml1 = "<dummy1 />"
        xml2 = "<dummy2 />"
        error = AWSError(xml1, 400)
        error.parse(xml2)
        self.assertEquals(error.original, xml2)

    def test_parse_html(self):
        xml = "<html><body>a page</body></html>"
        self.assertRaises(AWSResponseParseError, AWSError, xml, 400)

    def test_empty_xml(self):
        self.assertRaises(ValueError, AWSError, "", 400)

    def test_no_request_id(self):
        errors = "<Errors><Error><Code /><Message /></Error></Errors>"
        xml = "<Response>%s<RequestID /></Response>" % errors
        error = AWSError(xml, 400)
        self.assertEquals(error.request_id, "")

    def test_no_request_id_node(self):
        errors = "<Errors><Error><Code /><Message /></Error></Errors>"
        xml = "<Response>%s</Response>" % errors
        error = AWSError(xml, 400)
        self.assertEquals(error.request_id, "")

    def test_no_errors_node(self):
        xml = "<Response><RequestID /></Response>"
        error = AWSError(xml, 400)
        self.assertEquals(error.errors, [])

    def test_no_error_node(self):
        xml = "<Response><Errors /><RequestID /></Response>"
        error = AWSError(xml, 400)
        self.assertEquals(error.errors, [])

    def test_no_error_code_node(self):
        errors = "<Errors><Error><Message /></Error></Errors>"
        xml = "<Response>%s<RequestID /></Response>" % errors
        error = AWSError(xml, 400)
        self.assertEquals(error.errors, [])

    def test_no_error_message_node(self):
        errors = "<Errors><Error><Code /></Error></Errors>"
        xml = "<Response>%s<RequestID /></Response>" % errors
        error = AWSError(xml, 400)
        self.assertEquals(error.errors, [])

    def test_set_500_error(self):
        xml = "<Error><Code>500</Code><Message>Oops</Message></Error>"
        error = AWSError("<dummy />", 500)
        error._set_500_error(XML(xml))
        self.assertEquals(error.errors[0]["Code"], "500")
        self.assertEquals(error.errors[0]["Message"], "Oops")
