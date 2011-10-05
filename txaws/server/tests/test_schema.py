from datetime import datetime

from pytz import UTC, FixedOffset

from twisted.trial.unittest import TestCase

from txaws.server.exception import APIError
from txaws.server.schema import (
    Arguments, Bool, Date, Enum, Integer, Parameter, RawStr, Schema, Unicode)


class ArgumentsTest(TestCase):

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


class ParameterTest(TestCase):

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
        error = self.assertRaises(APIError, parameter.coerce, None)
        self.assertEqual(400, error.status)
        self.assertEqual("MissingParameter", error.code)
        self.assertEqual("The request must contain the parameter Test",
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


class UnicodeTest(TestCase):

    def test_parse(self):
        """L{Unicode.parse} converts the given raw C{value} to C{unicode}."""
        parameter = Unicode("Test")
        self.assertEqual(u"foo", parameter.parse("foo"))

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


class RawStrTest(TestCase):

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


class IntegerTest(TestCase):

    def test_parse(self):
        """L{Integer.parse} converts the given raw C{value} to C{int}."""
        parameter = Integer("Test")
        self.assertEqual(123, parameter.parse("123"))

    def test_parse_with_negative(self):
        """L{Integer.parse} converts the given raw C{value} to C{int}."""
        parameter = Integer("Test")
        self.assertRaises(ValueError, parameter.parse, "-1")

    def test_format(self):
        """L{Integer.format} converts the given integer to a string."""
        parameter = Integer("Test")
        self.assertEqual("123", parameter.format(123))


class BoolTest(TestCase):

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


class EnumTest(TestCase):

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


class DateTest(TestCase):

    def test_parse(self):
        """L{Date.parse checks that the given raw C{value} is a date/time."""
        parameter = Date("Test")
        date = datetime(2010, 9, 15, 23, 59, 59, tzinfo=UTC)
        self.assertEqual(date, parameter.parse("2010-09-15T23:59:59Z"))

    def test_format(self):
        """
        L{Date.format} returns a string representation of the given datetime
        instance.
        """
        parameter = Date("Test")
        date = datetime(2010, 9, 15, 23, 59, 59,
                        tzinfo=FixedOffset(120))
        self.assertEqual("2010-09-15T21:59:59Z", parameter.format(date))


class SchemaTest(TestCase):

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

    def test_extract_with_numbered(self):
        """
        L{Schema.extract} can handle parameters with numbered values.
        """
        schema = Schema(Unicode("name.n"))
        arguments, _ = schema.extract({"name.0": "Joe", "name.1": "Tom"})
        self.assertEqual("Joe", arguments.name[0])
        self.assertEqual("Tom", arguments.name[1])

    def test_extract_with_single_numbered(self):
        """
        L{Schema.extract} can handle a single parameter with a numbered value.
        """
        schema = Schema(Unicode("name.n"))
        arguments, _ = schema.extract({"name.0": "Joe"})
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
        _, rest = schema.extract({"name": "foo", "name.1": "bar"})
        self.assertEqual(rest, {"name": "foo"})

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
        self.assertEqual("The parameter name.one is not recognized",
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
        self.assertEqual("The parameter name.-1 is not recognized",
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
        params = schema.bundle(names=[])
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
