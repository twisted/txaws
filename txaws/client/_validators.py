# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
attrs validators for internal use.
"""

import attr
from attr import validators


def list_of(validator):
    """
    Require a value which is a list containing elements which the
    given validator accepts.
    """
    return _ContainerOf(list, validator)


def set_of(validator):
    """
    Require a value which is a set containing elements which the given
    validator accepts.
    """
    return _ContainerOf(set, validator)


@attr.s(frozen=True)
class _ContainerOf(object):
    """
    attrs validator for a container of objects which satisfy another
    validator.

    L{list_of}, L{set_of}, etc are the public constructors to hide the
    type and prevent subclassing.
    """
    container_type = attr.ib()
    validator = attr.ib()

    def __call__(self, inst, a, value):
        validators.instance_of(self.container_type)(inst, a, value)
        for n, element in enumerate(sorted(value)):
            inner_identifier = u"sorted({})[{}]".format(a.name, n)
            # Create an Attribute with a name that refers to the
            # validator we're using and the index we're validating.
            # Otherwise the validation failure is pretty confusing.
            inner_attr = attr.Attribute(
                name=inner_identifier,
                default=None,
                validator=self.validator,
                repr=False,
                cmp=False,
                hash=False,
                init=False,
            )
            self.validator(inst, inner_attr, element)
