from datetime import datetime
from operator import itemgetter

from dateutil.tz import tzutc
from dateutil.parser import parse

from txaws.server.exception import APIError


class SchemaError(APIError):
    """Raised when failing to extract or bundle L{Parameter}s."""

    def __init__(self, message):
        code = self.__class__.__name__[:-len("Error")]
        super(SchemaError, self).__init__(400, code=code, message=message)


class MissingParameterError(SchemaError):
    """Raised when a parameter is missing.

    @param name: The name of the missing parameter.
    """

    def __init__(self, name):
        message = "The request must contain the parameter %s" % name
        super(MissingParameterError, self).__init__(message)


class InconsistentParameterError(SchemaError):
    def __init__(self, name):
        message = "Parameter %s is used inconsistently" % (name,)
        super(InconsistentParameterError, self).__init__(message)


class InvalidParameterValueError(SchemaError):
    """Raised when the value of a parameter is invalid."""


class InvalidParameterCombinationError(SchemaError):
    """
    Raised when there is more than one parameter with the same name,
    when this isn't explicitly allowed for.

    @param name: The name of the missing parameter.
    """

    def __init__(self, name):
        message = "The parameter '%s' may only be specified once." % name
        super(InvalidParameterCombinationError, self).__init__(message)


class UnknownParameterError(SchemaError):
    """Raised when a parameter to extract is unknown."""

    def __init__(self, name):
        message = "The parameter %s is not recognized" % name
        super(UnknownParameterError, self).__init__(message)


class UnknownParametersError(Exception):
    """
    Raised when extra unknown fields are passed to L{Structure.parse}.

    @ivar result: The already coerced result representing the known parameters.
    @ivar unknown: The unknown parameters.
    """
    def __init__(self, result, unknown):
        self.result = result
        self.unknown = unknown
        message = "The parameters %s are not recognized" % (unknown,)
        super(UnknownParametersError, self).__init__(message)


class Parameter(object):
    """A single parameter in an HTTP request.

    @param name: A name for the key of the parameter, as specified
        in a request. For example, a single parameter would be specified
        simply as 'GroupName'.  If more than one group name was accepted,
        it would be specified as 'GroupName.n'.  A more complex example
        is 'IpPermissions.n.Groups.m.GroupName'.
    @param optional: If C{True} the parameter may not be present.
    @param default: A default value for the parameter, if not present.
    @param min: Minimum value for a parameter.
    @param max: Maximum value for a parameter.
    @param allow_none: Whether the parameter may be C{None}.
    @param validator: A callable to validate the parameter, returning a bool.
    """

    supports_multiple = False

    def __init__(self, name=None, optional=False, default=None,
                 min=None, max=None, allow_none=False, validator=None,
                 doc=None):
        self.name = name
        self.optional = optional
        self.default = default
        self.min = min
        self.max = max
        self.allow_none = allow_none
        self.validator = validator
        self.doc = doc

    def coerce(self, value):
        """Coerce a single value according to this parameter's settings.

        @param value: A L{str}, or L{None}. If L{None} is passed - meaning no
            value is avalable at all, not even the empty string - and this
            parameter is optional, L{self.default} will be returned.
        """
        if value is None:
            if self.optional:
                return self.default
            else:
                value = ""
        if value == "":
            if not self.allow_none:
                raise MissingParameterError(self.name)
            return self.default
        try:
            self._check_range(value)
            parsed = self.parse(value)
            if self.validator and not self.validator(parsed):
                raise ValueError(value)
            return parsed
        except ValueError:
            try:
                value = value.decode("utf-8")
                message = "Invalid %s value %s" % (self.kind, value)
            except UnicodeDecodeError:
                message = "Invalid %s value" % self.kind
            raise InvalidParameterValueError(message)

    def _check_range(self, value):
        """Check that the given C{value} is in the expected range."""
        if self.min is None and self.max is None:
            return

        measure = self.measure(value)
        prefix = "Value (%s) for parameter %s is invalid.  %s"

        if self.min is not None and measure < self.min:
            message = prefix % (value, self.name,
                                self.lower_than_min_template % self.min)
            raise InvalidParameterValueError(message)

        if self.max is not None and measure > self.max:
            message = prefix % (value, self.name,
                                self.greater_than_max_template % self.max)
            raise InvalidParameterValueError(message)

    def parse(self, value):
        """
        Parse a single parameter value coverting it to the appropriate type.
        """
        raise NotImplementedError()

    def format(self, value):
        """
        Format a single parameter value in a way suitable for an HTTP request.
        """
        raise NotImplementedError()

    def measure(self, value):
        """
        Return an C{int} providing a measure for C{value}, used for C{range}.
        """
        raise NotImplementedError()


