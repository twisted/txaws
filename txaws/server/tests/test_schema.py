# -*- coding: utf-8 -*-

from datetime import datetime

from dateutil.tz import tzutc, tzoffset

from twisted.trial.unittest import TestCase

from txaws.server.exception import APIError
from txaws.server.schema import (
    Arguments, Bool, Date, Enum, Integer, Float, Parameter, RawStr, Schema,
    Unicode, UnicodeLine, List, Structure, InconsistentParameterError)


class ArgumentsTestCase(TestCase):

    def test_instantiate_empty(self):
        """Creating an L{Arguments} object."""
        arguments = Arguments({})
        self.assertEqual({}, arguments.__dict__)

    def test_instantiate_non_empty(self):
        """Creating an L{Arguments} object with some arguments."""
        arguments = Arguments({"foo": 123, "bar": 456})
        self.assertEqual(123, arguments.foo)
        self.assertEqual(456, arguments.bar)

    def test_iterate(self):
        """L{Arguments} returns an iterator with both keys and values."""
        arguments = Arguments({"foo": 123, "bar": 456})
        self.assertEqual([("foo", 123), ("bar", 456)], list(arguments))

    def test_getitem(self):
        """Values can be looked up using C{[index]} notation."""
        arguments = Arguments({1: "a", 2: "b", "foo": "bar"})
        self.assertEqual("b", arguments[2])
        self.assertEqual("bar", arguments["foo"])

    def test_getitem_error(self):
        """L{KeyError} is raised when the argument is not found."""
        arguments = Arguments({})
        self.assertRaises(KeyError, arguments.__getitem__, 1)

    def test_contains(self):
        """
        The presence of a certain argument can be inspected using the 'in'
        keyword.
        ."""
        arguments = Arguments({"foo": 1})
        self.assertIn("foo", arguments)
        self.assertNotIn("bar", arguments)

    def test_len(self):
        """C{len()} can be used with an L{Arguments} instance."""
        self.assertEqual(0, len(Arguments({})))
        self.assertEqual(1, len(Arguments({1: 2})))

    def test_nested_data(self):
        """L{Arguments} can cope fine with nested data structures."""
        arguments = Arguments({"foo": Arguments({"bar": "egg"})})
        self.assertEqual("egg", arguments.foo.bar)

    def test_nested_data_with_numbers(self):
        """L{Arguments} can cope fine with list items."""
        arguments = Arguments({"foo": {1: "egg"}})
        self.assertEqual("egg", arguments.foo[0])


