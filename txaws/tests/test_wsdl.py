# Copyright (C) 2010-2012 Canonical Ltd.
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import os
from twisted.trial.unittest import TestCase

from txaws.wsdl import (
    WSDLParseError, LeafSchema, NodeSchema, NodeItem, SequenceSchema,
    SequenceItem, WSDLParser, etree)


class WsdlBaseTestCase(TestCase):

    if not etree:
        skip = "lxml is either not installed or broken on your system."


class NodeSchemaTestCase(WsdlBaseTestCase):

    def test_create_with_bad_tag(self):
        """
        L{NodeSchema.create} raises an error if the tag of the given element
        doesn't match the expected one.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        root = etree.fromstring("<egg><bar>spam</bar></egg>")
        error = self.assertRaises(WSDLParseError, schema.create, root)
        self.assertEqual("Expected response with tag 'foo', but got "
                         "'egg' instead", error.args[0])

    def test_add_with_invalid_min(self):
        """
        L{NodeSchema.add} allows the C{min_occurs} parameter to only be
        C{None}, zero or one.
        """
        schema = NodeSchema("foo")
        self.assertRaises(RuntimeError, schema.add, LeafSchema("bar"),
                          min_occurs=-1)
        self.assertRaises(RuntimeError, schema.add, LeafSchema("bar"),
                          min_occurs=2)

    def test_dump(self):
        """
        L{NodeSchema.dump} creates an L{etree.Element} out of a L{NodeItem}.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        foo = NodeItem(schema)
        foo.bar = "spam"
        self.assertEqual("<foo><bar>spam</bar></foo>",
                         etree.tostring(schema.dump(foo)))

    def test_dump_with_multiple_children(self):
        """
        L{NodeSchema.dump} supports multiple children.
        """
        schema = NodeSchema("foo", [LeafSchema("bar"), LeafSchema("egg")])
        foo = NodeItem(schema)
        foo.bar = "spam1"
        foo.egg = "spam2"
        self.assertEqual("<foo><bar>spam1</bar><egg>spam2</egg></foo>",
                         etree.tostring(schema.dump(foo)))

    def test_dump_with_missing_attribute(self):
        """
        L{NodeSchema.dump} ignores missing attributes if C{min_occurs} is zero.
        """
        schema = NodeSchema("foo")
        schema.add(LeafSchema("bar"), min_occurs=0)
        foo = NodeItem(schema)
        self.assertEqual("<foo/>", etree.tostring(schema.dump(foo)))