class Unicode(Parameter):
    """A parameter that must be a C{unicode}."""

    kind = "unicode"

    lower_than_min_template = "Length must be at least %s."
    greater_than_max_template = "Length exceeds maximum of %s."

    def parse(self, value):
        return value.decode("utf-8")

    def format(self, value):
        return value.encode("utf-8")

    def measure(self, value):
        return len(value)


class RawStr(Parameter):
    """A parameter that must be a C{str}."""

    kind = "raw string"

    def parse(self, value):
        return str(value)

    def format(self, value):
        return value


class Integer(Parameter):
    """A parameter that must be a positive C{int}."""

    kind = "integer"

    lower_than_min_template = "Value must be at least %s."
    greater_than_max_template = "Value exceeds maximum of %s."

    def __init__(self, name=None, optional=False, default=None,
                 min=0, max=None, allow_none=False, validator=None,
                 doc=None):
        super(Integer, self).__init__(name, optional, default, min, max,
                                      allow_none, validator, doc=doc)

    def parse(self, value):
        return int(value)

    def format(self, value):
        return str(value)

    def measure(self, value):
        return int(value)


class Bool(Parameter):
    """A parameter that must be a C{bool}."""

    kind = "boolean"

    def parse(self, value):
        if value == "true":
            return True
        if value == "false":
            return False
        raise ValueError()

    def format(self, value):
        if value:
            return "true"
        else:
            return "false"


class Enum(Parameter):
    """A parameter with enumerated values.

    @param name: The name of the parameter, as specified in a request.
    @param optional: If C{True} the parameter may not be present.
    @param default: A default value for the parameter, if not present.
    @param mapping: A mapping of accepted values to the values that
        will be returned by C{parse}.
    """

    kind = "enum"

    def __init__(self, name=None, mapping=None, optional=False, default=None,
                 doc=None):
        super(Enum, self).__init__(name, optional=optional, default=default,
                                   doc=doc)
        if mapping is None:
            raise TypeError("Must provide mapping")
        self.mapping = mapping
        self.reverse = dict((value, key) for key, value in mapping.iteritems())

    def parse(self, value):
        try:
            return self.mapping[value]
        except KeyError:
            raise ValueError()

    def format(self, value):
        return self.reverse[value]


class Date(Parameter):
    """A parameter that must be a valid ISO 8601 formatted date."""

    kind = "date"

    def parse(self, value):
        return parse(value).replace(tzinfo=tzutc())

    def format(self, value):
        # Convert value to UTC.
        tt = value.utctimetuple()
        utc_value = datetime(
            tt.tm_year, tt.tm_mon, tt.tm_mday, tt.tm_hour, tt.tm_min,
            tt.tm_sec)
        return datetime.strftime(utc_value, "%Y-%m-%dT%H:%M:%SZ")


class List(Parameter):
    """
    A homogenous list of instances of a parameterized type.

    There is a strange behavior that lists can have any starting index and any
    gaps are ignored.  Conventionally they are 1-based, and so indexes proceed
    like 1, 2, 3...  However, any non-negative index can be used and the
    ordering will be used to determine the true index. So::

        {5: 'a', 7: 'b', 9: 'c'}

    becomes::

        ['a', 'b', 'c']
    """

    kind = "list"
    supports_multiple = True

    def __init__(self, name=None, item=None, optional=False, default=None,
                 doc=None):
        """
        @param item: A L{Parameter} instance which will be used to parse and
            format the values in the list.
        """
        if item is None:
            raise TypeError("Must provide item")
        super(List, self).__init__(name, optional=optional, default=default,
                                   doc=doc)
        self.item = item
        if default is None:
            self.default = []

    def parse(self, value):
        """
        Convert a dictionary of {relative index: value} to a list of parsed
        C{value}s.
        """
        indices = []
        if not isinstance(value, dict):
            raise InvalidParameterValueError("%r should be a dict." % (value,))
        for index in value.keys():
            try:
                indices.append(int(index))
            except ValueError:
                raise UnknownParameterError(index)
        result = [None] * len(value)
        for index_index, index in enumerate(sorted(indices)):
            v = value[str(index)]
            if index < 0:
                raise UnknownParameterError(index)
            result[index_index] = self.item.coerce(v)
        return result

    def format(self, value):
        """
        Convert a list like::

            ["a", "b", "c"]

        to:

            {"1": "a", "2": "b", "3": "c"}

        C{value} may also be an L{Arguments} instance, mapping indices to
        values. Who knows why.
        """
        if isinstance(value, Arguments):
            return dict((str(i), self.item.format(v)) for i, v in value)
        return dict((str(i + 1), self.item.format(v))
                        for i, v in enumerate(value))