class ParameterTestCase(TestCase):

    def test_coerce(self):
        """
        L{Parameter.coerce} coerces a request argument with a single value.
        """
        parameter = Parameter("Test")
        parameter.parse = lambda value: value
        self.assertEqual("foo", parameter.coerce("foo"))

    def test_coerce_with_optional(self):
        """L{Parameter.coerce} returns C{None} if the parameter is optional."""
        parameter = Parameter("Test", optional=True)
        self.assertEqual(None, parameter.coerce(None))

    def test_coerce_with_required(self):
        """
        L{Parameter.coerce} raises an L{APIError} if the parameter is
        required but not present in the request.
        """
        parameter = Parameter("Test")
        parameter.kind = "testy kind"
        error = self.assertRaises(APIError, parameter.coerce, None)
        self.assertEqual(400, error.status)
        self.assertEqual("MissingParameter", error.code)
        self.assertEqual("The request must contain the parameter Test "
                         "(testy kind)",
                         error.message)

    def test_coerce_with_default(self):
        """
        L{Parameter.coerce} returns F{Parameter.default} if the parameter is
        optional and not present in the request.
        """
        parameter = Parameter("Test", optional=True, default=123)
        self.assertEqual(123, parameter.coerce(None))

    def test_coerce_with_parameter_error(self):
        """
        L{Parameter.coerce} raises an L{APIError} if an invalid value is
        passed as request argument.
        """
        parameter = Parameter("Test")
        parameter.parse = lambda value: int(value)
        parameter.kind = "integer"
        error = self.assertRaises(APIError, parameter.coerce, "foo")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertEqual("Invalid integer value foo", error.message)

    def test_coerce_with_parameter_error_unicode(self):
        """
        L{Parameter.coerce} raises an L{APIError} if an invalid value is
        passed as request argument and parameter value is unicode.
        """
        parameter = Parameter("Test")
        parameter.parse = lambda value: int(value)
        parameter.kind = "integer"
        error = self.assertRaises(APIError, parameter.coerce, "citt\xc3\xa1")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertEqual(u"Invalid integer value cittá", error.message)

    def test_coerce_with_empty_strings(self):
        """
        L{Parameter.coerce} returns C{None} if the value is an empty string and
        C{allow_none} is C{True}.
        """
        parameter = Parameter("Test", allow_none=True)
        self.assertEqual(None, parameter.coerce(""))

    def test_coerce_with_empty_strings_error(self):
        """
        L{Parameter.coerce} raises an error if the value is an empty string and
        C{allow_none} is not C{True}.
        """
        parameter = Parameter("Test")
        error = self.assertRaises(APIError, parameter.coerce, "")
        self.assertEqual(400, error.status)
        self.assertEqual("MissingParameter", error.code)
        self.assertEqual("The request must contain the parameter Test",
                         error.message)

    def test_coerce_with_min(self):
        """
        L{Parameter.coerce} raises an error if the given value is lower than
        the lower bound.
        """
        parameter = Parameter("Test", min=50)
        parameter.measure = lambda value: int(value)
        parameter.lower_than_min_template = "Please give me at least %s"
        error = self.assertRaises(APIError, parameter.coerce, "4")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertEqual("Value (4) for parameter Test is invalid.  "
                         "Please give me at least 50", error.message)

    def test_coerce_with_max(self):
        """
        L{Parameter.coerce} raises an error if the given value is greater than
        the upper bound.
        """
        parameter = Parameter("Test", max=3)
        parameter.measure = lambda value: len(value)
        parameter.greater_than_max_template = "%s should be enough for anybody"
        error = self.assertRaises(APIError, parameter.coerce, "longish")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertEqual("Value (longish) for parameter Test is invalid.  "
                         "3 should be enough for anybody", error.message)

    def test_validator_invalid(self):
        """
        L{Parameter.coerce} raises an error if the validator returns False.
        """
        parameter = Parameter("Test", validator=lambda _: False)
        parameter.parse = lambda value: value
        parameter.kind = "test_parameter"
        error = self.assertRaises(APIError, parameter.coerce, "foo")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertEqual("Invalid test_parameter value foo", error.message)

    def test_validator_valid(self):
        """
        L{Parameter.coerce} returns the correct value if validator returns
        True.
        """
        parameter = Parameter("Test", validator=lambda _: True)
        parameter.parse = lambda value: value
        parameter.kind = "test_parameter"
        self.assertEqual("foo", parameter.coerce("foo"))

    def test_parameter_doc(self):
        """
        All L{Parameter} subclasses accept a 'doc' keyword argument.
        """
        parameters = [
            Unicode(doc="foo"),
            RawStr(doc="foo"),
            Integer(doc="foo"),
            Bool(doc="foo"),
            Enum(mapping={"hey": 1}, doc="foo"),
            Date(doc="foo"),
            List(item=Integer(), doc="foo"),
            Structure(fields={}, doc="foo")]
        for parameter in parameters:
            self.assertEqual("foo", parameter.doc)


class UnicodeTestCase(TestCase):

    def test_parse(self):
        """L{Unicode.parse} converts the given raw C{value} to C{unicode}."""
        parameter = Unicode("Test")
        self.assertEqual(u"foo", parameter.parse("foo"))

    def test_parse_unicode(self):
        """L{Unicode.parse} works with unicode input."""
        parameter = Unicode("Test")
        self.assertEqual(u"cittá", parameter.parse("citt\xc3\xa1"))

    def test_format(self):
        """L{Unicode.format} encodes the given C{unicode} with utf-8."""
        parameter = Unicode("Test")
        value = parameter.format(u"fo\N{TAGBANWA LETTER SA}")
        self.assertEqual("fo\xe1\x9d\xb0", value)
        self.assertTrue(isinstance(value, str))

    def test_min_and_max(self):
        """The L{Unicode} parameter properly supports ranges."""
        parameter = Unicode("Test", min=2, max=4)

        error = self.assertRaises(APIError, parameter.coerce, "a")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertIn("Length must be at least 2.", error.message)

        error = self.assertRaises(APIError, parameter.coerce, "abcde")
        self.assertIn("Length exceeds maximum of 4.", error.message)
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)

    def test_invalid_unicode(self):
        """
        The L{Unicode} parameter returns an error with invalid unicode data.
        """
        parameter = Unicode("Test")
        error = self.assertRaises(APIError, parameter.coerce, "Test\x95Error")
        self.assertIn(u"Invalid unicode value", error.message)
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)


class UnicodeLineTestCase(TestCase):

    def test_parse(self):
        """L{UnicodeLine.parse} converts the given raw C{value} to
        C{unicode}."""
        parameter = UnicodeLine("Test")
        self.assertEqual(u"foo", parameter.parse("foo"))

    def test_newlines_in_text(self):
        """
        The L{UnicodeLine} parameter returns an error if text contains
        newlines.
        """
        parameter = UnicodeLine("Test")
        error = self.assertRaises(APIError, parameter.coerce, "Test\nError")
        self.assertIn(
            u"Invalid unicode line value Test\nError",
            error.message)
        self.assertEqual(400, error.status)


