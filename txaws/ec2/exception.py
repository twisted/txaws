try:
    from xml.etree import ElementTree
except ImportError:
    from elementtree import ElementTree

from txaws.exception import AWSError


class EC2Error(AWSError):
    """
    A error class providing custom methods on EC2 errors.
    """
    def __init__(self, xml):
        if not xml:
            raise ValueError("XML cannot be empty.")
        self.original = xml
        self.errors = []
        self.requestID = ""
        self.parse()

    def __str__(self):
        return self._getErrorMessageString()

    def __repr__(self):
        return "<%s object with %s>" % (
            self.__class__.__name__, self._getErrorCodeString())

    def _getErrorCodeString(self):
        count = len(self.errors)
        if count > 1:
            codeString = "Error count: %s" % count
        else:
            # what if no errors? what if no code?
            codeString = "Error code: %s" % self.errors[0]["Code"]
        return codeString

    def _getErrorMessageString(self):
        count = len(self.errors)
        if count > 1:
            messageString = "Multiple EC2 Errors."
        else:
            messageString = "Error Message: %s" % self.errors[0]["Message"]
        return messageString

    def _nodeToDict(self, node):
        data = {}
        for child in node:
            if child.tag and child.text:
                data[child.tag] = child.text
        return data

    def setRequestID(self, tree):
        requestIDNode = tree.find(".//RequestID")
        if hasattr(requestIDNode, "text"):
            text = requestIDNode.text
            if text:
                self.requestID = text

    def setErrors(self, tree):
        errorsNode = tree.find(".//Errors")
        if errorsNode:
            for error in errorsNode:
                data = self._nodeToDict(error)
                if data:
                    self.errors.append(data)

    def parse(self, xml=""):
        if not xml:
            xml = self.original
        tree = ElementTree.fromstring(xml.strip())
        self.setRequestID(tree)
        self.setErrors(tree)

    def hasError(self, errorString):
        for error in self.errors:
            if errorString in error.values():
                return True
        return False
