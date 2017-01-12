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
    return _ListOf(validator)


@attr.s(frozen=True)
class _ListOf(object):
    """
    attrs validator for a list of elements which satisfy another
    validator.

    L{list_of} is the public constructor to hide the type and prevent
    subclassing.
    """
    validator = attr.ib()

    def __call__(self, inst, a, value):
        validators.instance_of(list)(inst, a, value)
        for n, element in enumerate(value):
            inner_identifier = u"{}[{}]".format(a.name, n)
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