class RawStrTestCase(TestCase):

    def test_parse(self):
        """L{RawStr.parse} checks that the given raw C{value} is a string."""
        parameter = RawStr("Test")
        self.assertEqual("foo", parameter.parse("foo"))

    def test_format(self):
        """L{RawStr.format} simply returns the given string."""
        parameter = RawStr("Test")
        value = parameter.format("foo")
        self.assertEqual("foo", value)
        self.assertTrue(isinstance(value, str))


class IntegerTestCase(TestCase):

    def test_parse(self):
        """L{Integer.parse} converts the given raw C{value} to C{int}."""
        parameter = Integer("Test")
        self.assertEqual(123, parameter.parse("123"))

    def test_parse_with_negative(self):
        """L{Integer.parse} converts the given raw C{value} to C{int}."""
        parameter = Integer("Test")
        error = self.assertRaises(APIError, parameter.coerce, "-1")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertIn("Value must be at least 0.", error.message)

    def test_format(self):
        """L{Integer.format} converts the given integer to a string."""
        parameter = Integer("Test")
        self.assertEqual("123", parameter.format(123))

    def test_min_and_max(self):
        """The L{Integer} parameter properly supports ranges."""
        parameter = Integer("Test", min=2, max=4)

        error = self.assertRaises(APIError, parameter.coerce, "1")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertIn("Value must be at least 2.", error.message)

        error = self.assertRaises(APIError, parameter.coerce, "5")
        self.assertIn("Value exceeds maximum of 4.", error.message)
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)

    def test_non_integer_string(self):
        """
        The L{Integer} parameter raises an L{APIError} when passed non-int
        values (in this case, a string).
        """
        garbage = "blah"
        parameter = Integer("Test")
        error = self.assertRaises(APIError, parameter.coerce, garbage)
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertIn("Invalid integer value %s" % garbage, error.message)


class FloatTestCase(TestCase):

    def test_parse(self):
        """L{Float.parse} converts the given raw C{value} to C{float}."""
        parameter = Float("Test")
        self.assertEqual(123.45, parameter.parse("123.45"))

    def test_format(self):
        """L{Float.format} converts the given float to a string."""
        parameter = Float("Test")
        self.assertEqual("123.45", parameter.format(123.45))

    def test_min_and_max(self):
        """The L{Float} parameter properly supports ranges."""
        parameter = Float("Test", min=2.3, max=4.5)

        error = self.assertRaises(APIError, parameter.coerce, "1.2")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertIn("Value must be at least 2.3.", error.message)

        error = self.assertRaises(APIError, parameter.coerce, "5")
        self.assertIn("Value exceeds maximum of 4.5.", error.message)
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)

    def test_non_float_string(self):
        """
        The L{Float} parameter raises an L{APIError} when passed non-float
        values (in this case, a string).
        """
        garbage = "blah"
        parameter = Float("Test")
        error = self.assertRaises(APIError, parameter.coerce, garbage)
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterValue", error.code)
        self.assertIn("Invalid float value {}".format(garbage), error.message)


class BoolTestCase(TestCase):

    def test_parse(self):
        """L{Bool.parse} converts 'true' to C{True}."""
        parameter = Bool("Test")
        self.assertEqual(True, parameter.parse("true"))

    def test_parse_with_false(self):
        """L{Bool.parse} converts 'false' to C{False}."""
        parameter = Bool("Test")
        self.assertEqual(False, parameter.parse("false"))

    def test_parse_with_error(self):
        """
        L{Bool.parse} raises C{ValueError} if the given value is neither 'true'
        or 'false'.
        """
        parameter = Bool("Test")
        self.assertRaises(ValueError, parameter.parse, "0")

    def test_format(self):
        """L{Bool.format} converts the given boolean to either '0' or '1'."""
        parameter = Bool("Test")
        self.assertEqual("true", parameter.format(True))
        self.assertEqual("false", parameter.format(False))


class EnumTestCase(TestCase):

    def test_parse(self):
        """L{Enum.parse} accepts a map for translating values."""
        parameter = Enum("Test", {"foo": "bar"})
        self.assertEqual("bar", parameter.parse("foo"))

    def test_parse_with_error(self):
        """
        L{Bool.parse} raises C{ValueError} if the given value is not
        present in the mapping.
        """
        parameter = Enum("Test", {})
        self.assertRaises(ValueError, parameter.parse, "bar")

    def test_format(self):
        """L{Enum.format} converts back the given value to the original map."""
        parameter = Enum("Test", {"foo": "bar"})
        self.assertEqual("foo", parameter.format("bar"))


