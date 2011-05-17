from uuid import uuid4

from txaws.version import ec2_api as ec2_api_version
from txaws.server.exception import APIError


class Call(object):
    """Hold information about a single API call initiated by an HTTP request.

    @param raw_params: The raw parameters for the action to be executed, the
        format is a dictionary mapping parameter names to parameter values,
        like C{{'ParamName': param_value}}.
    @param principal: The principal issuing this API L{Call}.
    @param action: The action to be performed.

    @ivar id: A unique identifier for the API call.
    @ivar principal: The principal performing the call.
    @ivar args: An L{Arguments} object holding parameters extracted from the
       raw parameters according to a L{Schema}, it will be available after
       calling the C{parse} method.
    @ivar rest: Extra parameters not included in the given arguments schema,
       it will be available after calling the L{parse} method.
    @ivar version: The version of the API call. Defaults to 2008-12-01.
    """

    def __init__(self, raw_params=None, principal=None, action=None,
                 version=None, id=None):
        if id is None:
            id = str(uuid4())
        self.id = id
        self._raw_params = {}
        if raw_params is not None:
            self._raw_params.update(raw_params)
        self.action = action
        if version is None:
            version = ec2_api_version
        self.version = version
        self.principal = principal

    def parse(self, schema, strict=True):
        """Update C{args} and C{rest}, parsing the raw request arguments.

        @param schema: The L{Schema} the parameters must be extracted with.
        @param strict: If C{True} an error is raised if parameters not included
            in the schema are found, otherwise the extra parameters will be
            saved in the C{rest} attribute.
        """
        self.args, self.rest = schema.extract(self._raw_params)
        if strict and self.rest:
            raise APIError(400, "UnknownParameter",
                           "The parameter %s is not "
                           "recognized" % self.rest.keys()[0])

    def get_raw_params(self):
        """Return a C{dict} holding the raw API call paramaters.

        The format of the dictionary is C{{'ParamName': param_value}}.
        """
        return self._raw_params.copy()
