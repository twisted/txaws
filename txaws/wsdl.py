# Copyright (C) 2010-2012 Canonical Ltd.
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""Parse WSDL definitions and generate schemas.

To understand how the machinery in this module works, let's consider the
following bit of the WSDL definition, that specifies the format for
the response of a DescribeKeyPairs query:

  <element name='DescribeKeyPairsResponse'
           type='tns:DescribeKeyPairsResponseType'/>

  <complexType name='DescribeKeyPairsResponseType'>
    <sequence>
      <element name='requestId' type='string'/>
      <element name='keySet' type='tns:DescribeKeyPairsResponseInfoType'/>
    </sequence>
  </complexType>

  <complexType name='DescribeKeyPairsResponseInfoType'>
    <sequence>
      <element name='item' type='tns:DescribeKeyPairsResponseItemType'
               minOccurs='0' maxOccurs='unbounded'/>
    </sequence>
  </complexType>

  <complexType name='DescribeKeyPairsResponseItemType'>
    <sequence>
      <element name='keyName' type='string' />
      <element name='keyFingerprint' type='string' />
  <complexType>

The L{WSDLParser} will take the above XML input and automatically generate
a top-level L{NodeSchema} that can be used to access and modify the XML content
of an actual DescribeKeyPairsResponse payload in an easy way.

The automatically generated L{NodeSchema} object will be the same as the
following manually created one:

>>> child1 = LeafSchema('requestId')
>>> sub_sub_child1 = LeafSchema('key_name')
>>> sub_sub_child2 = LeafSchema('key_fingerprint')
>>> sub_child = NodeSchema('item')
>>> sub_child.add(sub_sub_child1)
>>> sub_child.add(sub_sub_child2)
>>> child2 = SequenceSchema('keySet')
>>> child2.set(sub_child)
>>> schema = NodeSchema('DescribeKeyPairsResponse')
>>> schema.add(child1)
>>> schema.add(child2)

Now this L{NodeSchema} object can be used to access and modify a response
XML payload, for example:

  <DescribeKeyPairsResponse xmlns='http://ec2.amazonaws.com/doc/2008-12-01/'>
    <requestId>3ef0aa1d-57dd-4272</requestId>
    <keySet>
      <item>
        <keyName>some-key</keyName>
        <keyFingerprint>94:88:29:60:cf</keyFingerprint>
      </item>
    </keySet>
  </DescribeKeyPairsResponse>

Let's assume to have an 'xml' variable that holds the XML payload above, now
we can:

>>> response = schema.create(etree.fromstring(xml))
>>> response.requestId
3ef0aa1d-57dd-4272
>>> response.keySet[0].keyName
some-key
>>> response.keySet[0].keyFingerprint
94:88:29:60:cf

Note that there is no upfront parsing, the schema just makes sure that
the response elements one actually accesses are consistent with the
WDSL definition and that all modifications of those items are consistent
as well.
"""
try:
    from lxml import etree
except ImportError:
    etree = None


class WSDLParseError(Exception):
    """Raised when a response doesn't comply with its schema."""


class LeafSchema(object):
    """Schema for a single XML leaf element in a response.

    @param tag: The name of the XML element tag this schema is for.
    """

    def __init__(self, tag):
        self.tag = tag


class NodeSchema(object):
    """Schema for a single XML inner node in a response.

    A L{Node} can have other L{Node} or L{LeafSchema} objects as children.

    @param tag: The name of the XML element tag this schema is for.
    @param _children: Optionally, the schemas for the child nodes, used only
        by tests.
    """

    reserved = ["return"]

    def __init__(self, tag, _children=None):
        self.tag = tag
        self.children = {}
        self.children_min_occurs = {}
        if _children:
            for child in _children:
                self.add(child)

    def create(self, root=None, namespace=None):
        """Create an inner node element.

        @param root: The inner C{etree.Element} the item will be rooted at.
        @result: A L{NodeItem} with the given root, or a new one if none.
        @raises L{ECResponseError}: If the given C{root} has a bad tag.
        """
        if root is not None:
            tag = root.tag
            if root.nsmap:
                namespace = root.nsmap[None]
                tag = tag[len(namespace) + 2:]
            if tag != self.tag:
                raise WSDLParseError("Expected response with tag '%s', but "
                                     "got '%s' instead" % (self.tag, tag))
        return NodeItem(self, root, namespace)

    def dump(self, item):
        """Return the C{etree.Element} of the given L{NodeItem}.

        @param item: The L{NodeItem} to dump.
        """
        return item._root

    def add(self, child, min_occurs=1):
        """Add a child node.

        @param child: The schema for the child node.
        @param min_occurs: The minimum number of times the child node must
            occur, if C{None} is given the default is 1.
        """
        if not min_occurs in (0, 1):
            raise RuntimeError("Unexpected min bound for node schema")
        self.children[child.tag] = child
        self.children_min_occurs[child.tag] = min_occurs
        return child


