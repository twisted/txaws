# Copyright (c) 2009 Canonical Ltd <duncan.mcgreggor@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from twisted.web.error import Error

from txaws.util import XML


class AWSError(Error):
    """
    A base class for txAWS errors.
    """
    def __init__(self, xml_bytes, status, message=None, response=None):
        super(AWSError, self).__init__(status, message, response)
        if not xml_bytes:
            raise ValueError("XML cannot be empty.")
        self.original = xml_bytes
        self.errors = []
        self.request_id = ""
        self.host_id = ""
        self.parse()

    def __str__(self):
        return self._get_error_message_string()

    def __repr__(self):
        return "<%s object with %s>" % (
            self.__class__.__name__, self._get_error_code_string())

    def _set_request_id(self, tree):
        request_id_node = tree.find(".//RequestID")
        if hasattr(request_id_node, "text"):
            text = request_id_node.text
            if text:
                self.request_id = text

    def _set_host_id(self, tree):
        host_id = tree.find(".//HostID")
        if hasattr(host_id, "text"):
            text = host_id.text
            if text:
                self.host_id = text

    def _get_error_code_string(self):
        count = len(self.errors)
        error_code = self.get_error_codes()
        if count > 1:
            return "Error count: %s" % error_code
        else:
            return "Error code: %s" % error_code

    def _get_error_message_string(self):
        count = len(self.errors)
        error_message = self.get_error_messages()
        if count > 1:
            return "%s." % error_message
        else:
            return "Error Message: %s" % error_message

    def _node_to_dict(self, node):
        data = {}
        for child in node:
            if child.tag and child.text:
                data[child.tag] = child.text
        return data

    def _check_for_html(self, tree):
        if tree.tag == "html":
            message = "Could not parse HTML in the response."
            raise AWSResponseParseError(message)

    def _set_400_error(self, tree):
        """
        This method needs to be implemented by subclasses.
        """

    def _set_500_error(self, tree):
        self._set_request_id(tree)
        self._set_host_id(tree)
        data = self._node_to_dict(tree)
        if data:
            self.errors.append(data)

    def parse(self, xml_bytes=""):
        if not xml_bytes:
            xml_bytes = self.original
        self.original = xml_bytes
        tree = XML(xml_bytes.strip())
        self._check_for_html(tree)
        self._set_request_id(tree)
        if self.status:
            status = int(self.status)
        else:
            status = 400
        if status >= 500:
            self._set_500_error(tree)
        else:
            self._set_400_error(tree)

    def has_error(self, errorString):
        for error in self.errors:
            if errorString in error.values():
                return True
        return False

    def get_error_codes(self):
        count = len(self.errors)
        if count > 1:
            return count
        elif count == 0:
            return
        else:
            return self.errors[0]["Code"]

    def get_error_messages(self):
        count = len(self.errors)
        if count > 1:
            return "Multiple EC2 Errors"
        elif count == 0:
            return "Empty error list"
        else:
            return self.errors[0]["Message"]



class AWSResponseParseError(Exception):
    """
    txAWS was unable to parse the server response.
    """
