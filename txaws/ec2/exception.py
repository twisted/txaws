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

    def __repr__(self):
        pass

    def __str__(self):
        pass

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
