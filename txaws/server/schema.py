from datetime import datetime
from operator import itemgetter

from pytz import UTC

from zope.datetime import parse, SyntaxError


class SchemaError(Exception):
    """Raised when failing to extract or bundle L{Parameter}s."""

    def __init__(self, message, details=None):
        super(Schema, self).__init__(message)
        self.details = details


class MissingParameterError(SchemaError):
    """Raised when a parameter is missing.

    @param name: The name of the missing parameter.
    """

    def __init__(self, name):
        message = "The request must contain the parameter %s" % name
        super(MissingParameterError, self).__init__(
            400, "MissingParameter", message)
        self.parameter_name = name


class InvalidParameterValueError(SchemaError):
    """Raised when the value of a parameter is invalid.

    @param message: The error message to report.
    """

    def __init__(self, message):
        super(InvalidParameterValueError, self).__init__(
            400, "InvalidParameterValue", message)


class InvalidParameterCombinationError(SchemaError):
    """
    Raised when there is more than one parameter with the same name,
    when this isn't explicitly allowed for.

    @param name: The name of the missing parameter.
    """

    def __init__(self, name):
        message = "The parameter '%s' may only be specified once." % name
        super(InvalidParameterCombinationError, self).__init__(
            400, "InvalidParameterCombination", message)
        self.parameter_name = name


class UnknownParametersError(SchemaError):
    """Raised when the value of a parameter is invalid.

    @param name: The name of the parameter.
    """

    def __init__(self, details):
        message = "The parameter %s is not recognized" % details.keys()[0]
        super(UnknownParametersError, self).__init__(
            400, "UnknownParameter", message)
        self.details = details


class Parameter(object):
    """A single parameter in an HTTP request.

    @param template: A template for the key of the parameter, as specified
        in a request. For example, a single parameter would be specified
        simply as 'GroupName'.  If more than one group name was accepted,
        it would be specified as 'GroupName.n'.  A more complex example
        is 'IpPermissions.n.Groups.m.GroupName'.
    @param optional: If C{True} the parameter may not be present.
    @param default: A default value for the parameter, if not present.
    @param min: Minimum value for a parameter.
    @param max: Maximum value for a parameter.
    @param allow_none: Whether the parameter may be C{None}.
    """

    def __init__(self, template, optional=False, default=None,
                 min=None, max=None, allow_none=False):
        self.template = template
        self.optional = optional
        self.default = default
        self.min = min
        self.max = max
        self.allow_none = allow_none

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
                raise MissingParameterError(self.template)
            return self.default
        self._check_range(value)
        try:
            return self.parse(value)
        except ValueError:
            raise InvalidParameterValueError("Invalid %s value %s" %
                                             (self.kind, value))

    def _check_range(self, value):
        """Check that the given C{value} is in the expected range."""
        if self.min is None and self.max is None:
            return

        measure = self.measure(value)
        prefix = "Value (%s) for parameter %s is invalid.  %s"

        if self.min is not None and measure < self.min:
            message = prefix % (value, self.template,
                                self.lower_than_min_template % self.min)
            raise InvalidParameterValueError(message)

        if self.max is not None and measure > self.max:
            message = prefix % (value, self.template,
                                self.greater_than_max_template % self.max)
            raise InvalidParameterValueError(message)

    def expand(self, value):
        """Expand a single values to a full-fledged request argument.

        @values: A single value to expand.
        @return: The expanded value, always a L{str}.
        """
        if value is None:
            return ""
        else:
            return self.format(value)

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

    def parse(self, value):
        number = int(value)
        if number < 0:
            raise ValueError()
        return number

    def format(self, value):
        return str(value)


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

    def __init__(self, name, mapping, optional=False, default=None):
        super(Enum, self).__init__(name, optional=optional, default=default)
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
        try:
            return datetime(*parse(value, local=False)[:6], tzinfo=UTC)
        except (TypeError, SyntaxError):
            raise ValueError()

    def format(self, value):
        # Convert value to UTC.
        tt = value.utctimetuple()
        utc_value = datetime(
            tt.tm_year, tt.tm_mon, tt.tm_mday, tt.tm_hour, tt.tm_min,
            tt.tm_sec)
        return datetime.strftime(utc_value, "%Y-%m-%dT%H:%M:%SZ")


class Arguments(object):
    """Arguments parsed from a request."""

    def __init__(self, tree):
        """Initialize a new L{Arguments} instance.

        @param arguments: An iterable yielding C{(argument_name, value)}
        tuples.
        """
        for key, value in tree.iteritems():
            self.__dict__[key] = self._wrap(value)

    def __iter__(self):
        """Returns an iterator yielding C{(argument_name, value)} tuples."""
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
        else:
            return value