class NodeItemTestCase(WsdlBaseTestCase):

    def test_get(self):
        """
        The child leaf elements of a L{NodeItem} can be accessed as attributes.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        root = etree.fromstring("<foo><bar>egg</bar></foo>")
        foo = schema.create(root)
        self.assertEqual("egg", foo.bar)

    def test_get_with_many_children(self):
        """
        Multiple children are supported.
        """
        schema = NodeSchema("foo", [LeafSchema("bar"), LeafSchema("egg")])
        root = etree.fromstring("<foo><bar>spam1</bar><egg>spam2</egg></foo>")
        foo = schema.create(root)
        self.assertEqual("spam1", foo.bar)
        self.assertEqual("spam2", foo.egg)

    def test_get_with_namespace(self):
        """
        The child leaf elements of a L{NodeItem} can be accessed as attributes.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        root = etree.fromstring("<foo xmlns=\"spam\"><bar>egg</bar></foo>")
        foo = schema.create(root)
        self.assertEqual("egg", foo.bar)

    def test_get_with_unknown_tag(self):
        """
        An error is raised when trying to access an attribute not in the
        schema.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        root = etree.fromstring("<foo><bar>egg</bar><spam>boom</spam></foo>")
        foo = schema.create(root)
        error = self.assertRaises(WSDLParseError, getattr, foo, "spam")
        self.assertEqual("Unknown tag 'spam'", error.args[0])

    def test_get_with_duplicate_tag(self):
        """
        An error is raised when trying to access an attribute associated
        with a tag that appears more than once.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        root = etree.fromstring("<foo><bar>spam1</bar><bar>spam2</bar></foo>")
        item = schema.create(root)
        error = self.assertRaises(WSDLParseError, getattr, item, "bar")
        self.assertEqual("Duplicate tag 'bar'", error.args[0])

    def test_get_with_missing_required_tag(self):
        """
        An error is raised when trying to access a required attribute and
        the associated tag is missing.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        root = etree.fromstring("<foo></foo>")
        item = schema.create(root)
        error = self.assertRaises(WSDLParseError, getattr, item, "bar")
        self.assertEqual("Missing tag 'bar'", error.args[0])

    def test_get_with_empty_required_tag(self):
        """
        An error is raised if an expected required tag is found but has and
        empty value.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        root = etree.fromstring("<foo><bar/></foo>")
        item = schema.create(root)
        error = self.assertRaises(WSDLParseError, getattr, item, "bar")
        self.assertEqual("Missing tag 'bar'", error.args[0])

    def test_get_with_non_required_tag(self):
        """
        No error is raised if a tag is missing and its min count is zero.
        """
        schema = NodeSchema("foo")
        schema.add(LeafSchema("bar"), min_occurs=0)
        root = etree.fromstring("<foo></foo>")
        foo = schema.create(root)
        self.assertIdentical(None, foo.bar)

    def test_get_with_reserved_keyword(self):
        """
        Attributes associated to tags named against required attributes can
        be accessed appending a '_' to the name.
        """
        schema = NodeSchema("foo", [LeafSchema("return")])
        root = etree.fromstring("<foo><return>true</return></foo>")
        foo = schema.create(root)
        self.assertEqual("true", foo.return_)

    def test_get_with_nested(self):
        """
        It is possible to access nested nodes.
        """
        schema = NodeSchema("foo", [NodeSchema("bar", [LeafSchema("egg")])])
        root = etree.fromstring("<foo><bar><egg>spam</egg></bar></foo>")
        foo = schema.create(root)
        self.assertEqual("spam", foo.bar.egg)

    def test_get_with_non_required_nested(self):
        """
        It is possible to access a non-required nested node that has no
        associated element in the XML yet, in that case a new element is
        created for it.
        """
        schema = NodeSchema("foo")
        schema.add(NodeSchema("bar", [LeafSchema("egg")]), min_occurs=0)
        root = etree.fromstring("<foo/>")
        foo = schema.create(root)
        foo.bar.egg = "spam"
        self.assertEqual("<foo><bar><egg>spam</egg></bar></foo>",
                         etree.tostring(schema.dump(foo)))

    def test_set_with_unknown_tag(self):
        """
        An error is raised when trying to set an attribute not in the schema.
        """
        schema = NodeSchema("foo")
        foo = schema.create()
        error = self.assertRaises(WSDLParseError, setattr, foo, "bar", "egg")
        self.assertEqual("Unknown tag 'bar'", error.args[0])

    def test_set_with_duplicate_tag(self):
        """
        An error is raised when trying to set an attribute associated
        with a tag that appears more than once.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        root = etree.fromstring("<foo><bar>spam1</bar><bar>spam2</bar></foo>")
        foo = schema.create(root)
        error = self.assertRaises(WSDLParseError, setattr, foo, "bar", "egg")
        self.assertEqual("Duplicate tag 'bar'", error.args[0])

    def test_set_with_required_tag(self):
        """
        An error is raised when trying to set a required attribute to C{None}.
        """
        schema = NodeSchema("foo", [LeafSchema("bar")])
        root = etree.fromstring("<foo><bar>spam</bar></foo>")
        foo = schema.create(root)
        error = self.assertRaises(WSDLParseError, setattr, foo, "bar", None)
        self.assertEqual("Missing tag 'bar'", error.args[0])
        self.assertEqual("spam", foo.bar)

    def test_set_with_non_required_tag(self):
        """
        It is possible to set a non-required tag value to C{None}, in that
        case the element will be removed if present.
        """
        schema = NodeSchema("foo")
        schema.add(LeafSchema("bar"), min_occurs=0)
        root = etree.fromstring("<foo><bar>spam</bar></foo>")
        foo = schema.create(root)
        foo.bar = None
        self.assertEqual("<foo/>", etree.tostring(schema.dump(foo)))

    def test_set_with_non_leaf_tag(self):
        """
        An error is raised when trying to set a non-leaf attribute to
        a value other than C{None}.
        """
        schema = NodeSchema("foo", [NodeSchema("bar", [LeafSchema("egg")])])
        root = etree.fromstring("<foo><bar><egg>spam</egg></bar></foo>")
        foo = schema.create(root)
        error = self.assertRaises(WSDLParseError, setattr, foo, "bar", "yo")
        self.assertEqual("Can't set non-leaf tag 'bar'", error.args[0])

    def test_set_with_optional_node_tag(self):
        """
        It is possible to set an optional node tag to C{None}, in that
        case it will be removed from the tree.
        """
        schema = NodeSchema("foo")
        schema.add(NodeSchema("bar", [LeafSchema("egg")]), min_occurs=0)
        root = etree.fromstring("<foo><bar><egg>spam</egg></bar></foo>")
        foo = schema.create(root)
        foo.bar = None
        self.assertEqual("<foo/>", etree.tostring(schema.dump(foo)))

    def test_set_with_sequence_tag(self):
        """
        It is possible to set a sequence tag to C{None}, in that case
        all its children will be removed
        """
        schema = NodeSchema("foo")
        schema.add(SequenceSchema("bar",
                                  NodeSchema("item", [LeafSchema("egg")])))
        root = etree.fromstring("<foo>"
                                "<bar><item><egg>spam</egg></item></bar><"
                                "/foo>")
        foo = schema.create(root)
        foo.bar = None
        self.assertEqual("<foo><bar/></foo>", etree.tostring(schema.dump(foo)))

    def test_set_with_required_non_leaf_tag(self):
        """
        An error is raised when trying to set a required non-leaf tag
        to C{None}.
        """
        schema = NodeSchema("foo", [NodeSchema("bar", [LeafSchema("egg")])])
        root = etree.fromstring("<foo><bar><egg>spam</egg></bar></foo>")
        foo = schema.create(root)
        error = self.assertRaises(WSDLParseError, setattr, foo, "bar", None)
        self.assertEqual("Missing tag 'bar'", error.args[0])
        self.assertTrue(hasattr(foo, "bar"))


class SequenceSchemaTestCase(WsdlBaseTestCase):

    def test_create_with_bad_tag(self):
        """
        L{SequenceSchema.create} raises an error if the tag of the given
        element doesn't match the expected one.
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<spam><item><bar>egg</bar></item></spam>")
        error = self.assertRaises(WSDLParseError, schema.create, root)
        self.assertEqual("Expected response with tag 'foo', but got "
                         "'spam' instead", error.args[0])

    def test_set_with_leaf(self):
        """
        L{SequenceSchema.set} raises an error if the given child is a leaf node
        """
        schema = SequenceSchema("foo")
        error = self.assertRaises(RuntimeError, schema.set, LeafSchema("bar"))
        self.assertEqual("Sequence can't have leaf children", str(error))

    def test_set_with_previous_child(self):
        """
        L{SequenceSchema.set} raises an error if the sequence has already
        a child.
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        error = self.assertRaises(RuntimeError, schema.set, NodeSchema("egg"))
        self.assertEqual("Sequence has already a child", str(error))

    def test_set_with_no_min_or_max(self):
        """
        L{SequenceSchema.set} raises an error if no values are provided for the
        min and max parameters.
        """
        schema = SequenceSchema("foo")
        child = NodeSchema("item", [LeafSchema("bar")])
        error = self.assertRaises(RuntimeError, schema.set, child,
                                  min_occurs=0, max_occurs=None)
        self.assertEqual("Sequence node without min or max", str(error))
        error = self.assertRaises(RuntimeError, schema.set, child,
                                  min_occurs=None, max_occurs=1)
        self.assertEqual("Sequence node without min or max", str(error))

    def test_dump(self):
        """
        L{SequenceSchema.dump} creates a L{etree.Element} out of
        a L{SequenceItem}.
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        foo = SequenceItem(schema)
        foo.append().bar = "egg"
        self.assertEqual("<foo><item><bar>egg</bar></item></foo>",
                         etree.tostring(schema.dump(foo)))

    def test_dump_with_many_items(self):
        """
        L{SequenceSchema.dump} supports many child items in the sequence.
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        foo = SequenceItem(schema)
        foo.append().bar = "spam0"
        foo.append().bar = "spam1"
        self.assertEqual("<foo>"
                         "<item><bar>spam0</bar></item>"
                         "<item><bar>spam1</bar></item>"
                         "</foo>",
                         etree.tostring(schema.dump(foo)))


class SequenceItemTestCase(WsdlBaseTestCase):

    def test_get(self):
        """
        The child elements of a L{SequenceItem} can be accessed as attributes.
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<foo><item><bar>egg</bar></item></foo>")
        foo = schema.create(root)
        self.assertEqual("egg", foo[0].bar)

    def test_get_items(self):
        """L{SequenceItem} supports elements with many child items."""
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<foo>"
                                "<item><bar>egg0</bar></item>"
                                "<item><bar>egg1</bar></item>"
                                "</foo>")
        foo = schema.create(root)
        self.assertEqual("egg0", foo[0].bar)
        self.assertEqual("egg1", foo[1].bar)

    def test_get_with_namespace(self):
        """
        The child elements of a L{SequenceItem} can be accessed as attributes.
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<foo xmlns=\"spam\">"
                                "<item><bar>egg</bar></item>"
                                "</foo>")
        foo = schema.create(root)
        self.assertEqual("egg", foo[0].bar)

    def test_get_with_non_existing_index(self):
        """An error is raised when trying to access a non existing item."""
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<foo><item><bar>egg</bar></item></foo>")
        foo = schema.create(root)
        error = self.assertRaises(WSDLParseError, foo.__getitem__, 1)
        self.assertEqual("Non existing item in tag 'foo'", error.args[0])

    def test_get_with_index_higher_than_max(self):
        """
        An error is raised when trying to access an item above the allowed
        max value.
        """
        schema = SequenceSchema("foo")
        schema.set(NodeSchema("item", [LeafSchema("bar")]), min_occurs=0,
                   max_occurs=1)
        root = etree.fromstring("<foo>"
                                "<item><bar>egg0</bar></item>"
                                "<item><bar>egg1</bar></item>"
                                "</foo>")
        foo = schema.create(root)
        error = self.assertRaises(WSDLParseError, foo.__getitem__, 1)
        self.assertEqual("Out of range item in tag 'foo'", error.args[0])

    def test_append(self):
        """
        L{SequenceItem.append} adds a new item to the sequence, appending it
        at the end.
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<foo><item><bar>egg0</bar></item></foo>")
        foo = schema.create(root)
        foo.append().bar = "egg1"
        self.assertEqual("egg1", foo[1].bar)
        self.assertEqual("<foo>"
                         "<item><bar>egg0</bar></item>"
                         "<item><bar>egg1</bar></item>"
                         "</foo>",
                         etree.tostring(schema.dump(foo)))

    def test_append_with_too_many_items(self):
        """
        An error is raised when trying to append items above the max.
        """
        schema = SequenceSchema("foo")
        schema.set(NodeSchema("item", [LeafSchema("bar")]), min_occurs=0,
                   max_occurs=1)
        root = etree.fromstring("<foo><item><bar>egg</bar></item></foo>")
        foo = schema.create(root)
        error = self.assertRaises(WSDLParseError, foo.append)
        self.assertEqual("Too many items in tag 'foo'", error.args[0])
        self.assertEqual(1, len(list(foo)))

    def test_delitem(self):
        """
        L{SequenceItem.__delitem__} removes from the sequence the item with the
        given index.
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<foo>"
                                "<item><bar>egg0</bar></item>"
                                "<item><bar>egg1</bar></item>"
                                "</foo>")
        foo = schema.create(root)
        del foo[0]
        self.assertEqual("egg1", foo[0].bar)
        self.assertEqual("<foo><item><bar>egg1</bar></item></foo>",
                         etree.tostring(schema.dump(foo)))

    def test_delitem_with_not_enough_items(self):
        """
        L{SequenceItem.__delitem__} raises an error if trying to remove an item
        would make the sequence shorter than the required minimum.
        """
        schema = SequenceSchema("foo")
        schema.set(NodeSchema("item", [LeafSchema("bar")]), min_occurs=1,
                   max_occurs=10)
        root = etree.fromstring("<foo><item><bar>egg</bar></item></foo>")
        foo = schema.create(root)
        error = self.assertRaises(WSDLParseError, foo.__delitem__, 0)
        self.assertEqual("Not enough items in tag 'foo'", error.args[0])
        self.assertEqual(1, len(list(foo)))

    def test_remove(self):
        """
        L{SequenceItem.remove} removes the given item from the sequence.
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<foo>"
                                "<item><bar>egg0</bar></item>"
                                "<item><bar>egg1</bar></item>"
                                "</foo>")
        foo = schema.create(root)
        foo.remove(foo[0])
        self.assertEqual("egg1", foo[0].bar)
        self.assertEqual("<foo><item><bar>egg1</bar></item></foo>",
                         etree.tostring(schema.dump(foo)))

    def test_remove_with_non_existing_item(self):
        """
        L{SequenceItem.remove} raises an exception when trying to remove a
        non existing item
        """
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<foo><item><bar>egg</bar></item></foo>")
        foo = schema.create(root)
        item = foo.remove(foo[0])
        error = self.assertRaises(WSDLParseError, foo.remove, item)
        self.assertEqual("Non existing item in tag 'foo'", error.args[0])

    def test_iter(self):
        """L{SequenceItem} objects are iterable."""
        schema = SequenceSchema("foo", NodeSchema("item", [LeafSchema("bar")]))
        root = etree.fromstring("<foo>"
                                "<item><bar>egg0</bar></item>"
                                "<item><bar>egg1</bar></item>"
                                "</foo>")
        foo = schema.create(root)
        [item0, item1] = list(foo)
        self.assertEqual("egg0", item0.bar)
        self.assertEqual("egg1", item1.bar)