class NodeItem(object):
    """An inner node item in a tree of response elements.

    @param schema: The L{NodeSchema} this item must comply to.
    @param root: The C{etree.Element} this item is rooted at, if C{None}
        a new one will be created.
    """

    def __init__(self, schema, root=None, namespace=None):
        object.__setattr__(self, "_schema", schema)
        object.__setattr__(self, "_namespace", namespace)
        if root is None:
            tag = self._get_namespace_tag(schema.tag)
            nsmap = None
            if namespace is not None:
                nsmap = {None: namespace}
            root = etree.Element(tag, nsmap=nsmap)
        object.__setattr__(self, "_root", root)

    def __getattr__(self, name):
        """Get the child item with the given C{name}.

        @raises L{WSDLParseError}: In the following cases:
            - The given C{name} is not in the schema.
            - There is more than one element tagged C{name} in the response.
            - No matching element is found in the response and C{name} is
              requred.
            - A required element is present but empty.
        """
        tag = self._get_tag(name)
        schema = self._get_schema(tag)

        child = self._find_child(tag)
        if child is None:
            if isinstance(schema, LeafSchema):
                return self._check_value(tag, None)
            child = self._create_child(tag)

        if isinstance(schema, LeafSchema):
            return self._check_value(tag, child.text)
        return schema.create(child)

    def __setattr__(self, name, value):
        """Set the child item with the given C{name} to the given C{value}.

        Setting a non-leaf child item to C{None} will make it disappear from
        the tree completely.

        @raises L{WSDLParseError}: In the following cases:
            - The given C{name} is not in the schema.
            - There is more than one element tagged C{name} in the response.
            - The given value is C{None} and the element is required.
            - The given C{name} is associated with a non-leaf node, and
              the given C{value} is not C{None}.
            - The given C{name} is associated with a required non-leaf
              and the given C{value} is C{None}.
        """
        tag = self._get_tag(name)
        schema = self._get_schema(tag)
        child = self._find_child(tag)
        if not isinstance(schema, LeafSchema):
            if value is not None:
                raise WSDLParseError("Can't set non-leaf tag '%s'" % tag)

            if isinstance(schema, NodeSchema):
                # Setting a node child item to None means removing it.
                self._check_value(tag, None)
                if child is not None:
                    self._root.remove(child)
            if isinstance(schema, SequenceSchema):
                # Setting a sequence child item to None means removing all
                # its children.
                if child is None:
                    child = self._create_child(tag)
                for item in child.getchildren():
                    child.remove(item)
            return

        if child is None:
            child = self._create_child(tag)
        child.text = self._check_value(tag, value)
        if child.text is None:
            self._root.remove(child)

    def _create_child(self, tag):
        """Create a new child element with the given tag."""
        return etree.SubElement(self._root, self._get_namespace_tag(tag))

    def _find_child(self, tag):
        """Find the child C{etree.Element} with the matching C{tag}.

        @raises L{WSDLParseError}: If more than one such elements are found.
        """
        tag = self._get_namespace_tag(tag)
        children = self._root.findall(tag)
        if len(children) > 1:
            raise WSDLParseError("Duplicate tag '%s'" % tag)
        if len(children) == 0:
            return None
        return children[0]

    def _check_value(self, tag, value):
        """Ensure that the element matching C{tag} can have the given C{value}.

        @param tag: The tag to consider.
        @param value: The value to check
        @return: The unchanged L{value}, if valid.
        @raises L{WSDLParseError}: If the value is invalid.
        """
        if value is None:
            if self._schema.children_min_occurs[tag] > 0:
                raise WSDLParseError("Missing tag '%s'" % tag)
            return value
        return value

    def _get_tag(self, name):
        """Get the L{NodeItem} attribute name for the given C{tag}."""
        if name.endswith("_"):
            if name[:-1] in self._schema.reserved:
                return name[:-1]
        return name

    def _get_namespace_tag(self, tag):
        """Return the given C{tag} with the namespace prefix added, if any."""
        if self._namespace is not None:
            tag = "{%s}%s" % (self._namespace, tag)
        return tag

    def _get_schema(self, tag):
        """Return the child schema for the given C{tag}.

        @raises L{WSDLParseError}: If the tag doesn't belong to the schema.
        """
        schema = self._schema.children.get(tag)
        if not schema:
            raise WSDLParseError("Unknown tag '%s'" % tag)
        return schema

    def to_xml(self):
        """Convert the response to bare bones XML."""
        return etree.tostring(self._root, encoding="utf-8")