class Structure(Parameter):
    """
    A structure with named fields of parameterized types.
    """

    kind = "structure"
    supports_multiple = True

    def __init__(self, name=None, fields=None, optional=False, default=None,
                 doc=None):
        """
        @param fields: A mapping of field name to field L{Parameter} instance.
        """
        if fields is None:
            raise TypeError("Must provide fields")
        super(Structure, self).__init__(name, optional=optional,
                                        default=default, doc=doc)
        self.fields = fields

    def parse(self, value):
        """
        Convert a dictionary of raw values to a dictionary of processed values.
        """
        result = {}
        rest = {}
        for k, v in value.iteritems():
            if k in self.fields:
                if (isinstance(v, dict)
                    and not self.fields[k].supports_multiple):
                    if len(v) == 1:
                        # We support "foo.1" as "foo" as long as there is only
                        # one "foo.#" parameter provided.... -_-
                        v = v.values()[0]
                    else:
                        raise InvalidParameterCombinationError(k)
                result[k] = self.fields[k].coerce(v)
            else:
                rest[k] = v
        for k, v in self.fields.iteritems():
            if k not in result:
                result[k] = v.coerce(None)
        if rest:
            raise UnknownParametersError(result, rest)
        return result

    def format(self, value):
        """
        Convert a dictionary of processed values to a dictionary of raw values.
        """
        if not isinstance(value, Arguments):
            value = value.iteritems()
        return dict((k, self.fields[k].format(v)) for k, v in value)


class Arguments(object):
    """Arguments parsed from a request."""

    def __init__(self, tree):
        """Initialize a new L{Arguments} instance.

        @param tree: The C{dict}-based structure of the L{Argument} instance
            to create.
        """
        for key, value in tree.iteritems():
            self.__dict__[key] = self._wrap(value)

    def __str__(self):
        return "Arguments(%s)" % (self.__dict__,)

    __repr__ = __str__

    def __iter__(self):
        """Returns an iterator yielding C{(name, value)} tuples."""
        return self.__dict__.iteritems()

    def __getitem__(self, index):
        """Return the argument value with the given L{index}."""
        return self.__dict__[index]

    def __len__(self):
        """Return the number of arguments."""
        return len(self.__dict__)

    def _wrap(self, value):
        """Wrap the given L{tree} with L{Arguments} as necessary.

        @param tree: A {dict}, containing L{dict}s and/or leaf values, nested
            arbitrarily deep.
        """
        if isinstance(value, dict):
            if any(isinstance(name, int) for name in value.keys()):
                if not all(isinstance(name, int) for name in value.keys()):
                    raise RuntimeError("Integer and non-integer keys: %r"
                                       % value.keys())
                items = sorted(value.iteritems(), key=itemgetter(0))
                return [self._wrap(value) for (name, value) in items]
            else:
                return Arguments(value)
        elif isinstance(value, list):
            return [self._wrap(x) for x in value]
        else:
            return value