class DateTestCase(TestCase):

    def test_parse(self):
        """L{Date.parse checks that the given raw C{value} is a date/time."""
        parameter = Date("Test")
        date = datetime(2010, 9, 15, 23, 59, 59, tzinfo=tzutc())
        self.assertEqual(date, parameter.parse("2010-09-15T23:59:59Z"))

    def test_format(self):
        """
        L{Date.format} returns a string representation of the given datetime
        instance.
        """
        parameter = Date("Test")
        date = datetime(2010, 9, 15, 23, 59, 59,
                        tzinfo=tzoffset('UTC', 120 * 60))
        self.assertEqual("2010-09-15T21:59:59Z", parameter.format(date))


class SchemaTestCase(TestCase):

    def test_get_parameters(self):
        """
        L{Schema.get_parameters} returns the original list of parameters.
        """
        schema = Schema(parameters=[
            Unicode("name"),
            List("scores", Integer())])
        parameters = schema.get_parameters()
        self.assertEqual("name", parameters[0].name)
        self.assertEqual("scores", parameters[1].name)

    def test_get_parameters_order_on_parameter_only_construction(self):
        """
        L{Schema.get_parameters} returns the original list of L{Parameter}s
        even when they are passed as positional arguments to L{Schema}.
        """
        schema = Schema(
            Unicode("name"),
            List("scores", Integer()),
            Integer("index", Integer()))
        self.assertEqual(["name", "scores", "index"],
                         [p.name for p in schema.get_parameters()])

    def test_extract(self):
        """
        L{Schema.extract} returns an L{Argument} object whose attributes are
        the arguments extracted from the given C{request}, as specified.
        """
        schema = Schema(Unicode("name"))
        arguments, _ = schema.extract({"name": "value"})
        self.assertEqual("value", arguments.name)

    def test_extract_with_rest(self):
        """
        L{Schema.extract} stores unknown parameters in the 'rest' return
        dictionary.
        """
        schema = Schema()
        _, rest = schema.extract({"name": "value"})
        self.assertEqual(rest, {"name": "value"})

    def test_extract_with_nested_rest(self):
        schema = Schema()
        _, rest = schema.extract({"foo.1.bar": "hey", "foo.2.baz": "there"})
        self.assertEqual({"foo.1.bar": "hey", "foo.2.baz": "there"}, rest)

    def test_extract_with_many_arguments(self):
        """L{Schema.extract} can handle multiple parameters."""
        schema = Schema(Unicode("name"), Integer("count"))
        arguments, _ = schema.extract({"name": "value", "count": "123"})
        self.assertEqual(u"value", arguments.name)
        self.assertEqual(123, arguments.count)

    def test_extract_with_optional(self):
        """L{Schema.extract} can handle optional parameters."""
        schema = Schema(Unicode("name"), Integer("count", optional=True))
        arguments, _ = schema.extract({"name": "value"})
        self.assertEqual(u"value", arguments.name)
        self.assertEqual(None, arguments.count)

    def test_extract_with_optional_default(self):
        """
        The value of C{default} on a parameter is used as the value when it is
        not provided as an argument and the parameter is C{optional}.
        """
        schema = Schema(Unicode("name"),
                        Integer("count", optional=True, default=5))
        arguments, _ = schema.extract({"name": "value"})
        self.assertEqual(u"value", arguments.name)
        self.assertEqual(5, arguments.count)

    def test_extract_structure_with_optional(self):
        """L{Schema.extract} can handle optional parameters."""
        schema = Schema(
            Structure(
                "struct",
                fields={"name": Unicode(optional=True, default="radix")}))
        arguments, _ = schema.extract({"struct": {}})
        self.assertEqual(u"radix", arguments.struct.name)

    def test_extract_with_numbered(self):
        """
        L{Schema.extract} can handle parameters with numbered values.
        """
        schema = Schema(Unicode("name.n"))
        arguments, _ = schema.extract({"name.0": "Joe", "name.1": "Tom"})
        self.assertEqual("Joe", arguments.name[0])
        self.assertEqual("Tom", arguments.name[1])

    def test_extract_with_goofy_numbered(self):
        """
        L{Schema.extract} only uses the relative values of indices to determine
        the index in the resultant list.
        """
        schema = Schema(Unicode("name.n"))
        arguments, _ = schema.extract({"name.5": "Joe", "name.10": "Tom"})
        self.assertEqual("Joe", arguments.name[0])
        self.assertEqual("Tom", arguments.name[1])

    def test_extract_with_single_numbered(self):
        """
        L{Schema.extract} can handle an un-numbered argument passed in to a
        numbered parameter.
        """
        schema = Schema(Unicode("name.n"))
        arguments, _ = schema.extract({"name": "Joe"})
        self.assertEqual("Joe", arguments.name[0])

    def test_extract_complex(self):
        """L{Schema} can cope with complex schemas."""
        schema = Schema(
            Unicode("GroupName"),
            RawStr("IpPermissions.n.IpProtocol"),
            Integer("IpPermissions.n.FromPort"),
            Integer("IpPermissions.n.ToPort"),
            Unicode("IpPermissions.n.Groups.m.UserId", optional=True),
            Unicode("IpPermissions.n.Groups.m.GroupName", optional=True))

        arguments, _ = schema.extract(
            {"GroupName": "Foo",
             "IpPermissions.1.IpProtocol": "tcp",
             "IpPermissions.1.FromPort": "1234",
             "IpPermissions.1.ToPort": "5678",
             "IpPermissions.1.Groups.1.GroupName": "Bar",
             "IpPermissions.1.Groups.2.GroupName": "Egg"})

        self.assertEqual(u"Foo", arguments.GroupName)
        self.assertEqual(1, len(arguments.IpPermissions))
        self.assertEqual(1234, arguments.IpPermissions[0].FromPort)
        self.assertEqual(5678, arguments.IpPermissions[0].ToPort)
        self.assertEqual(2, len(arguments.IpPermissions[0].Groups))
        self.assertEqual("Bar", arguments.IpPermissions[0].Groups[0].GroupName)
        self.assertEqual("Egg", arguments.IpPermissions[0].Groups[1].GroupName)

    def test_extract_with_multiple_parameters_in_singular_schema(self):
        """
        If multiple parameters are passed in to a Schema element that is not
        flagged as supporting multiple values then we should throw an
        C{APIError}.
        """
        schema = Schema(Unicode("name"))
        params = {"name.1": "value", "name.2": "value2"}
        error = self.assertRaises(APIError, schema.extract, params)
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidParameterCombination", error.code)
        self.assertEqual("The parameter 'name' may only be specified once.",
                         error.message)

    def test_extract_with_mixed(self):
        """
        L{Schema.extract} stores in the rest result all numbered parameters
        given without an index.
        """
        schema = Schema(Unicode("name.n"))
        self.assertRaises(
            InconsistentParameterError,
            schema.extract, {"nameFOOO": "foo", "nameFOOO.1": "bar"})

    def test_extract_with_non_numbered_template(self):
        """
        L{Schema.extract} accepts a single numbered argument even if the
        associated template is not numbered.
        """
        schema = Schema(Unicode("name"))
        arguments, _ = schema.extract({"name.1": "foo"})
        self.assertEqual("foo", arguments.name)

    def test_extract_with_non_integer_index(self):
        """
        L{Schema.extract} raises an error when trying to pass a numbered
        parameter with a non-integer index.
        """
        schema = Schema(Unicode("name.n"))
        params = {"name.one": "foo"}
        error = self.assertRaises(APIError, schema.extract, params)
        self.assertEqual(400, error.status)
        self.assertEqual("UnknownParameter", error.code)
        self.assertEqual("The parameter one is not recognized",
                         error.message)

    def test_extract_with_negative_index(self):
        """
        L{Schema.extract} raises an error when trying to pass a numbered
        parameter with a negative index.
        """
        schema = Schema(Unicode("name.n"))
        params = {"name.-1": "foo"}
        error = self.assertRaises(APIError, schema.extract, params)
        self.assertEqual(400, error.status)
        self.assertEqual("UnknownParameter", error.code)
        self.assertEqual("The parameter -1 is not recognized",
                         error.message)

    def test_bundle(self):
        """
        L{Schema.bundle} returns a dictionary of raw parameters that
        can be used for an EC2-style query.
        """
        schema = Schema(Unicode("name"))
        params = schema.bundle(name="foo")
        self.assertEqual({"name": "foo"}, params)

    def test_bundle_with_numbered(self):
        """
        L{Schema.bundle} correctly handles numbered arguments.
        """
        schema = Schema(Unicode("name.n"))
        params = schema.bundle(name=["foo", "bar"])
        self.assertEqual({"name.1": "foo", "name.2": "bar"}, params)

    def test_bundle_with_two_numbered(self):
        """
        L{Schema.bundle} can bundle multiple numbered lists.
        """
        schema = Schema(Unicode("names.n"), Unicode("things.n"))
        params = schema.bundle(names=["foo", "bar"], things=["baz", "quux"])
        self.assertEqual({"names.1": "foo", "names.2": "bar",
                          "things.1": "baz", "things.2": "quux"},
                         params)

    def test_bundle_with_none(self):
        """L{None} values are discarded in L{Schema.bundle}."""
        schema = Schema(Unicode("name.n", optional=True))
        params = schema.bundle(name=None)
        self.assertEqual({}, params)

    def test_bundle_with_empty_numbered(self):
        """
        L{Schema.bundle} correctly handles an empty numbered arguments list.
        """
        schema = Schema(Unicode("name.n"))
        params = schema.bundle(name=[])
        self.assertEqual({}, params)

    def test_bundle_with_numbered_not_supplied(self):
        """
        L{Schema.bundle} ignores parameters that are not present.
        """
        schema = Schema(Unicode("name.n"))
        params = schema.bundle()
        self.assertEqual({}, params)

    def test_bundle_with_multiple(self):
        """
        L{Schema.bundle} correctly handles multiple arguments.
        """
        schema = Schema(Unicode("name.n"), Integer("count"))
        params = schema.bundle(name=["Foo", "Bar"], count=123)
        self.assertEqual({"name.1": "Foo", "name.2": "Bar", "count": "123"},
                         params)

    def test_bundle_with_structure(self):
        """L{Schema.bundle} can bundle L{Structure}s."""
        schema = Schema(
            parameters=[
                Structure("struct", fields={"field1": Unicode(),
                                            "field2": Integer()})])
        params = schema.bundle(struct={"field1": "hi", "field2": 59})
        self.assertEqual({"struct.field1": "hi", "struct.field2": "59"},
                         params)

    def test_bundle_with_list(self):
        """L{Schema.bundle} can bundle L{List}s."""
        schema = Schema(parameters=[List("things", item=Unicode())])
        params = schema.bundle(things=["foo", "bar"])
        self.assertEqual({"things.1": "foo", "things.2": "bar"}, params)

    def test_bundle_with_structure_with_arguments(self):
        """
        L{Schema.bundle} can bundle L{Structure}s (specified as L{Arguments}).
        """
        schema = Schema(
            parameters=[
                Structure("struct", fields={"field1": Unicode(),
                                            "field2": Integer()})])
        params = schema.bundle(struct=Arguments({"field1": "hi",
                                                 "field2": 59}))
        self.assertEqual({"struct.field1": "hi", "struct.field2": "59"},
                         params)

    def test_bundle_with_list_with_arguments(self):
        """L{Schema.bundle} can bundle L{List}s (specified as L{Arguments})."""
        schema = Schema(parameters=[List("things", item=Unicode())])
        params = schema.bundle(things=Arguments({1: "foo", 2: "bar"}))
        self.assertEqual({"things.1": "foo", "things.2": "bar"}, params)

    def test_bundle_with_arguments(self):
        """L{Schema.bundle} can bundle L{Arguments} too."""
        schema = Schema(Unicode("name.n"), Integer("count"))
        arguments = Arguments({"name": Arguments({1: "Foo", 7: "Bar"}),
                               "count": 123})
        params = schema.bundle(arguments)
        self.assertEqual({"name.1": "Foo", "name.7": "Bar", "count": "123"},
                         params)

    def test_bundle_with_arguments_and_extra(self):
        """
        L{Schema.bundle} can bundle L{Arguments} with keyword arguments too.

        Keyword arguments take precedence.
        """
        schema = Schema(Unicode("name.n"), Integer("count"))
        arguments = Arguments({"name": {1: "Foo", 7: "Bar"}, "count": 321})
        params = schema.bundle(arguments, count=123)
        self.assertEqual({"name.1": "Foo", "name.2": "Bar", "count": "123"},
                         params)

    def test_bundle_with_missing_parameter(self):
        """
        L{Schema.bundle} raises an exception one of the given parameters
        doesn't exist in the schema.
        """
        schema = Schema(Integer("count"))
        self.assertRaises(RuntimeError, schema.bundle, name="foo")

    def test_add_single_extra_schema_item(self):
        """New Parameters can be added to the Schema."""
        schema = Schema(Unicode("name"))
        schema = schema.extend(Unicode("computer"))
        arguments, _ = schema.extract({"name": "value", "computer": "testing"})
        self.assertEqual(u"value", arguments.name)
        self.assertEqual("testing", arguments.computer)

    def test_add_extra_schema_items(self):
        """A list of new Parameters can be added to the Schema."""
        schema = Schema(Unicode("name"))
        schema = schema.extend(Unicode("computer"), Integer("count"))
        arguments, _ = schema.extract({"name": "value", "computer": "testing",
                                       "count": "5"})
        self.assertEqual(u"value", arguments.name)
        self.assertEqual("testing", arguments.computer)
        self.assertEqual(5, arguments.count)

    def test_list(self):
        """L{List}s can be extracted."""
        schema = Schema(List("foo", Integer()))
        arguments, _ = schema.extract({"foo.1": "1", "foo.2": "2"})
        self.assertEqual([1, 2], arguments.foo)

    def test_optional_list(self):
        """
        The default value of an optional L{List} is C{[]}.
        """
        schema = Schema(List("names", Unicode(), optional=True))
        arguments, _ = schema.extract({})
        self.assertEqual([], arguments.names)

    def test_default_list(self):
        """
        The default of a L{List} can be specified as a list.
        """
        schema = Schema(List("names", Unicode(), optional=True,
                             default=[u"foo", u"bar"]))
        arguments, _ = schema.extract({})
        self.assertEqual([u"foo", u"bar"], arguments.names)

    def test_list_of_list(self):
        """L{List}s can be nested."""
        schema = Schema(List("foo", List(item=Unicode())))
        arguments, _ = schema.extract(
            {"foo.1.1": "first-first", "foo.1.2": "first-second",
             "foo.2.1": "second-first", "foo.2.2": "second-second"})
        self.assertEqual([["first-first", "first-second"],
                          ["second-first", "second-second"]],
                         arguments.foo)

    def test_structure(self):
        """
        L{Schema}s with L{Structure} parameters can have arguments extracted.
        """
        schema = Schema(Structure("foo", {"a": Integer(), "b": Integer()}))
        arguments, _ = schema.extract({"foo.a": "1", "foo.b": "2"})
        self.assertEqual(1, arguments.foo.a)
        self.assertEqual(2, arguments.foo.b)

    def test_structure_of_structures(self):
        """L{Structure}s can be nested."""
        sub_struct = Structure(fields={"a": Unicode(), "b": Unicode()})
        schema = Schema(Structure("foo", fields={"a": sub_struct,
                                                 "b": sub_struct}))
        arguments, _ = schema.extract({"foo.a.a": "a-a", "foo.a.b": "a-b",
                                       "foo.b.a": "b-a", "foo.b.b": "b-b"})
        self.assertEqual("a-a", arguments.foo.a.a)
        self.assertEqual("a-b", arguments.foo.a.b)
        self.assertEqual("b-a", arguments.foo.b.a)
        self.assertEqual("b-b", arguments.foo.b.b)

    def test_list_of_structures(self):
        """L{List}s of L{Structure}s are extracted properly."""
        schema = Schema(
            List("foo", Structure(fields={"a": Integer(), "b": Integer()})))
        arguments, _ = schema.extract({"foo.1.a": "1", "foo.1.b": "2",
                                       "foo.2.a": "3", "foo.2.b": "4"})
        self.assertEqual(1, arguments.foo[0]['a'])
        self.assertEqual(2, arguments.foo[0]['b'])
        self.assertEqual(3, arguments.foo[1]['a'])
        self.assertEqual(4, arguments.foo[1]['b'])

    def test_structure_of_list(self):
        """L{Structure}s of L{List}s are extracted properly."""
        schema = Schema(Structure("foo", fields={"l": List(item=Integer())}))
        arguments, _ = schema.extract({"foo.l.1": "1", "foo.l.2": "2"})
        self.assertEqual([1, 2], arguments.foo.l)

    def test_new_parameters(self):
        """
        L{Schema} accepts a C{parameters} parameter to specify parameters in a
        {name: field} format.
        """
        schema = Schema(
            parameters=[Structure("foo",
                                  fields={"l": List(item=Integer())})])
        arguments, _ = schema.extract({"foo.l.1": "1", "foo.l.2": "2"})
        self.assertEqual([1, 2], arguments.foo.l)

    def test_schema_conversion_list(self):
        """
        Backwards-compatibility conversion maintains the name of lists.
        """
        schema = Schema(Unicode("foos.N"))
        parameters = schema.get_parameters()
        self.assertEqual(1, len(parameters))
        self.assertTrue(isinstance(parameters[0], List))
        self.assertEqual("foos", parameters[0].name)

    def test_coerce_list(self):
        """
        When a L{List} coerces the value of one of its item, it uses the the
        proper name in the C{MissingParameter} error raised.
        """
        parameter = List("foo", Unicode())
        error = self.assertRaises(APIError, parameter.item.coerce, "")
        self.assertEqual(400, error.status)
        self.assertEqual("MissingParameter", error.code)
        self.assertEqual("The request must contain the parameter foo "
                         "(unicode)",
                         error.message)

    def test_schema_conversion_structure_name(self):
        """
        Backwards-compatibility conversion maintains the names of fields in
        structures.
        """
        schema = Schema(Unicode("foos.N.field"),
                        Unicode("foos.N.field2"))
        parameters = schema.get_parameters()
        self.assertEqual(1, len(parameters))
        self.assertTrue(isinstance(parameters[0], List))
        self.assertEqual("foos", parameters[0].name)
        self.assertEqual("N",
                         parameters[0].item.name)
        self.assertEqual("field",
                         parameters[0].item.fields["field"].name)
        self.assertEqual("field2",
                         parameters[0].item.fields["field2"].name)

    def test_schema_conversion_optional_list(self):
        """
        Backwards-compatibility conversions maintains optional-ness of lists.
        """
        schema = Schema(Unicode("foos.N", optional=True))
        arguments, _ = schema.extract({})
        self.assertEqual([], arguments.foos)

    def test_schema_conversion_optional_structure_field(self):
        """
        Backwards-compatibility conversion maintains optional-ness of structure
        fields.
        """
        schema = Schema(Unicode("foos.N.field"),
                        Unicode("foos.N.field2", optional=True, default=u"hi"))
        arguments, _ = schema.extract({"foos.0.field": u"existent"})
        self.assertEqual(u"existent", arguments.foos[0].field)
        self.assertEqual(u"hi", arguments.foos[0].field2)

    def test_additional_schema_attributes(self):
        """
        Additional data can be specified on the Schema class for specifying a
        more rich schema.
        """
        result = {'id': Integer(), 'name': Unicode(), 'data': RawStr()}
        errors = [APIError]

        schema = Schema(
            name="GetStuff",
            doc="""Get the stuff.""",
            parameters=[
                Integer("id"),
                Unicode("scope")],
            result=result,
            errors=errors)

        self.assertEqual("GetStuff", schema.name)
        self.assertEqual("Get the stuff.", schema.doc)
        self.assertEqual(result, schema.result)
        self.assertEqual(set(errors), schema.errors)

    def test_extend_with_additional_schema_attributes(self):
        """
        The additional schema attributes can be passed to L{Schema.extend}.
        """
        result = {'id': Integer(), 'name': Unicode(), 'data': RawStr()}
        errors = [APIError]

        schema = Schema(
            name="GetStuff",
            parameters=[Integer("id")])

        schema2 = schema.extend(
            name="GetStuff2",
            doc="Get stuff 2",
            parameters=[Unicode("scope")],
            result=result,
            errors=errors)

        self.assertEqual("GetStuff2", schema2.name)
        self.assertEqual("Get stuff 2", schema2.doc)
        self.assertEqual(result, schema2.result)
        self.assertEqual(set(errors), schema2.errors)

        arguments, _ = schema2.extract({'id': '5', 'scope': u'foo'})
        self.assertEqual(5, arguments.id)
        self.assertEqual(u'foo', arguments.scope)

    def test_extend_maintains_existing_attributes(self):
        """
        If additional schema attributes aren't passed to L{Schema.extend}, they
        stay the same.
        """
        result = {'id': Integer(), 'name': Unicode(), 'data': RawStr()}
        errors = [APIError]

        schema = Schema(
            name="GetStuff",
            doc="""Get the stuff.""",
            parameters=[Integer("id")],
            result=result,
            errors=errors)

        schema2 = schema.extend(parameters=[Unicode("scope")])

        self.assertEqual("GetStuff", schema2.name)
        self.assertEqual("Get the stuff.", schema2.doc)
        self.assertEqual(result, schema2.result)
        self.assertEqual(set(errors), schema2.errors)

        arguments, _ = schema2.extract({'id': '5', 'scope': u'foo'})
        self.assertEqual(5, arguments.id)
        self.assertEqual(u'foo', arguments.scope)

    def test_extend_result(self):
        """
        Result fields can also be extended with L{Schema.extend}.
        """
        schema = Schema(result={'name': Unicode()})
        schema2 = schema.extend(
            result={'id': Integer()})
        result_structure = Structure(fields=schema2.result)
        self.assertEqual(
            {'name': u'foo', 'id': 5},
            result_structure.coerce({'name': u'foo', 'id': '5'}))

    def test_extend_errors(self):
        """
        Errors can be extended with L{Schema.extend}.
        """
        schema = Schema(parameters=[], errors=[APIError])
        schema2 = schema.extend(errors=[ZeroDivisionError])
        self.assertEqual(set([APIError, ZeroDivisionError]), schema2.errors)

    def test_extend_maintains_parameter_order(self):
        """
        Extending a schema with additional parameters puts the new parameters
        at the end.
        """
        schema = Schema(parameters=[Unicode("name"), Unicode("value")])
        schema2 = schema.extend(parameters=[Integer("foo"), Unicode("index")])
        self.assertEqual(["name", "value", "foo", "index"],
                         [p.name for p in schema2.get_parameters()])

    def test_schema_field_names(self):
        structure = Structure(fields={"foo": Integer()})
        self.assertEqual("foo", structure.fields["foo"].name)