class WDSLParserTestCase(WsdlBaseTestCase):

    def setUp(self):
        super(WDSLParserTestCase, self).setUp()
        parser = WSDLParser()
        wsdl_dir = os.path.join(os.path.dirname(__file__), "../wsdl")
        wsdl_path = os.path.join(wsdl_dir, "2009-11-30.ec2.wsdl")
        self.schemas = parser.parse(open(wsdl_path).read())

    def test_parse_create_key_pair_response(self):
        """Parse a CreateKeyPairResponse payload."""
        schema = self.schemas["CreateKeyPairResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        xml = ("<CreateKeyPairResponse xmlns=\"%s\">"
               "<requestId>65d85081-abbc</requestId>"
               "<keyName>foo</keyName>"
               "<keyFingerprint>9a:81:96:46</keyFingerprint>"
               "<keyMaterial>MIIEowIBAAKCAQEAi</keyMaterial>"
               "</CreateKeyPairResponse>" % xmlns)

        response = schema.create(etree.fromstring(xml))
        self.assertEqual("65d85081-abbc", response.requestId)
        self.assertEqual("foo", response.keyName)
        self.assertEqual("9a:81:96:46", response.keyFingerprint)
        self.assertEqual("MIIEowIBAAKCAQEAi", response.keyMaterial)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_parse_delete_key_pair_response(self):
        """Parse a DeleteKeyPairResponse payload."""
        schema = self.schemas["DeleteKeyPairResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        xml = ("<DeleteKeyPairResponse xmlns=\"%s\">"
               "<requestId>acc41b73-4c47-4f80</requestId>"
               "<return>true</return>"
               "</DeleteKeyPairResponse>" % xmlns)
        root = etree.fromstring(xml)
        response = schema.create(root)
        self.assertEqual("acc41b73-4c47-4f80", response.requestId)
        self.assertEqual("true", response.return_)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_parse_describe_key_pairs_response(self):
        """Parse a DescribeKeyPairsResponse payload."""
        schema = self.schemas["DescribeKeyPairsResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        xml = ("<DescribeKeyPairsResponse xmlns=\"%s\">"
               "<requestId>3ef0aa1d-57dd-4272</requestId>"
               "<keySet>"
               "<item>"
               "<keyName>europe-key</keyName>"
               "<keyFingerprint>94:88:29:60:cf</keyFingerprint>"
               "</item>"
               "</keySet>"
               "</DescribeKeyPairsResponse>" % xmlns)
        root = etree.fromstring(xml)
        response = schema.create(root)
        self.assertEqual("3ef0aa1d-57dd-4272", response.requestId)
        self.assertEqual("europe-key", response.keySet[0].keyName)
        self.assertEqual("94:88:29:60:cf", response.keySet[0].keyFingerprint)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_modify_describe_key_pairs_response(self):
        """Modify a DescribeKeyPairsResponse payload."""
        schema = self.schemas["DescribeKeyPairsResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        xml = ("<DescribeKeyPairsResponse xmlns=\"%s\">"
               "<requestId>3ef0aa1d-57dd-4272</requestId>"
               "<keySet>"
               "<item>"
               "<keyName>europe-key</keyName>"
               "<keyFingerprint>94:88:29:60:cf</keyFingerprint>"
               "</item>"
               "</keySet>"
               "</DescribeKeyPairsResponse>" % xmlns)
        root = etree.fromstring(xml)
        response = schema.create(root)
        response.keySet[0].keyName = "new-key"
        xml = ("<DescribeKeyPairsResponse xmlns=\"%s\">"
               "<requestId>3ef0aa1d-57dd-4272</requestId>"
               "<keySet>"
               "<item>"
               "<keyName>new-key</keyName>"
               "<keyFingerprint>94:88:29:60:cf</keyFingerprint>"
               "</item>"
               "</keySet>"
               "</DescribeKeyPairsResponse>" % xmlns)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_create_describe_key_pairs_response(self):
        """Create a DescribeKeyPairsResponse payload."""
        schema = self.schemas["DescribeKeyPairsResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        response = schema.create(namespace=xmlns)
        response.requestId = "abc"
        key = response.keySet.append()
        key.keyName = "some-key"
        key.keyFingerprint = "11:22:33:44"
        xml = ("<DescribeKeyPairsResponse xmlns=\"%s\">"
               "<requestId>abc</requestId>"
               "<keySet>"
               "<item>"
               "<keyName>some-key</keyName>"
               "<keyFingerprint>11:22:33:44</keyFingerprint>"
               "</item>"
               "</keySet>"
               "</DescribeKeyPairsResponse>" % xmlns)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_create_describe_addresses_response(self):
        """Create a DescribeAddressesResponse payload.
        """
        schema = self.schemas["DescribeAddressesResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        response = schema.create(namespace=xmlns)
        response.requestId = "abc"
        address = response.addressesSet.append()
        address.publicIp = "192.168.0.1"
        xml = ("<DescribeAddressesResponse xmlns=\"%s\">"
               "<requestId>abc</requestId>"
               "<addressesSet>"
               "<item>"
               "<publicIp>192.168.0.1</publicIp>"
               "</item>"
               "</addressesSet>"
               "</DescribeAddressesResponse>" % xmlns)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_create_describe_instances_response_with_username(self):
        """Create a DescribeInstancesResponse payload.
        """
        schema = self.schemas["DescribeInstancesResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        response = schema.create(namespace=xmlns)
        response.requestId = "abc"
        reservation = response.reservationSet.append()
        instance = reservation.instancesSet.append()
        instance.instanceId = "i-01234567"
        xml = ("<DescribeInstancesResponse xmlns=\"%s\">"
               "<requestId>abc</requestId>"
               "<reservationSet>"
               "<item>"
               "<instancesSet>"
               "<item>"
               "<instanceId>i-01234567</instanceId>"
               "</item>"
               "</instancesSet>"
               "</item>"
               "</reservationSet>"
               "</DescribeInstancesResponse>" % xmlns)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_create_describe_instances_response(self):
        """Create a DescribeInstancesResponse payload.
        """
        schema = self.schemas["DescribeInstancesResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        response = schema.create(namespace=xmlns)
        response.requestId = "abc"
        reservation = response.reservationSet.append()
        instance = reservation.instancesSet.append()
        instance.instanceId = "i-01234567"
        xml = ("<DescribeInstancesResponse xmlns=\"%s\">"
               "<requestId>abc</requestId>"
               "<reservationSet>"
               "<item>"
               "<instancesSet>"
               "<item>"
               "<instanceId>i-01234567</instanceId>"
               "</item>"
               "</instancesSet>"
               "</item>"
               "</reservationSet>"
               "</DescribeInstancesResponse>" % xmlns)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_parse_describe_security_groups_response(self):
        """Parse a DescribeSecurityGroupsResponse payload."""
        schema = self.schemas["DescribeSecurityGroupsResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        xml = ("<DescribeSecurityGroupsResponse xmlns=\"%s\">"
               "<requestId>3ef0aa1d-57dd-4272</requestId>"
               "<securityGroupInfo>"
               "<item>"
               "<ownerId>UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM</ownerId>"
               "<groupName>WebServers</groupName>"
               "<groupDescription>Web</groupDescription>"
               "<ipPermissions>"
               "<item>"
               "<ipProtocol>tcp</ipProtocol>"
               "<fromPort>80</fromPort>"
               "<toPort>80</toPort>"
               "<groups/>"
               "<ipRanges>"
               "<item>"
               "<cidrIp>0.0.0.0/0</cidrIp>"
               "</item>"
               "</ipRanges>"
               "</item>"
               "</ipPermissions>"
               "</item>"
               "</securityGroupInfo>"
               "</DescribeSecurityGroupsResponse>" % xmlns)
        root = etree.fromstring(xml)
        response = schema.create(root)
        self.assertEqual("3ef0aa1d-57dd-4272", response.requestId)
        self.assertEqual("UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM",
                         response.securityGroupInfo[0].ownerId)
        self.assertEqual("WebServers", response.securityGroupInfo[0].groupName)
        self.assertEqual("Web", response.securityGroupInfo[0].groupDescription)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_modify_describe_security_groups_response(self):
        """Modify a DescribeSecurityGroupsResponse payload."""
        schema = self.schemas["DescribeSecurityGroupsResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        xml = ("<DescribeSecurityGroupsResponse xmlns=\"%s\">"
               "<requestId>3ef0aa1d-57dd-4272</requestId>"
               "<securityGroupInfo>"
               "<item>"
               "<ownerId>UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM</ownerId>"
               "<groupName>WebServers</groupName>"
               "<groupDescription>Web</groupDescription>"
               "<ipPermissions>"
               "<item>"
               "<ipProtocol>tcp</ipProtocol>"
               "<fromPort>80</fromPort>"
               "<toPort>80</toPort>"
               "<groups/>"
               "<ipRanges>"
               "<item>"
               "<cidrIp>0.0.0.0/0</cidrIp>"
               "</item>"
               "</ipRanges>"
               "</item>"
               "</ipPermissions>"
               "</item>"
               "</securityGroupInfo>"
               "</DescribeSecurityGroupsResponse>" % xmlns)
        root = etree.fromstring(xml)
        response = schema.create(root)
        response.securityGroupInfo[0].ownerId = "abc123"
        response.securityGroupInfo[0].groupName = "Everybody"
        response.securityGroupInfo[0].groupDescription = "All People"
        xml = ("<DescribeSecurityGroupsResponse xmlns=\"%s\">"
               "<requestId>3ef0aa1d-57dd-4272</requestId>"
               "<securityGroupInfo>"
               "<item>"
               "<ownerId>abc123</ownerId>"
               "<groupName>Everybody</groupName>"
               "<groupDescription>All People</groupDescription>"
               "<ipPermissions>"
               "<item>"
               "<ipProtocol>tcp</ipProtocol>"
               "<fromPort>80</fromPort>"
               "<toPort>80</toPort>"
               "<groups/>"
               "<ipRanges>"
               "<item>"
               "<cidrIp>0.0.0.0/0</cidrIp>"
               "</item>"
               "</ipRanges>"
               "</item>"
               "</ipPermissions>"
               "</item>"
               "</securityGroupInfo>"
               "</DescribeSecurityGroupsResponse>" % xmlns)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))

    def test_create_describe_security_groups_response(self):
        """Create a DescribeSecurityGroupsResponse payload."""
        schema = self.schemas["DescribeSecurityGroupsResponse"]
        xmlns = "http://ec2.amazonaws.com/doc/2008-12-01/"
        response = schema.create(namespace=xmlns)
        response.requestId = "requestId123"
        group = response.securityGroupInfo.append()
        group.ownerId = "deadbeef31337"
        group.groupName = "hexadecimalonly"
        group.groupDescription = "All people that love hex"
        xml = ("<DescribeSecurityGroupsResponse xmlns=\"%s\">"
               "<requestId>requestId123</requestId>"
               "<securityGroupInfo>"
               "<item>"
               "<ownerId>deadbeef31337</ownerId>"
               "<groupName>hexadecimalonly</groupName>"
               "<groupDescription>All people that love hex</groupDescription>"
               "</item>"
               "</securityGroupInfo>"
               "</DescribeSecurityGroupsResponse>" % xmlns)
        self.assertEqual(xml, etree.tostring(schema.dump(response)))