class Schema(object):
    """
    The schema that the arguments of an HTTP request must be compliant with.
    """

    def __init__(self, *_parameters, **kwargs):
        """Initialize a new L{Schema} instance.

        Any number of L{Parameter} instances can be passed. The parameter path
        is used as the target in L{Schema.extract} and L{Schema.bundle}. For
        example::

          schema = Schema(name="SetName", parameters={"Name": Unicode()})

        means that the result of L{Schema.extract} would have a C{Name}
        attribute. Similarly, L{Schema.bundle} would look for a C{Name}
        attribute.

        A more complex example::

          schema = Schema(
              name="SetNames",
              parameters={"Names": List(item=Unicode())})

        means that the result of L{Schema.extract} would have a C{Names}
        attribute, which would itself contain a list of names. Similarly,
        L{Schema.bundle} would look for a C{Names} attribute.
        """
        self.name = kwargs.pop('name', None)
        self.doc = kwargs.pop('doc', None)
        self.result = kwargs.pop('result', None)
        self.errors = kwargs.pop('errors', [])
        if 'parameters' in kwargs:
            if len(_parameters) > 0:
                raise TypeError("parameters= must only be passed "
                                "without positional arguments")
            self._parameters = kwargs['parameters']
        else:
            self._parameters = self._convert_old_schema(_parameters)

    def extract(self, params):
        """Extract parameters from a raw C{dict} according to this schema.

        @param params: The raw parameters to parse.
        @return: A tuple of an L{Arguments} object holding the extracted
            arguments and any unparsed arguments.
        """
        structure = Structure(fields=self._parameters)
        try:
            tree = structure.coerce(self._convert_flat_to_nest(params))
            rest = {}
        except UnknownParametersError, error:
            tree = error.result
            rest = self._convert_nest_to_flat(error.unknown)
        return Arguments(tree), rest

    def bundle(self, *arguments, **extra):
        """Bundle the given arguments in a C{dict} with EC2-style format.

        @param arguments: L{Arguments} instances to bundle. Keys in
            later objects will override those in earlier objects.
        @param extra: Any number of additional parameters. These will override
            similarly named arguments in L{arguments}.
        """
        params = {}

        for argument in arguments:
            params.update(argument)

        params.update(extra)
        result = {}
        for name, value in params.iteritems():
            if value is None:
                continue
            segments = name.split('.')
            first = segments[0]
            parameter = self._parameters.get(first)
            if parameter is None:
                raise RuntimeError("Parameter '%s' not in schema" % name)
            else:
                if value is None:
                    result[name] = ""
                else:
                    result[name] = parameter.format(value)

        return self._convert_nest_to_flat(result)

    def _convert_flat_to_nest(self, params):
        """
        Convert a structure in the form of::

            {'foo.1.bar': 'value',
             'foo.2.baz': 'value'}

        to::

            {'foo': {'1': {'bar': 'value'},
                     '2': {'baz': 'value'}}}

        This is intended for use both during parsing of HTTP arguments like
        'foo.1.bar=value' and when dealing with schema declarations that look
        like 'foo.n.bar'.

        This is the inverse of L{_convert_nest_to_flat}.
        """
        result = {}
        for k, v in params.iteritems():
            last = result
            segments = k.split('.')
            for index, item in enumerate(segments):
                if index == len(segments) - 1:
                    newd = v
                else:
                    newd = {}
                if not isinstance(last, dict):
                    raise InconsistentParameterError(k)
                if type(last.get(item)) is dict and type(newd) is not dict:
                    raise InconsistentParameterError(k)
                last = last.setdefault(item, newd)
        return result

    def _convert_nest_to_flat(self, params, _result=None, _prefix=None):
        """
        Convert a data structure that looks like::

            {"foo": {"bar": "baz", "shimmy": "sham"}}

        to::

            {"foo.bar": "baz",
             "foo.shimmy": "sham"}

        This is the inverse of L{_convert_flat_to_nest}.
        """
        if _result is None:
            _result = {}
        for k, v in params.iteritems():
            if _prefix is None:
                path = k
            else:
                path = _prefix + '.' + k
            if isinstance(v, dict):
                self._convert_nest_to_flat(v, _result=_result, _prefix=path)
            else:
                _result[path] = v
        return _result

    def extend(self, *schema_items, **kwargs):
        """
        Add any number of schema items to a new schema. Takes the same
        arguments as the constructor.
        """
        new_kwargs = {
            'name': self.name,
            'doc': self.doc,
            'parameters': self._parameters.copy(),
            'result': self.result.copy() if self.result else {},
            'errors': self.errors}
        new_kwargs['parameters'].update(kwargs.pop('parameters', {}))
        new_kwargs['result'].update(kwargs.pop('result', {}))
        new_kwargs.update(kwargs)

        if schema_items:
            parameters = self._convert_old_schema(schema_items)
            new_kwargs['parameters'].update(parameters)
        return Schema(**new_kwargs)

    def _convert_old_schema(self, parameters):
        """
        Convert an ugly old schema, using dotted names, to the hot new schema,
        using List and Structure.

        The old schema assumes that every other dot implies an array. So a list
        of two parameters,

            [Integer("foo.bar.baz.quux"), Integer("foo.bar.shimmy")]

        becomes::

            {"foo": List(
                item=Structure(
                    fields={"baz": List(item=Integer()),
                            "shimmy": Integer()}))}

        By design, the old schema syntax ignored the names "bar" and "quux".
        """
        crap = {}
        for parameter in parameters:
            crap[parameter.name] = parameter
        nest = self._convert_flat_to_nest(crap)
        return self._inner_convert_old_schema(nest, 0).fields

    def _inner_convert_old_schema(self, mapping, depth):
        """
        Internal recursion helper for L{_convert_old_schema}.
        """
        if not isinstance(mapping, dict):
            return mapping
        if depth % 2 == 0:
            fields = {}
            for k, v in mapping.iteritems():
                fields[k] = self._inner_convert_old_schema(v, depth + 1)
            return Structure("anonymous_structure", fields=fields)
        else:
            if not isinstance(mapping, dict):
                raise TypeError("mapping %r must be a dict" % (mapping,))
            if not len(mapping) == 1:
                raise ValueError("Multiple different index names specified: %r"
                                 % (mapping.keys(),))
            item = mapping.values()[0]
            item = self._inner_convert_old_schema(item, depth + 1)
            name = item.name.split('.', 1)[0]
            return List(name=name, item=item, optional=item.optional)