class Schema(object):
    """
    The schema that the arguments of an HTTP request must be compliant with.
    """

    def __init__(self, *parameters):
        """Initialize a new L{Schema} instance.

        Any number of L{Parameter} instances can be passed. The parameter path
        is used as the target in L{Schema.extract} and L{Schema.bundle}. For
        example::

          schema = Schema(Unicode('Name'))

        means that the result of L{Schema.extract} would have a C{Name}
        attribute. Similarly, L{Schema.bundle} would look for a C{Name}
        attribute.

        A more complex example::

          schema = Schema(Unicode('Name.#'))

        means that the result of L{Schema.extract} would have a C{Name}
        attribute, which would itself contain a list of names. Similarly,
        L{Schema.bundle} would look for a C{Name} attribute.
        """
        self._parameters = dict(
            (self._get_template(parameter.template), parameter)
            for parameter in parameters)

    def extract(self, params):
        """Extract parameters from a raw C{dict} according to this schema.

        @param params: The raw parameters to parse.

        @return: An L{Arguments} object holding the extracted arguments.
        """
        tree = {}
        unknown = {}

        # Extract from the given arguments and parse according to the
        # corresponding parameters.
        for key, value in params.iteritems():
            template = self._get_template(key)
            parameter = self._parameters.get(template)

            if template.endswith(".#") and parameter is None:
                # If we were unable to find a direct match for a template that
                # allows multiple values. Let's attempt to find it without the
                # multiple value marker which Amazon allows. For example if the
                # template is 'PublicIp', then a single key 'PublicIp.1' is
                # allowed.
                parameter = self._parameters.get(template[:-2])
                if parameter is not None:
                    key = key[:-2]

                # At this point, we have a template that doesn't have the .#
                # marker to indicate multiple values. We don't allow multiple
                # "single" values for the same element.
                if key in tree:
                    raise InvalidParameterCombinationError(key)

            if parameter is None:
                unknown[key] = value
            else:
                self._set_value(tree, key, parameter.coerce(value))

        # Ensure that the tree arguments are consistent with constraints
        # defined in the schema.
        for template, parameter in self._parameters.iteritems():
            try:
                self._ensure_tree(tree, parameter, *template.split("."))
            except MissingParameterError:
                raise MissingParameterError(parameter.template)

        if unknown:
            raise UnknownParametersError(unknown)

        return Arguments(tree)

    def bundle(self, *arguments, **extra):
        """Bundle the given arguments in a C{dict} with EC2-style format.

        @param arguments: Objects to bundle, L{Arguments} instances for
            example. Keys in later objects will override those in earlier
            objects.
        @param extra: Any number of additional parameters. These will override
            similarly named arguments in L{arguments}.
        """
        bundled = {}

        flattened = []
        for thing in arguments:
            self._flatten(flattened, thing)
        self._flatten(flattened, extra)

        for name, value in flattened:
            parameter = self._parameters.get(self._get_template(name))
            if parameter is None:
                raise RuntimeError("Parameter '%s' not in schema" % name)
            else:
                bundled[name] = parameter.expand(value)

        return bundled

    def _get_template(self, key):
        """Return the canonical template for a given parameter key.

        For example::

          'Child.1.Name.2'

        becomes::

          'Child.#.Name.#'

        """
        parts = key.split(".")
        for index, part in enumerate(parts[1::2]):
            parts[index * 2 + 1] = "#"
        return ".".join(parts)

    def _set_value(self, tree, key, value):
        """Set C{value} at C{key} in the given C{tree}.

        For example::

          tree = {}
          _set_value(tree, 'foo.1.bar.2', True)

        results in C{tree} becoming::

          {'foo': {1: {'bar': {2: True}}}}

        @param tree: A L{dict}.
        @param key: A L{str}.
        @param value: The value to set. Can be anything.
        """
        nodes = tuple((int(node) if node.isdigit() else node)
                      for node in key.split("."))
        for node in nodes[:-1]:
            tree = tree.setdefault(node, {})
        tree[nodes[-1]] = value

    def _ensure_tree(self, tree, parameter, node, *nodes):
        """Check that C{node} exists in C{tree} and is followed by C{nodes}.

        C{node} and C{nodes} should correspond to a template path (i.e. where
        there are no absolute indexes, but C{#} instead).
        """
        if node == "#":
            if len(nodes) == 0:
                if len(tree.keys()) == 0 and not parameter.optional:
                    raise MissingParameterError(node)
            else:
                for subtree in tree.itervalues():
                    self._ensure_tree(subtree, parameter, *nodes)
        else:
            if len(nodes) == 0:
                if node not in tree.keys():
                    # No value for this parameter is present, if it's not
                    # optional nor allow_none is set, the call below will
                    # raise a MissingParameterError
                    tree[node] = parameter.coerce(None)
            else:
                if node not in tree.keys():
                    tree[node] = {}
                self._ensure_tree(tree[node], parameter, *nodes)

    def _flatten(self, into, node, path=""):
        """
        For every element in L{node}, append a C{(path, value)} tuple to
        L{into}.

        @param into: A L{list} into which the tuples will be appended.
        @param node: A structure made up of L{Argument}s, L{list}s, L{dict}s
            and leaf values.
        """
        if isinstance(node, Arguments):
            for name, value in node.__dict__.iteritems():
                self._flatten(into, value, "%s.%s" % (path, name))
        elif isinstance(node, dict):
            for name, value in node.iteritems():
                self._flatten(into, value, "%s.%s" % (path, name))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                self._flatten(into, value, "%s.%d" % (path, index + 1))
        elif node is not None:
            into.append((path.lstrip("."), node))
        else:
            # None is discarded.
            pass
