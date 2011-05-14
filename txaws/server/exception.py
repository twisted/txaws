class APIError(Exception):
    """Raised while handling an API request.

    @param status: The HTTP status code the response will be set to.
    @param code: A machine-parsable textual code for the error.
    @param message: A human-readable description of the error.
    @param response: The full body of the response to be sent to the client,
        if C{None} it will be generated from C{code} and C{message}. See
        also L{API.dump_error}.
    """

    def __init__(self, status, code=None, message=None, response=None):
        super(APIError, self).__init__(message)
        self.status = int(status)
        self.code = code
        self.message = message
        self.response = response
        if self.response is None:
            if self.code is None or self.message is None:
                raise RuntimeError("If the response is not specified, code "
                                   "and status must both be set.")
        else:
            if self.code is not None or self.message is not None:
                raise RuntimeError("If the full response payload is passed, "
                                   "code and message must not be set.")