class SequenceSchema(object):
    """Schema for a single XML inner node holding a sequence of other nodes.

    @param tag: The name of the XML element tag this schema is for.
    @param _child: Optionally the schema of the items in the sequence, used
        by tests only.
    """

    def __init__(self, tag, _child=None):
        self.tag = tag
        self.child = None
        if _child:
            self.set(_child, 0, "unbounded")

    def create(self, root=None, namespace=None):
        """Create a sequence element with the given root.

        @param root: The C{etree.Element} to root the sequence at, if C{None} a
            new one will be created..
        @result: A L{SequenceItem} with the given root.
        @raises L{ECResponseError}: If the given C{root} has a bad tag.
        """
        if root is not None:
            tag = root.tag
            if root.nsmap:
                namespace = root.nsmap[None]
                tag = tag[len(namespace) + 2:]
            if tag != self.tag:
                raise WSDLParseError("Expected response with tag '%s', but "
                                       "got '%s' instead" % (self.tag, tag))
        return SequenceItem(self, root, namespace)

    def dump(self, item):
        """Return the C{etree.Element} of the given L{SequenceItem}.

        @param item: The L{SequenceItem} to dump.
        """
        return item._root

    def set(self, child, min_occurs=1, max_occurs=1):
        """Set the schema for the sequence children.

        @param child: The schema that children must match.
        @param min_occurs: The minimum number of children the sequence
            must have.
        @param max_occurs: The maximum number of children the sequence
            can have.
        """
        if isinstance(child, LeafSchema):
            raise RuntimeError("Sequence can't have leaf children")
        if self.child is not None:
            raise RuntimeError("Sequence has already a child")
        if min_occurs is None or max_occurs is None:
            raise RuntimeError("Sequence node without min or max")
        if isinstance(child, LeafSchema):
            raise RuntimeError("Sequence node with leaf child type")
        if not child.tag == "item":
            raise RuntimeError("Sequence node with bad child tag")

        self.child = child
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        return child


class SequenceItem(object):
    """A sequence node item in a tree of response elements.

    @param schema: The L{SequenceSchema} this item must comply to.
    @param root: The C{etree.Element} this item is rooted at, if C{None}
        a new one will be created.
    """

    def __init__(self, schema, root=None, namespace=None):
        if root is None:
            root = etree.Element(schema.tag)
        object.__setattr__(self, "_schema", schema)
        object.__setattr__(self, "_root", root)
        object.__setattr__(self, "_namespace", namespace)

    def __getitem__(self, index):
        """Get the item with the given C{index} in the sequence.

        @raises L{WSDLParseError}: In the following cases:
            - If there is no child element with the given C{index}.
            - The given C{index} is higher than the allowed max.
        """
        schema = self._schema.child
        tag = self._schema.tag
        if (self._schema.max_occurs != "unbounded" and
            index > self._schema.max_occurs - 1):
            raise WSDLParseError("Out of range item in tag '%s'" % tag)
        child = self._get_child(self._root.getchildren(), index)
        return schema.create(child)

    def append(self):
        """Append a new item to the sequence, appending it to the end.

        @return: The newly created item.
        @raises L{WSDLParseError}: If the operation would result in having
             more child elements than the allowed max.
        """
        tag = self._schema.tag
        children = self._root.getchildren()
        if len(children) >= self._schema.max_occurs:
            raise WSDLParseError("Too many items in tag '%s'" % tag)
        schema = self._schema.child
        tag = "item"
        if self._namespace is not None:
            tag = "{%s}%s" % (self._namespace, tag)
        child = etree.SubElement(self._root, tag)
        return schema.create(child)

    def __delitem__(self, index):
        """Remove the item with the given C{index} from the sequence.

        @raises L{WSDLParseError}: If the operation would result in having
             less child elements than the required min_occurs, or if no such
             index is found.
        """
        tag = self._schema.tag
        children = self._root.getchildren()
        if len(children) <= self._schema.min_occurs:
            raise WSDLParseError("Not enough items in tag '%s'" % tag)
        self._root.remove(self._get_child(children, index))

    def remove(self, item):
        """Remove the given C{item} from the sequence.

        @raises L{WSDLParseError}: If the operation would result in having
             less child elements than the required min_occurs, or if no such
             index is found.
        """
        for index, child in enumerate(self._root.getchildren()):
            if child is item._root:
                del self[index]
                return item
        raise WSDLParseError("Non existing item in tag '%s'" %
                               self._schema.tag)

    def __iter__(self):
        """Iter all the sequence items in order."""
        schema = self._schema.child
        for child in self._root.iterchildren():
            yield schema.create(child)

    def __len__(self):
        """Return the length of the sequence."""
        return len(self._root.getchildren())

    def _get_child(self, children, index):
        """Return the child with the given index."""
        try:
            return children[index]
        except IndexError:
            raise WSDLParseError("Non existing item in tag '%s'" %
                                   self._schema.tag)


