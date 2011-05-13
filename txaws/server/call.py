class Call(object):
    """Hold information about a single API call initiated by an HTTP request.

    @param params: The raw parameters for the action to be executed, the
        format is a dictionary mapping parameter names to parameter
        values, like C{{'ParamName': param_value}}.
    @param user: The L{User} issuing this API L{Call}.
    @param action: The action to be performed.

    @ivar id: A unique identifier for the API call.
    @ivar principal: The L{Principal} of the L{User} performing the call.
    @ivar args: An L{Arguments} object holding parameters extracted from the
       raw parameters according to a L{Schema}.
    @ivar rest: Extra parameters not included in the given arguments schema,
       see L{parse}.
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
            version = txaws.version.ec2_api
        self.version = version
        self.principal = principal

    def parse(self, schema, strict=True):
        """Update our C{args} parsing values from the raw request arguments.

        @param schema: The L{Schema} the parameters must be extracted with.
        @param strict: If C{True} an error is raised if parameters not included
            in the schema are found, otherwise the extra parameters will be
            saved in the C{rest} attribute.
        """
        self.args, self.rest = schema.extract(self._raw_params, strict=strict)

    def get_raw_params(self):
        """Return a C{dict} holding the raw API call paramaters.

        The format of the dictionary is C{{'ParamName': param_value}}.
        """
        return self._raw_params.copy()