class WSDLParser(object):
    """Build response schemas out of WSDL definitions"""

    leaf_types = ["string", "boolean", "dateTime", "int", "long", "double",
        "integer"]

    def parse(self, wsdl):
        """Parse the given C{wsdl} data and build the associated schemas.

        @param wdsl: A string containing the raw xml of the WDSL definition
            to parse.
        @return: A C{dict} mapping response type names to their schemas.
        """
        parser = etree.XMLParser(remove_blank_text=True, remove_comments=True)
        root = etree.fromstring(wsdl, parser=parser)
        types = {}
        responses = {}
        schemas = {}
        namespace = root.attrib["targetNamespace"]

        for element in root[0][0]:
            self._remove_namespace_from_tag(element)
            if element.tag in ["annotation", "group"]:
                continue
            name = element.attrib["name"]
            if element.tag == "element":
                if name.endswith("Response"):
                    if name in responses:
                        raise RuntimeError("Schema already defined")
                    responses[name] = element
            elif element.tag == "complexType":
                types[name] = [element, False]
            else:
                raise RuntimeError("Top-level element with unexpected tag")

        for name, element in responses.iteritems():
            schemas[name] = self._parse_type(element, types)
            schemas[name].namespace = namespace

        return schemas

    def _remove_namespace_from_tag(self, element):
        tag = element.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        element.tag = tag

    def _parse_type(self, element, types):
        """Parse a 'complexType' element.

        @param element: The top-level complexType element
        @param types: A map of the elements of all available complexType's.
        @return: The schema for the complexType.
        """
        name = element.attrib["name"]
        type = element.attrib["type"]
        if not type.startswith("tns:"):
            raise RuntimeError("Unexpected element type %s" % type)
        type = type[4:]

        [children] = types[type][0]
        types[type][1] = True

        self._remove_namespace_from_tag(children)
        if children.tag not in ("sequence", "choice"):
            raise RuntimeError("Unexpected children type %s" % children.tag)

        if children[0].attrib["name"] == "item":
            schema = SequenceSchema(name)
        else:
            schema = NodeSchema(name)

        for child in children:
            self._remove_namespace_from_tag(child)
            if child.tag == "element":
                name, type, min_occurs, max_occurs = self._parse_child(child)
                if type in self.leaf_types:
                    if max_occurs != 1:
                        raise RuntimeError("Unexpected max value for leaf")
                    if not isinstance(schema, NodeSchema):
                        raise RuntimeError("Attempt to add leaf to a non-node")
                    schema.add(LeafSchema(name), min_occurs=min_occurs)
                else:
                    if name == "item":  # sequence
                        if not isinstance(schema, SequenceSchema):
                            raise RuntimeError("Attempt to set child for "
                                               "non-sequence")
                        schema.set(self._parse_type(child, types),
                                   min_occurs=min_occurs,
                                   max_occurs=max_occurs)
                    else:
                        if max_occurs != 1:
                            raise RuntimeError("Unexpected max for node")
                        if not isinstance(schema, NodeSchema):
                            raise RuntimeError("Unexpected schema type")
                        schema.add(self._parse_type(child, types),
                                   min_occurs=min_occurs)
            elif child.tag == "choice":
                pass
            else:
                raise RuntimeError("Unexpected child type")
        return schema

    def _parse_child(self, child):
        """Parse a single child element.

        @param child: The child C{etree.Element} to parse.
        @return: A tuple C{(name, type, min_occurs, max_occurs)} with the
            details about the given child.
        """
        if set(child.attrib) - set(["name", "type", "minOccurs", "maxOccurs"]):
            raise RuntimeError("Unexpected attribute in child")
        name = child.attrib["name"]
        type = child.attrib["type"].split(":")[1]
        min_occurs = child.attrib.get("minOccurs")
        max_occurs = child.attrib.get("maxOccurs")
        if min_occurs is None:
            min_occurs = "1"
        min_occurs = int(min_occurs)
        if max_occurs is None:
            max_occurs = "1"
        if max_occurs != "unbounded":
            max_occurs = int(max_occurs)
        return name, type, min_occurs, max_occurs
